"""
CIAM Intent Classifier — Agent 1
Spec:    SPEC-CIAM-0001
Version: 0.3.0

What this file does
-------------------
This is the entrypoint file that Amazon Bedrock AgentCore runs every time
a Jira TQI ticket arrives. It:

  1. Validates the incoming Jira webhook payload
  2. Calls Claude Haiku (the ONLY permitted external call) to classify intent
  3. Extracts the user email and portal hint
  4. Returns a RoutingEnvelope JSON to tell the orchestrator which
     downstream agents (2, 3, 4) to invoke

Security model
--------------
The agent may call ONLY bedrock:InvokeModel.
All other AWS services (DynamoDB, S3, SNS, Auth0, Jira writes, etc.)
are denied by the IAM execution role AND enforced in code via the
assert_posture() tripwire below.
"""

import json
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Literal, List, Any

import boto3
from botocore.exceptions import ClientError
from bedrock_agentcore import BedrockAgentCoreApp
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION  ── change these if needed
# ─────────────────────────────────────────────────────────────────────────────

# Bedrock model — cross-region inference profile (us. prefix).
# AWS automatically routes to the best available endpoint across
# us-east-1, us-east-2, us-west-2 for resilience.
MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# AWS region where Bedrock is available (match your AgentCore region)
AWS_REGION = "us-east-1"

# Classification confidence threshold (§6, step 6 of spec)
# Tickets below this confidence auto-escalate to L2
CONFIDENCE_THRESHOLD = 0.7


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ciam-intent-classifier")


# ─────────────────────────────────────────────────────────────────────────────
# POSTURE GUARD  (§4, §5 of SPEC-CIAM-0001)
#
# Defense-in-depth tripwire.  Every external call must pass assert_posture()
# before the SDK/HTTP call is issued.  Any call NOT in ALLOWED_ACTIONS raises
# PostureViolationError, which aborts the invocation and emits a CRITICAL
# posture-violation finding.
#
# The IAM execution role (in infra/aws/ciam-intent-classifier/) enforces
# the same deny at the AWS level.  Both layers must agree.
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_ACTIONS = frozenset({"bedrock:InvokeModel"})


class PostureViolationError(RuntimeError):
    """Raised before any denied API call is issued."""
    pass


