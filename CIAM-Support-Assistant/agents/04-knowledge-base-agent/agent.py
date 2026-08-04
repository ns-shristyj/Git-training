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

import json
import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, List

import boto3
import requests
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth
from botocore.exceptions import ClientError
from bedrock_agentcore import BedrockAgentCoreApp
from pydantic import BaseModel

# Configuration
AWS_REGION = "us-east-1"
KNOWLEDGE_BASE_ID = "O4XMWIIEHS"  # ciam-kb -- Managed Knowledge Base (see OQ-1)
DEFAULT_TOP_K = 3
MAX_TOP_K = 10
BEDROCK_TIMEOUT_SECONDS = 10
MAX_RETRIES = 3

KNOWN_PORTAL_KEYWORDS = frozenset({"Support", "Community", "Academy", "Notification", "Dashboard", "Partner", "Prime"})

# Real block-keyword format from the Birthright & Entitlements Guide --
# hyphenated abbreviations (e.g. "Block-Supp"), NOT "block_<FullKeywordName>"
# as an earlier revision of this code incorrectly assumed. C-Academy/P-Academy
# are legacy, sunset 2025-11-17, but their block keywords remain assignable
# per the source doc's own footnote ("*Not released, but still assignable").
BLOCK_KEYWORD_TO_PORTAL = {
    "Block-Supp": "Support",
    "Block-Acad": "Academy",
    "Block-Comm": "Community",
    "Block-Notif": "Notification",
    "Block-Partner": "Partner",
    "Block-Prime": "Prime",
    "Block-Dash": "Dashboard",
    "Block-CAcad": "C-Academy",
    "Block-PAcad": "P-Academy",
}

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
    """Maps a failure symptom to the real Auth0 Action(s) responsible,
    fetched live from the nskp tenant's Management API (see
    fetch_auth0_workflow_scripts.py). Resolved OQ-8."""
    workflow_identified: bool = False
    workflow_name: Optional[str] = None
    workflow_script_ref: Optional[str] = None
    enforcement_workflow_name: Optional[str] = None
    enforcement_workflow_script_ref: Optional[str] = None
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
#
# Persona/expected-birthright table -- sourced from the real "Birthright &
# Entitlements Guide" (Confluence, Netskope ISI space, p.106-112 of the
# 2026-07-28 export). This REPLACES the earlier provisional table entirely --
# the two do not agree on several rows (e.g. the real "Partner" persona gets
# nearly the full portal set, not just 3 keywords as previously guessed).
#
# Real source field name is `Account_Status__c` (Salesforce). Some rows match
# by EXACT equality, others by SUBSTRING ("Includes") per the source table --
# this distinction is preserved below, not flattened to equality-only.
#
# NOT YET WIRED: "Customer Partner" / "MSP Partner" / "Service Provider/Telco
# Partner" personas require additional fields (customer_status, partner_type)
# that Agent 2's AccountPayload and the orchestrator's _agent4_input_builder
# do not currently supply. Until those are added, any account with
# Account_Status__c == "Partner" resolves to the plain "Partner" row --
# functionally identical to "Customer Partner"/"MSP Partner"/"Service
# Provider/Telco Partner" for birthright purposes (all four grant the same
# keyword set), so this is NOT a correctness gap for Tool 1's output today,
# only a persona-label granularity gap. The `(Prime)` keyword noted for
# Partner-type personas is also not yet added -- source distinguishes "Prime
# partners" via a value not yet identified in Agent 2's schema (see OQ-10).
def derive_persona(account_status: Optional[str], active_tenant_count: Optional[int]) -> tuple:
    has_tenant = (active_tenant_count or 0) >= 1

    if account_status is None:
        return "Individual", ["Community", "Dashboard"]

    status_lower = account_status.lower()

    if "quarantine" in status_lower or "out of business" in status_lower:
        return "QOB", ["Community", "Dashboard"]

    if "prospect" in status_lower:
        if has_tenant:
            return "Prospect (w/ Tenant)", ["Community", "Academy", "Support", "Notification", "Dashboard"]
        return "Prospect", ["Community", "Academy", "Dashboard"]

    if account_status == "Customer":
        return "Customer", ["Community", "Academy", "Support", "Notification", "Dashboard"]

    if account_status == "Pending Partner":
        if has_tenant:
            return "Pending Partner (w/ Tenant)", ["Community", "Academy", "Support", "Notification", "Dashboard"]
        return "Pending Partner", ["Community", "Academy", "Dashboard"]

    if account_status == "Partner":
        # Covers plain Partner, Customer Partner, MSP Partner, and Service
        # Provider/Telco Partner -- all four grant the same keyword set per
        # the source table; only the persona *label* would differ if
        # customer_status/partner_type were wired in (see docstring above).
        return "Partner", ["Support", "Community", "Academy", "Partner", "Notification", "Dashboard"]

    if account_status == "Churn":
        if has_tenant:
            return "Churn (w/ Tenant)", ["Community", "Academy", "Support", "Notification", "Dashboard"]
        return "Churn", ["Community", "Dashboard"]

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

    # Block keyword detection (pre-check, §4.1) -- real format is
    # "Block-<Abbrev>" (e.g. "Block-Supp"), not "block_<FullName>".
    block_keywords_found = [e for e in entitlements if e in BLOCK_KEYWORD_TO_PORTAL]
    explicit_block_detected = len(block_keywords_found) > 0
    blocked_portals = {BLOCK_KEYWORD_TO_PORTAL[b] for b in block_keywords_found}

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
        account_status is not None
        and "prospect" in account_status.lower()
        and (active_tenant_count or 0) >= 1
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


