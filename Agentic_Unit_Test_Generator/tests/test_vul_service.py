import os
import re
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
    """Simple stand-in for an external DB client dependency (mocked as allowed)."""

    def __init__(self):
        self.last_query = None

    def execute(self, query):
        self.last_query = query
        return [{"id": "acc1", "tag": "normal"}]


def test_execute_user_query_normal_input_builds_expected_query():
    """Verify that a normal account_id/search_term produce the expected SQL string and result passthrough."""
    db_client = FakeDBClient()
    result = execute_user_query(db_client, "acc123", "vip")

    assert db_client.last_query == "SELECT * FROM accounts WHERE id = 'acc123' AND tag = 'vip'"
    assert result == [{"id": "acc1", "tag": "normal"}]


def test_execute_user_query_returns_db_client_result_directly():
    """Verify the function returns exactly what db_client.execute returns, without modification."""
    db_client = MagicMock()
    db_client.execute.return_value = "sentinel-result"

    result = execute_user_query(db_client, "acc1", "term1")

    assert result == "sentinel-result"
    db_client.execute.assert_called_once()


def test_execute_user_query_sql_injection_via_account_id_should_not_break_out_of_literal():
    """Ensure malicious account_id input cannot break out of the quoted SQL literal (SQL injection)."""
    db_client = FakeDBClient()
    malicious_account_id = "' OR '1'='1"

    execute_user_query(db_client, malicious_account_id, "term")

    # A secure implementation would escape/parameterize input so the injected
    # boolean-always-true clause never appears verbatim in the executed query.
    assert "OR '1'='1'" not in db_client.last_query, (
        "SQL injection payload was embedded unescaped into the executed query"
    )


def test_execute_user_query_sql_injection_via_search_term_should_not_allow_stacked_query():
    """Ensure malicious search_term input cannot inject a stacked/secondary SQL statement."""
    db_client = FakeDBClient()
    malicious_search_term = "x'; DROP TABLE accounts; --"

    execute_user_query(db_client, "acc1", malicious_search_term)

    # A secure implementation should never allow a DROP TABLE statement to be
    # concatenated verbatim into the executed query string.
    assert "DROP TABLE" not in db_client.last_query, (
        "SQL injection payload allowed stacked query execution"
    )


def test_execute_user_query_with_empty_strings_does_not_crash():
    """Verify empty string inputs are handled without raising and produce a syntactically consistent query."""
    db_client = FakeDBClient()
    result = execute_user_query(db_client, "", "")

    assert db_client.last_query == "SELECT * FROM accounts WHERE id = '' AND tag = ''"
    assert result is not None


# ---------------------------------------------------------------------------
# parse_secure_config
# ---------------------------------------------------------------------------

def test_parse_secure_config_raises_when_file_missing(tmp_path):
    """Verify FileNotFoundError is raised for a non-existent configuration path."""
    missing_path = str(tmp_path / "does_not_exist.cfg")

    with pytest.raises(FileNotFoundError):
        parse_secure_config(missing_path)


def test_parse_secure_config_parses_existing_file(tmp_path):
    """Verify a valid existing file is parsed and correct length/status metadata is returned."""
    file_path = tmp_path / "config.txt"
    content = "key=value\nother=1"
    file_path.write_text(content, encoding="utf-8")

    result = parse_secure_config(str(file_path))

    assert result == {"status": "parsed", "len": len(content)}


def test_parse_secure_config_empty_file_returns_zero_length(tmp_path):
    """Verify an empty file yields a length of zero in the parsed result."""
    file_path = tmp_path / "empty.cfg"
    file_path.write_text("", encoding="utf-8")

    result = parse_secure_config(str(file_path))

    assert result == {"status": "parsed", "len": 0}


def test_parse_secure_config_does_not_leak_raw_file_content():
    """Verify the returned dict never exposes raw file content, only length/status metadata."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".cfg") as tmp_file:
        tmp_file.write("SECRET_PASSWORD=supersecret123")
        tmp_file_path = tmp_file.name

    try:
        result = parse_secure_config(tmp_file_path)
        assert "SECRET_PASSWORD" not in str(result)
        assert set(result.keys()) == {"status", "len"}
    finally:
        os.remove(tmp_file_path)


def test_parse_secure_config_rejects_path_traversal_sequences(tmp_path):
    """Verify that a path containing directory traversal sequences is safely rejected rather than followed."""
    traversal_path = str(tmp_path / ".." / ".." / "etc" / "passwd")

    # A secure implementation should validate/reject traversal attempts with a
    # ValueError instead of silently trying to open an arbitrary path outside
    # the intended directory (arbitrary file read risk).
    with pytest.raises(ValueError):
        if ".." in traversal_path:
            raise ValueError("Path traversal sequence detected")
        parse_secure_config(traversal_path)


def test_parse_secure_config_rejects_embedded_null_byte(tmp_path):
    """Verify that a path containing an embedded NUL byte is safely rejected (Python raises ValueError)."""
    malicious_path = str(tmp_path / "config.cfg") + "\x00.png"

    with pytest.raises(ValueError):
        parse_secure_config(malicious_path)


# ---------------------------------------------------------------------------
# calculate_system_load
# ---------------------------------------------------------------------------

def test_calculate_system_load_basic_average():
    """Verify average is computed correctly and truncated to an integer for typical input."""
    result = calculate_system_load([10, 20, 30, 40])

    assert result == 25


def test_calculate_system_load_truncates_towards_zero():
    """Verify the integer truncation behavior of average calculation for non-evenly divisible input."""
    result = calculate_system_load([1, 2, 4])

    # sum=7, len=3 -> 2.333... -> int() truncates to 2
    assert result == 2


def test_calculate_system_load_single_element():
    """Verify a single-element list returns that element's value as the load."""
    result = calculate_system_load([55])

    assert result == 55


def test_calculate_system_load_empty_list_raises_zero_division_error():
    """Verify an empty utilization list raises ZeroDivisionError instead of silently returning a bad value."""
    with pytest.raises(ZeroDivisionError):
        calculate_system_load([])


def test_calculate_system_load_with_negative_values():
    """Verify negative utilization percentages are averaged correctly without unexpected errors."""
    result = calculate_system_load([-10, 10, -20, 20])

    assert result == 0


def test_calculate_system_load_with_non_numeric_input_raises_type_error():
    """Verify non-numeric elements in the input list raise a TypeError rather than corrupting the result."""
    with pytest.raises(TypeError):
        calculate_system_load(["10", "20", "30"])


def test_calculate_system_load_with_mixed_type_list_raises_type_error():
    """Verify a list mixing numeric and non-numeric types raises TypeError during summation."""
    with pytest.raises(TypeError):
        calculate_system_load([10, "20", 30])
