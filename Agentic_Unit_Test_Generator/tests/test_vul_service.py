import os
import pytest
from unittest.mock import MagicMock, patch, mock_open

from NIC_SecEng_Task.vul_service import (
    execute_user_query,
    parse_secure_config,
    calculate_system_load,
)


# ---------------------------------------------------------------------------
# execute_user_query
# ---------------------------------------------------------------------------

def test_execute_user_query_happy_path():
    db_client = MagicMock()
    db_client.execute.return_value = [{"id": "123", "tag": "vip"}]

    result = execute_user_query(db_client, "123", "vip")

    expected_query = "SELECT * FROM accounts WHERE id = '123' AND tag = 'vip'"
    db_client.execute.assert_called_once_with(expected_query)
    assert result == [{"id": "123", "tag": "vip"}]


def test_execute_user_query_sql_injection_payload_passed_verbatim():
    db_client = MagicMock()
    db_client.execute.return_value = []

    injection = "' OR 1=1--"
    execute_user_query(db_client, "123", injection)

    called_query = db_client.execute.call_args[0][0]
    assert injection in called_query
    assert "OR 1=1" in called_query


def test_execute_user_query_oversized_input():
    db_client = MagicMock()
    db_client.execute.return_value = []

    huge_term = "a" * 10000
    execute_user_query(db_client, "123", huge_term)

    called_query = db_client.execute.call_args[0][0]
    assert huge_term in called_query


# ---------------------------------------------------------------------------
# parse_secure_config
# ---------------------------------------------------------------------------

def test_parse_secure_config_happy_path():
    with patch("NIC_SecEng_Task.vul_service.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="hello=world")):
        result = parse_secure_config("/etc/app/config.ini")

    assert result == {"status": "parsed", "len": len("hello=world")}


def test_parse_secure_config_missing_file_raises_filenotfounderror():
    missing_path = "/nonexistent/path/config.ini"
    with patch("NIC_SecEng_Task.vul_service.os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError) as exc_info:
            parse_secure_config(missing_path)

    assert str(exc_info.value) == f"Configuration profile not found at: {missing_path}"


def test_parse_secure_config_path_traversal_treated_as_ordinary_path():
    traversal_path = "../../../etc/passwd"
    with patch("NIC_SecEng_Task.vul_service.os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError) as exc_info:
            parse_secure_config(traversal_path)

    assert str(exc_info.value) == f"Configuration profile not found at: {traversal_path}"


# ---------------------------------------------------------------------------
# calculate_system_load
# ---------------------------------------------------------------------------

def test_calculate_system_load_happy_path():
    assert calculate_system_load([10, 20, 30]) == 20


def test_calculate_system_load_empty_list_raises_zerodivisionerror():
    with pytest.raises(ZeroDivisionError):
        calculate_system_load([])


def test_calculate_system_load_with_negative_values():
    assert calculate_system_load([-10, 10]) == 0


def test_calculate_system_load_non_numeric_raises_typeerror():
    with pytest.raises(TypeError):
        calculate_system_load(["a", "b", "c"])