# Tool 4 — identify_failing_workflow (§4.1 Tool 4, resolves OQ-8)
#
# Real Auth0 Actions fetched live from the nskp tenant (18 actions,
# see fetch_auth0_workflow_scripts.py, indexed in the KB as
# auth0-action-*.md). Root cause of a birthright/entitlement gap traces to
# two distinct Actions:
#
#   1. NetskopeID-Sync-2 (`set_birthright_access`, action ID
#      bb237d59-6ef7-420e-881a-345c8d0bc3a2) computes the user's birthright
#      array from Salesforce Account Status + Tenant Requests at login.
#      A missing keyword almost always originates here -- the SF-derived
#      calculation didn't grant it.
#   2. Gatekeeper (action ID 35d76097-24c1-4b5b-b3cc-e853e286b7e6) is the
#      enforcement point: it checks
#      `entitlements.includes(block) || !(entitlements.includes(x) || birthright.includes(x))`
#      per portal at login and is what actually produces the "insufficient
#      permissions" denial the user sees -- including explicit Block-<X>
#      keyword checks.
_BIRTHRIGHT_SOURCE_WORKFLOW = ("NetskopeID-Sync-2", "bb237d59-6ef7-420e-881a-345c8d0bc3a2")
_ENFORCEMENT_WORKFLOW = ("Gatekeeper", "35d76097-24c1-4b5b-b3cc-e853e286b7e6")


