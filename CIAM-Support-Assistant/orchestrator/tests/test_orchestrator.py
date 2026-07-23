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
