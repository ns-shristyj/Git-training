import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from ciam_orchestrator.errors import ValidationError
from ciam_orchestrator.handler import lambda_handler


VALID_EVENT = {
    "issue_key": "TQI-9001",
    "summary": "User cannot reset password",
    "description": (
        "Customer at user.account@example.com unable to reset password, "
        "getting error: 'Reset token invalid'. Issue occurred after Nov 1 "
        "CIAM migration. User works in support team."
    ),
}


def _mock_orchestrator(return_dict=None, side_effect=None):
    """Helper building a mocked CIAMOrchestrator class whose instance's
    orchestrate() either returns an object with model_dump() -> return_dict
    or raises side_effect."""
    instance = MagicMock()
    if side_effect is not None:
        instance.orchestrate.side_effect = side_effect
    else:
        output_obj = MagicMock()
        output_obj.model_dump.return_value = return_dict or {"status": "ok"}
        instance.orchestrate.return_value = output_obj
    mocked_class = MagicMock(return_value=instance)
    return mocked_class


class TestLambdaHandlerFunctionality:
    def test_valid_event_returns_200_with_expected_body(self):
        """A well-formed Jira-shaped event is validated and orchestrated successfully, returning 200 with the orchestrator output."""
        mocked_class = _mock_orchestrator(return_dict={"resolution": "done"})
        with patch("ciam_orchestrator.handler.CIAMOrchestrator", mocked_class):
            result = lambda_handler(dict(VALID_EVENT))

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body == {"resolution": "done"}
        mocked_class.return_value.orchestrate.assert_called_once()

    def test_run_id_uses_context_aws_request_id_when_available(self):
        """When a context object with aws_request_id is supplied, that value is used as run_id on error paths."""
        mocked_class = _mock_orchestrator(
            side_effect=Exception("boom")
        )
        context = MagicMock()
        context.aws_request_id = "req-1234"
        with patch("ciam_orchestrator.handler.CIAMOrchestrator", mocked_class):
            result = lambda_handler(dict(VALID_EVENT), context=context)

        body = json.loads(result["body"])
        assert result["statusCode"] == 500
        assert body["run_id"] == "req-1234"


class TestLambdaHandlerInvalidInput:
    @pytest.mark.parametrize(
        "mutation",
        [
            "missing_summary",
            "missing_description",
            "missing_issue_key",
            "wrong_type_summary",
        ],
    )
    def test_invalid_events_return_400(self, mutation):
        """Malformed or incomplete events fail pydantic validation and are safely converted into a 400 response."""
        event = dict(VALID_EVENT)
        if mutation == "missing_summary":
            del event["summary"]
        elif mutation == "missing_description":
            del event["description"]
        elif mutation == "missing_issue_key":
            del event["issue_key"]
        elif mutation == "wrong_type_summary":
            event["summary"] = ["not", "a", "string"]

        # Orchestrator should never even be constructed for invalid input.
        mocked_class = MagicMock()
        with patch("ciam_orchestrator.handler.CIAMOrchestrator", mocked_class):
            result = lambda_handler(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body
        assert "run_id" in body
        mocked_class.assert_not_called()

    def test_application_validation_error_from_orchestrator_returns_400(self):
        """A domain-level ValidationError raised inside orchestrate() is caught and mapped to a 400 response."""
        mocked_class = _mock_orchestrator(side_effect=ValidationError("bad ticket"))
        with patch("ciam_orchestrator.handler.CIAMOrchestrator", mocked_class):
            result = lambda_handler(dict(VALID_EVENT))

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "bad ticket" in body["error"]

    def test_unhandled_exception_returns_500_with_generic_error(self):
        """An unexpected exception during orchestration is caught by the broad handler and reported as a 500 without crashing the process."""
        mocked_class = _mock_orchestrator(side_effect=RuntimeError("catastrophic failure"))
        with patch("ciam_orchestrator.handler.CIAMOrchestrator", mocked_class):
            result = lambda_handler(dict(VALID_EVENT))

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["error"] == "internal_error"
        assert "catastrophic failure" in body["detail"]
        assert "run_id" in body


class TestLambdaHandlerSecurity:
    @pytest.mark.parametrize(
        "malicious_description",
        [
            "\"; DROP TABLE tickets; --",
            "<script>alert('xss')</script>",
            "../../../../etc/passwd",
            "line1\r\nlog-injected-line: FAKE ENTRY",
            "{malicious_format_string}",
        ],
    )
    def test_malicious_input_is_treated_as_inert_data_and_safely_json_encoded(
        self, malicious_description
    ):
        """Untrusted ticket content containing injection-style payloads is passed through as plain data and never breaks JSON encoding or triggers code execution."""
        event = dict(VALID_EVENT)
        event["description"] = malicious_description

        def _fake_orchestrate(ticket):
            output = MagicMock()
            output.model_dump.return_value = {"echoed_description": ticket.description}
            return output

        instance = MagicMock()
        instance.orchestrate.side_effect = _fake_orchestrate
        mocked_class = MagicMock(return_value=instance)

        with patch("ciam_orchestrator.handler.CIAMOrchestrator", mocked_class):
            result = lambda_handler(event)

        # Response must always be valid, parseable JSON regardless of payload content.
        body = json.loads(result["body"])
        assert result["statusCode"] == 200
        assert body["echoed_description"] == malicious_description
