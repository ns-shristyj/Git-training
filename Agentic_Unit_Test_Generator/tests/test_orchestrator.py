# test_orchestrator.py
"""
Pytest suite for NIC_SecEng_Task.operations.orchestrator.UserOperationsOrchestrator

Since ProfileService wraps a database client (external dependency) and
SecureGateway wraps filesystem access (external/system dependency), we
control their behavior at the instance-method boundary via monkeypatch
rather than mocking the orchestrator under test itself. This lets us
verify the orchestrator's own branching, error handling, and safe
propagation logic in isolation.
"""

import pytest

from NIC_SecEng_Task.operations.orchestrator import UserOperationsOrchestrator
from NIC_SecEng_Task.user_management.profile_service import ProfileService
from NIC_SecEng_Task.user_management.secure_gateway import SecureGateway


class FakeDBClient:
    """A stand-in for a real database client (external dependency)."""
    pass


@pytest.fixture
def orchestrator():
    """Provides a fresh orchestrator instance with a fake db client."""
    return UserOperationsOrchestrator(db_client=FakeDBClient())


def test_constructor_wires_dependencies(orchestrator):
    """Verify orchestrator constructs real ProfileService and SecureGateway instances."""
    assert isinstance(orchestrator.profile_service, ProfileService)
    assert isinstance(orchestrator.gateway, SecureGateway)


def test_successful_flow_returns_profile_and_logs(orchestrator, monkeypatch):
    """Verify a successful profile update followed by successful log read returns combined success payload."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        lambda user_id, payload: {"status": "ok", "data": {"name": "Alice"}},
    )
    monkeypatch.setattr(
        orchestrator.gateway,
        "read_user_file",
        lambda path: "log contents",
    )

    result = orchestrator.run_security_scan_and_update(
        "user123", {"name": "Alice"}, "logs/system.log"
    )

    assert result == {
        "success": True,
        "profile": {"name": "Alice"},
        "logs": "log contents",
    }


def test_profile_update_error_short_circuits_before_log_read(orchestrator, monkeypatch):
    """Verify that when profile update fails, the orchestrator returns early and never attempts to read logs."""
    called = {"gateway": False}

    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        lambda user_id, payload: {"status": "error", "message": "invalid payload"},
    )

    def fail_if_called(path):
        called["gateway"] = True
        return "should not be called"

    monkeypatch.setattr(orchestrator.gateway, "read_user_file", fail_if_called)

    result = orchestrator.run_security_scan_and_update(
        "user123", {"bad": "data"}, "irrelevant/path.log"
    )

    assert result == {
        "success": False,
        "stage": "profile_update",
        "error": "invalid payload",
    }
    assert called["gateway"] is False


def test_log_reading_exception_is_caught_and_reported_safely(orchestrator, monkeypatch):
    """Verify that exceptions raised while reading logs are caught and surfaced as a safe error, not propagated."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        lambda user_id, payload: {"status": "ok", "data": {}},
    )

    def raise_error(path):
        raise ValueError("path traversal blocked")

    monkeypatch.setattr(orchestrator.gateway, "read_user_file", raise_error)

    result = orchestrator.run_security_scan_and_update(
        "user123", {}, "../../etc/passwd"
    )

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "path traversal blocked" in result["error"]
    # Ensure no raw file content or logs key leaked into the error response
    assert "logs" not in result
    assert "profile" not in result


def test_path_traversal_attempt_does_not_crash_orchestrator(orchestrator, monkeypatch):
    """Verify a classic path traversal payload is handled by catching the downstream exception safely."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        lambda user_id, payload: {"status": "ok", "data": {"id": "u1"}},
    )

    malicious_path = "../../../../etc/shadow"

    def secure_gateway_blocks_traversal(path):
        # Simulates a hardened SecureGateway rejecting traversal attempts.
        if ".." in path:
            raise ValueError("Invalid path: traversal detected")
        return "safe log content"

    monkeypatch.setattr(orchestrator.gateway, "read_user_file", secure_gateway_blocks_traversal)

    result = orchestrator.run_security_scan_and_update("user123", {}, malicious_path)

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "traversal detected" in result["error"]


def test_generic_exception_from_gateway_is_caught(orchestrator, monkeypatch):
    """Verify that any generic exception type (not just ValueError) from the gateway is caught safely."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        lambda user_id, payload: {"status": "ok", "data": {}},
    )

    def raise_runtime_error(path):
        raise RuntimeError("disk read failure")

    monkeypatch.setattr(orchestrator.gateway, "read_user_file", raise_runtime_error)

    result = orchestrator.run_security_scan_and_update("user123", {}, "some/log.txt")

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "disk read failure" in result["error"]


