"""
CIAM Knowledge Base Agent — Agent 4
Spec:    SPEC-CIAM-0004
Version: 0.3.0

What this file does
-------------------
Entrypoint Amazon Bedrock AgentCore runs when the orchestrator invokes
Agent 4. It:

  1. Applies the Birthright & Entitlements Guide rules as pure local logic
     (Tool 1: evaluate_birthright) to compute expected vs. actual access
  2. Classifies the fix complexity as a deterministic decision tree
     (Tool 3: classify_fix_complexity)
  3. Queries the Bedrock Knowledge Base for relevant SOPs and similar past
     tickets (Tool 2: query_knowledge_base) -- non-fatal on failure
  4. [PLACEHOLDER] Attempts to map the failure to a specific Auth0 workflow
     script (Tool 4: identify_failing_workflow) -- always a stub until real
     Auth0 Action/Rule/Flow scripts are supplied (see spec OQ-8)

Security model
--------------
Tools 1, 3, and 4 are pure local functions -- zero network calls, zero IAM
permissions required. Tool 2 is the only external call: bedrock:Retrieve /
bedrock:RetrieveAndGenerate, scoped to the CIAM Knowledge Base ARN only.
No DynamoDB, no Auth0, no Secrets Manager, no writes of any kind.
"""

import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, List

import boto3
from botocore.exceptions import ClientError
from bedrock_agentcore import BedrockAgentCoreApp
from pydantic import BaseModel

# Configuration
AWS_REGION = "us-east-1"
KNOWLEDGE_BASE_ID = "PLACEHOLDER_KB_ID"  # set once the real KB is provisioned (see OQ-1)
DEFAULT_TOP_K = 3
MAX_TOP_K = 10
BEDROCK_TIMEOUT_SECONDS = 10
MAX_RETRIES = 3

KNOWN_PORTAL_KEYWORDS = frozenset({"Support", "Community", "Academy", "Notification", "Dashboard"})

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ciam-knowledge-base-agent")

# Posture Guard: Tools 1, 3, 4 are pure local logic (no IAM needed). Tool 2
# is the only external call.
ALLOWED_ACTIONS = frozenset({"bedrock:Retrieve", "bedrock:RetrieveAndGenerate"})
ALLOWED_TOOL_NAMES = frozenset({
    "evaluate_birthright", "query_knowledge_base",
    "classify_fix_complexity", "identify_failing_workflow",
})


class PostureViolationError(RuntimeError):
    pass


def assert_posture(action: str) -> None:
    if action not in ALLOWED_ACTIONS:
        raise PostureViolationError(
            f"Posture violation: '{action}' not permitted. Allowed: {ALLOWED_ACTIONS}"
        )


def assert_tool_posture(tool_name: str) -> None:
    if tool_name not in ALLOWED_TOOL_NAMES:
        raise PostureViolationError(
            f"Posture violation: tool '{tool_name}' not permitted. Allowed: {ALLOWED_TOOL_NAMES}"
        )


# Schemas (§7.1)
class BirthrightEvaluation(BaseModel):
    match: bool
    persona: str
    expected_birthright: List[str]
    actual_birthright: List[str]
    entitlements: List[str]
    missing_keywords: List[str]
    extra_keywords: List[str]
    entitlements_compensate: bool
    explicit_block_detected: bool
    block_keywords_found: List[str]
    no_access_configured: bool
    birthright_correct_but_access_denied: bool
    sync_never_ran: bool
    sync_stale: bool


class FixClassification(BaseModel):
    complexity: Literal["SIMPLE_FIX", "ESCALATE_TO_L2", "NO_GAP"]
    reason: str
    recommended_actions: List[str]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]


class WorkflowIdentification(BaseModel):
    """PLACEHOLDER schema -- see Tool 4. Always returns stub values until
    real Auth0 Action/Rule/Flow scripts are supplied (OQ-8)."""
    workflow_identified: bool = False
    workflow_name: Optional[str] = None
    workflow_script_ref: Optional[str] = None
    note: str = "Auth0 workflow scripts not yet provided -- placeholder only"


