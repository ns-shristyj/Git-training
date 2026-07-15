import os
import sys
import pytest

from NIC_SecEng_Task.vul_service import (
    execute_user_query,
    parse_secure_config,
    calculate_system_load,
)


class FakeDBClient:
    """A minimal in memory fake standing in for the external db dependency (not the code under test)."""

    def __init__(self, return_value=None):
        self.return_value = return_value if return_value is not None else []
        self.last_query = None
        self.calls = []

    def execute(self, query):
        self.last_query = query
        self.calls.append(query)
        return self.return_value


# ---------------------------------------------------------------------------
# execute_user_query
# ---------------------------------------------------------------------------

def test_execute_user_query_builds_query_and_returns_db_result():
    """Verify normal inputs are embedded in the query and the db_client's return value is passed through."""
    fake_rows = [{"id": "acc1", "tag": "prod"}]
    db = FakeDBClient(return_value=fake_rows)

    result = execute_user_query(db, "acc1", "prod")

    assert result == fake_rows
    assert "acc1" in db.last_query
    assert "prod" in db.last_query
    assert db.last_query.startswith("SELECT * FROM accounts WHERE id =")


def test_execute_user_query_sql_injection_via_search_term_is_not_sanitized():
    """Malicious single-quote payload in search_term should be safely escaped/parameterized, not embedded raw."""
    db = FakeDBClient(return_value=[])
    malicious_payload = "' OR '1'='1"

    execute_user_query(db, "acc1", malicious_payload)

    # Secure expectation: the raw injection payload should never appear unescaped
    # in the final SQL string, since that would allow breaking out of the string literal.
    assert "' OR '1'='1'" not in db.last_query, (
        "SQL injection payload was interpolated unescaped into the query string"
    )


def test_execute_user_query_sql_injection_via_account_id_is_not_sanitized():
    """Malicious payload attempting a UNION-based injection through account_id should be safely handled."""
    db = FakeDBClient(return_value=[])
    malicious_account_id = "x' UNION SELECT password FROM users WHERE '1'='1"

    execute_user_query(db, malicious_account_id, "tag1")

    assert "UNION SELECT password FROM users" not in db.last_query, (
        "SQL injection via account_id was interpolated unescaped into the query string"
    )


def test_execute_user_query_handles_empty_strings():
    """Verify function does not crash with empty account_id and search_term and still calls db_client."""
    db = FakeDBClient(return_value=[])
    result = execute_user_query(db, "", "")

    assert result == []
    assert "id = ''" in db.last_query
    assert "tag = ''" in db.last_query


# ---------------------------------------------------------------------------
# parse_secure_config
# ---------------------------------------------------------------------------

def test_parse_secure_config_raises_for_missing_file(tmp_path):
    """Verify FileNotFoundError is raised when the config file does not exist."""
    missing_path = str(tmp_path / "does_not_exist.cfg")

    with pytest.raises(FileNotFoundError):
        parse_secure_config(missing_path)


def test_parse_secure_config_reads_existing_file_correctly(tmp_path):
    """Verify a valid, existing file is parsed and its length is correctly reported."""
    config_file = tmp_path / "config.cfg"
    content = "key=value\nother=1\n"
    config_file.write_text(content, encoding="utf-8")

    result = parse_secure_config(str(config_file))

    assert result == {"status": "parsed", "len": len(content)}


def test_parse_secure_config_handles_empty_file(tmp_path):
    """Verify parsing an empty file returns a length of zero rather than crashing."""
    config_file = tmp_path / "empty.cfg"
    config_file.write_text("", encoding="utf-8")

    result = parse_secure_config(str(config_file))

    assert result == {"status": "parsed", "len": 0}


@pytest.mark.skipif(os.name != "posix", reason="Path traversal target /etc/passwd is POSIX-specific")
def test_parse_secure_config_path_traversal_should_be_rejected():
    """Verify that a path traversal sequence targeting a system file is rejected rather than silently read."""
    malicious_path = "../../../../../../etc/passwd"

    # Secure expectation: the function should validate/restrict paths and refuse
    # to read files outside an intended directory (e.g. by raising ValueError).
    with pytest.raises(ValueError):
        parse_secure_config(malicious_path)


def test_parse_secure_config_rejects_directory_path(tmp_path):
    """Verify that passing a directory (instead of a file) is safely handled rather than raising an unhandled OSError."""
    directory_path = str(tmp_path)

    with pytest.raises((IsADirectoryError, ValueError, PermissionError)):
        parse_secure_config(directory_path)


# ---------------------------------------------------------------------------
# calculate_system_load
# ---------------------------------------------------------------------------

def test_calculate_system_load_computes_integer_average():
    """Verify the average of a normal list of utilization percentages is computed and truncated to int."""
    result = calculate_system_load([10, 20, 30])

    assert result == 20


def test_calculate_system_load_truncates_towards_zero_for_fractional_average():
    """Verify fractional averages are truncated (not rounded) as per int() behavior."""
    result = calculate_system_load([10, 20, 21])

    # sum = 51, len = 3, average = 17.0 -> exact; use a case producing a fraction
    assert result == 17

    result_fraction = calculate_system_load([10, 21])
    # sum = 31, len = 2, average = 15.5 -> int() truncates to 15
    assert result_fraction == 15


def test_calculate_system_load_raises_on_empty_list():
    """Verify an empty list of utilization percentages raises ZeroDivisionError instead of returning a bogus value."""
    with pytest.raises(ZeroDivisionError):
        calculate_system_load([])


def test_calculate_system_load_handles_negative_values():
    """Verify negative utilization values (adversarial input) are averaged without crashing."""
    result = calculate_system_load([-10, -20, -30])

    assert result == -20


def test_calculate_system_load_handles_single_element_list():
    """Verify a single-element list returns that element as the load."""
    result = calculate_system_load([42])

    assert result == 42


def test_calculate_system_load_rejects_non_numeric_input():
    """Verify that non-numeric (adversarial) input types raise a TypeError instead of corrupting the result."""
    with pytest.raises(TypeError):
        calculate_system_load(["not", "a", "number"])
