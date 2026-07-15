# test_orchestrator.py

import pytest
from unittest.mock import MagicMock, patch

from NIC_SecEng_Task.operations.orchestrator import UserOperationsOrchestrator


@pytest.fixture
def mock_db_client():
    """Provides a mock database client to satisfy ProfileService's external dependency."""
    return MagicMock(name="db_client")


@pytest.fixture
def orchestrator(mock_db_client):
    """Builds a real UserOperationsOrchestrator instance with a mocked db client."""
    return UserOperationsOrchestrator(mock_db_client)


def test_init_creates_dependencies(orchestrator):
    """Verifies the orchestrator constructs a profile_service and gateway on init."""
    assert orchestrator.profile_service is not None
    assert orchestrator.gateway is not None


def test_successful_flow_returns_profile_and_logs(orchestrator):
    """Validates the happy path: successful profile update followed by successful log read."""
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"status": "ok", "data": {"name": "alice"}},
    ) as mock_process, patch.object(
        orchestrator.gateway, "read_user_file", return_value="log-contents"
    ) as mock_read:
        result = orchestrator.run_security_scan_and_update(
            "user123", {"field": "value"}, "logs/user123.log"
        )

    mock_process.assert_called_once_with("user123", {"field": "value"})
    mock_read.assert_called_once_with("logs/user123.log")
    assert result == {
        "success": True,
        "profile": {"name": "alice"},
        "logs": "log-contents",
    }


def test_profile_update_error_short_circuits_before_gateway(orchestrator):
    """Ensures that when profile_service reports an error, the gateway is never invoked."""
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"status": "error", "message": "invalid user"},
    ) as mock_process, patch.object(
        orchestrator.gateway, "read_user_file"
    ) as mock_read:
        result = orchestrator.run_security_scan_and_update(
            "bad_user", {}, "some/path.log"
        )

    mock_process.assert_called_once()
    mock_read.assert_not_called()
    assert result == {
        "success": False,
        "stage": "profile_update",
        "error": "invalid user",
    }


def test_log_reading_exception_is_caught_and_reported(orchestrator):
    """Confirms that exceptions raised while reading logs are caught and surfaced safely, not propagated."""
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"status": "ok", "data": {"name": "bob"}},
    ), patch.object(
        orchestrator.gateway,
        "read_user_file",
        side_effect=ValueError("Path traversal detected"),
    ):
        result = orchestrator.run_security_scan_and_update(
            "bob", {}, "../../../../etc/passwd"
        )

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "Path traversal detected" in result["error"]
    # No unhandled exception should have propagated out of the orchestrator.


def test_path_traversal_payload_is_not_swallowed_silently(orchestrator):
    """Ensures a malicious path traversal input causes a safe, reported failure rather than success."""
    malicious_path = "../../../../etc/shadow"
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"status": "ok", "data": {}},
    ), patch.object(
        orchestrator.gateway,
        "read_user_file",
        side_effect=PermissionError("Access denied: path traversal blocked"),
    ) as mock_read:
        result = orchestrator.run_security_scan_and_update(
            "victim", {}, malicious_path
        )

    mock_read.assert_called_once_with(malicious_path)
    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "Access denied" in result["error"]


def test_gateway_receives_exact_unsanitized_path_argument(orchestrator):
    """Verifies the orchestrator forwards system_log_path unchanged to the gateway (no sanitization at this layer)."""
    suspicious_path = "..%2f..%2fetc%2fpasswd"
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"status": "ok", "data": {}},
    ), patch.object(
        orchestrator.gateway, "read_user_file", return_value="safe-log"
    ) as mock_read:
        orchestrator.run_security_scan_and_update("u1", {}, suspicious_path)

    mock_read.assert_called_once_with(suspicious_path)


def test_payload_with_injection_strings_passed_through_unmodified(orchestrator):
    """Ensures injection-style payload content is passed to profile_service verbatim without orchestrator-level mutation."""
    malicious_payload = {"username": "admin' OR '1'='1", "bio": "<script>alert(1)</script>"}
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"status": "ok", "data": {}},
    ) as mock_process, patch.object(
        orchestrator.gateway, "read_user_file", return_value="log"
    ):
        orchestrator.run_security_scan_and_update("u2", malicious_payload, "log.txt")

    mock_process.assert_called_once_with("u2", malicious_payload)


def test_result_missing_status_key_treated_as_non_error(orchestrator):
    """Checks that a profile_service result lacking a 'status' key does not incorrectly short-circuit as an error."""
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"data": {"name": "no-status"}},
    ), patch.object(
        orchestrator.gateway, "read_user_file", return_value="logdata"
    ) as mock_read:
        result = orchestrator.run_security_scan_and_update("u3", {}, "path.log")

    mock_read.assert_called_once()
    assert result["success"] is True
    assert result["profile"] == {"name": "no-status"}


def test_result_missing_data_key_returns_none_profile(orchestrator):
    """Confirms that a success result without a 'data' key yields profile=None rather than raising."""
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"status": "ok"},
    ), patch.object(
        orchestrator.gateway, "read_user_file", return_value="logdata"
    ):
        result = orchestrator.run_security_scan_and_update("u4", {}, "path.log")

    assert result["success"] is True
    assert result["profile"] is None


def test_empty_user_id_still_forwarded_to_profile_service(orchestrator):
    """Validates that an empty string user_id is passed through without orchestrator-level validation errors."""
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"status": "ok", "data": {}},
    ) as mock_process, patch.object(
        orchestrator.gateway, "read_user_file", return_value="log"
    ):
        result = orchestrator.run_security_scan_and_update("", {}, "log.txt")

    mock_process.assert_called_once_with("", {})
    assert result["success"] is True


def test_non_dict_payload_propagates_to_profile_service(orchestrator):
    """Ensures a non-dict payload is passed through as-is, exercising type confusion resilience at this layer."""
    weird_payload = "not-a-dict"
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"status": "ok", "data": {}},
    ) as mock_process, patch.object(
        orchestrator.gateway, "read_user_file", return_value="log"
    ):
        orchestrator.run_security_scan_and_update("u5", weird_payload, "log.txt")

    mock_process.assert_called_once_with("u5", weird_payload)


def test_generic_exception_from_gateway_is_caught_with_message(orchestrator):
    """Ensures arbitrary exceptions (not just path errors) raised by the gateway are caught and reported safely."""
    with patch.object(
        orchestrator.profile_service,
        "process_user_data",
        return_value={"status": "ok", "data": {}},
    ), patch.object(
        orchestrator.gateway,
        "read_user_file",
        side_effect=RuntimeError("unexpected system failure"),
    ):
        result = orchestrator.run_security_scan_and_update("u6", {}, "log.txt")

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "unexpected system failure" in result["error"]
