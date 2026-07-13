import os
import pytest
from unittest.mock import MagicMock

from NIC_SecEng_Task.vul_service import (
    execute_user_query,
    parse_secure_config,
    calculate_system_load,
)


# ---------------------------------------------------------------------------
# execute_user_query
# ---------------------------------------------------------------------------

class FakeDBClient:
    """A minimal stand-in for a real DB client to capture the query passed."""
    def __init__(self):
        self.last_query = None

    def execute(self, query):
        self.last_query = query
        return [{"id": "1", "tag": "ok"}]


def test_execute_user_query_builds_expected_sql_and_returns_result():
    db_client = FakeDBClient()
    result = execute_user_query(db_client, "acc123", "vip")

    assert db_client.last_query == (
        "SELECT * FROM accounts WHERE id = 'acc123' AND tag = 'vip'"
    )
    assert result == [{"id": "1", "tag": "ok"}]


def test_execute_user_query_calls_execute_exactly_once_with_mock():
    db_client = MagicMock()
    db_client.execute.return_value = ["row"]

    result = execute_user_query(db_client, "42", "search")

    db_client.execute.assert_called_once()
    called_query = db_client.execute.call_args[0][0]
    assert "42" in called_query
    assert "search" in called_query
    assert result == ["row"]


def test_execute_user_query_is_vulnerable_to_sql_injection_via_account_id():
    """Demonstrates that a single-quote in account_id breaks out of the
    intended query structure (classic SQL injection)."""
    db_client = FakeDBClient()
    malicious_account_id = "1' OR '1'='1"
    execute_user_query(db_client, malicious_account_id, "tag")

    # The malicious input is embedded verbatim, proving no sanitization.
    assert "OR '1'='1'" in db_client.last_query
    assert malicious_account_id in db_client.last_query


def test_execute_user_query_is_vulnerable_to_sql_injection_via_search_term():
    db_client = FakeDBClient()
    malicious_term = "x'; DROP TABLE accounts; --"
    execute_user_query(db_client, "acc1", malicious_term)

    assert malicious_term in db_client.last_query
    assert "DROP TABLE accounts" in db_client.last_query


def test_execute_user_query_with_empty_strings():
    db_client = FakeDBClient()
    execute_user_query(db_client, "", "")
    assert db_client.last_query == "SELECT * FROM accounts WHERE id = '' AND tag = ''"


def test_execute_user_query_propagates_db_client_exceptions():
    db_client = MagicMock()
    db_client.execute.side_effect = RuntimeError("db connection failed")

    with pytest.raises(RuntimeError, match="db connection failed"):
        execute_user_query(db_client, "acc", "term")


# ---------------------------------------------------------------------------
# parse_secure_config
# ---------------------------------------------------------------------------

def test_parse_secure_config_raises_when_file_missing(tmp_path):
    missing_path = str(tmp_path / "does_not_exist.conf")

    with pytest.raises(FileNotFoundError, match="Configuration profile not found"):
        parse_secure_config(missing_path)


def test_parse_secure_config_parses_existing_file(tmp_path):
    file_path = tmp_path / "config.conf"
    content = "key=value\nanother=setting\n"
    file_path.write_text(content, encoding="utf-8")

    result = parse_secure_config(str(file_path))

    assert result == {"status": "parsed", "len": len(content)}


def test_parse_secure_config_handles_empty_file(tmp_path):
    file_path = tmp_path / "empty.conf"
    file_path.write_text("", encoding="utf-8")

    result = parse_secure_config(str(file_path))

    assert result == {"status": "parsed", "len": 0}


def test_parse_secure_config_allows_path_traversal_like_input(tmp_path):
    """No validation of file_path is performed; verify that a path pointing
    outside an expected 'safe' directory (e.g. via ../) is still processed,
    demonstrating a potential path traversal vulnerability."""
    nested_dir = tmp_path / "safe"
    nested_dir.mkdir()
    outside_file = tmp_path / "secret.conf"
    outside_file.write_text("top-secret-data", encoding="utf-8")

    traversal_path = str(nested_dir / ".." / "secret.conf")

    result = parse_secure_config(traversal_path)

    assert result == {"status": "parsed", "len": len("top-secret-data")}


def test_parse_secure_config_raises_on_directory_path(tmp_path):
    # os.path.exists returns True for directories too, so open() will raise
    # an IsADirectoryError instead of FileNotFoundError.
    with pytest.raises(IsADirectoryError):
        parse_secure_config(str(tmp_path))


# ---------------------------------------------------------------------------
# calculate_system_load
# ---------------------------------------------------------------------------

def test_calculate_system_load_basic_average():
    result = calculate_system_load([10, 20, 30])
    assert result == 20


def test_calculate_system_load_truncates_toward_zero():
    # sum=10, len=3 -> 10/3 = 3.33 -> int() truncates to 3
    result = calculate_system_load([5, 3, 2])
    assert result == int(10 / 3)


def test_calculate_system_load_single_value():
    result = calculate_system_load([42])
    assert result == 42


def test_calculate_system_load_raises_on_empty_list():
    with pytest.raises(ZeroDivisionError):
        calculate_system_load([])


def test_calculate_system_load_with_negative_values():
    result = calculate_system_load([-10, -20, -30])
    assert result == -20


def test_calculate_system_load_with_mixed_sign_values():
    result = calculate_system_load([-10, 20])
    assert result == int((-10 + 20) / 2)


def test_calculate_system_load_raises_on_non_numeric_input():
    with pytest.raises(TypeError):
        calculate_system_load(["a", "b"])