class KBDocument(BaseModel):
    title: str
    url: Optional[str] = None
    excerpt: str
    relevance_score: float


class KBTicket(BaseModel):
    ticket_key: str
    summary: str
    resolution: Optional[str] = None
    relevance_score: float


class KnowledgeBaseResults(BaseModel):
    relevant_docs: List[KBDocument] = []
    similar_past_tickets: List[KBTicket] = []


class KnowledgeBasePayload(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    spec_id: Literal["SPEC-CIAM-0004"] = "SPEC-CIAM-0004"
    agent: Literal["ciam-knowledge-base-agent"] = "ciam-knowledge-base-agent"
    run_id: str
    evaluated_at: datetime

    birthright_evaluation: Optional[BirthrightEvaluation] = None
    fix_classification: Optional[FixClassification] = None
    workflow_identification: Optional[WorkflowIdentification] = None

    knowledge_base_results: KnowledgeBaseResults = KnowledgeBaseResults()
    knowledge_base_error: Optional[str] = None

    error: Optional[str] = None


# Tool 1 — evaluate_birthright (§4.1)
def derive_persona(account_status: Optional[str], active_tenant_count: Optional[int]) -> tuple:
    """Persona/expected-birthright table -- PROVISIONAL, see spec §1/OQ-6/OQ-7."""
    if account_status == "Customer":
        return "Customer", ["Support", "Community", "Academy", "Notification", "Dashboard"]
    if account_status == "Prospect - Net New":
        if (active_tenant_count or 0) >= 1:
            return "Prospect with Tenant", ["Support", "Community", "Academy", "Notification", "Dashboard"]
        return "Prospect without Tenant", ["Community", "Academy", "Dashboard"]
    if account_status == "Partner":
        return "Partner", ["Community", "Academy", "Dashboard"]
    if account_status == "Former Customer":
        return "Former Customer", ["Community", "Academy", "Dashboard"]
    return "UNKNOWN", []


def evaluate_birthright(
    account_status: Optional[str],
    active_tenant_count: Optional[int],
    actual_birthright: List[str],
    entitlements: List[str],
) -> BirthrightEvaluation:
    """Tool 1 -- pure local logic, zero external calls (§4.1)."""
    assert_tool_posture("evaluate_birthright")

    persona, expected_birthright = derive_persona(account_status, active_tenant_count)

    # Block keyword detection (pre-check, §4.1)
    block_keywords_found = [
        e for e in entitlements
        if e.startswith("block_") and e[len("block_"):] in KNOWN_PORTAL_KEYWORDS
    ]
    explicit_block_detected = len(block_keywords_found) > 0
    blocked_portals = {b[len("block_"):] for b in block_keywords_found}

    # Union semantics (§6.2), then block keywords override the grant
    effective_access = (set(actual_birthright) | set(entitlements)) - blocked_portals

    missing_keywords = sorted(set(expected_birthright) - effective_access)
    extra_keywords = sorted(set(actual_birthright) - set(expected_birthright))
    match = len(missing_keywords) == 0 and len(extra_keywords) == 0

    missing_from_birthright_alone = set(expected_birthright) - set(actual_birthright)
    entitlements_compensate = (
        len(missing_from_birthright_alone) > 0 and len(missing_keywords) == 0
    )

    no_access_configured = len(actual_birthright) == 0 and len(entitlements) == 0

    return BirthrightEvaluation(
        match=match,
        persona=persona,
        expected_birthright=expected_birthright,
        actual_birthright=actual_birthright,
        entitlements=entitlements,
        missing_keywords=missing_keywords,
        extra_keywords=extra_keywords,
        entitlements_compensate=entitlements_compensate,
        explicit_block_detected=explicit_block_detected,
        block_keywords_found=block_keywords_found,
        no_access_configured=no_access_configured,
        birthright_correct_but_access_denied=False,  # set by caller (§6 step 3)
        sync_never_ran=False,  # set by caller (§6 step 2)
        sync_stale=False,  # set by caller (§6 step 2)
    )


# Tool 3 — classify_fix_complexity (§4.1)
def classify_fix_complexity(
    missing_keywords: List[str],
    extra_keywords: List[str],
    account_status: Optional[str],
    active_tenant_count: Optional[int],
    user_found_in_auth0: bool,
    explicit_block_detected: bool,
    intent: Optional[str],
    birthright_correct_but_access_denied: bool,
) -> FixClassification:
    """Tool 3 -- pure local logic, zero external calls (§4.1)."""
    assert_tool_posture("classify_fix_complexity")

    # ESCALATE_TO_L2 triggers -- any single condition (checked first, per spec priority)
    if extra_keywords:
        return FixClassification(
            complexity="ESCALATE_TO_L2",
            reason="User has more access than entitled (over-provisioned) -- security risk, must not auto-remediate.",
            recommended_actions=[
                "Review over-provisioned keywords",
                "Do not modify entitlements without L2 approval",
                "Escalate to L2 with birthright evaluation attached",
            ],
            confidence="HIGH",
        )

    if explicit_block_detected:
        return FixClassification(
            complexity="ESCALATE_TO_L2",
            reason="Explicit block keyword found in entitlements -- security-sensitive, requires L2 review.",
            recommended_actions=[
                "Identify who added block keyword and why",
                "Escalate to L2 for block keyword review",
            ],
            confidence="HIGH",
        )

    if account_status is None or account_status == "UNKNOWN":
        return FixClassification(
            complexity="ESCALATE_TO_L2",
            reason="account_status_unknown -- cannot safely determine correct entitlement without confirmed account data.",
            recommended_actions=[
                "Gather additional context",
                "Escalate to L2 with full KnowledgeBasePayload attached",
            ],
            confidence="LOW",
        )

    if not user_found_in_auth0:
        return FixClassification(
            complexity="ESCALATE_TO_L2",
            reason="Provisioning issue -- entitlement add is insufficient; user needs to be created in Auth0.",
            recommended_actions=[
                "Create user in Auth0 per SOP: User Creation in Auth0",
                "Escalate to L2 for provisioning",
            ],
            confidence="HIGH",
        )

    if intent == "SSO_ERROR":
        return FixClassification(
            complexity="ESCALATE_TO_L2",
            reason="Requires Auth0 Connection or federation config review -- out of agent scope.",
            recommended_actions=[
                "Gather additional context",
                "Escalate to L2 with full KnowledgeBasePayload attached",
            ],
            confidence="MEDIUM",
        )

    if any(k not in KNOWN_PORTAL_KEYWORDS for k in missing_keywords):
        return FixClassification(
            complexity="ESCALATE_TO_L2",
            reason="missing_keywords contains an unrecognized value -- requires human review.",
            recommended_actions=[
                "Gather additional context",
                "Escalate to L2 with full KnowledgeBasePayload attached",
            ],
            confidence="LOW",
        )

    if birthright_correct_but_access_denied:
        return FixClassification(
            complexity="ESCALATE_TO_L2",
            reason="Mismatch between Auth0 data and Gatekeeper behaviour -- likely Auth0 Action code issue.",
            recommended_actions=[
                "Gather additional context",
                "Escalate to L2 with full KnowledgeBasePayload attached",
            ],
            confidence="MEDIUM",
        )

    # No gap: nothing missing, nothing extra
    if not missing_keywords:
        return FixClassification(
            complexity="NO_GAP",
            reason="no_gap_detected",
            recommended_actions=["No action needed -- access matches expected birthright"],
            confidence="HIGH",
        )

    # SIMPLE_FIX -- all criteria met (§4.1 Tool 3)
    account_ok = account_status == "Customer" or (
        account_status == "Prospect - Net New" and (active_tenant_count or 0) >= 1
    )
    if account_ok:
        return FixClassification(
            complexity="SIMPLE_FIX",
            reason="Missing entitlements can be safely added; no over-provisioning or provisioning issues detected.",
            recommended_actions=[
                f"Add {missing_keywords} to entitlements array via Auth0 Management API",
                "Verify access after update",
                "Monitor next sync to confirm birthright recalculation does not remove entitlement",
            ],
            confidence="HIGH",
        )

    # Fallback: account status doesn't clearly support auto-remediation
    return FixClassification(
        complexity="ESCALATE_TO_L2",
        reason="account_status does not meet SIMPLE_FIX criteria (not Customer or Prospect with tenant).",
        recommended_actions=[
            "Gather additional context",
            "Escalate to L2 with full KnowledgeBasePayload attached",
        ],
        confidence="MEDIUM",
    )


# Tool 4 — identify_failing_workflow (PLACEHOLDER, §4.1 Tool 4, OQ-8)
def identify_failing_workflow(failed_step: Optional[str]) -> WorkflowIdentification:
    """PLACEHOLDER -- not yet implemented. Always returns the stub result
    until real Auth0 Action/Rule/Flow scripts for the nskp tenant are
    supplied (see spec OQ-8). Never blocks or fails."""
    assert_tool_posture("identify_failing_workflow")
    return WorkflowIdentification()


# Tool 2 — query_knowledge_base (§4.1)
_bedrock_agent_runtime_client = None


def get_bedrock_agent_runtime_client():
    global _bedrock_agent_runtime_client
    if _bedrock_agent_runtime_client is None:
        _bedrock_agent_runtime_client = boto3.client(
            "bedrock-agent-runtime", region_name=AWS_REGION
        )
    return _bedrock_agent_runtime_client


def query_knowledge_base(query: str, top_k: int = DEFAULT_TOP_K) -> tuple:
    """Tool 2 -- calls Bedrock Knowledge Base RetrieveAndGenerate (§4.1).
    Returns (KnowledgeBaseResults, error)."""
    assert_tool_posture("query_knowledge_base")
    assert_posture("bedrock:RetrieveAndGenerate")

    top_k = min(top_k, MAX_TOP_K)
    client = get_bedrock_agent_runtime_client()

    attempt = 0
    while True:
        attempt += 1
        try:
            response = client.retrieve_and_generate(
                input={"text": query},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": KNOWLEDGE_BASE_ID,
                        "modelArn": "anthropic.claude-haiku-4-5-20251001-v1:0",
                        "retrievalConfiguration": {
                            "vectorSearchConfiguration": {"numberOfResults": top_k}
                        },
                    },
                },
            )
            break
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ThrottlingException" and attempt < MAX_RETRIES:
                time.sleep(2 ** (attempt - 1))
                continue
            if error_code == "ThrottlingException":
                return KnowledgeBaseResults(), "bedrock_throttled"
            return KnowledgeBaseResults(), "bedrock_error"
        except Exception:
            return KnowledgeBaseResults(), "bedrock_timeout"

    relevant_docs = []
    similar_past_tickets = []
    for citation in response.get("citations", []):
        for ref in citation.get("retrievedReferences", []):
            content = ref.get("content", {}).get("text", "")[:500]
            metadata = ref.get("metadata", {})
            source_type = metadata.get("source_type", "")
            location = ref.get("location", {})
            score = ref.get("score", 0.0)

            if source_type == "tqi_ticket":
                similar_past_tickets.append(KBTicket(
                    ticket_key=metadata.get("ticket_key", "UNKNOWN"),
                    summary=metadata.get("summary", content),
                    resolution=metadata.get("resolution"),
                    relevance_score=score,
                ))
            else:
                relevant_docs.append(KBDocument(
                    title=metadata.get("title", "Untitled"),
                    url=location.get("s3Location", {}).get("uri"),
                    excerpt=content,
                    relevance_score=score,
                ))

    return KnowledgeBaseResults(relevant_docs=relevant_docs, similar_past_tickets=similar_past_tickets), None