def identify_failing_workflow(failed_step: Optional[str]) -> WorkflowIdentification:
    """Tool 4 -- pure local logic, zero external calls at runtime (the Auth0
    Action/Rule data was fetched offline and is hardcoded here + indexed in
    the KB as auth0-action-*.md for Tool 2 to surface alongside this)."""
    assert_tool_posture("identify_failing_workflow")

    if not failed_step:
        return WorkflowIdentification(
            workflow_identified=False,
            note="No failing step to map -- birthright matched expected, no workflow implicated.",
        )

    source_name, source_ref = _BIRTHRIGHT_SOURCE_WORKFLOW
    enforce_name, enforce_ref = _ENFORCEMENT_WORKFLOW

    if failed_step == "explicit_block_detected":
        return WorkflowIdentification(
            workflow_identified=True,
            workflow_name=enforce_name,
            workflow_script_ref=enforce_ref,
            note=(
                f"{enforce_name} checks entitlements against the client's Block-<Portal> "
                "metadata at login and denies access when a block keyword is present. "
                "See auth0-action-gatekeeper.md for the exact check."
            ),
        )

    # Any missing birthright keyword (e.g. "Support", "Academy") traces to
    # the Salesforce-driven birthright calculation, then is enforced by Gatekeeper.
    return WorkflowIdentification(
        workflow_identified=True,
        workflow_name=source_name,
        workflow_script_ref=source_ref,
        enforcement_workflow_name=enforce_name,
        enforcement_workflow_script_ref=enforce_ref,
        note=(
            f"{source_name}'s set_birthright_access() computes birthright from Salesforce "
            f"Account Status/Tenant Requests -- investigate why '{failed_step}' wasn't granted "
            f"there. {enforce_name} is what enforces the resulting gap at login (denies the "
            f"portal because '{failed_step}' is absent from entitlements/birthright). "
            "See auth0-action-netskopeid-sync-2.md and auth0-action-gatekeeper.md."
        ),
    )


# Tool 2 — query_knowledge_base (§4.1)
#
# NOTE: this KB is a Managed Knowledge Base (Bedrock's fully-managed vector
# store -- see spec OQ-1), which requires `managedSearchConfiguration` in
# the retrieve request instead of `vectorSearchConfiguration`. As of the
# latest boto3 (1.42.97), botocore's client-side parameter validator does
# not yet recognize this new field -- calling client.retrieve() rejects it
# before the request is ever sent. Until botocore ships support, this
# issues a raw SigV4-signed HTTP request to the same API instead of going
# through the boto3 client method. This is a temporary SDK-gap workaround,
# not an architectural choice -- switch back to client.retrieve() once
# botocore adds managedSearchConfiguration support.
BEDROCK_AGENT_RUNTIME_HOST = f"bedrock-agent-runtime.{AWS_REGION}.amazonaws.com"

# KB now indexes raw Auth0 Action source (auth0-action-*.md, see
# auth0_workflow_scripts/) alongside prose docs. A retrieved chunk can land
# mid-function with no surrounding markdown fence to strip, so fence-based
# stripping isn't enough -- this must never surface literal script code in
# a response an L1 agent or Jira ticket ultimately sees.
_CODE_TOKEN_PATTERN = re.compile(
    r'(=>|\bconst\s+\w+\s*=|\blet\s+\w+\s*=|\bfunction\s*\(|\bawait\s+\w+\(|'
    r'\brequire\(|\bexports\.\w+|\bapi\.\w+\(|\.setAppMetadata\(|;\s*$|^\s*}\s*$)',
    re.MULTILINE,
)
_CODE_TOKEN_MIN_HITS = 3  # a few isolated hits can occur in prose examples; require several

