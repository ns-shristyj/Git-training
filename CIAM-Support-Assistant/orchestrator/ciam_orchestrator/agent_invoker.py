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
from datetime import datetime, timedelta, timezone
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

    # Matches a `datetime.datetime(...)` constructor-call repr in one shot,
    # including its optional `tzinfo=TzInfo(<offset_seconds>)` kwarg (pydantic
    # v2's own tzinfo class -- its repr for a UTC-aware datetime looks like
    # `tzinfo=TzInfo(0)`). Anchoring on the tzinfo= substructure explicitly
    # avoids the historical bug where a naive `[^)]*` on the datetime.datetime(
    # call stopped at TzInfo's inner closing paren instead of the outer one.
    _DATETIME_CALL_PATTERN = re.compile(
        r"datetime\.datetime\(\s*"
        r"(?P<args>-?\d+(?:\s*,\s*-?\d+)*)"
        r"(?:\s*,\s*tzinfo=TzInfo\(\s*(?P<offset>-?\d+)\s*\))?"
        r"\s*\)"
    )
    # Catch-all fallback for any datetime.datetime(...) call the specific
    # pattern above didn't match (unexpected/non-numeric args, an
    # unrecognized tzinfo class, etc.) -- handles one level of nested parens
    # so it can't leave an unbalanced call behind either. Real pydantic
    # datetime reprs never hit this path; it exists purely so one
    # unrecognized field degrades to None instead of failing the entire
    # payload parse (matching the old code's per-field fail-safe contract).
    _DATETIME_CALL_FALLBACK_PATTERN = re.compile(
        r"datetime\.datetime\([^()]*(?:\([^()]*\)[^()]*)*\)"
    )

    @classmethod
    def _replace_datetime_call(cls, match: "re.Match") -> str:
        """Converts one matched `datetime.datetime(...)` repr into a quoted
        ISO-8601 string literal, so it survives `ast.literal_eval` as real
        data instead of being discarded. Fails safe to the literal `None`
        (matching the old behavior) if the captured args don't form a valid
        datetime -- this must never raise and break the whole parse over one
        malformed timestamp."""
        try:
            parts = [int(p.strip()) for p in match.group("args").split(",")]
            dt = datetime(*parts)
            offset = match.group("offset")
            if offset is not None:
                dt = dt.replace(tzinfo=timezone(timedelta(seconds=int(offset))))
            return repr(dt.isoformat())
        except Exception:
            return "None"

    @staticmethod
    def _parse_agent_response(body_raw: bytes) -> dict:
        """Agent 1 returns a plain JSON object. Agent 2 (and future agents built
        the same way) return `AccountPayload.model_dump()`'s dict *repr* — i.e.
        a JSON string whose content is a Python dict literal containing
        `datetime.datetime(...)` constructor calls, which `json.loads` alone
        can't parse and plain `ast.literal_eval` rejects (it only handles
        literals, not calls).

        Every `datetime.datetime(...)` call is converted to a quoted
        ISO-8601 string literal (see _replace_datetime_call) rather than
        discarded to `None` -- an earlier version of this function nulled
        every timestamp on the theory that "no consumer here needs the
        timestamp itself", which held until Agent 4's sync-timing checks
        (comparing Auth0 last_login against Agent 2's account change
        history) started needing exactly that. Nulling was also never
        selective -- it destroyed timestamps for every field, on every
        agent's response, not just the ones nothing used. Consumers that
        still don't care about a given timestamp can simply ignore the
        (now-populated) string field, exactly as easily as they ignored
        None before.

        Uses regex + a controlled per-field conversion rather than
        eval()'ing untrusted-shaped agent output with the interpreter open."""
        try:
            parsed = json.loads(body_raw)
        except json.JSONDecodeError:
            return {"_raw": body_raw.decode(errors="replace")}

        if isinstance(parsed, dict):
            return parsed

        if isinstance(parsed, str):
            sanitized = AgentInvoker._DATETIME_CALL_PATTERN.sub(
                AgentInvoker._replace_datetime_call, parsed
            )
            sanitized = AgentInvoker._DATETIME_CALL_FALLBACK_PATTERN.sub("None", sanitized)
            try:
                return ast.literal_eval(sanitized)
            except Exception:
                return {"_raw": parsed}

        return {"_raw": body_raw.decode(errors="replace")}
