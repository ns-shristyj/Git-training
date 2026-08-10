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
  4. Maps the failure to the real Auth0 Action(s) responsible (Tool 4:
     identify_failing_workflow), backed by a LIVE fetch of the current
     Action list/metadata from the Auth0 Management API on every invocation
     (Tool 5: fetch_live_auth0_actions) -- non-fatal on failure, falls back
     to the last-known-good offline snapshot. This exists because Auth0
     Actions are edited independently of this agent's deploys: a hardcoded
     "what this Action does" description silently goes stale the moment
     someone edits the Action in the Auth0 dashboard. The live fetch also
     flags "code drift" -- when the live Action's source no longer contains
     the marker strings this agent's diagnosis logic assumes -- so a broken
     or changed Action shows up as a signal in the response instead of
     silently producing a wrong root cause.

Security model
--------------
Tools 1 and 3 are pure local functions -- zero network calls, zero IAM
permissions required. Tool 2 calls bedrock:Retrieve / bedrock:RetrieveAndGenerate,
scoped to the CIAM Knowledge Base ARN only. Tool 5 (used by Tool 4) calls
secretsmanager:GetSecretValue scoped ONLY to the ciam-agent/auth0-workflows
secret (a read-only M2M app with read:actions/read:rules/read:triggers
scopes -- distinct from Agent 3's ciam-agent/auth0 user-lookup credential,
which Agent 4 has no access to), then HTTPS GET to the Auth0 Management API
(GET /api/v2/actions/actions only -- no writes, ever). No DynamoDB, no
Auth0 user data, no writes of any kind.
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

# Live Auth0 Action fetch (Tool 5) -- same tenant Agent 3 talks to, but a
# separate, narrower-scoped M2M app/secret (read:actions/read:rules/
# read:triggers only, no user data access).
AUTH0_DOMAIN = "netskope-dev.us.auth0.com"
AUTH0_WORKFLOWS_SECRET_PATH = "ciam-agent/auth0-workflows"
AUTH0_HTTP_TIMEOUT_SECONDS = 5
AUTH0_MAX_RETRIES = 2  # best-effort, non-fatal -- don't retry as aggressively as Tool 2

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

# Posture Guard: Tools 1 and 3 are pure local logic (no IAM needed). Tool 2
# and Tool 5 are the only external calls.
ALLOWED_ACTIONS = frozenset({
    "bedrock:Retrieve", "bedrock:RetrieveAndGenerate", "secretsmanager:GetSecretValue",
})
ALLOWED_TOOL_NAMES = frozenset({
    "evaluate_birthright", "query_knowledge_base",
    "classify_fix_complexity", "identify_failing_workflow",
    "fetch_live_auth0_actions",
})

# HTTP allow-list for Tool 5 -- exactly two permitted call patterns, read-only,
# same host Agent 3 uses but a narrower path set (no user-data endpoints).
ALLOWED_HTTP_HOSTS = frozenset({AUTH0_DOMAIN})
ALLOWED_HTTP_PATHS = frozenset({"/oauth/token", "/api/v2/actions/actions"})


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


def assert_http_posture(host: str, path: str, method: str) -> None:
    if host != AUTH0_DOMAIN:
        raise PostureViolationError(f"Posture violation: host '{host}' not permitted")
    if path not in ALLOWED_HTTP_PATHS:
        raise PostureViolationError(f"Posture violation: path '{path}' not permitted")


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
    """Maps a failure symptom to the real Auth0 Action(s) responsible.
    `workflow_script_ref`/`enforcement_workflow_script_ref` are the LIVE
    action IDs fetched from the Auth0 Management API on this invocation
    when available (`live_verified=True`), falling back to the last-known
    offline snapshot when the live fetch fails (`live_verified=False`,
    `live_fetch_error` populated) -- never blocks the rest of Agent 4's
    output either way. Resolved OQ-8."""
    workflow_identified: bool = False
    workflow_name: Optional[str] = None
    workflow_script_ref: Optional[str] = None
    enforcement_workflow_name: Optional[str] = None
    enforcement_workflow_script_ref: Optional[str] = None
    note: str = "Auth0 workflow scripts not yet provided -- placeholder only"
    live_verified: bool = False
    live_fetch_error: Optional[str] = None
    code_drift_detected: bool = False
    code_drift_note: Optional[str] = None


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