# Plain-English summaries of each real Auth0 Action, derived by reading the
# actual fetched script bodies (see auth0_workflow_scripts/*.md) -- used in
# place of raw code so Tool 2 stays *informed by* the real implementation
# without ever printing a line of it. Keyed by the KB document title.
_AUTH0_ACTION_SUMMARIES = {
    "auth0-action-netskopeid-sync-2.md": (
        "NetskopeID-Sync-2 (post-login) is the core birthright engine: it computes a "
        "user's birthright access array from Salesforce Account Status and Tenant "
        "Requests on every login and writes the result (plus last_sync) back to the "
        "user's app_metadata."
    ),
    "auth0-action-netskopeid-sync-1.md": (
        "NetskopeID-Sync-1 (post-login) bootstraps a user's app_metadata on first "
        "login, initializing an empty birthright array if one doesn't exist yet."
    ),
    "auth0-action-gatekeeper.md": (
        "Gatekeeper (post-login) enforces per-portal access at login: it checks "
        "whether the user's birthright/entitlements include the portal's required "
        "keyword (and denies access if a Block-<Portal> keyword is present), producing "
        "the 'insufficient permissions' denial the user sees."
    ),
    "auth0-action-rbac-consolidated.md": (
        "RBAC - Consolidated (post-login) grants portal-specific roles (e.g. Partner "
        "Portal, Support) at login based on which birthright/entitlement keywords the "
        "user holds, mapping keyword combinations to the client's role IDs."
    ),
    "auth0-action-federated-user-to-netskopeid-sync.md": (
        "Federated-User-To-NetskopeID-Sync (event-stream) syncs federated (SSO) user "
        "profile data into the internal NetskopeID database. It explicitly does not "
        "write birthright/roles back -- those are Salesforce-derived and owned by "
        "NetskopeID-Sync-2 at login time."
    ),
    "auth0-action-federated-user-deletion-sync.md": (
        "Federated-User-Deletion-Sync (event-stream) reacts to Auth0's user.deleted "
        "event for federated users and removes the corresponding row from the "
        "external NetskopeID database, since Auth0 deletions don't cascade to it "
        "automatically."
    ),
    "auth0-action-provisioner.md": (
        "Provisioner (pre-user-registration) runs before a new user is created via "
        "self-service sign-up: it validates and sanitizes the submitted email address "
        "before allowing the sign-up to proceed."
    ),
    "auth0-action-impartner-org-admin-sync.md": (
        "ImPartner-Org-Admin-Sync (event-stream) syncs a user's org-admin permission "
        "state to Impartner's Administrative_Privileges custom field."
    ),
    "auth0-action-mfa-consolidated.md": (
        "MFA - Consolidated (post-login) enforces or skips multi-factor authentication "
        "at login (skipped for a specific internal client and for migration-script "
        "logins), and includes a self-service MFA opt-in flow backed by DynamoDB."
    ),
    "auth0-action-registration-forms.md": (
        "Registration-Forms (post-login) retrieves the user's profile from the "
        "NetskopeID table and drives Auth0's registration/onboarding forms flow; "
        "bypasses migration-script-driven logins."
    ),
    "auth0-action-account-migration-acknowledgement.md": (
        "Account Migration Acknowledgement (post-login) records a one-time "
        "acknowledgement for users migrated from the legacy system before allowing "
        "login to proceed; bypasses migration-script-driven logins."
    ),
    "auth0-action-privacy-policy-acknowledgement.md": (
        "Privacy Policy Acknowledgement (post-login) requires the user to acknowledge "
        "the current privacy policy at login before proceeding; bypasses "
        "migration-script-driven logins."
    ),
    "auth0-action-email-verification-v2.md": (
        "Email Verification v2 (post-login) presents/enforces the email verification "
        "form at login and triggers Auth0's verification email if the user isn't yet "
        "verified; bypasses migration-script-driven logins."
    ),
    "auth0-action-send-mail.md": (
        "Send Mail (post-login) checks whether the user's email is verified and, if "
        "not, triggers Auth0's verification email via the Management API."
    ),
    "auth0-action-custom-phone-provider.md": (
        "Custom Phone Provider (custom-phone-provider) sends OTP codes for MFA/"
        "verification via AWS End User Messaging Notify, replacing Auth0's built-in "
        "SMS provider; only handles otp_verify and otp_enroll message types."
    ),
    "auth0-action-custom-email-provider.md": (
        "Custom Email Provider (custom-email-provider) is Auth0's custom SMTP hook -- "
        "it sends the actual email content for auth-related notifications (verification, "
        "password reset, etc.) instead of Auth0's default sender."
    ),
    "auth0-action-sms-mfa-ack.md": (
        "SMS-MFA-Ack (post-login) presents an acknowledgement form tied to SMS-based MFA."
    ),
    "auth0-action-password-rotation-v1.md": (
        "Password Rotation v1 (post-login) is registered but has no retrievable script "
        "body via the Management API -- may be disabled or not yet implemented."
    ),
}