def test_result_without_status_key_proceeds_to_log_stage(orchestrator, monkeypatch):
    """Verify that a malformed profile_service response missing 'status' does not equal 'error' and proceeds."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        lambda user_id, payload: {"data": {"id": "u1"}},  # no "status" key
    )
    monkeypatch.setattr(
        orchestrator.gateway,
        "read_user_file",
        lambda path: "logs-ok",
    )

    result = orchestrator.run_security_scan_and_update("user123", {}, "log.txt")

    assert result["success"] is True
    assert result["profile"] == {"id": "u1"}
    assert result["logs"] == "logs-ok"


def test_result_missing_data_key_defaults_to_none(orchestrator, monkeypatch):
    """Verify that a success result missing 'data' produces profile=None rather than raising KeyError."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        lambda user_id, payload: {"status": "ok"},  # no "data" key
    )
    monkeypatch.setattr(
        orchestrator.gateway,
        "read_user_file",
        lambda path: "logs",
    )

    result = orchestrator.run_security_scan_and_update("user123", {}, "log.txt")

    assert result["success"] is True
    assert result["profile"] is None
    assert result["logs"] == "logs"


def test_non_string_user_id_does_not_break_orchestration(orchestrator, monkeypatch):
    """Verify type confusion inputs (non-string user_id) are simply forwarded without orchestrator-level crashes."""
    received = {}

    def capture(user_id, payload):
        received["user_id"] = user_id
        return {"status": "ok", "data": {}}

    monkeypatch.setattr(orchestrator.profile_service, "process_user_data", capture)
    monkeypatch.setattr(orchestrator.gateway, "read_user_file", lambda path: "logs")

    result = orchestrator.run_security_scan_and_update(12345, {}, "log.txt")

    assert received["user_id"] == 12345
    assert result["success"] is True


def test_malicious_payload_is_forwarded_untouched_not_executed(orchestrator, monkeypatch):
    """Verify a payload containing suspicious keys is passed through as inert data, never executed by orchestrator."""
    malicious_payload = {"__class__": "attempt", "__import__": "os"}
    received = {}

    def capture(user_id, payload):
        received["payload"] = payload
        return {"status": "ok", "data": payload}

    monkeypatch.setattr(orchestrator.profile_service, "process_user_data", capture)
    monkeypatch.setattr(orchestrator.gateway, "read_user_file", lambda path: "logs")

    result = orchestrator.run_security_scan_and_update("user1", malicious_payload, "log.txt")

    assert received["payload"] == malicious_payload
    assert result["profile"] == malicious_payload
    assert result["success"] is True


def test_empty_system_log_path_handled_by_gateway_exception(orchestrator, monkeypatch):
    """Verify an empty log path string is forwarded to the gateway and any resulting error is safely caught."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        lambda user_id, payload: {"status": "ok", "data": {}},
    )

    def reject_empty_path(path):
        if not path:
            raise ValueError("empty path not allowed")
        return "logs"

    monkeypatch.setattr(orchestrator.gateway, "read_user_file", reject_empty_path)

    result = orchestrator.run_security_scan_and_update("user1", {}, "")

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "empty path not allowed" in result["error"]


def test_error_message_none_when_message_key_absent(orchestrator, monkeypatch):
    """Verify that an error result without a 'message' key produces error=None rather than raising KeyError."""
    monkeypatch.setattr(
        orchestrator.profile_service,
        "process_user_data",
        lambda user_id, payload: {"status": "error"},  # no "message" key
    )

    result = orchestrator.run_security_scan_and_update("user1", {}, "log.txt")

    assert result == {"success": False, "stage": "profile_update", "error": None}