class SyncDiagnostics(BaseModel):
    """CIAM ops feedback: a birthright gap has (at least) three distinct root
    causes that all look identical from missing_keywords alone -- (a) the
    user simply hasn't logged in since the Salesforce-side change that would
    grant it (sync only runs at login, so no login means no refresh,
    regardless of how correct the calculation is), (b) accounts[0]/users[0]
    isn't even the right record for this email (multiple accounts/Auth0
    users exist, and we're confidently evaluating the wrong one), or (c) the
    Auth0 Action's own code is broken (see WorkflowIdentification.code_drift_
    detected). This model surfaces (a) and (b) as their own signals so
    classify_fix_complexity can react to them instead of confidently
    recommending a manual entitlements add when the real fix is "ask the
    user to log back in" or "confirm which account this ticket is about"."""
    pending_login_refresh: bool = False
    pending_login_refresh_note: Optional[str] = None
    multi_account_ambiguity: bool = False
    multi_account_ambiguity_reasons: List[str] = []


class KnowledgeBasePayload(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    spec_id: Literal["SPEC-CIAM-0004"] = "SPEC-CIAM-0004"
    agent: Literal["ciam-knowledge-base-agent"] = "ciam-knowledge-base-agent"
    run_id: str
    evaluated_at: datetime

    birthright_evaluation: Optional[BirthrightEvaluation] = None
    fix_classification: Optional[FixClassification] = None
    workflow_identification: Optional[WorkflowIdentification] = None
    sync_diagnostics: Optional[SyncDiagnostics] = None

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
#
# HARD RULE (per CIAM ops policy, confirmed against the Birthright & Entitlements Guide):
# BIRTHRIGHT is computed by the NetskopeID-Sync-2 Auth0 Action from Salesforce Account
# Status/Tenant Requests at every login -- it is NEVER manually edited, under any
# circumstance. The only manually-editable field for compensating a birthright gap is
# ENTITLEMENTS. No recommended_actions text below may ever suggest adding to or
# modifying "birthright" directly; every SIMPLE_FIX path must say "entitlements".
def classify_fix_complexity(
    missing_keywords: List[str],
    extra_keywords: List[str],
    account_status: Optional[str],
    active_tenant_count: Optional[int],
    user_found_in_auth0: bool,
    explicit_block_detected: bool,
    intent: Optional[str],
    birthright_correct_but_access_denied: bool,
    multi_account_ambiguity: bool = False,
    multi_account_ambiguity_reasons: Optional[List[str]] = None,
    code_drift_detected: bool = False,
    code_drift_note: Optional[str] = None,
    pending_login_refresh: bool = False,
    pending_login_refresh_note: Optional[str] = None,
) -> FixClassification:
    """Tool 3 -- pure local logic, zero external calls (§4.1).

    The last five params are CIAM ops feedback additions: `missing_keywords`/
    `extra_keywords` alone can't distinguish "this data is genuinely
    accurate and there's a real gap" from "this data can't be trusted right
    now" -- multi_account_ambiguity (evaluating possibly the wrong account/
    user record entirely) and code_drift_detected (the Auth0 Action that
    computes birthright may itself be broken) are both reasons the
    underlying missing/extra keyword computation might not mean what it
    looks like it means, so they're checked before trusting that
    computation at all. pending_login_refresh is different in kind -- it
    doesn't undermine trust in the data, it explains WHY there's a gap
    (sync hasn't run since a Salesforce change because the user hasn't
    logged in), which changes the recommended fix, not the complexity."""
    assert_tool_posture("classify_fix_complexity")

    # Checked FIRST: if we can't even be confident WHICH account/user record
    # this evaluation is based on, every downstream signal (extra_keywords,
    # missing_keywords, block detection) is potentially about the wrong
    # record entirely. Must not silently proceed as if accounts[0]/users[0]
    # is definitely correct.
    if multi_account_ambiguity:
        return FixClassification(
            complexity="ESCALATE_TO_L2",
            reason=(
                "Multiple accounts and/or Auth0 user records exist for this email -- "
                f"({'; '.join(multi_account_ambiguity_reasons or [])}) -- cannot safely "
                "determine which record is authoritative for this ticket without disambiguation. "
                "Any diagnosis below is based on the FIRST record returned, which may not be "
                "the one this ticket is actually about."
            ),
            recommended_actions=[
                "Confirm with the user (or Salesforce/tenant context) which specific "
                "account/tenant this ticket is about",
                "Re-run diagnosis scoped to the confirmed account/user before taking any "
                "entitlements action",
                "Escalate to L2 for account disambiguation",
            ],
            confidence="LOW",
        )

    # Checked SECOND: if the Auth0 Action that computes birthright has
    # itself changed in a way that no longer matches this agent's
    # assumptions, the missing/extra keyword computation below may reflect
    # a code bug rather than a real account/entitlement issue.
    if code_drift_detected:
        return FixClassification(
            complexity="ESCALATE_TO_L2",
            reason=(
                "The Auth0 Action responsible for computing birthright and/or enforcing access "
                f"has changed in a way that doesn't match expected logic: {code_drift_note or 'see workflow_identification for details.'} "
                "The apparent access gap below may be caused by this code change rather than "
                "Salesforce data -- do not assume a manual entitlements fix will hold."
            ),
            recommended_actions=[
                "Review the current Auth0 Action code for the workflow named in "
                "workflow_identification before making any entitlements change",
                "Escalate to L2 / Auth0 Action owner for code review",
            ],
            confidence="MEDIUM",
        )

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
        if pending_login_refresh:
            # A pending Salesforce-side change that hasn't hit a login yet
            # is NOT the same situation as "birthright is just wrong" --
            # the correct fix is a fresh login (free, no manual edit, and
            # actually addresses the cause), tried BEFORE reaching for a
            # manual entitlements compensation.
            return FixClassification(
                complexity="SIMPLE_FIX",
                reason=(
                    f"Missing keyword(s) appear explained by a pending sync, not a real gap: "
                    f"{pending_login_refresh_note} Try a fresh login before adding entitlements "
                    "manually."
                ),
                recommended_actions=[
                    "Ask the user to log out and log back in -- this triggers NetskopeID-Sync-2 "
                    "to recompute birthright from the CURRENT Salesforce Account Status, which "
                    "may already resolve this without any manual change",
                    f"If access is still missing after a fresh login, THEN add {missing_keywords} "
                    "to the ENTITLEMENTS array via Auth0 Management API as a compensating "
                    "control (never modify birthright directly -- it will be recalculated and "
                    "overwritten on next login regardless)",
                    "Verify access after whichever step resolves it",
                ],
                confidence="HIGH",
            )
        return FixClassification(
            complexity="SIMPLE_FIX",
            reason=(
                "Missing keyword(s) can be safely compensated via entitlements; no "
                "over-provisioning or provisioning issues detected. NOTE: birthright itself is "
                "computed by NetskopeID-Sync-2 from Salesforce Account Status/Tenant Requests at "
                "login and must NEVER be edited directly -- any direct edit would be silently "
                "overwritten on the user's next login regardless."
            ),
            recommended_actions=[
                f"Do NOT modify birthright directly. Add {missing_keywords} to the ENTITLEMENTS "
                "array via Auth0 Management API instead -- entitlements is the only "
                "manually-editable field for compensating a birthright gap",
                "Verify access after the entitlements update",
                "This is a compensating control, not a root-cause fix: if the same keyword goes "
                "missing again after a future login/sync, escalate to check the Salesforce "
                "Account Status/Tenant Requests feeding NetskopeID-Sync-2 instead of re-adding "
                "the entitlement repeatedly",
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


# Tool 5 — fetch_live_auth0_actions (CIAM ops feedback: Auth0 Actions are
# edited independently of this agent's deploys, so Tool 4's understanding of
# "what NetskopeID-Sync-2/Gatekeeper currently do" must be re-verified live
# on every invocation, not trusted from a point-in-time hardcoded snapshot.
#
# _OFFLINE_FALLBACK_WORKFLOWS is the last-known-good snapshot from the
# original offline fetch (see fetch_auth0_workflow_scripts.py, action IDs
# valid as of 2026-07-28) -- used ONLY when the live fetch below fails
# (network error, credential issue, Auth0 API outage). When the live fetch
# succeeds, its action IDs/status always take precedence.
_OFFLINE_FALLBACK_WORKFLOWS = {
    "NetskopeID-Sync-2": "bb237d59-6ef7-420e-881a-345c8d0bc3a2",
    "Gatekeeper": "35d76097-24c1-4b5b-b3cc-e853e286b7e6",
}

# Marker strings this agent's diagnosis logic assumes are present in each
# Action's current source. Not code review -- a lightweight drift detector:
# if a marker goes missing, the Action was very likely edited in a way that
# changes its behavior, and Tool 4's root-cause mapping may no longer be
# accurate (addresses CIAM ops feedback: "the action code could be something
# wrong and not applying to calculate birthright properly"). Never surfaces
# the underlying code itself -- only a boolean + a description of what's
# missing.
# Verified against the actual fetched source (auth0_workflow_scripts/
# auth0-action-*.md, 2026-07-28 snapshot) -- NOT against the prose
# description. An earlier version of this dict used "Tenant_Requests__c",
# which is a paraphrase from a code COMMENT ("Salesforce Account Status and
# Tenant Requests") and never appears as a literal token anywhere in the
# real source; the actual second Salesforce field referenced is
# `Customer_Status__c`. That mismatch would have fired a false "code drift"
# warning on every single ticket. Lesson: markers must be copy-verified
# against real fetched code, never inferred from a summary/comment.
_EXPECTED_CODE_MARKERS = {
    "NetskopeID-Sync-2": ["Account_Status__c", "Customer_Status__c", "birthright"],
    "Gatekeeper": ["birthright", "entitlements"],
}


class LiveActionInfo(BaseModel):
    name: str
    action_id: str
    status: Optional[str] = None
    updated_at: Optional[str] = None
    code_drift_detected: bool = False
    code_drift_note: Optional[str] = None


_auth0_secrets_client = None
_auth0_cached_token: Optional[str] = None
_auth0_cached_token_expires_at: Optional[datetime] = None


class Auth0WorkflowFetchError(RuntimeError):
    pass


def _get_auth0_secrets_client():
    global _auth0_secrets_client
    if _auth0_secrets_client is None:
        _auth0_secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)
    return _auth0_secrets_client


def _get_auth0_workflows_credentials() -> dict:
    assert_posture("secretsmanager:GetSecretValue")
    client = _get_auth0_secrets_client()
    response = client.get_secret_value(SecretId=AUTH0_WORKFLOWS_SECRET_PATH)
    return json.loads(response["SecretString"])


def _acquire_auth0_token() -> tuple:
    creds = _get_auth0_workflows_credentials()
    assert_http_posture(AUTH0_DOMAIN, "/oauth/token", "POST")

    last_error = None
    for attempt in range(1, AUTH0_MAX_RETRIES + 1):
        try:
            response = requests.post(
                f"https://{AUTH0_DOMAIN}/oauth/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": creds["client_id"],
                    "client_secret": creds["client_secret"],
                    "audience": f"https://{AUTH0_DOMAIN}/api/v2/",
                },
                timeout=AUTH0_HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
            return body["access_token"], body.get("expires_in", 3600)
        except Exception as e:
            last_error = e
            if attempt < AUTH0_MAX_RETRIES:
                time.sleep(1)

    raise Auth0WorkflowFetchError(str(last_error))


def _get_valid_auth0_token() -> str:
    """Caching the TOKEN is just an auth-perf optimization (avoids an extra
    round trip when Agent 4 is invoked repeatedly in a warm container) -- it
    is NOT a cache of Action data. The actions list itself (below) is always
    re-fetched fresh on every call; nothing about Action content is ever
    cached across invocations."""
    global _auth0_cached_token, _auth0_cached_token_expires_at
    now = now_utc()
    if _auth0_cached_token and _auth0_cached_token_expires_at and now < _auth0_cached_token_expires_at:
        return _auth0_cached_token
    token, expires_in = _acquire_auth0_token()
    _auth0_cached_token = token
    _auth0_cached_token_expires_at = now + timedelta(seconds=max(expires_in - 60, 30))
    return token


def fetch_live_auth0_actions(action_names: List[str]) -> tuple:
    """Tool 5 -- fetches the CURRENT Auth0 Action list from the live
    Management API (GET /api/v2/actions/actions, read-only) and checks each
    requested action's live source against _EXPECTED_CODE_MARKERS. Always
    attempted fresh on every Agent 4 invocation -- no caching of Action data.
    Non-fatal: any failure (network, credentials, Auth0 API error/timeout)
    returns ({}, error_string) and callers fall back to
    _OFFLINE_FALLBACK_WORKFLOWS, exactly like Tool 2's KB failure handling."""
    assert_tool_posture("fetch_live_auth0_actions")

    try:
        token = _get_valid_auth0_token()
        assert_http_posture(AUTH0_DOMAIN, "/api/v2/actions/actions", "GET")
        response = requests.get(
            f"https://{AUTH0_DOMAIN}/api/v2/actions/actions",
            headers={"Authorization": f"Bearer {token}"},
            params={"per_page": 100},
            timeout=AUTH0_HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
    except Exception as e:
        logger.warning(
            f"Live Auth0 Action fetch failed, falling back to offline snapshot: "
            f"{type(e).__name__}: {e}"
        )
        return {}, f"auth0_live_fetch_error: {type(e).__name__}"

    actions_by_name = {a.get("name"): a for a in body.get("actions", []) if a.get("name")}
    results = {}
    for name in action_names:
        live = actions_by_name.get(name)
        if not live:
            results[name] = LiveActionInfo(
                name=name,
                action_id="",
                status="not_found_live",
                code_drift_detected=True,
                code_drift_note=(
                    f"Action '{name}' was not found by that name in the live tenant -- it may "
                    "have been renamed, deleted, or consolidated. Root-cause mapping for this "
                    "workflow can't be verified against current reality."
                ),
            )
            continue

        code = live.get("code") or ""
        expected_markers = _EXPECTED_CODE_MARKERS.get(name, [])
        missing_markers = [m for m in expected_markers if m not in code]
        drift = len(missing_markers) > 0
        results[name] = LiveActionInfo(
            name=name,
            action_id=live.get("id", ""),
            status=live.get("status"),
            updated_at=live.get("updated_at"),
            code_drift_detected=drift,
            code_drift_note=(
                f"Action '{name}' current live code no longer contains expected marker(s) "
                f"{missing_markers} -- its logic may have changed since this diagnosis mapping "
                "was last validated. Escalate for manual review of the Action's current code."
            ) if drift else None,
        )

    return results, None


# Tool 4 — identify_failing_workflow (§4.1 Tool 4, resolves OQ-8)
#
# Root cause of a birthright/entitlement gap traces to two distinct Actions
# (verified live via Tool 5 above on every call; falls back to
# _OFFLINE_FALLBACK_WORKFLOWS only if that live fetch fails):
#
#   1. NetskopeID-Sync-2 (`set_birthright_access`) computes the user's
#      birthright array from Salesforce Account Status + Tenant Requests at
#      login. A missing keyword almost always originates here -- the
#      SF-derived calculation didn't grant it.
#   2. Gatekeeper is the enforcement point: it checks
#      `entitlements.includes(block) || !(entitlements.includes(x) || birthright.includes(x))`
#      per portal at login and is what actually produces the "insufficient
#      permissions" denial the user sees -- including explicit Block-<X>
#      keyword checks.
def identify_failing_workflow(
    failed_step: Optional[str],
    all_missing_keywords: Optional[List[str]] = None,
    live_actions: Optional[dict] = None,
    live_fetch_error: Optional[str] = None,
) -> WorkflowIdentification:
    """Tool 4. `live_actions` (from Tool 5, keyed by Action name) supplies
    live-verified action IDs/drift status when available; falls back to
    _OFFLINE_FALLBACK_WORKFLOWS when `live_actions` is None/empty or doesn't
    contain a given name (e.g. Tool 5's fetch failed entirely).

    `failed_step` is the single value used for backward-compat call sites and
    the "explicit_block_detected" sentinel. When there's more than one
    missing keyword, `all_missing_keywords` drives the note text so a
    ticket about e.g. "Partner Portal" doesn't get a note that only
    mentions the alphabetically-first gap (e.g. "Academy")."""
    assert_tool_posture("identify_failing_workflow")

    if not failed_step:
        return WorkflowIdentification(
            workflow_identified=False,
            note="No failing step to map -- birthright matched expected, no workflow implicated.",
            live_fetch_error=live_fetch_error,
        )

    live_actions = live_actions or {}
    source_name = "NetskopeID-Sync-2"
    enforce_name = "Gatekeeper"
    source_live = live_actions.get(source_name)
    enforce_live = live_actions.get(enforce_name)

    source_ref = (source_live.action_id if source_live and source_live.action_id
                  else _OFFLINE_FALLBACK_WORKFLOWS[source_name])
    enforce_ref = (enforce_live.action_id if enforce_live and enforce_live.action_id
                   else _OFFLINE_FALLBACK_WORKFLOWS[enforce_name])

    # live_verified means BOTH relevant actions were actually found in this
    # invocation's live fetch -- not just that the HTTP call succeeded.
    live_verified = (
        live_fetch_error is None
        and source_live is not None and source_live.action_id != ""
        and enforce_live is not None and enforce_live.action_id != ""
    )
    drift_infos = [info for info in (source_live, enforce_live) if info and info.code_drift_detected]
    code_drift_detected = len(drift_infos) > 0
    code_drift_note = " ".join(info.code_drift_note for info in drift_infos if info.code_drift_note) or None

    if failed_step == "explicit_block_detected":
        return WorkflowIdentification(
            workflow_identified=True,
            workflow_name=enforce_name,
            workflow_script_ref=enforce_ref,
            note=(
                f"{enforce_name} checks entitlements against the client's Block-<Portal> "
                "metadata at login and denies access when a block keyword is present. "
                "See auth0-action-gatekeeper.md for the exact check."
                + (f" LIVE-VERIFIED action ID as of this run: {enforce_ref}." if live_verified else
                   " (Live verification unavailable this run -- using last-known-good action ID.)")
            ),
            live_verified=live_verified,
            live_fetch_error=live_fetch_error,
            code_drift_detected=code_drift_detected,
            code_drift_note=code_drift_note,
        )

    keywords = all_missing_keywords or [failed_step]
    keywords_str = ", ".join(f"'{k}'" for k in keywords)
    plural = "s" if len(keywords) > 1 else ""
    was_were = "weren't" if len(keywords) > 1 else "wasn't"

    # Any missing birthright keyword(s) (e.g. "Support", "Partner") trace to
    # the Salesforce-driven birthright calculation, then are enforced by Gatekeeper.
    note = (
        f"{source_name}'s set_birthright_access() computes birthright from Salesforce "
        f"Account Status/Tenant Requests -- investigate why keyword{plural} {keywords_str} "
        f"{was_were} granted there. {enforce_name} is what enforces the resulting gap at "
        f"login (denies each portal whose required keyword is absent from entitlements/"
        f"birthright). See auth0-action-netskopeid-sync-2.md and auth0-action-gatekeeper.md."
    )
    if live_verified:
        note += f" LIVE-VERIFIED against the current Auth0 tenant as of this run (action IDs: {source_ref}, {enforce_ref})."
    else:
        note += (
            " (Live verification unavailable this run"
            + (f": {live_fetch_error}" if live_fetch_error else "")
            + " -- using last-known-good offline snapshot; action IDs above may be stale.)"
        )
    if code_drift_note:
        note += f" WARNING: {code_drift_note}"

    return WorkflowIdentification(
        workflow_identified=True,
        workflow_name=source_name,
        workflow_script_ref=source_ref,
        enforcement_workflow_name=enforce_name,
        enforcement_workflow_script_ref=enforce_ref,
        note=note,
        live_verified=live_verified,
        live_fetch_error=live_fetch_error,
        code_drift_detected=code_drift_detected,
        code_drift_note=code_drift_note,
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
# actual fetched script bodies as of the 2026-07-28 offline fetch (see
# auth0_workflow_scripts/*.md) -- used in place of raw code so Tool 2 stays
# *informed by* the real implementation without ever printing a line of it.
# Keyed by the KB document title. NOTE: this is now a point-in-time
# snapshot only used for excerpt sanitization (Tool 2) -- it is NOT the
# source of truth for Tool 4's root-cause mapping, which re-verifies
# NetskopeID-Sync-2/Gatekeeper against the LIVE Auth0 tenant on every
# invocation (see fetch_live_auth0_actions / Tool 5, below). If a KB
# document's underlying Action has since changed, this summary can go
# stale -- that staleness only affects the KB excerpt text (still labeled
# with the doc title so it's traceable), not the live diagnosis.
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
    seen_doc_excerpts = set()  # (title, excerpt) -- distinct raw chunks can sanitize to the
    # same curated summary (e.g. two code chunks from the same Action), which would otherwise
    # surface as duplicate entries eating into a small top_k
    for result in response.get("retrievalResults", []):
        metadata = result.get("metadata", {})
        location = result.get("location", {})
        score = result.get("score", 0.0)
        title = metadata.get("_document_title", "Untitled")
        url = metadata.get("_source_uri") or location.get("s3Location", {}).get("uri")
        content = _sanitize_kb_excerpt(result.get("content", {}).get("text", "")[:500], title)

        dedup_key = (title, content)
        if dedup_key in seen_doc_excerpts:
            continue
        seen_doc_excerpts.add(dedup_key)

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


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def derive_pending_login_refresh(last_login, recent_changes: Optional[List[dict]]) -> tuple:
    """CIAM ops feedback: birthright is only recalculated at login
    (NetskopeID-Sync-2 runs post-login). A Salesforce-side account change
    made after the user's last login has had NO chance to be reflected yet
    -- that's not a data bug or a code bug, it's just pending a login that
    hasn't happened. Returns (pending_login_refresh, note). Fails safe to
    (False, None) on missing/unparseable data -- this is a best-effort
    signal, not a hard gate."""
    if not recent_changes:
        return False, None

    last_login_dt = _parse_dt(last_login)
    newest_change = None
    for change in recent_changes:
        changed_at = _parse_dt(change.get("changed_date"))
        if changed_at and (newest_change is None or changed_at > newest_change[0]):
            newest_change = (changed_at, change)

    if newest_change is None:
        return False, None

    changed_at, change = newest_change
    field = change.get("field_name", "an account field")

    if last_login_dt is None:
        return True, (
            f"Account field '{field}' changed on {changed_at.isoformat()}, but this user has "
            "no recorded login since then (or ever) -- birthright can't have refreshed yet, "
            "since NetskopeID-Sync-2 only recalculates it at login."
        )

    if changed_at > last_login_dt:
        return True, (
            f"Account field '{field}' changed on {changed_at.isoformat()}, which is AFTER this "
            f"user's last login ({last_login_dt.isoformat()}) -- birthright can't have picked up "
            "that change yet, since NetskopeID-Sync-2 only recalculates it at login."
        )

    return False, None


def derive_multi_account_ambiguity(
    account_data_warnings: Optional[List[str]],
    auth0_warnings: Optional[List[str]],
    accounts_count: int,
    auth0_users_count: int,
) -> tuple:
    """CIAM ops feedback: the account/user this agent evaluates is always
    accounts[0]/users[0] -- if there's more than one candidate record for
    this email, silently picking the first one risks evaluating the WRONG
    account/user entirely. Returns (ambiguity_detected, reasons)."""
    reasons = []
    if account_data_warnings and "multiple_accounts_found" in account_data_warnings:
        reasons.append("Agent 2 (database) flagged multiple_accounts_found for this email")
    elif accounts_count > 1:
        reasons.append(f"{accounts_count} accounts found for this email")

    if auth0_warnings and "multiple_users_found" in auth0_warnings:
        reasons.append("Agent 3 (Auth0) flagged multiple_users_found for this email")
    elif auth0_users_count > 1:
        reasons.append(f"{auth0_users_count} Auth0 user records found for this email")

    return len(reasons) > 0, reasons


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

    # CIAM ops feedback additions -- all optional/best-effort, default to
    # "no signal" so older orchestrator payloads that don't send them yet
    # still work exactly as before.
    last_login = payload.get("last_login")
    recent_changes = payload.get("recent_changes") or []
    accounts_count = payload.get("accounts_count", 1 if account_status is not None else 0)
    auth0_users_count = payload.get("auth0_users_count", 1 if user_found_in_auth0 else 0)
    account_data_warnings = payload.get("account_data_warnings") or []
    auth0_warnings = payload.get("auth0_warnings") or []

    # Step 2: derive sync flags
    sync_never_ran, sync_stale = derive_sync_flags(last_sync)
    pending_login_refresh, pending_login_refresh_note = derive_pending_login_refresh(
        last_login, recent_changes
    )
    multi_account_ambiguity, ambiguity_reasons = derive_multi_account_ambiguity(
        account_data_warnings, auth0_warnings, accounts_count, auth0_users_count
    )

    # Step 3: evaluate birthright (Tool 1) -- always called
    evaluation = evaluate_birthright(account_status, active_tenant_count, actual_birthright, entitlements)
    evaluation.sync_never_ran = sync_never_ran
    evaluation.sync_stale = sync_stale

    birthright_correct_but_access_denied = evaluation.match and intent == "ACCESS_DENIED"
    evaluation.birthright_correct_but_access_denied = birthright_correct_but_access_denied

    # Step 4: fetch live Auth0 Action state (Tool 5), backed into Tool 3's
    # classification -- moved ahead of Tool 3 (previously only fed Tool 4)
    # so code drift can downgrade/escalate the fix classification itself,
    # not just annotate the workflow note after the fact. Only worth the
    # round trip when there's actually a gap to explain.
    failed_step = (
        "explicit_block_detected" if evaluation.explicit_block_detected
        else (evaluation.missing_keywords[0] if evaluation.missing_keywords else None)
    )
    live_actions, live_fetch_error = ({}, None)
    if failed_step:
        live_actions, live_fetch_error = fetch_live_auth0_actions(
            ["NetskopeID-Sync-2", "Gatekeeper"]
        )
    code_drift_detected = any(info.code_drift_detected for info in live_actions.values())
    code_drift_note = " ".join(
        info.code_drift_note for info in live_actions.values() if info.code_drift_note
    ) or None

    # Step 5: classify fix complexity (Tool 3) -- always called
    classification = classify_fix_complexity(
        missing_keywords=evaluation.missing_keywords,
        extra_keywords=evaluation.extra_keywords,
        account_status=account_status,
        active_tenant_count=active_tenant_count,
        user_found_in_auth0=user_found_in_auth0,
        explicit_block_detected=evaluation.explicit_block_detected,
        intent=intent,
        birthright_correct_but_access_denied=birthright_correct_but_access_denied,
        multi_account_ambiguity=multi_account_ambiguity,
        multi_account_ambiguity_reasons=ambiguity_reasons,
        code_drift_detected=code_drift_detected,
        code_drift_note=code_drift_note,
        pending_login_refresh=pending_login_refresh,
        pending_login_refresh_note=pending_login_refresh_note,
    )

    # Step 6: query Knowledge Base (Tool 2) -- always attempted, non-fatal
    query = build_kb_query(intent, evaluation.persona, evaluation.missing_keywords, evaluation.extra_keywords, raw_input)
    kb_results, kb_error = query_knowledge_base(query, top_k=payload.get("top_k", DEFAULT_TOP_K))

    # Step 7: identify failing workflow (Tool 4) -- reuses the live Auth0
    # data already fetched in Step 4, no second round trip.
    workflow_id = identify_failing_workflow(
        failed_step, evaluation.missing_keywords, live_actions, live_fetch_error
    )

    sync_diagnostics = SyncDiagnostics(
        pending_login_refresh=pending_login_refresh,
        pending_login_refresh_note=pending_login_refresh_note,
        multi_account_ambiguity=multi_account_ambiguity,
        multi_account_ambiguity_reasons=ambiguity_reasons,
    )

    logger.info(f"[{run_id}] Done. persona={evaluation.persona} complexity={classification.complexity}")

    return KnowledgeBasePayload(
        run_id=run_id,
        evaluated_at=evaluated_at,
        birthright_evaluation=evaluation,
        fix_classification=classification,
        workflow_identification=workflow_id,
        sync_diagnostics=sync_diagnostics,
        knowledge_base_results=kb_results,
        knowledge_base_error=kb_error,
        error=None,
    ).model_dump()


if __name__ == "__main__":
    app.run()
