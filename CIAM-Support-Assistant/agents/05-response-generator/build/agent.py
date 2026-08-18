"""
CIAM Response Generator Agent — Agent 5
Spec:    SPEC-CIAM-0005
Version: 0.2.0

What this file does
-------------------
Bedrock AgentCore entrypoint that synthesizes findings from Agents 2/3/4
into a single diagnostic recommendation with confidence scores. This is
the final analysis layer that turns raw data into actionable intelligence
for L2 support and Jira escalations.

Receives (from orchestrator):
  • AccountPayload (Agent 2: database records)
  • Auth0Payload (Agent 3: Auth0 user metadata)
  • KnowledgeBasePayload (Agent 4: birthright evaluation + KB matches)
  • Original ticket details (from orchestrator)

Produces:
  • Root cause diagnosis
  • Recommended actions (ordered by priority)
  • Confidence score for diagnosis (HIGH/MEDIUM/LOW)
  • Escalation level (L1 resolvable / escalate to L2)
  • Summary for Jira ticket update

Security model
--------------
Agent 5 is a pure analysis and synthesis agent:
  • No external API calls
  • No AWS service calls (no Bedrock KB, DynamoDB, Auth0, Salesforce)
  • No writes to any system (read-only synthesis)
  • All inputs validated by Pydantic models from prior agents
  • Deterministic pattern matching (no hallucination)
  • Output is read-only (no side effects)
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Literal, List, Dict, Any

from pydantic import BaseModel, Field
from bedrock_agentcore import BedrockAgentCoreApp

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ciam-response-generator")

# Initialize Bedrock AgentCore app
# The real SDK's constructor only accepts debug/lifespan/middleware -- it
# does not take agent_name/agent_version (that was never a valid kwarg on
# the actual BedrockAgentCoreApp class, only on the conftest.py test stub
# that accepted **kwargs and silently ignored them). Calling it with those
# kwargs against the real SDK raises TypeError before the app can start.
app = BedrockAgentCoreApp()

# ============================================================================
# INPUT SCHEMAS (from Agents 2/3/4)
# ============================================================================

# Agent 2 inputs
class AccountRecord(BaseModel):
    account_name: str
    account_status: str
    customer_status: str
    active_tenant_count: int
    tenant_url: Optional[str] = None
    sf_user_exists: bool
    sf_user_active: bool


class DataFreshness(BaseModel):
    last_synced_at: Optional[datetime] = None
    age_hours: Optional[float] = None
    is_stale: bool = False


class AccountPayloadInput(BaseModel):
    agent: Literal["ciam-database-agent"]
    account_found: bool
    accounts: List[AccountRecord] = []
    data_freshness: DataFreshness
    data_warnings: List[str] = []
    error: Optional[str] = None


# Agent 3 inputs
class Auth0UserRecord(BaseModel):
    user_id: str
    email: str
    connection: str
    # Optional, not required: the orchestrator's AgentInvoker strips
    # datetime(...) values from Agent 3's response to None when parsing its
    # dict-repr payload (they aren't needed downstream by any consumer of
    # that parsed dict), and created_at is never used in synthesis logic
    # below -- only carried through as passthrough metadata. Matches
    # last_login's existing Optional pattern.
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    logins_count: int
    birthright: List[str] = []
    entitlements: List[str] = []
    last_sync: Optional[datetime] = None


class Auth0PayloadInput(BaseModel):
    agent: Literal["ciam-auth0-agent"]
    user_found: bool = False
    users: List[Auth0UserRecord] = []
    failed_logins_last_7_days: int = 0
    last_failed_login_reason: Optional[str] = None
    sync_stale: bool = False
    auth0_warnings: List[str] = []
    error: Optional[str] = None


# Agent 4 inputs
class BirthrightEvaluation(BaseModel):
    match: bool
    persona: str
    expected_birthright: List[str]
    actual_birthright: List[str]
    entitlements: List[str]
    missing_keywords: List[str]
    extra_keywords: List[str]
    explicit_block_detected: bool
    block_keywords_found: List[str]
    no_access_configured: bool


class FixClassification(BaseModel):
    complexity: Literal["SIMPLE_FIX", "ESCALATE_TO_L2", "NO_GAP"]
    reason: str
    recommended_actions: List[str]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]


class SyncDiagnostics(BaseModel):
    """Mirrors Agent 4's SyncDiagnostics -- CIAM ops feedback additions
    surfacing WHY a birthright gap exists, not just that one exists: a
    pending sync (user hasn't logged in since the Salesforce change) and
    multi-account/user ambiguity (accounts[0]/users[0] might not be the
    right record) both look identical to a real gap from missing_keywords
    alone."""
    pending_login_refresh: bool = False
    pending_login_refresh_note: Optional[str] = None
    multi_account_ambiguity: bool = False
    multi_account_ambiguity_reasons: List[str] = []


class KBDocument(BaseModel):
    title: str
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


class KnowledgeBasePayloadInput(BaseModel):
    agent: Literal["ciam-knowledge-base-agent"]
    birthright_evaluation: Optional[BirthrightEvaluation] = None
    fix_classification: Optional[FixClassification] = None
    sync_diagnostics: Optional[SyncDiagnostics] = None
    knowledge_base_results: KnowledgeBaseResults = KnowledgeBaseResults()
    knowledge_base_error: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# OUTPUT SCHEMAS
# ============================================================================

class RecommendedAction(BaseModel):
    """A single recommended action with priority and execution details."""
    priority: Literal["IMMEDIATE", "NEXT", "OPTIONAL"]
    action: str = Field(
        description="The specific action to take (e.g., 'Add entitlements:[Community]')"
    )
    rationale: str = Field(
        description="Why this action is recommended"
    )
    complexity: Literal["SIMPLE", "COMPLEX"] = Field(
        description="Can L1 execute this, or does it need L2/other teams?"
    )
    estimated_effort: str = Field(
        description="Expected effort (minutes for simple, hours for complex)"
    )


class RootCauseDiagnosis(BaseModel):
    """The synthesized root cause based on all agent findings."""
    primary_cause: str = Field(
        description="The main issue causing the ticket"
    )
    secondary_causes: List[str] = Field(
        default_factory=list,
        description="Other contributing factors, if any"
    )
    evidence: List[str] = Field(
        description="Specific findings that support this diagnosis"
    )
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="Confidence in this diagnosis"
    )


class ResolutionPath(BaseModel):
    """The recommended path to resolve the issue."""
    escalation_level: Literal["L1_RESOLVABLE", "ESCALATE_TO_L2", "ESCALATE_TO_L3"] = Field(
        description="Can L1 handle this, or does it need L2/L3?"
    )
    actions: List[RecommendedAction] = Field(
        description="Ordered list of recommended actions"
    )
    estimated_resolution_time: str = Field(
        description="Expected time to resolve (e.g., '5 minutes', '1-2 hours')"
    )
    fallback_escalation: Optional[str] = Field(
        default=None,
        description="If actions don't resolve, escalate to this team"
    )


class SimilarPastCase(BaseModel):
    """A similar case from KB that has been resolved."""
    reference: str = Field(
        description="Ticket key or document reference"
    )
    summary: str = Field(
        description="What the issue was"
    )
    resolution: str = Field(
        description="How it was resolved"
    )
    relevance: float = Field(
        description="How relevant (0-1 scale)"
    )


class AnalysisMetadata(BaseModel):
    """Analysis metadata and data quality notes."""
    data_completeness: Literal["COMPLETE", "PARTIAL", "MISSING"]
    stale_data_detected: bool
    conflicting_signals: List[str] = Field(
        default_factory=list,
        description="Places where Agent 2/3/4 outputs conflict or are unclear"
    )
    reasoning_notes: List[str] = Field(
        default_factory=list,
        description="Internal notes on the reasoning process"
    )


class ResponseGeneratorPayload(BaseModel):
    """Final output from Agent 5."""
    schema_version: Literal["1.0"] = "1.0"
    spec_id: Literal["SPEC-CIAM-0005"] = "SPEC-CIAM-0005"
    agent: Literal["ciam-response-generator"] = "ciam-response-generator"
    run_id: str
    synthesized_at: datetime

    # Core diagnosis and resolution
    root_cause: RootCauseDiagnosis
    resolution_path: ResolutionPath

    # Supporting information
    similar_past_cases: List[SimilarPastCase] = Field(
        default_factory=list,
        description="Similar issues that were resolved (from KB)"
    )

    # Jira integration
    jira_summary: str = Field(
        description="One-line summary for Jira ticket title"
    )
    jira_description: str = Field(
        description="Detailed analysis for Jira ticket description"
    )

    # Quality/metadata
    metadata: AnalysisMetadata
    error: Optional[str] = None


# ============================================================================
# SYNTHESIS LOGIC
# ============================================================================

def _rationale_for_missing_portal_action(action_text: str, missing: List[str]) -> str:
    """Pattern 1's recommended_actions can contain qualitatively different
    KINDS of steps -- trigger a re-login, add entitlements, verify the fix
    worked -- since Agent 4 started distinguishing "pending login sync" from
    a real gap (CIAM ops feedback). A single blanket rationale no longer
    fits all of them: labeling a "log out and log back in" step with
    "compensated via entitlements" is simply wrong, since that step has
    nothing to do with entitlements. Derive the rationale from what the
    action text actually asks for, instead of restating the same sentence
    for every action regardless of content."""
    text_lower = action_text.lower()
    missing_str = ", ".join(missing) if missing else "the affected portal(s)"

    # Check "entitlements" BEFORE the login phrases: the conditional
    # follow-up action ("If still missing after a fresh login, add ... to
    # ENTITLEMENTS") legitimately mentions "fresh login" too, but its actual
    # instruction is the entitlements change -- the login mention there is
    # backward-referencing the prior step, not a new instruction to log in.
    # A pure "log out and log back in" action never mentions entitlements at
    # all, so checking this first doesn't miscategorize that one.
    if "entitlements" in text_lower:
        return (
            f"Missing portal(s) {missing_str} can be compensated via entitlements; "
            "birthright itself is not directly editable"
        )
    if any(phrase in text_lower for phrase in ("log out", "log back in", "fresh login", "re-login")):
        return (
            "A login is what actually triggers NetskopeID-Sync-2 to recompute birthright from "
            "current Salesforce data -- this may resolve the gap with no manual change at all"
        )
    if text_lower.startswith("verify"):
        return f"Confirms the fix actually restored access to {missing_str} for this user"
    # Fallback for any action text that doesn't match a known pattern above --
    # still accurate, just less specific than the three cases above.
    return f"Recommended step toward resolving missing portal access: {missing_str}"


class ResponseGenerator:
    """Synthesizes Agent 2/3/4 findings into diagnosis and recommendations."""

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or str(uuid.uuid4())
        self.logger = logging.getLogger(f"ciam-response-generator-{self.run_id[:8]}")

    def synthesize(
        self,
        account_payload: AccountPayloadInput,
        auth0_payload: Auth0PayloadInput,
        kb_payload: KnowledgeBasePayloadInput,
        ticket_email: str,
        ticket_intent: Optional[str] = None,
    ) -> ResponseGeneratorPayload:
        """
        Synthesize all agent findings into a single diagnosis.

        Args:
            account_payload: Agent 2 output (database records)
            auth0_payload: Agent 3 output (Auth0 metadata)
            kb_payload: Agent 4 output (birthright evaluation + KB)
            ticket_email: Original user email from ticket
            ticket_intent: User's stated intent (from Agent 1)

        Returns:
            ResponseGeneratorPayload with diagnosis, actions, and Jira output
        """
        try:
            # Step 1: Assess data completeness
            metadata = self._assess_data_quality(
                account_payload, auth0_payload, kb_payload
            )

            # Step 2: Extract key facts from each agent
            account_facts = self._extract_account_facts(account_payload)
            auth0_facts = self._extract_auth0_facts(auth0_payload)
            kb_facts = self._extract_kb_facts(kb_payload)

            # Step 3: Synthesize root cause
            root_cause = self._diagnose_root_cause(
                account_facts, auth0_facts, kb_facts, ticket_intent
            )

            # Step 4: Recommend resolution path
            resolution_path = self._recommend_resolution(
                root_cause, account_facts, auth0_facts, kb_facts
            )

            # Step 5: Extract similar past cases from KB
            similar_cases = self._extract_similar_cases(kb_payload)

            # Step 6: Generate Jira output
            jira_summary = self._generate_jira_summary(root_cause)
            jira_description = self._generate_jira_description(
                root_cause, resolution_path, similar_cases
            )

            return ResponseGeneratorPayload(
                run_id=self.run_id,
                synthesized_at=datetime.now(timezone.utc),
                root_cause=root_cause,
                resolution_path=resolution_path,
                similar_past_cases=similar_cases,
                jira_summary=jira_summary,
                jira_description=jira_description,
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error(f"Synthesis failed: {e}", exc_info=True)
            raise

    def _assess_data_quality(
        self,
        account_payload: AccountPayloadInput,
        auth0_payload: Auth0PayloadInput,
        kb_payload: KnowledgeBasePayloadInput,
    ) -> AnalysisMetadata:
        """Assess completeness and staleness of data from all agents."""
        completeness = "COMPLETE"
        stale = False
        conflicts = []
        notes = []

        # Check for errors
        if account_payload.error:
            completeness = "PARTIAL"
            conflicts.append(account_payload.error)
        if auth0_payload.error:
            completeness = "PARTIAL"
            conflicts.append(auth0_payload.error)
        if kb_payload.error:
            completeness = "PARTIAL"
            conflicts.append(kb_payload.error)

        # Check for missing data
        if not account_payload.account_found or not auth0_payload.user_found:
            completeness = "MISSING"
            notes.append("User or account not found in database or Auth0")

        # Check for stale sync
        if auth0_payload.sync_stale or account_payload.data_freshness.is_stale:
            stale = True
            notes.append("Data may be stale (sync older than expected)")

        # Check for conflicting signals
        if account_payload.data_warnings:
            conflicts.extend(account_payload.data_warnings)
        if auth0_payload.auth0_warnings:
            conflicts.extend(auth0_payload.auth0_warnings)

        return AnalysisMetadata(
            data_completeness=completeness,
            stale_data_detected=stale,
            conflicting_signals=conflicts,
            reasoning_notes=notes,
        )

    def _extract_account_facts(self, payload: AccountPayloadInput) -> Dict[str, Any]:
        """Extract key facts from Agent 2 account data."""
        self.logger.info(
            f"Extracting account facts: account_found={payload.account_found}, "
            f"accounts_count={len(payload.accounts) if payload.accounts else 0}"
        )

        if payload.error:
            self.logger.warning(f"Agent 2 error: {payload.error}")
            return {"error": f"Agent 2 error: {payload.error}"}

        if not payload.account_found:
            self.logger.info("Agent 2: account_found=False")
            return {"error": "No account found"}

        if not payload.accounts:
            self.logger.warning(
                "Agent 2 inconsistency: account_found=True but accounts list is empty"
            )
            return {"error": "No account found"}

        account = payload.accounts[0]
        self.logger.info(
            f"Extracted account: {account.account_name} "
            f"(status={account.account_status}, customer={account.customer_status})"
        )
        return {
            "account_name": account.account_name,
            "account_status": account.account_status,
            "customer_status": account.customer_status,
            "active_tenants": account.active_tenant_count,
            "sf_user_exists": account.sf_user_exists,
            "sf_user_active": account.sf_user_active,
            "data_freshness": payload.data_freshness,
        }

    def _extract_auth0_facts(self, payload: Auth0PayloadInput) -> Dict[str, Any]:
        """Extract key facts from Agent 3 Auth0 data."""
        if not payload.user_found or not payload.users:
            return {"error": "No Auth0 user found"}

        user = payload.users[0]
        return {
            "user_id": user.user_id,
            "email": user.email,
            "connection": user.connection,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "logins_count": user.logins_count,
            "birthright": user.birthright,
            "entitlements": user.entitlements,
            "last_sync": user.last_sync,
            "failed_logins_7d": payload.failed_logins_last_7_days,
            "sync_stale": payload.sync_stale,
        }

    def _extract_kb_facts(self, payload: KnowledgeBasePayloadInput) -> Dict[str, Any]:
        """Extract key facts from Agent 4 KB evaluation."""
        facts = {}

        if payload.birthright_evaluation:
            facts["birthright"] = {
                "match": payload.birthright_evaluation.match,
                "persona": payload.birthright_evaluation.persona,
                "expected": payload.birthright_evaluation.expected_birthright,
                "actual": payload.birthright_evaluation.actual_birthright,
                "missing": payload.birthright_evaluation.missing_keywords,
                "extra": payload.birthright_evaluation.extra_keywords,
                "block_detected": payload.birthright_evaluation.explicit_block_detected,
                "block_keywords": payload.birthright_evaluation.block_keywords_found,
                "no_access": payload.birthright_evaluation.no_access_configured,
            }

        if payload.fix_classification:
            facts["fix"] = {
                "complexity": payload.fix_classification.complexity,
                "reason": payload.fix_classification.reason,
                "recommended_actions": payload.fix_classification.recommended_actions,
                "confidence": payload.fix_classification.confidence,
            }

        if payload.sync_diagnostics:
            facts["sync_diagnostics"] = {
                "pending_login_refresh": payload.sync_diagnostics.pending_login_refresh,
                "pending_login_refresh_note": payload.sync_diagnostics.pending_login_refresh_note,
                "multi_account_ambiguity": payload.sync_diagnostics.multi_account_ambiguity,
                "multi_account_ambiguity_reasons": payload.sync_diagnostics.multi_account_ambiguity_reasons,
            }

        if payload.knowledge_base_results:
            facts["kb_matches"] = {
                "docs": len(payload.knowledge_base_results.relevant_docs),
                "tickets": len(payload.knowledge_base_results.similar_past_tickets),
            }

        return facts

    def _diagnose_root_cause(
        self,
        account_facts: Dict[str, Any],
        auth0_facts: Dict[str, Any],
        kb_facts: Dict[str, Any],
        ticket_intent: Optional[str],
    ) -> RootCauseDiagnosis:
        """
        Synthesize root cause from all facts.
        Uses heuristic logic based on patterns, NOT hallucination.
        """
        primary_cause = "Insufficient information for diagnosis"
        secondary_causes = []
        evidence = []
        confidence = "LOW"
        sync_diag = kb_facts.get("sync_diagnostics") or {}

        # Pattern -1: Multi-account/user ambiguity from Agent 4 (checked before
        # EVERYTHING else, including Pattern 0) -- if accounts[0]/users[0] might
        # not even be the correct record for this email, every other signal
        # below (over-provisioning, missing keywords, etc.) could be about the
        # wrong record entirely. CIAM ops feedback.
        if sync_diag.get("multi_account_ambiguity"):
            reasons = sync_diag.get("multi_account_ambiguity_reasons") or []
            primary_cause = "Multiple accounts/records found for this email -- cannot confirm correct record"
            evidence.extend(reasons)
            if kb_facts.get("fix", {}).get("reason"):
                evidence.append(kb_facts["fix"]["reason"])
            confidence = kb_facts.get("fix", {}).get("confidence", "LOW")

        # Pattern -0.5: Auth0 Action code drift detected live (Agent 4's Tool 5,
        # via classify_fix_complexity). Same regression class Pattern 0 below
        # guards against: an ESCALATE_TO_L2 classification from Agent 4 must
        # never be silently re-derived into a lower-priority pattern (e.g.
        # Pattern 3's "Missing portal access") just because this specific
        # signal doesn't have its own dedicated kb_facts field the way
        # extra_keywords does. Matched on the reason text Agent 4 always
        # includes verbatim for this case (see classify_fix_complexity).
        elif (
            kb_facts.get("fix", {}).get("complexity") == "ESCALATE_TO_L2"
            and "auth0 action responsible for computing birthright" in (kb_facts.get("fix", {}).get("reason") or "").lower()
        ):
            primary_cause = "Auth0 Action code may be miscalculating birthright/entitlements"
            evidence.append(kb_facts["fix"]["reason"])
            confidence = kb_facts["fix"].get("confidence", "MEDIUM")

        # Pattern 0: Over-provisioned / security escalation from Agent 4 (checked
        # ahead of every other remaining pattern including account-not-found).
        # Agent 4 already classifies this ESCALATE_TO_L2 with HIGH confidence
        # specifically because it's a security risk that must not be
        # auto-remediated -- a data-completeness issue like "no account record"
        # must never silently downgrade that into an L1 sync-refresh
        # recommendation (confirmed regression: CIAM-5001/CIAM-6010 both had this
        # pattern and were incorrectly downgraded to L1_RESOLVABLE before this fix).
        elif (
            kb_facts.get("fix", {}).get("complexity") == "ESCALATE_TO_L2"
            and kb_facts.get("birthright", {}).get("extra")
        ):
            extra = kb_facts["birthright"]["extra"]
            primary_cause = f"Over-provisioned access: {', '.join(extra)}"
            evidence.append(f"Extra keywords not expected for persona: {extra}")
            if kb_facts["fix"].get("reason"):
                evidence.append(kb_facts["fix"]["reason"])
            confidence = kb_facts["fix"].get("confidence", "HIGH")

        # Pattern 2A: No account found in database (check first)
        elif account_facts.get("error") == "No account found":
            primary_cause = "Account not found in Netskope or Salesforce"
            evidence.append("Database lookup returned no account")
            confidence = "HIGH"

        # Pattern 1: No Auth0 user found
        elif auth0_facts.get("error") == "No Auth0 user found":
            primary_cause = "User not created in Auth0"
            evidence.append("Auth0 lookup returned no user")
            if account_facts.get("sf_user_exists"):
                evidence.append("But user exists in Salesforce")
                secondary_causes.append("JIT provisioning may have failed")
            confidence = "HIGH"

        # Pattern 7: No access configured at all (check before birthright mismatch)
        elif kb_facts.get("birthright", {}).get("no_access"):
            primary_cause = "No portal access configured"
            evidence.append("Neither birthright nor entitlements have any keywords")
            confidence = "HIGH"

        # Pattern 3: Birthright mismatch. If Agent 4 flagged pending_login_refresh
        # (Salesforce changed after this user's last login, so sync hasn't had a
        # chance to run), label it distinctly -- the primary_cause text still
        # contains "Missing portal access" so the existing resolution Pattern 1
        # below still matches and reuses Agent 4's recommended_actions (which
        # already prefer "ask the user to log back in" over an immediate manual
        # entitlements edit in this case).
        elif kb_facts.get("birthright", {}).get("missing"):
            missing = kb_facts["birthright"]["missing"]
            if sync_diag.get("pending_login_refresh"):
                primary_cause = f"Missing portal access (pending sync): {', '.join(missing)}"
                if sync_diag.get("pending_login_refresh_note"):
                    evidence.append(sync_diag["pending_login_refresh_note"])
            else:
                primary_cause = f"Missing portal access: {', '.join(missing)}"
            evidence.append(f"Expected birthright: {kb_facts['birthright']['expected']}")
            evidence.append(f"Actual birthright: {kb_facts['birthright']['actual']}")

            # Sub-pattern: sync is stale
            if auth0_facts.get("sync_stale"):
                secondary_causes.append("Auth0 sync may be stale")
                evidence.append(f"Last sync: {auth0_facts.get('last_sync')}")

            confidence = "MEDIUM" if len(kb_facts["birthright"]["missing"]) == 1 else "MEDIUM"

        # Pattern 4: Block keyword detected
        elif kb_facts.get("birthright", {}).get("block_detected"):
            block_keywords = kb_facts["birthright"]["block_keywords"]
            primary_cause = f"Access explicitly blocked: {', '.join(block_keywords)}"
            evidence.append("Block keywords override all grants")
            confidence = "HIGH"

        # Pattern 5: Multiple failed logins
        elif auth0_facts.get("failed_logins_7d", 0) > 3:
            primary_cause = "Multiple failed login attempts"
            secondary_causes.append(f"Failed logins: {auth0_facts['failed_logins_7d']} in last 7 days")
            evidence.append(f"Last failure reason: {auth0_facts.get('last_failed_login_reason', 'unknown')}")
            confidence = "MEDIUM"

        # Pattern 6: Salesforce user doesn't exist or is inactive
        elif not account_facts.get("sf_user_exists") or not account_facts.get("sf_user_active"):
            primary_cause = "Salesforce user missing or deactivated"
            evidence.append(f"SF user exists: {account_facts.get('sf_user_exists')}")
            evidence.append(f"SF user active: {account_facts.get('sf_user_active')}")
            confidence = "HIGH"

        return RootCauseDiagnosis(
            primary_cause=primary_cause,
            secondary_causes=secondary_causes,
            evidence=evidence,
            confidence=confidence,
        )

    def _recommend_resolution(
        self,
        root_cause: RootCauseDiagnosis,
        account_facts: Dict[str, Any],
        auth0_facts: Dict[str, Any],
        kb_facts: Dict[str, Any],
    ) -> ResolutionPath:
        """Recommend specific actions based on root cause."""
        actions = []
        escalation = "L1_RESOLVABLE"
        estimated_time = "unknown"
        fallback = None

        # Pattern -1: Multi-account/user ambiguity (matches Pattern -1 in
        # _diagnose_root_cause). Checked before EVERYTHING else -- disambiguation
        # must happen before any other recommended action, since every other
        # signal could be about the wrong account/user record.
        if "Multiple accounts/records found" in root_cause.primary_cause:
            recommended = kb_facts.get("fix", {}).get("recommended_actions") or [
                "Confirm which account/tenant this ticket is about before taking any action",
                "Escalate to L2 for account disambiguation",
            ]
            for action_text in recommended:
                actions.append(
                    RecommendedAction(
                        priority="IMMEDIATE",
                        action=action_text,
                        rationale="Multiple accounts/Auth0 records found for this email -- risk of diagnosing the wrong record",
                        complexity="COMPLEX",
                        estimated_effort="review required",
                    )
                )
            escalation = "ESCALATE_TO_L2"
            fallback = "CIAM Support Lead"
            estimated_time = "15-30 minutes"

        # Pattern -0.5: Auth0 Action code drift (matches Pattern -0.5 in
        # _diagnose_root_cause). Reuses Agent 4's recommended_actions, same
        # approach as every other escalation pattern here.
        elif "Auth0 Action code may be miscalculating" in root_cause.primary_cause:
            recommended = kb_facts.get("fix", {}).get("recommended_actions") or [
                "Review the current Auth0 Action code before making any entitlements change",
                "Escalate to L2 / Auth0 Action owner for code review",
            ]
            for action_text in recommended:
                actions.append(
                    RecommendedAction(
                        priority="IMMEDIATE",
                        action=action_text,
                        rationale="Auth0 Action code drift detected -- apparent access gap may be a code bug, not a data issue",
                        complexity="COMPLEX",
                        estimated_effort="review required",
                    )
                )
            escalation = "ESCALATE_TO_L2"
            fallback = "Auth0 Action Owner / L2 Team"
            estimated_time = "1-2 hours"

        # Pattern 0: Over-provisioned / security escalation (matches the new Pattern 0 in
        # _diagnose_root_cause). Must be checked before any other pattern -- in particular
        # before the stale-sync elif below, which this used to silently fall through into,
        # producing a misleading "trigger sync refresh" / L1_RESOLVABLE recommendation for
        # what Agent 4 explicitly flagged as a security risk requiring L2 review.
        elif "Over-provisioned access" in root_cause.primary_cause:
            recommended = kb_facts.get("fix", {}).get("recommended_actions") or [
                "Review over-provisioned keywords",
                "Do not modify entitlements without L2 approval",
            ]
            for action_text in recommended:
                actions.append(
                    RecommendedAction(
                        priority="IMMEDIATE",
                        action=action_text,
                        rationale="Security risk -- user has more access than entitled; must not auto-remediate",
                        complexity="COMPLEX",
                        estimated_effort="review required",
                    )
                )
            escalation = "ESCALATE_TO_L2"
            fallback = "CIAM Security / L2 Team"
            estimated_time = "1-2 hours"

        # Pattern 1: Missing portal access -- compensate via ENTITLEMENTS, never birthright.
        # Birthright is Salesforce-computed (by NetskopeID-Sync-2) and is recalculated/
        # overwritten on every login; it is never manually edited (see Agent 4's classify_fix_
        # complexity docstring for the same hard rule). This reuses Agent 4's own
        # recommended_actions text -- same approach as Pattern 0 above -- instead of re-deriving
        # separate wording here, which is what previously produced the incorrect and undefined
        # "Add '{portal}' to birthright entitlements" phrasing (birthright and entitlements are
        # two distinct fields; that phrase conflated them and implied birthright is editable).
        elif "Missing portal access" in root_cause.primary_cause:
            missing = kb_facts.get("birthright", {}).get("missing", [])
            recommended = kb_facts.get("fix", {}).get("recommended_actions") or [
                f"Add {missing} to the entitlements array via Auth0 Management API "
                "(entitlements, not birthright -- birthright is Salesforce-computed and read-only)"
            ]
            for action_text in recommended:
                actions.append(
                    RecommendedAction(
                        priority="IMMEDIATE",
                        action=action_text,
                        rationale=_rationale_for_missing_portal_action(action_text, missing),
                        complexity="SIMPLE",
                        estimated_effort="2 minutes",
                    )
                )
            estimated_time = "5 minutes"

        # Pattern 2: Block keyword (L1 escalation required)
        elif "Access explicitly blocked" in root_cause.primary_cause:
            actions.append(
                RecommendedAction(
                    priority="IMMEDIATE",
                    action="Review and remove block keyword from entitlements",
                    rationale="Block keywords are manual overrides; verify if still needed",
                    complexity="COMPLEX",
                    estimated_effort="15 minutes",
                )
            )
            escalation = "ESCALATE_TO_L2"
            fallback = "CIAM Team Lead"
            estimated_time = "30 minutes"

        # Pattern 3: Stale sync (L1 can trigger refresh)
        elif auth0_facts.get("sync_stale"):
            actions.append(
                RecommendedAction(
                    priority="NEXT",
                    action="Trigger manual NetskopeID sync refresh",
                    rationale="Auth0 sync is stale; refreshing may resolve access issues",
                    complexity="SIMPLE",
                    estimated_effort="3 minutes",
                )
            )
            estimated_time = "10 minutes"

        # Pattern 4: User not in Auth0 (must escalate)
        elif "not created in Auth0" in root_cause.primary_cause:
            actions.append(
                RecommendedAction(
                    priority="IMMEDIATE",
                    action="Initiate user creation in Auth0 (DynamoDB → Auth0 sync)",
                    rationale="User exists in Salesforce but not in Auth0 yet",
                    complexity="COMPLEX",
                    estimated_effort="30 minutes",
                )
            )
            escalation = "ESCALATE_TO_L2"
            fallback = "NetskopeID Sync Team"
            estimated_time = "1-2 hours"

        # Pattern 5: Salesforce user issues (must escalate)
        elif "Salesforce" in root_cause.primary_cause:
            actions.append(
                RecommendedAction(
                    priority="IMMEDIATE",
                    action="Investigate Salesforce user status",
                    rationale="Salesforce user missing or deactivated; cannot proceed without SF user",
                    complexity="COMPLEX",
                    estimated_effort="30 minutes",
                )
            )
            escalation = "ESCALATE_TO_L2"
            fallback = "Salesforce Admin"
            estimated_time = "1-2 hours"

        # Pattern 6: Multiple failed logins (suspicious activity)
        elif "Multiple failed login" in root_cause.primary_cause:
            actions.append(
                RecommendedAction(
                    priority="IMMEDIATE",
                    action="Confirm user credentials are correct",
                    rationale="Multiple failed logins suggest wrong password or account compromise",
                    complexity="SIMPLE",
                    estimated_effort="5 minutes",
                )
            )
            actions.append(
                RecommendedAction(
                    priority="NEXT",
                    action="If needed: Force password reset",
                    rationale="User can reset password via Auth0 or help desk",
                    complexity="SIMPLE",
                    estimated_effort="5 minutes",
                )
            )
            estimated_time = "15 minutes"

        # Fallback: generic escalation
        if not actions:
            actions.append(
                RecommendedAction(
                    priority="NEXT",
                    action="Escalate for manual investigation",
                    rationale=f"Root cause: {root_cause.primary_cause}",
                    complexity="COMPLEX",
                    estimated_effort="varies",
                )
            )
            escalation = "ESCALATE_TO_L2"
            estimated_time = "1-4 hours"

        return ResolutionPath(
            escalation_level=escalation,
            actions=actions,
            estimated_resolution_time=estimated_time,
            fallback_escalation=fallback,
        )

    def _extract_similar_cases(self, payload: KnowledgeBasePayloadInput) -> List[SimilarPastCase]:
        """Extract similar past cases from KB results."""
        cases = []

        if payload.knowledge_base_results:
            for ticket in payload.knowledge_base_results.similar_past_tickets[:3]:
                cases.append(
                    SimilarPastCase(
                        reference=ticket.ticket_key,
                        summary=ticket.summary,
                        resolution=ticket.resolution or "Not documented",
                        relevance=ticket.relevance_score,
                    )
                )

        return cases

    def _generate_jira_summary(self, root_cause: RootCauseDiagnosis) -> str:
        """Generate one-line summary for Jira ticket."""
        return root_cause.primary_cause

    def _generate_jira_description(
        self,
        root_cause: RootCauseDiagnosis,
        resolution_path: ResolutionPath,
        similar_cases: List[SimilarPastCase],
    ) -> str:
        """Generate detailed description for Jira ticket."""
        lines = [
            "h2. Diagnosis",
            "",
            f"*Root Cause:* {root_cause.primary_cause}",
            f"*Confidence:* {root_cause.confidence}",
            "",
        ]

        if root_cause.evidence:
            lines.append("*Evidence:*")
            for evidence in root_cause.evidence:
                lines.append(f"* {evidence}")
            lines.append("")

        if root_cause.secondary_causes:
            lines.append("*Secondary Causes:*")
            for cause in root_cause.secondary_causes:
                lines.append(f"* {cause}")
            lines.append("")

        lines.extend([
            "h2. Recommended Actions",
            "",
            f"*Escalation Level:* {resolution_path.escalation_level}",
            f"*Estimated Time:* {resolution_path.estimated_resolution_time}",
            "",
        ])

        for i, action in enumerate(resolution_path.actions, 1):
            lines.append(f"{i}. [{action.priority}] {action.action}")
            lines.append(f"   - Rationale: {action.rationale}")
            lines.append(f"   - Effort: {action.estimated_effort}")
            lines.append("")

        if resolution_path.fallback_escalation:
            lines.append(f"*Fallback Escalation:* {resolution_path.fallback_escalation}")
            lines.append("")

        if similar_cases:
            lines.append("h2. Similar Past Cases")
            lines.append("")
            for case in similar_cases:
                lines.append(f"* [{case.reference}] {case.summary} ({case.relevance:.2%} match)")
                if case.resolution != "Not documented":
                    lines.append(f"  Resolution: {case.resolution}")
            lines.append("")

        return "\n".join(lines)


# ============================================================================
# BEDROCK AGENTCORE HANDLER
# ============================================================================

@app.entrypoint
def handle_response_generation(
    payload: Dict[str, Any],
) -> dict:
    """
    Bedrock AgentCore handler for Agent 5.

    Receives consolidated payloads from the orchestrator and returns
    a synthesized diagnosis.

    Args:
        payload: Dictionary with keys:
            - account_payload: AccountPayloadInput (Agent 2)
            - auth0_payload: Auth0PayloadInput (Agent 3)
            - kb_payload: KnowledgeBasePayloadInput (Agent 4)
            - ticket_email: str (from Agent 1)
            - ticket_intent: Optional[str] (from Agent 1)
            - run_id: Optional[str] (from AgentCore header)

    Returns:
        ResponseGeneratorPayload.model_dump() -- a plain dict, matching the
        return convention every other agent uses (Agents 2/3/4 all call
        .model_dump() too). Returning the raw Pydantic model here previously
        serialized as its str()/repr() form (`field=val field=val ...`)
        instead of JSON -- confirmed via a live orchestrator run where
        synthesis_payload fell back to {"_raw": ...} in AgentInvoker because
        the response body wasn't valid dict-literal syntax at all (unlike
        Agents 2/3/4's model_dump() output, which at least parses as a
        Python dict literal even with embedded datetime(...) calls).
    """
    try:
        # Log input structure for debugging data flow issues
        logger.info(f"Received payload keys: {list(payload.keys())}")
        logger.info(
            f"Agent 2 payload present: {'account_payload' in payload}, "
            f"Agent 3 payload present: {'auth0_payload' in payload}, "
            f"Agent 4 payload present: {'kb_payload' in payload}"
        )

        # Extract inputs
        account_payload_raw = payload.get("account_payload", {})
        logger.info(f"Account payload keys: {list(account_payload_raw.keys()) if isinstance(account_payload_raw, dict) else 'not a dict'}")

        account_payload = AccountPayloadInput(**account_payload_raw)
        auth0_payload = Auth0PayloadInput(**payload.get("auth0_payload", {}))
        kb_payload = KnowledgeBasePayloadInput(**payload.get("kb_payload", {}))
        ticket_email = payload.get("ticket_email", "unknown@example.com")
        ticket_intent = payload.get("ticket_intent")
        run_id = payload.get("run_id", str(uuid.uuid4()))

        # Create generator and synthesize
        generator = ResponseGenerator(run_id=run_id)
        result = generator.synthesize(
            account_payload=account_payload,
            auth0_payload=auth0_payload,
            kb_payload=kb_payload,
            ticket_email=ticket_email,
            ticket_intent=ticket_intent,
        )

        return result.model_dump()

    except Exception as e:
        logger.error(f"Synthesis failed: {e}", exc_info=True)
        # Return error payload
        return ResponseGeneratorPayload(
            run_id=payload.get("run_id", str(uuid.uuid4())),
            synthesized_at=datetime.now(timezone.utc),
            root_cause=RootCauseDiagnosis(
                primary_cause="Agent 5 synthesis error",
                secondary_causes=[],
                evidence=[str(e)],
                confidence="LOW",
            ),
            resolution_path=ResolutionPath(
                escalation_level="ESCALATE_TO_L2",
                actions=[
                    RecommendedAction(
                        priority="IMMEDIATE",
                        action="Agent 5 encountered an error; escalate to L2",
                        rationale="Internal synthesis error",
                        complexity="COMPLEX",
                        estimated_effort="30 minutes",
                    )
                ],
                estimated_resolution_time="1+ hours",
                fallback_escalation="CIAM Team Lead",
            ),
            jira_summary="Agent 5 synthesis error — escalate to L2",
            jira_description=f"# Synthesis Error\n\nAgent 5 encountered an error during synthesis:\n\n{str(e)}",
            metadata=AnalysisMetadata(
                data_completeness="MISSING",
                stale_data_detected=False,
                conflicting_signals=[str(e)],
                reasoning_notes=["Synthesis handler exception"],
            ),
            error=str(e),
        ).model_dump()


# ============================================================================
# AGENTCORE MAIN ENTRY
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting CIAM Response Generator Agent (Agent 5)")
    logger.info(f"Version: 0.2.0")
    logger.info(f"Spec: SPEC-CIAM-0005")
    app.run()
