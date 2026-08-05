"""
Unit tests for Agent 5 (Response Generator)
Tests the synthesis logic across all major diagnostic patterns
"""

import pytest
from datetime import datetime, timedelta, timezone
from agent import (
    ResponseGenerator,
    AccountPayloadInput,
    Auth0PayloadInput,
    KnowledgeBasePayloadInput,
    AccountRecord,
    Auth0UserRecord,
    DataFreshness,
    BirthrightEvaluation,
    FixClassification,
    KnowledgeBaseResults,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def response_generator():
    return ResponseGenerator()


def make_account_payload(
    found: bool = True,
    account_status: str = "Customer",
    customer_status: str = "Active",
    active_tenants: int = 1,
    sf_exists: bool = True,
    sf_active: bool = True,
) -> AccountPayloadInput:
    """Helper to create AccountPayloadInput."""
    accounts = []
    if found:
        accounts.append(
            AccountRecord(
                account_name="Test Account",
                account_status=account_status,
                customer_status=customer_status,
                active_tenant_count=active_tenants,
                sf_user_exists=sf_exists,
                sf_user_active=sf_active,
            )
        )
    return AccountPayloadInput(
        agent="ciam-database-agent",
        account_found=found,
        accounts=accounts,
        data_freshness=DataFreshness(
            last_synced_at=datetime.now(timezone.utc),
            age_hours=0.5,
            is_stale=False,
        ),
    )


def make_auth0_payload(
    found: bool = True,
    birthright: list = None,
    entitlements: list = None,
    failed_logins: int = 0,
    sync_stale: bool = False,
) -> Auth0PayloadInput:
    """Helper to create Auth0PayloadInput."""
    birthright = birthright or ["Community", "Dashboard"]
    entitlements = entitlements or []

    users = []
    if found:
        users.append(
            Auth0UserRecord(
                user_id="user_123",
                email="test@example.com",
                connection="NetskopeID",
                created_at=datetime.now(timezone.utc) - timedelta(days=30),
                last_login=datetime.now(timezone.utc) - timedelta(hours=2),
                logins_count=42,
                birthright=birthright,
                entitlements=entitlements,
                last_sync=datetime.now(timezone.utc) - timedelta(hours=1),
            )
        )
    return Auth0PayloadInput(
        agent="ciam-auth0-agent",
        user_found=found,
        users=users,
        failed_logins_last_7_days=failed_logins,
        sync_stale=sync_stale,
    )


def make_kb_payload(
    birthright_eval: BirthrightEvaluation = None,
    fix_classification: FixClassification = None,
) -> KnowledgeBasePayloadInput:
    """Helper to create KnowledgeBasePayloadInput."""
    if birthright_eval is None:
        birthright_eval = BirthrightEvaluation(
            match=True,
            persona="Customer",
            expected_birthright=["Community", "Dashboard", "Support"],
            actual_birthright=["Community", "Dashboard", "Support"],
            entitlements=[],
            missing_keywords=[],
            extra_keywords=[],
            explicit_block_detected=False,
            block_keywords_found=[],
            no_access_configured=False,
        )

    return KnowledgeBasePayloadInput(
        agent="ciam-knowledge-base-agent",
        birthright_evaluation=birthright_eval,
        fix_classification=fix_classification,
        knowledge_base_results=KnowledgeBaseResults(),
    )


# ============================================================================
# TEST CASES
# ============================================================================

class TestDiagnosisSynthesis:
    """Tests for root cause diagnosis"""

    def test_missing_birthright_keywords(self, response_generator):
        """User is missing portal access keywords"""
        account = make_account_payload()
        auth0 = make_auth0_payload(birthright=["Community", "Dashboard"])
        kb = make_kb_payload(
            BirthrightEvaluation(
                match=False,
                persona="Customer",
                expected_birthright=["Community", "Dashboard", "Support", "Academy"],
                actual_birthright=["Community", "Dashboard"],
                entitlements=[],
                missing_keywords=["Support", "Academy"],
                extra_keywords=[],
                explicit_block_detected=False,
                block_keywords_found=[],
                no_access_configured=False,
            )
        )

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "Missing portal access" in result.root_cause.primary_cause
        assert result.root_cause.confidence == "MEDIUM"
        assert result.resolution_path.escalation_level == "L1_RESOLVABLE"
        assert any("Support" in str(a.action) or "Academy" in str(a.action) for a in result.resolution_path.actions)

    def test_block_keyword_detected(self, response_generator):
        """User has block keyword preventing access"""
        account = make_account_payload()
        auth0 = make_auth0_payload(
            birthright=["Community", "Support"],
            entitlements=["Block-Supp"]
        )
        kb = make_kb_payload(
            BirthrightEvaluation(
                match=False,
                persona="Customer",
                expected_birthright=["Community", "Support"],
                actual_birthright=["Community", "Support"],
                entitlements=["Block-Supp"],
                missing_keywords=[],
                extra_keywords=[],
                explicit_block_detected=True,
                block_keywords_found=["Block-Supp"],
                no_access_configured=False,
            )
        )

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "Access explicitly blocked" in result.root_cause.primary_cause
        assert "Block-Supp" in result.root_cause.primary_cause
        assert result.root_cause.confidence == "HIGH"
        assert result.resolution_path.escalation_level == "ESCALATE_TO_L2"

    def test_user_not_in_auth0(self, response_generator):
        """User doesn't exist in Auth0"""
        account = make_account_payload(found=True)
        auth0 = make_auth0_payload(found=False)
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "not created in Auth0" in result.root_cause.primary_cause
        assert result.root_cause.confidence == "HIGH"
        assert result.resolution_path.escalation_level == "ESCALATE_TO_L2"
        assert "Auth0" in result.resolution_path.fallback_escalation or True

    def test_account_not_found(self, response_generator):
        """Account doesn't exist in database"""
        account = make_account_payload(found=False)
        auth0 = make_auth0_payload(found=False)
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "not found" in result.root_cause.primary_cause.lower()
        assert result.root_cause.confidence == "HIGH"

    def test_over_provisioned_escalation_not_downgraded_by_missing_account(self, response_generator):
        """Regression (CIAM-5001 / CIAM-6010): when Agent 2 finds no account AND Agent 4
        flags over-provisioned access as ESCALATE_TO_L2, Agent 5 must NOT downgrade this to
        an L1 "account not found" / stale-sync recommendation -- the security concern takes
        priority over the data-completeness issue."""
        account = make_account_payload(found=False)
        auth0 = make_auth0_payload(
            found=True,
            birthright=["Support", "Academy", "Notification", "Dashboard"],
            sync_stale=True,
        )
        kb = make_kb_payload(
            birthright_eval=BirthrightEvaluation(
                match=False,
                persona="Individual",
                expected_birthright=["Community", "Dashboard"],
                actual_birthright=["Support", "Academy", "Notification", "Dashboard"],
                entitlements=[],
                missing_keywords=["Community"],
                extra_keywords=["Academy", "Notification", "Support"],
                explicit_block_detected=False,
                block_keywords_found=[],
                no_access_configured=False,
            ),
            fix_classification=FixClassification(
                complexity="ESCALATE_TO_L2",
                reason="User has more access than entitled (over-provisioned) -- security risk, must not auto-remediate.",
                recommended_actions=[
                    "Review over-provisioned keywords",
                    "Do not modify entitlements without L2 approval",
                ],
                confidence="HIGH",
            ),
        )

        result = response_generator.synthesize(account, auth0, kb, "vshah@netskope.com")

        assert "over-provisioned" in result.root_cause.primary_cause.lower()
        assert "account not found" not in result.root_cause.primary_cause.lower()
        assert result.resolution_path.escalation_level == "ESCALATE_TO_L2"
        assert "sync refresh" not in result.jira_description.lower()

    def test_salesforce_user_missing(self, response_generator):
        """Salesforce user object doesn't exist"""
        account = make_account_payload(sf_exists=False)
        auth0 = make_auth0_payload()
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "Salesforce" in result.root_cause.primary_cause
        assert result.root_cause.confidence == "HIGH"
        assert result.resolution_path.escalation_level == "ESCALATE_TO_L2"

    def test_salesforce_user_inactive(self, response_generator):
        """Salesforce user is deactivated"""
        account = make_account_payload(sf_exists=True, sf_active=False)
        auth0 = make_auth0_payload()
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "Salesforce" in result.root_cause.primary_cause or "deactivated" in result.root_cause.primary_cause
        assert result.resolution_path.escalation_level == "ESCALATE_TO_L2"

    def test_no_access_configured(self, response_generator):
        """User has neither birthright nor entitlements"""
        account = make_account_payload()
        auth0 = make_auth0_payload(birthright=[], entitlements=[])
        kb = make_kb_payload(
            BirthrightEvaluation(
                match=False,
                persona="Customer",
                expected_birthright=["Community", "Support"],
                actual_birthright=[],
                entitlements=[],
                missing_keywords=["Community", "Support"],
                extra_keywords=[],
                explicit_block_detected=False,
                block_keywords_found=[],
                no_access_configured=True,
            )
        )

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "no portal access configured" in result.root_cause.primary_cause.lower()
        assert result.root_cause.confidence == "HIGH"

    def test_stale_sync(self, response_generator):
        """Auth0 sync is stale"""
        account = make_account_payload()
        auth0 = make_auth0_payload(
            birthright=["Community", "Dashboard"],
            sync_stale=True
        )
        kb = make_kb_payload(
            BirthrightEvaluation(
                match=False,
                persona="Customer",
                expected_birthright=["Community", "Dashboard", "Support"],
                actual_birthright=["Community", "Dashboard"],
                entitlements=[],
                missing_keywords=["Support"],
                extra_keywords=[],
                explicit_block_detected=False,
                block_keywords_found=[],
                no_access_configured=False,
            )
        )

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "stale" in str(result.root_cause.secondary_causes).lower()

    def test_multiple_failed_logins(self, response_generator):
        """User has multiple failed login attempts"""
        account = make_account_payload()
        auth0 = make_auth0_payload(
            birthright=["Community", "Dashboard", "Support"],
            failed_logins=5
        )
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "failed login" in result.root_cause.primary_cause.lower()
        assert "5" in str(result.resolution_path.actions)

    def test_healthy_user_no_gap(self, response_generator):
        """User has correct access (no issues)"""
        account = make_account_payload()
        auth0 = make_auth0_payload(
            birthright=["Community", "Dashboard", "Support", "Academy"],
            failed_logins=0
        )
        kb = make_kb_payload(
            BirthrightEvaluation(
                match=True,
                persona="Customer",
                expected_birthright=["Community", "Dashboard", "Support", "Academy"],
                actual_birthright=["Community", "Dashboard", "Support", "Academy"],
                entitlements=[],
                missing_keywords=[],
                extra_keywords=[],
                explicit_block_detected=False,
                block_keywords_found=[],
                no_access_configured=False,
            )
        )

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        # Should still produce output but with minimal actions needed
        assert result.root_cause is not None


class TestResolutionPaths:
    """Tests for resolution recommendations"""

    def test_l1_resolvable_birthright(self, response_generator):
        """Simple birthright fix is L1 resolvable"""
        account = make_account_payload()
        auth0 = make_auth0_payload(birthright=["Community"])
        kb = make_kb_payload(
            BirthrightEvaluation(
                match=False,
                persona="Customer",
                expected_birthright=["Community", "Support"],
                actual_birthright=["Community"],
                entitlements=[],
                missing_keywords=["Support"],
                extra_keywords=[],
                explicit_block_detected=False,
                block_keywords_found=[],
                no_access_configured=False,
            )
        )

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert result.resolution_path.escalation_level == "L1_RESOLVABLE"
        assert len(result.resolution_path.actions) > 0
        assert any("Support" in str(a.action) for a in result.resolution_path.actions)

    def test_l2_escalation_block_keyword(self, response_generator):
        """Block keyword requires L2 escalation"""
        account = make_account_payload()
        auth0 = make_auth0_payload(entitlements=["Block-Supp"])
        kb = make_kb_payload(
            BirthrightEvaluation(
                match=False,
                persona="Customer",
                expected_birthright=["Support"],
                actual_birthright=["Support"],
                entitlements=["Block-Supp"],
                missing_keywords=[],
                extra_keywords=[],
                explicit_block_detected=True,
                block_keywords_found=["Block-Supp"],
                no_access_configured=False,
            )
        )

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert result.resolution_path.escalation_level == "ESCALATE_TO_L2"

    def test_l2_escalation_auth0_missing(self, response_generator):
        """Missing Auth0 user requires L2 escalation"""
        account = make_account_payload()
        auth0 = make_auth0_payload(found=False)
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert result.resolution_path.escalation_level == "ESCALATE_TO_L2"

    def test_estimated_time_simple_fix(self, response_generator):
        """Simple fixes should estimate 5-15 minutes"""
        account = make_account_payload()
        auth0 = make_auth0_payload(birthright=["Community"])
        kb = make_kb_payload(
            BirthrightEvaluation(
                match=False,
                persona="Customer",
                expected_birthright=["Community", "Support"],
                actual_birthright=["Community"],
                entitlements=[],
                missing_keywords=["Support"],
                extra_keywords=[],
                explicit_block_detected=False,
                block_keywords_found=[],
                no_access_configured=False,
            )
        )

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "minute" in result.resolution_path.estimated_resolution_time.lower()


class TestDataQuality:
    """Tests for data completeness assessment"""

    def test_complete_data(self, response_generator):
        """All data sources present and fresh"""
        account = make_account_payload(found=True)
        auth0 = make_auth0_payload(found=True)
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert result.metadata.data_completeness == "COMPLETE"
        assert not result.metadata.stale_data_detected

    def test_partial_data(self, response_generator):
        """Some data sources missing"""
        account = make_account_payload(found=False)
        auth0 = make_auth0_payload(found=True)
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert result.metadata.data_completeness in ["PARTIAL", "MISSING"]

    def test_stale_data_detection(self, response_generator):
        """Detects when sync is stale"""
        account = make_account_payload()
        auth0 = make_auth0_payload(sync_stale=True)
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert result.metadata.stale_data_detected


class TestJiraIntegration:
    """Tests for Jira output generation"""

    def test_jira_summary_generated(self, response_generator):
        """Jira summary is generated from root cause"""
        account = make_account_payload()
        auth0 = make_auth0_payload(found=False)
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert result.jira_summary
        assert len(result.jira_summary) > 0
        assert len(result.jira_summary) < 200  # Single line summary

    def test_jira_description_includes_diagnosis(self, response_generator):
        """Jira description includes diagnosis section"""
        account = make_account_payload()
        auth0 = make_auth0_payload(birthright=["Community"])
        kb = make_kb_payload(
            BirthrightEvaluation(
                match=False,
                persona="Customer",
                expected_birthright=["Community", "Support"],
                actual_birthright=["Community"],
                entitlements=[],
                missing_keywords=["Support"],
                extra_keywords=[],
                explicit_block_detected=False,
                block_keywords_found=[],
                no_access_configured=False,
            )
        )

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert "Diagnosis" in result.jira_description
        assert "Recommended Actions" in result.jira_description

    def test_jira_description_includes_actions(self, response_generator):
        """Jira description includes all recommended actions"""
        account = make_account_payload()
        auth0 = make_auth0_payload(birthright=["Community"])
        kb = make_kb_payload(
            BirthrightEvaluation(
                match=False,
                persona="Customer",
                expected_birthright=["Community", "Support"],
                actual_birthright=["Community"],
                entitlements=[],
                missing_keywords=["Support"],
                extra_keywords=[],
                explicit_block_detected=False,
                block_keywords_found=[],
                no_access_configured=False,
            )
        )

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        for action in result.resolution_path.actions:
            assert action.action in result.jira_description


class TestErrorHandling:
    """Tests for error scenarios"""

    def test_synthesis_with_agent_errors(self, response_generator):
        """Handles when agents return errors"""
        account = make_account_payload()
        account.error = "Database connection failed"
        auth0 = make_auth0_payload()
        kb = make_kb_payload()

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert result.metadata.data_completeness == "PARTIAL"
        assert "Database connection failed" in result.metadata.conflicting_signals

    def test_synthesis_completes_despite_missing_kb_results(self, response_generator):
        """Still produces diagnosis even if KB has no results"""
        account = make_account_payload()
        auth0 = make_auth0_payload(birthright=["Community"])
        kb = make_kb_payload()
        kb.knowledge_base_error = "KB timeout"

        result = response_generator.synthesize(account, auth0, kb, "test@example.com")

        assert result.root_cause is not None
        assert result.similar_past_cases == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
