# test_orchestrator.py

import pytest
from unittest.mock import MagicMock, patch

from NIC_SecEng_Task.operations.orchestrator import UserOperationsOrchestrator


@pytest.fixture
def mock_db_client():
    """Provides a mock external database client (external dependency)."""
    return MagicMock(name="db_client")


@pytest.fixture
def patched_orchestrator(mock_db_client):
    """
    Creates an orchestrator instance with ProfileService and SecureGateway
    replaced by controllable mocks, since their internal implementations are
    external to this module and not part of the code under test.
    """
    with patch(
        "NIC_SecEng_Task.operations.orchestrator.ProfileService"
    ) as MockProfileService, patch(
        "NIC_SecEng_Task.operations.orchestrator.SecureGateway"
    ) as MockSecureGateway:
        mock_profile_instance = MagicMock(name="profile_service_instance")
        mock_gateway_instance = MagicMock(name="gateway_instance")
        MockProfileService.return_value = mock_profile_instance
        MockSecureGateway.return_value = mock_gateway_instance

        orchestrator = UserOperationsOrchestrator(mock_db_client)
        yield orchestrator, mock_profile_instance, mock_gateway_instance, MockProfileService, mock_db_client


def test_init_passes_db_client_to_profile_service(patched_orchestrator):
    """Verify the db_client is forwarded correctly to ProfileService constructor."""
    orchestrator, _, _, MockProfileService, mock_db_client = patched_orchestrator
    MockProfileService.assert_called_once_with(mock_db_client)


def test_successful_flow_returns_profile_and_logs(patched_orchestrator):
    """Verify a full successful run returns success=True with profile data and logs."""
    orchestrator, profile_service, gateway, _, _ = patched_orchestrator
    profile_service.process_user_data.return_value = {
        "status": "success",
        "data": {"name": "Alice"},
    }
    gateway.read_user_file.return_value = "log contents"

    result = orchestrator.run_security_scan_and_update(
        "user123", {"name": "Alice"}, "diagnostics.log"
    )

    assert result == {
        "success": True,
        "profile": {"name": "Alice"},
        "logs": "log contents",
    }


def test_profile_update_error_short_circuits_before_log_read(patched_orchestrator):
    """Verify that an error status from ProfileService prevents log reading entirely."""
    orchestrator, profile_service, gateway, _, _ = patched_orchestrator
    profile_service.process_user_data.return_value = {
        "status": "error",
        "message": "invalid payload",
    }

    result = orchestrator.run_security_scan_and_update(
        "user123", {"bad": "data"}, "logs/system.log"
    )

    assert result == {
        "success": False,
        "stage": "profile_update",
        "error": "invalid payload",
    }
    gateway.read_user_file.assert_not_called()


def test_log_reading_exception_is_caught_and_reported_safely(patched_orchestrator):
    """Verify exceptions raised during log reading are caught and returned as structured errors, not propagated."""
    orchestrator, profile_service, gateway, _, _ = patched_orchestrator
    profile_service.process_user_data.return_value = {
        "status": "success",
        "data": {"name": "Bob"},
    }
    gateway.read_user_file.side_effect = ValueError("Path traversal detected")

    result = orchestrator.run_security_scan_and_update(
        "user123", {"name": "Bob"}, "../../etc/passwd"
    )

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "Path traversal detected" in result["error"]


def test_path_traversal_payload_is_forwarded_but_failure_is_handled_safely(patched_orchestrator):
    """Verify a malicious traversal path is passed downstream but any resulting exception does not crash the orchestrator."""
    orchestrator, profile_service, gateway, _, _ = patched_orchestrator
    profile_service.process_user_data.return_value = {
        "status": "success",
        "data": {},
    }
    gateway.read_user_file.side_effect = PermissionError("Access denied: traversal blocked")

    malicious_path = "../../../etc/shadow"
    result = orchestrator.run_security_scan_and_update("user1", {}, malicious_path)

    gateway.read_user_file.assert_called_once_with(malicious_path)
    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "Access denied" in result["error"]


def test_missing_status_key_treated_as_non_error_and_proceeds(patched_orchestrator):
    """Verify that when 'status' key is absent from profile result, flow proceeds to log reading (not treated as error)."""
    orchestrator, profile_service, gateway, _, _ = patched_orchestrator
    profile_service.process_user_data.return_value = {"data": {"name": "Carl"}}
    gateway.read_user_file.return_value = "ok"

    result = orchestrator.run_security_scan_and_update("user1", {}, "file.log")

    assert result["success"] is True
    assert result["profile"] == {"name": "Carl"}
    assert result["logs"] == "ok"


def test_result_with_no_data_key_returns_none_profile(patched_orchestrator):
    """Verify graceful handling when the profile result dict lacks a 'data' key."""
    orchestrator, profile_service, gateway, _, _ = patched_orchestrator
    profile_service.process_user_data.return_value = {"status": "success"}
    gateway.read_user_file.return_value = "logdata"

    result = orchestrator.run_security_scan_and_update("user1", {}, "system.log")

    assert result["success"] is True
    assert result["profile"] is None
    assert result["logs"] == "logdata"


def test_payload_and_user_id_forwarded_unmodified_to_profile_service(patched_orchestrator):
    """Verify user_id and payload are passed through to process_user_data exactly as provided."""
    orchestrator, profile_service, gateway, _, _ = patched_orchestrator
    profile_service.process_user_data.return_value = {"status": "success", "data": {}}
    gateway.read_user_file.return_value = "logs"

    payload = {"key": "value", "nested": {"a": 1}}
    orchestrator.run_security_scan_and_update("special-user-id", payload, "app.log")

    profile_service.process_user_data.assert_called_once_with("special-user-id", payload)


def test_empty_user_id_and_payload_do_not_crash(patched_orchestrator):
    """Verify empty string user_id and empty dict payload are handled without raising exceptions."""
    orchestrator, profile_service, gateway, _, _ = patched_orchestrator
    profile_service.process_user_data.return_value = {"status": "success", "data": {}}
    gateway.read_user_file.return_value = ""

    result = orchestrator.run_security_scan_and_update("", {}, "")

    assert result["success"] is True
    profile_service.process_user_data.assert_called_once_with("", {})
    gateway.read_user_file.assert_called_once_with("")


def test_generic_exception_message_does_not_leak_internal_stack_trace_object(patched_orchestrator):
    """Verify that only the exception's string message is surfaced, not raw exception objects or tracebacks."""
    orchestrator, profile_service, gateway, _, _ = patched_orchestrator
    profile_service.process_user_data.return_value = {"status": "success", "data": {}}
    gateway.read_user_file.side_effect = RuntimeError("internal failure detail")

    result = orchestrator.run_security_scan_and_update("user1", {}, "bad/path")

    assert isinstance(result["error"], str)
    assert result["error"] == "Failed to retrieve logs: internal failure detail"


def test_non_dict_payload_type_forwarded_without_orchestrator_crash(patched_orchestrator):
    """Verify that unexpected payload types (e.g., a string instead of dict) don't cause the orchestrator itself to raise."""
    orchestrator, profile_service, gateway, _, _ = patched_orchestrator
    profile_service.process_user_data.return_value = {"status": "success", "data": {}}
    gateway.read_user_file.return_value = "logs"

    # Even a malformed payload type should just be forwarded; orchestrator has no type validation itself.
    result = orchestrator.run_security_scan_and_update("user1", "not-a-dict", "file.log")

    assert result["success"] is True
    profile_service.process_user_data.assert_called_once_with("user1", "not-a-dict")
