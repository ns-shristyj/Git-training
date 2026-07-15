# test_orchestrator.py
import pytest
from unittest.mock import MagicMock, patch

from NIC_SecEng_Task.operations.orchestrator import UserOperationsOrchestrator


@pytest.fixture
def mock_db_client():
    """Provides a mock database client, since ProfileService is a DB-backed external dependency."""
    return MagicMock(name="db_client")


@pytest.fixture
def orchestrator_factory(mock_db_client):
    """Factory that builds an orchestrator with patched ProfileService/SecureGateway (system/DB deps)."""
    def _build(profile_service_mock=None, gateway_mock=None):
        with patch(
            "NIC_SecEng_Task.operations.orchestrator.ProfileService"
        ) as ProfileServiceCls, patch(
            "NIC_SecEng_Task.operations.orchestrator.SecureGateway"
        ) as SecureGatewayCls:
            ps_instance = profile_service_mock or MagicMock()
            gw_instance = gateway_mock or MagicMock()
            ProfileServiceCls.return_value = ps_instance
            SecureGatewayCls.return_value = gw_instance
            orch = UserOperationsOrchestrator(mock_db_client)
            return orch, ProfileServiceCls, SecureGatewayCls, ps_instance, gw_instance
    return _build


def test_constructor_initializes_profile_service_with_db_client(orchestrator_factory, mock_db_client):
    """Verify the constructor instantiates ProfileService with the supplied db_client."""
    orch, ProfileServiceCls, SecureGatewayCls, ps_instance, gw_instance = orchestrator_factory()
    ProfileServiceCls.assert_called_once_with(mock_db_client)
    SecureGatewayCls.assert_called_once_with()
    assert orch.profile_service is ps_instance
    assert orch.gateway is gw_instance


def test_successful_flow_returns_profile_and_logs(orchestrator_factory):
    """Verify a full successful run returns success=True with profile data and log data."""
    ps = MagicMock()
    ps.process_user_data.return_value = {"status": "success", "data": {"name": "Alice"}}
    gw = MagicMock()
    gw.read_user_file.return_value = "log contents"

    orch, *_ , ps_instance, gw_instance = orchestrator_factory(profile_service_mock=ps, gateway_mock=gw)

    result = orch.run_security_scan_and_update("user123", {"field": "value"}, "logs/system.log")

    assert result == {
        "success": True,
        "profile": {"name": "Alice"},
        "logs": "log contents",
    }
    ps_instance.process_user_data.assert_called_once_with("user123", {"field": "value"})
    gw_instance.read_user_file.assert_called_once_with("logs/system.log")


def test_profile_update_error_short_circuits_before_gateway_call(orchestrator_factory):
    """Verify that when ProfileService reports an error, the gateway is never invoked."""
    ps = MagicMock()
    ps.process_user_data.return_value = {"status": "error", "message": "invalid payload"}
    gw = MagicMock()

    orch, *_ , ps_instance, gw_instance = orchestrator_factory(profile_service_mock=ps, gateway_mock=gw)

    result = orch.run_security_scan_and_update("user123", {"bad": "data"}, "logs/system.log")

    assert result == {
        "success": False,
        "stage": "profile_update",
        "error": "invalid payload",
    }
    gw_instance.read_user_file.assert_not_called()


def test_profile_update_error_missing_message_key_defaults_to_none(orchestrator_factory):
    """Verify graceful handling when the error result lacks a 'message' key (no KeyError)."""
    ps = MagicMock()
    ps.process_user_data.return_value = {"status": "error"}
    gw = MagicMock()

    orch, *_ , ps_instance, gw_instance = orchestrator_factory(profile_service_mock=ps, gateway_mock=gw)

    result = orch.run_security_scan_and_update("user123", {}, "logs/system.log")

    assert result["success"] is False
    assert result["stage"] == "profile_update"
    assert result["error"] is None
    gw_instance.read_user_file.assert_not_called()


def test_gateway_exception_is_caught_and_returns_safe_error(orchestrator_factory):
    """Verify a path-traversal-triggered exception from SecureGateway is caught, not propagated."""
    ps = MagicMock()
    ps.process_user_data.return_value = {"status": "success", "data": {"name": "Bob"}}
    gw = MagicMock()
    gw.read_user_file.side_effect = ValueError("Path traversal detected: ../../etc/passwd")

    orch, *_ , ps_instance, gw_instance = orchestrator_factory(profile_service_mock=ps, gateway_mock=gw)

    result = orch.run_security_scan_and_update(
        "user123", {"field": "value"}, "../../etc/passwd"
    )

    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "Failed to retrieve logs safely" in result["error"]
    # Ensure no unhandled exception propagates out of the orchestrator method.


def test_malicious_log_path_is_forwarded_but_failure_is_contained(orchestrator_factory):
    """Verify a malicious traversal path is passed downstream but any resulting failure stays contained."""
    ps = MagicMock()
    ps.process_user_data.return_value = {"status": "success", "data": {}}
    gw = MagicMock()
    gw.read_user_file.side_effect = PermissionError("Access denied outside sandbox")

    orch, *_ , ps_instance, gw_instance = orchestrator_factory(profile_service_mock=ps, gateway_mock=gw)

    malicious_path = "../../../../etc/shadow"
    result = orch.run_security_scan_and_update("user123", {}, malicious_path)

    gw_instance.read_user_file.assert_called_once_with(malicious_path)
    assert result["success"] is False
    assert result["stage"] == "log_reading"
    assert "Access denied outside sandbox" in result["error"]


def test_profile_data_missing_defaults_to_none_on_success(orchestrator_factory):
    """Verify that when a successful result lacks a 'data' key, profile defaults to None safely."""
    ps = MagicMock()
    ps.process_user_data.return_value = {"status": "success"}
    gw = MagicMock()
    gw.read_user_file.return_value = "some logs"

    orch, *_ , ps_instance, gw_instance = orchestrator_factory(profile_service_mock=ps, gateway_mock=gw)

    result = orch.run_security_scan_and_update("user123", {}, "logs/system.log")

    assert result["success"] is True
    assert result["profile"] is None
    assert result["logs"] == "some logs"


def test_empty_string_inputs_do_not_crash_orchestrator(orchestrator_factory):
    """Verify that empty/degenerate string inputs for user_id and log path are handled without crashing."""
    ps = MagicMock()
    ps.process_user_data.return_value = {"status": "success", "data": {}}
    gw = MagicMock()
    gw.read_user_file.return_value = ""

    orch, *_ , ps_instance, gw_instance = orchestrator_factory(profile_service_mock=ps, gateway_mock=gw)

    result = orch.run_security_scan_and_update("", {}, "")

    ps_instance.process_user_data.assert_called_once_with("", {})
    gw_instance.read_user_file.assert_called_once_with("")
    assert result["success"] is True
    assert result["logs"] == ""


def test_non_dict_result_from_profile_service_raises_attribute_error_is_contained(orchestrator_factory):
    """Verify orchestrator's behavior is deterministic (raises) if profile_service returns a non-dict object."""
    ps = MagicMock()
    ps.process_user_data.return_value = None  # malformed / unexpected downstream response
    gw = MagicMock()

    orch, *_ , ps_instance, gw_instance = orchestrator_factory(profile_service_mock=ps, gateway_mock=gw)

    with pytest.raises(AttributeError):
        orch.run_security_scan_and_update("user123", {}, "logs/system.log")

    gw_instance.read_user_file.assert_not_called()