def build_kb_query(intent, persona, missing_keywords, extra_keywords, raw_input) -> str:
    """§6.3 -- deterministic query construction."""
    missing_csv = ",".join(missing_keywords) if missing_keywords else ""
    extra_csv = ",".join(extra_keywords) if extra_keywords else ""
    truncated_input = (raw_input or "")[:500]
    return f"{intent} {persona} missing:{missing_csv} extra:{extra_csv} {truncated_input}"


# Helpers
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def derive_sync_flags(last_sync) -> tuple:
    """§6 step 2."""
    if not last_sync:
        return True, False
    if isinstance(last_sync, str):
        last_sync = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
    if (now_utc() - last_sync) > timedelta(days=7):
        return False, True
    return False, False


# Main
app = BedrockAgentCoreApp()


@app.entrypoint
def evaluate_ciam_case(payload: dict) -> dict:
    run_id = str(uuid.uuid4())
    evaluated_at = now_utc()

    logger.info(f"[{run_id}] Agent 4 invoked. Keys: {list(payload.keys())}")

    # Step 1: validate inputs
    actual_birthright = payload.get("actual_birthright")
    entitlements = payload.get("entitlements")
    user_found_in_auth0 = payload.get("user_found_in_auth0")
    intent = payload.get("intent")

    if not isinstance(actual_birthright, list) or not isinstance(entitlements, list) \
            or not isinstance(user_found_in_auth0, bool) or not isinstance(intent, str):
        logger.warning(f"[{run_id}] Invalid input")
        return KnowledgeBasePayload(
            run_id=run_id,
            evaluated_at=evaluated_at,
            error="invalid_input",
        ).model_dump()

    account_status = payload.get("account_status")
    active_tenant_count = payload.get("active_tenant_count")
    last_sync = payload.get("last_sync")
    raw_input = payload.get("raw_input", "")

    # Step 2: derive sync flags
    sync_never_ran, sync_stale = derive_sync_flags(last_sync)

    # Step 3: evaluate birthright (Tool 1) -- always called
    evaluation = evaluate_birthright(account_status, active_tenant_count, actual_birthright, entitlements)
    evaluation.sync_never_ran = sync_never_ran
    evaluation.sync_stale = sync_stale

    birthright_correct_but_access_denied = evaluation.match and intent == "ACCESS_DENIED"
    evaluation.birthright_correct_but_access_denied = birthright_correct_but_access_denied

    # Step 4: classify fix complexity (Tool 3) -- always called
    classification = classify_fix_complexity(
        missing_keywords=evaluation.missing_keywords,
        extra_keywords=evaluation.extra_keywords,
        account_status=account_status,
        active_tenant_count=active_tenant_count,
        user_found_in_auth0=user_found_in_auth0,
        explicit_block_detected=evaluation.explicit_block_detected,
        intent=intent,
        birthright_correct_but_access_denied=birthright_correct_but_access_denied,
    )

    # Step 5: query Knowledge Base (Tool 2) -- always attempted, non-fatal
    query = build_kb_query(intent, evaluation.persona, evaluation.missing_keywords, evaluation.extra_keywords, raw_input)
    kb_results, kb_error = query_knowledge_base(query, top_k=payload.get("top_k", DEFAULT_TOP_K))

    # Step 6: identify failing workflow (Tool 4 -- placeholder) -- always called, never fails
    failed_step = (
        "explicit_block_detected" if evaluation.explicit_block_detected
        else (evaluation.missing_keywords[0] if evaluation.missing_keywords else None)
    )
    workflow_id = identify_failing_workflow(failed_step)

    logger.info(f"[{run_id}] Done. persona={evaluation.persona} complexity={classification.complexity}")

    return KnowledgeBasePayload(
        run_id=run_id,
        evaluated_at=evaluated_at,
        birthright_evaluation=evaluation,
        fix_classification=classification,
        workflow_identification=workflow_id,
        knowledge_base_results=kb_results,
        knowledge_base_error=kb_error,
        error=None,
    ).model_dump()


if __name__ == "__main__":
    app.run()
