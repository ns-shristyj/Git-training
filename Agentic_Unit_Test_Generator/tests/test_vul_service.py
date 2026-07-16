import os
import stat
import pytest

from NIC_SecEng_Task.vul_service import (
    execute_user_query,
    parse_secure_config,
    calculate_system_load,
)


class FakeDBClient:
    """A minimal in-memory fake standing in for the external DB dependency."""

    def __init__(self, return_value=None):
        self.return_value = return_value if return_value is not None else []
        self.last_query = None
        self.call_count = 0

    def execute(self, query):
        self.last_query = query
        self.call_count += 1
        return self.return_value


# ---------------------------------------------------------------------------
# execute_user_query
# ---------------------------------------------------------------------------

def test_execute_user_query_builds_expected_query_and_returns_result():
    """Verify normal inputs produce the expected query text and pass through db_client's result."""
    fake_client = FakeDBClient(return_value=[{"id": "123", "tag": "prod"}])
    result = execute_user_query(fake_client, "123", "prod")

    assert fake_client.call_count == 1
    assert "123" in fake_client.last_query
    assert "prod" in fake_client.last_query
    assert result == [{"id": "123", "tag": "prod"}]


def test_execute_user_query_calls_execute_exactly_once():
    """Ensure the function invokes db_client.execute exactly once per call."""
    fake_client = FakeDBClient()
    execute_user_query(fake_client, "acc1", "term1")
    assert fake_client.call_count == 1


def test_execute_user_query_sql_injection_in_account_id_is_not_sanitized():
    """SECURITY: account_id containing a SQL injection payload must not be executed as raw unescaped SQL."""
    fake_client = FakeDBClient()
    malicious_account_id = "1' OR '1'='1"
    execute_user_query(fake_client, malicious_account_id, "safe_term")

    # A secure implementation should never place the raw breakout sequence
    # unescaped into the executed query string.
    assert "' OR '1'='1" not in fake_client.last_query, (
        "SQL injection payload was concatenated unsanitized into the query"
    )


def test_execute_user_query_sql_injection_in_search_term_is_not_sanitized():
    """SECURITY: search_term containing a SQL injection payload must not be executed as raw unescaped SQL."""
    fake_client = FakeDBClient()
    malicious_search_term = "x'; DROP TABLE accounts; --"
    execute_user_query(fake_client, "acc1", malicious_search_term)

    assert "DROP TABLE" not in fake_client.last_query, (
        "SQL injection payload allowed destructive SQL to be embedded in the query"
    )


def test_execute_user_query_quote_breakout_is_escaped():
    """SECURITY: a single quote intended to break out of the string literal should be escaped, not passed through raw."""
    fake_client = FakeDBClient()
    execute_user_query(fake_client, "acc1", "a' UNION SELECT password FROM users --")

    assert "UNION SELECT password" not in fake_client.last_query, (
        "UNION-based injection payload was not sanitized before query execution"
    )


# ---------------------------------------------------------------------------
# parse_secure_config
# ---------------------------------------------------------------------------

def test_parse_secure_config_valid_file_returns_parsed_status(tmp_path):
    """Verify a valid, existing config file is parsed and status/len are correctly reported."""
    config_file = tmp_path / "config.txt"
    content = "key=value\nother=data"
    config_file.write_text(content, encoding="utf-8")

    result = parse_secure_config(str(config_file))

    assert result["status"] == "parsed"
    assert result["len"] == len(content)


def test_parse_secure_config_nonexistent_file_raises_file_not_found(tmp_path):
    """Verify a FileNotFoundError is raised when the requested config path does not exist."""
    missing_path = str(tmp_path / "does_not_exist.cfg")

    with pytest.raises(FileNotFoundError):
        parse_secure_config(missing_path)


def test_parse_secure_config_empty_file_returns_zero_length(tmp_path):
    """Verify an empty config file yields length 0 without raising."""
    config_file = tmp_path / "empty.cfg"
    config_file.write_text("", encoding="utf-8")

    result = parse_secure_config(str(config_file))

    assert result == {"status": "parsed", "len": 0}


def test_parse_secure_config_path_traversal_is_rejected(tmp_path):
    """SECURITY: a path traversal sequence attempting to escape the intended directory should be rejected."""
    traversal_path = str(tmp_path / ".." / ".." / "etc" / "passwd")

    # A secure implementation should validate/normalize the path and reject
    # traversal attempts explicitly (e.g. via ValueError) rather than silently
    # attempting to open arbitrary filesystem locations.
    with pytest.raises(ValueError):
        parse_secure_config(traversal_path)


def test_parse_secure_config_null_byte_in_path_is_rejected(tmp_path):
    """SECURITY: a path containing an embedded null byte must be rejected rather than passed to filesystem calls."""
    malicious_path = str(tmp_path) + "\x00malicious"

    with pytest.raises(ValueError):
        parse_secure_config(malicious_path)


# ---------------------------------------------------------------------------
# calculate_system_load
# ---------------------------------------------------------------------------

def test_calculate_system_load_computes_integer_average():
    """Verify the average utilization is computed and truncated to an int."""
    result = calculate_system_load([10, 20, 30])
    assert result == 20


def test_calculate_system_load_truncates_toward_zero_for_fractional_average():
    """Verify fractional averages are truncated (not rounded) per int() semantics."""
    result = calculate_system_load([10, 15])
    # (10 + 15) / 2 = 12.5 -> int() truncates to 12
    assert result == 12


def test_calculate_system_load_empty_list_raises_zero_division_error():
    """Verify passing an empty list raises ZeroDivisionError rather than silently returning a bogus value."""
    with pytest.raises(ZeroDivisionError):
        calculate_system_load([])


def test_calculate_system_load_handles_negative_values():
    """Verify negative utilization values are averaged correctly without special-case failures."""
    result = calculate_system_load([-10, 10, 0])
    assert result == 0


def test_calculate_system_load_non_numeric_elements_raise_type_error():
    """SECURITY/ROBUSTNESS: non-numeric elements in the input list must raise TypeError rather than corrupt output."""
    with pytest.raises(TypeError):
        calculate_system_load(["a", "b", "c"])


def test_calculate_system_load_mixed_type_list_raises_type_error():
    """SECURITY/ROBUSTNESS: mixing numeric and non-numeric types should raise TypeError instead of producing an incorrect result."""
    with pytest.raises(TypeError):
        calculate_system_load([10, "20", 30])
