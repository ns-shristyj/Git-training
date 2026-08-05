"""Wraps a single Bedrock AgentCore agent-runtime invocation with timeout
handling and structured result capture.

This is a thin layer over boto3's `bedrock-agentcore` `invoke_agent_runtime`
call — the same API we've been calling manually via the AWS CLI throughout
testing, just wrapped for programmatic use inside the orchestrator.
"""

import ast
import json
import logging
import re
import time
from typing import Optional

import boto3
from botocore.exceptions import ClientError, ReadTimeoutError

from .config import ALLOWED_ORCHESTRATOR_ACTIONS, AWS_REGION
from .errors import PostureViolationError
from .schemas import AgentInvocationResult

logger = logging.getLogger("ciam-orchestrator")

_client = None


def _get_client():
    global _client
    if _client is None:
        # verify=False mirrors the --no-verify-ssl flag used throughout manual
        # CLI testing, required by the corporate proxy in this environment.
        _client = boto3.client("bedrock-agentcore", region_name=AWS_REGION, verify=False)
    return _client


def assert_posture(action: str) -> None:
    if action not in ALLOWED_ORCHESTRATOR_ACTIONS:
        raise PostureViolationError(
            f"Posture violation: '{action}' not permitted. "
            f"Allowed: {ALLOWED_ORCHESTRATOR_ACTIONS}"
        )


class AgentInvoker:
    """Invokes one Bedrock AgentCore agent runtime, with a timeout and
    structured success/timeout/error result — never raises for a failed
    agent call, so the orchestrator can keep going and escalate/warn instead.
    """

    def __init__(self, agent_arn: str, agent_name: str, timeout_sec: int = 30):
        self.agent_arn = agent_arn
        self.agent_name = agent_name
        self.timeout_sec = timeout_sec

    def invoke(self, payload: dict) -> AgentInvocationResult:
        if not self.agent_arn:
            return AgentInvocationResult(
                agent_name=self.agent_name,
                agent_arn="",
                status="skipped",
                error_message="No ARN configured for this agent (not yet deployed)",
            )

        assert_posture("bedrock-agentcore:InvokeAgentRuntime")

        start = time.time()
        try:
            client = _get_client()
            # boto3's `payload` is a raw bytes blob (unlike the AWS CLI, which
            # expects a base64 STRING on the command line and decodes it for you).
            raw_payload = json.dumps(payload).encode()

            response = client.invoke_agent_runtime(
                agentRuntimeArn=self.agent_arn,
                payload=raw_payload,
            )

            body_raw = response["response"].read()
            elapsed_ms = (time.time() - start) * 1000

            parsed = self._parse_agent_response(body_raw)

            logger.info(
                f"Invoked {self.agent_name} in {elapsed_ms:.0f}ms, status=success"
            )
            return AgentInvocationResult(
                agent_name=self.agent_name,
                agent_arn=self.agent_arn,
                status="success",
                response_time_ms=elapsed_ms,
                response_payload=parsed,
            )

        except (ClientError, ReadTimeoutError) as e:
            elapsed_ms = (time.time() - start) * 1000
            is_timeout = isinstance(e, ReadTimeoutError) or "Timeout" in type(e).__name__
            logger.warning(f"{self.agent_name} failed after {elapsed_ms:.0f}ms: {e}")
            return AgentInvocationResult(
                agent_name=self.agent_name,
                agent_arn=self.agent_arn,
                status="timeout" if is_timeout else "error",
                response_time_ms=elapsed_ms,
                error_message=str(e),
            )
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            logger.error(f"{self.agent_name} unexpected error: {type(e).__name__}: {e}")
            return AgentInvocationResult(
                agent_name=self.agent_name,
                agent_arn=self.agent_arn,
                status="error",
                response_time_ms=elapsed_ms,
                error_message=f"{type(e).__name__}: {e}",
            )

    @staticmethod
    def _parse_agent_response(body_raw: bytes) -> dict:
        """Agent 1 returns a plain JSON object. Agent 2 (and future agents built
        the same way) return `AccountPayload.model_dump()`'s dict *repr* — i.e.
        a JSON string whose content is a Python dict literal containing
        `datetime.datetime(...)` constructor calls, which `json.loads` alone
        can't parse and plain `ast.literal_eval` rejects (it only handles
        literals, not calls). Strip the datetime(...) calls out (they're not
        needed downstream -- every consumer here only reads specific fields,
        never the timestamp itself) and literal_eval the rest, rather than
        eval()'ing untrusted-shaped agent output with the interpreter open.

        Timezone-aware datetimes nest a `TzInfo(0)` call INSIDE the
        datetime.datetime(...) args (e.g. `datetime.datetime(2025, 1, 1,
        tzinfo=TzInfo(0))`) -- a naive `[^)]*` stops at TzInfo's closing
        paren, not the outer one, corrupting the string. Strip the inner
        TzInfo(...) call first so the outer datetime.datetime(...) match
        has no nested parens left to trip on."""
        try:
            parsed = json.loads(body_raw)
        except json.JSONDecodeError:
            return {"_raw": body_raw.decode(errors="replace")}

        if isinstance(parsed, dict):
            return parsed

        if isinstance(parsed, str):
            sanitized = re.sub(r"TzInfo\([^)]*\)", "None", parsed)
            sanitized = re.sub(r"datetime\.datetime\([^)]*\)", "None", sanitized)
            try:
                return ast.literal_eval(sanitized)
            except Exception:
                return {"_raw": parsed}

        return {"_raw": body_raw.decode(errors="replace")}