def assert_posture(action: str) -> None:
    """
    Call this before every external API call.
    Raises PostureViolationError if action is not in the allow-list.
    """
    if action not in ALLOWED_ACTIONS:
        raise PostureViolationError(
            f"Posture violation: '{action}' is not permitted. "
            f"Permitted set: {ALLOWED_ACTIONS}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS  (§7 of SPEC-CIAM-0001)
# ─────────────────────────────────────────────────────────────────────────────

IntentType = Literal[
    "ACCESS_DENIED",
    "SSO_ERROR",
    "ACCOUNT_NOT_FOUND",
    "MFA_RESET",
    "ACCOUNT_CREATION",
    "BIRTHRIGHT_INQUIRY",
    "SYNC_ISSUE",
    "UNKNOWN",
]

PortalType = Literal[
    "Support", "Community", "Academy", "Partner",
    "Notification", "Dashboard", "Prime",
]


class RoutingEnvelope(BaseModel):
    """
    The output this agent returns to the orchestrator.
    Every field maps 1:1 to §7.1 of SPEC-CIAM-0001.
    """
    schema_version: Literal["1.0"] = "1.0"
    spec_id: Literal["SPEC-CIAM-0001"] = "SPEC-CIAM-0001"
    agent: Literal["ciam-intent-classifier"] = "ciam-intent-classifier"
    run_id: str
    classified_at: str               # UTC ISO-8601 string
    source: Literal["jira"] = "jira" # fixed in Phase 1 (§3.1)
    ticket_key: str
    raw_text_length: int             # character count, no PII
    intent: IntentType
    confidence: float                # 0.0 – 1.0
    extracted_email: Optional[str] = None
    extracted_portal: Optional[PortalType] = None
    invoke_agent_2: bool             # Database Agent
    invoke_agent_3: bool             # Auth0 Agent
    invoke_agent_4: bool             # Knowledge Base Agent
    auto_escalate: bool
    escalation_reason: Optional[str] = None
    routing_warnings: List[str] = []


class PostureViolationFinding(BaseModel):
    """Emitted when the posture tripwire fires (§7.2 of spec)."""
    schema_version: Literal["1.0"] = "1.0"
    spec_id: Literal["SPEC-CIAM-0001"] = "SPEC-CIAM-0001"
    agent: Literal["ciam-intent-classifier"] = "ciam-intent-classifier"
    run_id: str
    detected_at: str
    category: Literal["posture-violation"] = "posture-violation"
    severity: Literal["CRITICAL"] = "CRITICAL"
    evidence: dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING TABLE  (§6.1 of spec)
#
# Maps each intent to which sub-agents should be invoked.
# When auto_escalate=True, all flags are forced to False regardless.
# ─────────────────────────────────────────────────────────────────────────────

ROUTING_TABLE: dict[str, dict[str, bool]] = {
    "ACCESS_DENIED":      {"invoke_agent_2": True,  "invoke_agent_3": True,  "invoke_agent_4": True},
    "SSO_ERROR":          {"invoke_agent_2": False, "invoke_agent_3": True,  "invoke_agent_4": False},
    "ACCOUNT_NOT_FOUND":  {"invoke_agent_2": True,  "invoke_agent_3": True,  "invoke_agent_4": False},
    "MFA_RESET":          {"invoke_agent_2": False, "invoke_agent_3": False, "invoke_agent_4": False},
    "ACCOUNT_CREATION":   {"invoke_agent_2": True,  "invoke_agent_3": True,  "invoke_agent_4": False},
    "BIRTHRIGHT_INQUIRY": {"invoke_agent_2": True,  "invoke_agent_3": True,  "invoke_agent_4": True},
    "SYNC_ISSUE":         {"invoke_agent_2": True,  "invoke_agent_3": True,  "invoke_agent_4": True},
    "UNKNOWN":            {"invoke_agent_2": False, "invoke_agent_3": False, "invoke_agent_4": False},
}

NO_ROUTING = {"invoke_agent_2": False, "invoke_agent_3": False, "invoke_agent_4": False}

VALID_INTENTS = set(ROUTING_TABLE.keys())


# ─────────────────────────────────────────────────────────────────────────────
# PORTAL KEYWORD TABLE  (§6.2 of spec)
#
# Ordered most-specific → least-specific to prevent partial matches.
# e.g. "prime" must come before "partner" so "prime partner okta"
# maps to Prime, not Partner.
# ─────────────────────────────────────────────────────────────────────────────

PORTAL_KEYWORD_TABLE = [
    (["prime okta", "prime partner okta", "prime tenant", "prime"], "Prime"),
    (["support portal", "support access", "support"], "Support"),
    (["community"], "Community"),
    (["academy", "learning"], "Academy"),
    (["partner portal", "partner access", "partner"], "Partner"),
    (["notification center", "notification"], "Notification"),
    (["dashboard"], "Dashboard"),
]

VALID_PORTALS = {p for _, p in PORTAL_KEYWORD_TABLE}

# Email regex (used as deterministic fallback)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFICATION SYSTEM PROMPT
# Versioned at: prompts/ciam-intent-classifier/v1.md
#
# This prompt is the "reviewed, versioned source" mentioned in the AI Agent
# Operating Model.  Changes here must bump the version in that file too.
# ─────────────────────────────────────────────────────────────────────────────

CLASSIFICATION_SYSTEM_PROMPT = """\
You are a CIAM (Customer Identity and Access Management) support ticket classifier
for Netskope. Your only job is to classify Jira TQI tickets into ONE intent
category and extract key entities.

=== THE 8 INTENT CATEGORIES ===

1. ACCESS_DENIED
   User cannot access a Netskope portal (Support, Community, Academy, Dashboard, etc.)
   Examples: "getting access denied", "403 error on portal", "can't open support site"

2. SSO_ERROR
   SSO or SAML error, redirect loop, or login failure via enterprise SSO / Okta
   Examples: "SSO redirect loop", "SAML assertion failed", "can't log in via Okta"

3. ACCOUNT_NOT_FOUND
   User does not exist in Auth0 or the Salesforce-backed customer database
   Examples: "user not found", "no account for this email", "can't find user record"

4. MFA_RESET
   MFA reset, 2FA reset, lost authenticator app, or password reset request
   Examples: "MFA reset", "lost authenticator", "reset 2FA", "password reset"

5. ACCOUNT_CREATION
   Request to create a brand new portal account for a user
   Examples: "create account", "new user needs portal access", "onboard this user"

6. BIRTHRIGHT_INQUIRY
   Question about what access a user SHOULD have based on their account type
   Examples: "what portals should they have?", "check birthright", "expected entitlements"

7. SYNC_ISSUE
   Birthright sync has not run, is stale, or entitlements are not being populated
   Examples: "sync not running", "stale entitlements", "birthright not updated", "sync failed"

8. UNKNOWN
   Cannot classify with confidence, or insufficient context

=== YOUR OUTPUT ===

Return a JSON object with EXACTLY these four fields.
Return ONLY the JSON — no markdown, no explanation, no preamble, no ```json:

{
  "intent": "<one of the 8 categories above>",
  "confidence": <float 0.0 to 1.0>,
  "extracted_email": "<first email address found in the ticket, or null>",
  "extracted_portal": "<Support|Community|Academy|Partner|Notification|Dashboard|Prime, or null>"
}

=== RULES ===

- Choose the SINGLE best intent. Never list multiple.
- For extracted_email: extract the FIRST email address you see. If none, return null.
- For extracted_portal: use these canonical names only:
    "prime okta" / "prime tenant" / "prime partner" → "Prime"
    "support portal" / "support access"             → "Support"
    "community"                                     → "Community"
    "academy" / "learning"                          → "Academy"
    "partner portal" / "partner access"             → "Partner"
    "notification center" / "notification"          → "Notification"
    "dashboard"                                     → "Dashboard"
    If no portal mentioned → null
- Be conservative with confidence. Use < 0.7 if the ticket is vague or ambiguous.
- temperature is 0 so your output must be deterministic for identical inputs.
"""


# ─────────────────────────────────────────────────────────────────────────────
# BEDROCK CLIENT  (the ONLY permitted external call in this agent)
# ─────────────────────────────────────────────────────────────────────────────

_bedrock_client = None   # lazy singleton — avoids re-creating on every warm invocation


def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    return _bedrock_client


def invoke_bedrock_classifier(text: str) -> dict:
    """
    Call Claude Haiku via Bedrock to classify the ticket text.

    This is the ONLY external call this agent makes.
    assert_posture() fires first — if something modified ALLOWED_ACTIONS
    to exclude this call, the posture tripwire catches it here.
    """
    assert_posture("bedrock:InvokeModel")    # posture tripwire

    client = get_bedrock_client()

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 256,
        "system": CLASSIFICATION_SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": f"Classify this Jira TQI ticket:\n\n{text[:4000]}",
                # Truncate to stay within model context; 4000 chars covers
                # the vast majority of real Jira ticket descriptions.
            }
        ],
        "temperature": 0.0,   # deterministic (AC-12 requirement)
    }

    try:
        response = client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )
        response_body = json.loads(response["body"].read())
        raw_text = response_body["content"][0]["text"].strip()
        logger.debug(f"Bedrock raw response: {raw_text}")
        
        # Strip markdown code blocks if present
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)
            raw_text = raw_text.strip()
        
        # Fallback: extract JSON if wrapped in other text
        if not raw_text.startswith("{"):
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(0)
        
        return json.loads(raw_text)

    except ClientError as e:
        logger.error(f"Bedrock ClientError: {e.response['Error']['Code']} — {e.response['Error']['Message']}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Model returned non-JSON output: {e}")
        raise ValueError(f"Model returned non-parseable JSON: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_emails(text: str) -> list[str]:
    return EMAIL_RE.findall(text)


def extract_portals_from_text(text: str) -> list[str]:
    """Return all distinct portal canonical names mentioned in text."""
    text_lower = text.lower()
    found: list[str] = []
    for keywords, canonical in PORTAL_KEYWORD_TABLE:
        for kw in keywords:
            if kw in text_lower:
                if canonical not in found:
                    found.append(canonical)
                break
    return found


def _build_error_envelope(
    run_id: str,
    ticket_key: str,
    raw_text_length: int,
    reason: str,
    routing_warnings: list[str],
) -> dict:
    """Convenience wrapper: build an auto-escalate RoutingEnvelope for error cases."""
    envelope = RoutingEnvelope(
        run_id=run_id,
        classified_at=now_utc_iso(),
        ticket_key=ticket_key or "UNKNOWN",
        raw_text_length=raw_text_length,
        intent="UNKNOWN",
        confidence=0.0,
        **NO_ROUTING,
        auto_escalate=True,
        escalation_reason=reason,
        routing_warnings=routing_warnings,
    )
    return envelope.model_dump()


def _build_posture_finding(run_id: str, attempted_action: str) -> dict:
    finding = PostureViolationFinding(
        run_id=run_id,
        detected_at=now_utc_iso(),
        evidence={"attempted_call": attempted_action},
    )
    return finding.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AGENTCORE ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────

app = BedrockAgentCoreApp()


@app.entrypoint
def classify_ticket(payload: dict) -> dict:
    """
    AgentCore calls this function for every incoming request.

    Expected payload (assembled by the Jira webhook adapter):
    {
        "issue_key":   "TQI-4321",                  # required
        "summary":     "User cannot access portal", # required if description missing
        "description": "john@example.com getting Access Denied on support.netskope.com"
    }

    Returns: a RoutingEnvelope dict  (or a posture-violation finding dict on error)
    """
    run_id = str(uuid.uuid4())
    routing_warnings: list[str] = []

    logger.info(f"[{run_id}] Agent 1 invoked. Keys received: {list(payload.keys())}")

    # ── Step 1: Validate input ────────────────────────────────────────────────
    # §6 step 1: Confirm non-empty text and issue.key
    issue_key = (payload.get("issue_key") or payload.get("ticket_key", "")).strip()
    summary = payload.get("summary", "").strip()
    description = payload.get("description", "").strip()

    if not issue_key or not (summary or description):
        logger.warning(f"[{run_id}] Malformed input — missing issue_key or text body.")
        return _build_error_envelope(run_id, issue_key, 0, "malformed_input", [])

    # ── Step 2: Build classification text ─────────────────────────────────────
    # §6 step 1 (OQ-5): concatenate summary + description
    text = f"{summary}\n\n{description}".strip()
    raw_text_length = len(text)

    # ── Step 3: Classify via Bedrock ──────────────────────────────────────────
    # §6 step 3: invoke bedrock:InvokeModel (ONLY permitted external call)
    intent: IntentType = "UNKNOWN"
    confidence: float = 0.0
    model_email: Optional[str] = None
    model_portal: Optional[str] = None

    try:
        classification = invoke_bedrock_classifier(text)

        raw_intent = classification.get("intent", "UNKNOWN")
        intent = raw_intent if raw_intent in VALID_INTENTS else "UNKNOWN"
        if raw_intent not in VALID_INTENTS:
            logger.warning(f"[{run_id}] Model returned unknown intent '{raw_intent}' → UNKNOWN")

        raw_conf = classification.get("confidence", 0.0)
        confidence = float(max(0.0, min(1.0, raw_conf)))   # clamp to [0,1]

        model_email = classification.get("extracted_email")
        model_portal_raw = classification.get("extracted_portal")
        model_portal = model_portal_raw if model_portal_raw in VALID_PORTALS else None

    except PostureViolationError as e:
        # §6 step (posture): abort immediately, return finding
        logger.critical(f"[{run_id}] POSTURE VIOLATION: {e}")
        return {
            "error": "posture_violation",
            "finding": _build_posture_finding(run_id, str(e)),
        }
    except Exception as e:
        # §8: model inference timeout / error → escalate
        logger.error(f"[{run_id}] Model inference error: {type(e).__name__}: {e}")
        return _build_error_envelope(run_id, issue_key, raw_text_length,
                                     "model_inference_error", routing_warnings)

    # ── Step 4: Validate classification output ────────────────────────────────
    # §6 step 4: if output cannot be parsed as ClassificationResult → model_parse_error
    if intent not in VALID_INTENTS:
        return _build_error_envelope(run_id, issue_key, raw_text_length,
                                     "model_parse_error", routing_warnings)

    # ── Step 5: Email extraction ───────────────────────────────────────────────
    # §6 step 5: first email wins; multiple emails → routing_warning
    regex_emails = extract_emails(text)
    if len(regex_emails) > 1:
        routing_warnings.append("multiple_emails_found")

    # Prefer model's extraction; fall back to first regex match
    extracted_email = model_email or (regex_emails[0] if regex_emails else None)

    if not extracted_email:
        logger.warning(f"[{run_id}] No email found → forcing UNKNOWN + no_email_found")
        return RoutingEnvelope(
            run_id=run_id,
            classified_at=now_utc_iso(),
            ticket_key=issue_key,
            raw_text_length=raw_text_length,
            intent="UNKNOWN",
            confidence=confidence,
            extracted_email=None,
            extracted_portal=model_portal,
            **NO_ROUTING,
            auto_escalate=True,
            escalation_reason="no_email_found",
            routing_warnings=routing_warnings,
        ).model_dump()

    # ── Step 6: Confidence threshold ──────────────────────────────────────────
    # §6 step 6: confidence < CONFIDENCE_THRESHOLD → auto_escalate
    auto_escalate = False
    escalation_reason: Optional[str] = None

    if confidence < CONFIDENCE_THRESHOLD:
        auto_escalate = True
        escalation_reason = "low_confidence"

    # ── Step 7: MFA / UNKNOWN always escalate ─────────────────────────────────
    # §6 step 7: MFA_RESET and UNKNOWN are always escalated
    if intent in ("MFA_RESET", "UNKNOWN"):
        auto_escalate = True
        escalation_reason = escalation_reason or intent.lower()

    # ── Portal extraction (deterministic fallback + multi-portal detection) ───
    # §6.2: first match wins; multiple portals → routing_warning
    portals_found = extract_portals_from_text(text)
    if len(portals_found) > 1:
        routing_warnings.append("multiple_portals_found")

    # Use model portal if valid, else first regex portal
    extracted_portal = model_portal or (portals_found[0] if portals_found else None)

    # ── Step 8: Routing flags ──────────────────────────────────────────────────
    # §6 step 8: all flags False when auto_escalate=True
    routing_flags = NO_ROUTING if auto_escalate else ROUTING_TABLE.get(intent, NO_ROUTING)

    # ── Step 9: Build and return RoutingEnvelope ───────────────────────────────
    envelope = RoutingEnvelope(
        run_id=run_id,
        classified_at=now_utc_iso(),
        ticket_key=issue_key,
        raw_text_length=raw_text_length,
        intent=intent,
        confidence=confidence,
        extracted_email=extracted_email,
        extracted_portal=extracted_portal,
        **routing_flags,
        auto_escalate=auto_escalate,
        escalation_reason=escalation_reason,
        routing_warnings=routing_warnings,
    )

    logger.info(
        f"[{run_id}] Done. intent={intent} confidence={confidence:.2f} "
        f"email={extracted_email} portal={extracted_portal} "
        f"auto_escalate={auto_escalate} escalation_reason={escalation_reason}"
    )
    return envelope.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# LOCAL DEVELOPMENT ENTRYPOINT
# Run `python agent.py` to start a local HTTP server on port 8080 for testing.
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run()
