# test_orchestrator.py
"""
Pytest test suite for NIC_SecEng_Task.operations.orchestrator.UserOperationsOrchestrator

Since ProfileService and SecureGateway are external collaborator classes whose
internal implementations are not part of this file under test, their instance
methods are patched (not the orchestrator class itself) to deterministically
exercise the orchestrator's own control flow, error handling, and pass-through
behavior -- including verifying it does not swallow or mishandle dangerous
inputs such as path traversal payloads.
"""
import pytest
from unittest.mock import Mock

from NIC_SecEng_Task.operations.orchestrator import UserOperationsOrchestrator


@pytest.fixture
def orchestrator():
    """Provide an orchestrator instance with a dummy db_client (system dependency)."""
    dummy_db_client = Mock(name="db_client")
    return UserOperationsOrchestrator(db_client=dummy_db_client)


def test_successful_scan_and_update_returns_profile_and_logs(orchestrator, monkeypatch):
    """Verify a fully successful flow returns success=True with profile and log data."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        Mock(return_value={"status": "ok", "data": {"name": "Alice"}}),
    )
    monkeypatch.setattr(
        orchestrator.gateway,
        "read_user_file",
        Mock(return_value="log contents"),
    )

    result = orchestrator.run_security_scan_and_update("user1", {"key": "value"}, "diagnostics.log")

    assert result == {
        "success": True,
        "profile": {"name": "Alice"},
        "logs": "log contents",
    }


def test_profile_update_error_short_circuits_before_log_read(orchestrator, monkeypatch):
    """Verify that a profile update error prevents any log-reading attempt."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        Mock(return_value={"status": "error", "message": "invalid payload"}),
    )
    read_mock = Mock(return_value="should never be called")
    monkeypatch.setattr(orchestrator.gateway, "read_user_file", read_mock)

    result = orchestrator.run_security_scan_and_update("user1", {"bad": "data"}, "any_path.log")

    assert result == {
        "success": False,
        "stage": "profile_update",
        "error": "invalid payload",
    }
    read_mock.assert_not_called()


def test_missing_status_key_treated_as_non_error(orchestrator, monkeypatch):
    """Verify that a profile result missing the 'status' key does not trigger the error branch."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        Mock(return_value={"data": {"id": 1}}),
    )
    monkeypatch.setattr(
        orchestrator.gateway,
        "read_user_file",
        Mock(return_value="logs"),
    )

    result = orchestrator.run_security_scan_and_update("user1", {}, "sys.log")

    assert result["success"] is True
    assert result["profile"] == {"id": 1}
    assert result["logs"] == "logs"


def test_log_reading_exception_is_caught_and_reported_safely(orchestrator, monkeypatch):
    """Verify exceptions raised while reading logs are caught and surfaced as a safe error dict, not propagated."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        Mock(return_value={"status": "ok", "data": {}}),
    )
    monkeypatch.setattr(
        orchestrator.gateway,
        "read_user_file",
        Mock(side_effect=FileNotFoundError("no such file")),
    )

    result = orchestrator.run_security_scan_and_update("user1", {}, "missing.log")

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "no such file" in result["error"]


def test_path_traversal_payload_rejected_by_downstream_gateway_is_handled_safely(orchestrator, monkeypatch):
    """Verify that if the downstream gateway rejects a path-traversal attempt (e.g. raises ValueError),
    the orchestrator returns a safe error response instead of leaking the traversal or crashing."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        Mock(return_value={"status": "ok", "data": {}}),
    )
    malicious_path = "../../../../etc/passwd"

    def fake_read_user_file(path):
        # Simulate a hardened SecureGateway rejecting traversal attempts.
        if ".." in path:
            raise ValueError("Path traversal detected")
        return "safe content"

    monkeypatch.setattr(orchestrator.gateway, "read_user_file", fake_read_user_file)

    result = orchestrator.run_security_scan_and_update("user1", {}, malicious_path)

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "Path traversal detected" in result["error"]
    # Ensure no raw filesystem content or traversal path leaked into the success path.
    assert "logs" not in result


def test_system_log_path_forwarded_unmodified_to_gateway(orchestrator, monkeypatch):
    """Verify the orchestrator forwards system_log_path verbatim to the gateway (no silent sanitization masking a bug)."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        Mock(return_value={"status": "ok", "data": {}}),
    )
    read_mock = Mock(return_value="content")
    monkeypatch.setattr(orchestrator.gateway, "read_user_file", read_mock)

    suspicious_path = "../secrets/config.env"
    orchestrator.run_security_scan_and_update("user1", {}, suspicious_path)

    read_mock.assert_called_once_with(suspicious_path)


def test_payload_and_user_id_forwarded_unmodified_to_profile_service(orchestrator, monkeypatch):
    """Verify user_id and payload are passed through to ProfileService without alteration or type coercion."""
    process_mock = Mock(return_value={"status": "ok", "data": {}})
    monkeypatch.setattr(orchestrator.profile_service, "process_user_data", process_mock)
    monkeypatch.setattr(orchestrator.gateway, "read_user_file", Mock(return_value="logs"))

    user_id = "<script>alert(1)</script>"
    payload = {"field": "'; DROP TABLE users; --"}

    orchestrator.run_security_scan_and_update(user_id, payload, "app.log")

    process_mock.assert_called_once_with(user_id, payload)


def test_non_dict_payload_does_not_crash_orchestrator(orchestrator, monkeypatch):
    """Verify a non-dict payload (type confusion) is passed through without the orchestrator itself crashing."""
    process_mock = Mock(return_value={"status": "ok", "data": {}})
    monkeypatch.setattr(orchestrator.profile_service, "process_user_data", process_mock)
    monkeypatch.setattr(orchestrator.gateway, "read_user_file", Mock(return_value="logs"))

    weird_payload = ["not", "a", "dict"]
    result = orchestrator.run_security_scan_and_update("user1", weird_payload, "app.log")

    process_mock.assert_called_once_with("user1", weird_payload)
    assert result["success"] is True


def test_profile_result_without_data_key_returns_none_profile(orchestrator, monkeypatch):
    """Verify a success result lacking a 'data' key yields profile=None rather than raising KeyError."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        Mock(return_value={"status": "ok"}),
    )
    monkeypatch.setattr(orchestrator.gateway, "read_user_file", Mock(return_value="logs"))

    result = orchestrator.run_security_scan_and_update("user1", {}, "app.log")

    assert result["success"] is True
    assert result["profile"] is None
    assert result["logs"] == "logs"


def test_error_result_without_message_key_returns_none_error(orchestrator, monkeypatch):
    """Verify an error result lacking a 'message' key yields error=None rather than raising KeyError."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        Mock(return_value={"status": "error"}),
    )

    result = orchestrator.run_security_scan_and_update("user1", {}, "app.log")

    assert result == {"success": False, "stage": "profile_update", "error": None}


def test_generic_exception_during_log_read_does_not_propagate(orchestrator, monkeypatch):
    """Verify any unexpected exception type from the gateway is caught generically and reported, never raised."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        Mock(return_value={"status": "ok", "data": {}}),
    )
    monkeypatch.setattr(
        orchestrator.gateway,
        "read_user_file",
        Mock(side_effect=RuntimeError("unexpected internal failure")),
    )

    try:
        result = orchestrator.run_security_scan_and_update("user1", {}, "app.log")
    except Exception:
        pytest.fail("Orchestrator must not let downstream exceptions propagate unhandled")

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "unexpected internal failure" in result["error"]