def _sanitize_kb_excerpt(text: str, title: Optional[str] = None) -> str:
    """Replace an excerpt with a curated, code-free summary if it looks like
    source code rather than prose -- literal code must never reach a
    user-facing response, but the excerpt should stay as informative as
    possible rather than a dead-end placeholder. Falls back to a generic
    note (still naming the doc) only for actions not yet characterized."""
    if not text:
        return text
    if len(_CODE_TOKEN_PATTERN.findall(text)) < _CODE_TOKEN_MIN_HITS:
        return text
    if title and title in _AUTH0_ACTION_SUMMARIES:
        return _AUTH0_ACTION_SUMMARIES[title]
    doc_ref = f" ({title})" if title else ""
    return f"[Implementation not yet summarized{doc_ref} -- code omitted from excerpt.]"


def query_knowledge_base(query: str, top_k: int = DEFAULT_TOP_K) -> tuple:
    """Tool 2 -- calls Bedrock Knowledge Base Retrieve (§4.1).
    Returns (KnowledgeBaseResults, error).

    Uses the plain `retrieve` API rather than `retrieve_and_generate` --
    Agent 4 only needs the raw retrieved chunks (to build its own
    relevant_docs / similar_past_tickets split), not an LLM-synthesized
    answer, so retrieve_and_generate's extra model-invocation cost and
    latency buys nothing here."""
    assert_tool_posture("query_knowledge_base")
    assert_posture("bedrock:Retrieve")

    top_k = min(top_k, MAX_TOP_K)
    session = boto3.Session()
    frozen_creds = session.get_credentials().get_frozen_credentials()

    url = f"https://{BEDROCK_AGENT_RUNTIME_HOST}/knowledgebases/{KNOWLEDGE_BASE_ID}/retrieve"
    body = json.dumps({
        "retrievalQuery": {"text": query},
        "retrievalConfiguration": {"managedSearchConfiguration": {"numberOfResults": top_k}},
    })

    attempt = 0
    while True:
        attempt += 1
        try:
            request = AWSRequest(method="POST", url=url, data=body, headers={"Content-Type": "application/json"})
            SigV4Auth(frozen_creds, "bedrock", AWS_REGION).add_auth(request)
            resp = requests.post(url, headers=dict(request.headers), data=body, timeout=BEDROCK_TIMEOUT_SECONDS)

            if resp.status_code == 429:
                if attempt >= MAX_RETRIES:
                    return KnowledgeBaseResults(), "bedrock_throttled"
                time.sleep(2 ** (attempt - 1))
                continue

            if resp.status_code >= 400:
                return KnowledgeBaseResults(), "bedrock_error"

            response = resp.json()
            break
        except requests.exceptions.Timeout:
            return KnowledgeBaseResults(), "bedrock_timeout"
        except Exception:
            return KnowledgeBaseResults(), "bedrock_error"

    relevant_docs = []
    similar_past_tickets = []
    for result in response.get("retrievalResults", []):
        metadata = result.get("metadata", {})
        location = result.get("location", {})
        score = result.get("score", 0.0)
        title = metadata.get("_document_title", "Untitled")
        url = metadata.get("_source_uri") or location.get("s3Location", {}).get("uri")
        content = _sanitize_kb_excerpt(result.get("content", {}).get("text", "")[:500], title)

        # Resolved TQI ticket exports are named/prefixed distinctly from SOPs
        # and guides in the KB data source -- see spec OQ-3 for the exact
        # convention to confirm once real ticket exports are ingested.
        is_ticket = title.upper().startswith("TQI-") or "tqi-" in title.lower()

        if is_ticket:
            similar_past_tickets.append(KBTicket(
                ticket_key=metadata.get("ticket_key", title),
                summary=metadata.get("summary", content),
                resolution=metadata.get("resolution"),
                relevance_score=score,
            ))
        else:
            relevant_docs.append(KBDocument(
                title=title,
                url=url,
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
