"""Unit tests for CIAMOrchestrator's decision logic, using mocked AgentInvoker
instances so no real AWS calls are made.
"""

from unittest.mock import patch

import pytest

from ciam_orchestrator.orchestrator import CIAMOrchestrator
from ciam_orchestrator.schemas import JiraTicket, AgentInvocationResult
from ciam_orchestrator.errors import ValidationError


def make_agent1_result(**envelope_overrides) -> AgentInvocationResult:
    envelope = {
        "intent": "ACCESS_DENIED",
        "confidence": 0.9,
        "extracted_email": "user.account@example.com",
        "invoke_agent_2": True,
        "invoke_agent_3": False,
        "invoke_agent_4": False,
        "auto_escalate": False,
        **envelope_overrides,
    }
    return AgentInvocationResult(
        agent_name="ciam-intent-classifier",
        agent_arn="arn:test:agent1",
        status="success",
        response_time_ms=120.0,
        response_payload=envelope,
    )


SAMPLE_TICKET = JiraTicket(
    issue_key="TQI-0001",
    summary="User cannot access portal",
    description="user.account@example.com getting Access Denied error",
)


def test_missing_issue_key_raises_validation_error():
    orchestrator = CIAMOrchestrator()
    bad_ticket = JiraTicket(issue_key="", summary="x", description="y")
    with pytest.raises(ValidationError):
        orchestrator.orchestrate(bad_ticket)


def test_confidence_below_threshold_triggers_escalation():
    orchestrator = CIAMOrchestrator()
    with patch.object(
        orchestrator.invoker_1, "invoke",
        return_value=make_agent1_result(confidence=0.65),
    ):
        output = orchestrator.orchestrate(SAMPLE_TICKET)

    assert output.should_escalate_to_l2 is True
    assert output.escalation_reason == "low_confidence"
    assert output.account_payload is None


def test_agent1_auto_escalate_is_a_hard_stop():
    """Per SPEC-CIAM-0001: auto_escalate=true must skip Agents 2-4 regardless
    of their individual invoke_agent_* flags."""
    orchestrator = CIAMOrchestrator()
    with patch.object(
        orchestrator.invoker_1, "invoke",
        return_value=make_agent1_result(
            auto_escalate=True,
            invoke_agent_2=True,  # deliberately true, to prove it's still ignored
            escalation_reason="unknown_intent",
        ),
    ):
        output = orchestrator.orchestrate(SAMPLE_TICKET)

    assert output.should_escalate_to_l2 is True
    assert output.escalation_reason == "unknown_intent"
    assert output.account_payload is None


def test_agent1_failure_escalates():
    orchestrator = CIAMOrchestrator()
    failed_result = AgentInvocationResult(
        agent_name="ciam-intent-classifier",
        agent_arn="arn:test:agent1",
        status="timeout",
        error_message="timed out after 30s",
    )
    with patch.object(orchestrator.invoker_1, "invoke", return_value=failed_result):
        output = orchestrator.orchestrate(SAMPLE_TICKET)

    assert output.should_escalate_to_l2 is True
    assert "agent1_failed" in output.escalation_reason


def test_agent2_invoked_when_flag_true_and_email_exists():
    orchestrator = CIAMOrchestrator()
    agent2_result = AgentInvocationResult(
        agent_name="ciam-database-agent",
        agent_arn="arn:test:agent2",
        status="success",
        response_payload={"account_found": True, "accounts": [{"account_name": "Acme"}]},
    )

    with patch.object(orchestrator.invoker_1, "invoke", return_value=make_agent1_result()):
        with patch(
            "ciam_orchestrator.orchestrator.AgentInvoker.invoke",
            return_value=agent2_result,
        ):
            output = orchestrator.orchestrate(SAMPLE_TICKET)

    assert output.should_escalate_to_l2 is False
    assert output.account_payload is not None
    assert output.account_payload["account_found"] is True


def test_agent2_failure_does_not_block_output():
    orchestrator = CIAMOrchestrator()
    agent2_failure = AgentInvocationResult(
        agent_name="ciam-database-agent",
        agent_arn="arn:test:agent2",
        status="error",
        error_message="ProvisionedThroughputExceededException",
    )

    with patch.object(orchestrator.invoker_1, "invoke", return_value=make_agent1_result()):
        with patch(
            "ciam_orchestrator.orchestrator.AgentInvoker.invoke",
            return_value=agent2_failure,
        ):
            output = orchestrator.orchestrate(SAMPLE_TICKET)

    assert output.should_escalate_to_l2 is False
    assert output.account_payload is None
    assert any("ciam-database-agent" in w for w in output.orchestration_warnings)


def test_agent2_not_invoked_when_flag_false():
    orchestrator = CIAMOrchestrator()
    with patch.object(
        orchestrator.invoker_1, "invoke",
        return_value=make_agent1_result(invoke_agent_2=False),
    ):
        with patch("ciam_orchestrator.orchestrator.AgentInvoker.invoke") as mock_invoke:
            output = orchestrator.orchestrate(SAMPLE_TICKET)
            mock_invoke.assert_not_called()

    assert output.account_payload is None


def test_agent5_invoked_after_agent4_succeeds():
    """Agent 5 has no routing_flag (unlike Agents 2/3/4) -- it's a final,
    unconditional synthesis step gated only on Agent 4 having succeeded."""
    orchestrator = CIAMOrchestrator()

    def fake_invoke(self, payload):
        if self.agent_name == "ciam-kb-agent":
            return AgentInvocationResult(
                agent_name="ciam-kb-agent", agent_arn="arn:test:agent4",
                status="success", response_payload={"birthright_evaluation": {"match": False}},
            )
        if self.agent_name == "ciam-response-generator":
            # Assert Agent 5 receives the kb_payload Agent 4 just produced
            assert payload["kb_payload"] == {"birthright_evaluation": {"match": False}}
            return AgentInvocationResult(
                agent_name="ciam-response-generator", agent_arn="arn:test:agent5",
                status="success", response_payload={"jira_summary": "Missing Support"},
            )
        # Agents 2/3 aren't this test's focus -- return a generic success
        return AgentInvocationResult(
            agent_name=self.agent_name, agent_arn="arn:test:generic",
            status="success", response_payload={},
        )

    with patch.object(orchestrator.invoker_1, "invoke", return_value=make_agent1_result(invoke_agent_4=True)):
        with patch("ciam_orchestrator.orchestrator.AgentInvoker.invoke", fake_invoke):
            output = orchestrator.orchestrate(SAMPLE_TICKET)

    assert output.synthesis_payload == {"jira_summary": "Missing Support"}
    agent_names_invoked = [inv.agent_name for inv in output.agent_invocations]
    assert "ciam-response-generator" in agent_names_invoked


def test_agent5_not_invoked_when_agent4_not_run():
    """Without a kb_payload (Agent 4 disabled/not routed to), there's nothing
    for Agent 5 to synthesize -- it must not be invoked."""
    orchestrator = CIAMOrchestrator()

    with patch.object(
        orchestrator.invoker_1, "invoke",
        return_value=make_agent1_result(invoke_agent_2=False, invoke_agent_4=False),
    ):
        with patch("ciam_orchestrator.orchestrator.AgentInvoker.invoke") as mock_invoke:
            output = orchestrator.orchestrate(SAMPLE_TICKET)
            mock_invoke.assert_not_called()

    assert output.synthesis_payload is None
    agent_names_invoked = [inv.agent_name for inv in output.agent_invocations]
    assert "ciam-response-generator" not in agent_names_invoked
