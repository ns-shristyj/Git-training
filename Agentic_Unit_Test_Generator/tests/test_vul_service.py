import os
import pytest

from NIC_SecEng_Task.vul_service import (
    execute_user_query,
    parse_secure_config,
    calculate_system_load,
)


class FakeDBClient:
    """A minimal stand-in for a real DB client dependency (not the code under test)."""

    def __init__(self, return_value=None):
        self.last_query = None
        self.calls = []
        self._return_value = return_value if return_value is not None else []

    def execute(self, query):
        self.last_query = query
        self.calls.append(query)
        return self._return_value


# ---------------------------------------------------------------------------
# execute_user_query
# ---------------------------------------------------------------------------

def test_execute_user_query_returns_db_client_result():
    """Verifies the function returns exactly what db_client.execute() returns for benign input."""
    expected_rows = [{"id": "acc1", "tag": "prod"}]
    db = FakeDBClient(return_value=expected_rows)

    result = execute_user_query(db, "acc1", "prod")

    assert result == expected_rows
    assert db.last_query is not None


def test_execute_user_query_includes_benign_values_in_query():
    """Verifies benign account_id and search_term values are present in the generated query."""
    db = FakeDBClient()

    execute_user_query(db, "acc123", "billing")

    assert "acc123" in db.last_query
    assert "billing" in db.last_query


def test_execute_user_query_sql_injection_via_search_term_should_be_sanitized():
    """SECURITY: a SQL injection payload in search_term must not appear verbatim/unescaped in the executed query."""
    db = FakeDBClient()
    malicious_payload = "'; DROP TABLE accounts; --"

    execute_user_query(db, "acc1", malicious_payload)

    assert malicious_payload not in db.last_query, (
        "SQL injection payload was embedded unescaped in the query - "
        "search_term is not sanitized/parameterized, which is a vulnerability."
    )


def test_execute_user_query_sql_injection_via_account_id_should_be_sanitized():
    """SECURITY: a SQL injection payload in account_id must not appear verbatim/unescaped in the executed query."""
    db = FakeDBClient()
    malicious_payload = "' OR '1'='1"

    execute_user_query(db, malicious_payload, "tag1")

    assert malicious_payload not in db.last_query, (
        "SQL injection payload was embedded unescaped in the query via account_id - "
        "account_id is not sanitized/parameterized, which is a vulnerability."
    )


def test_execute_user_query_boolean_based_injection_does_not_bypass_filter():
    """SECURITY: an always-true injection (e.g. OR '1'='1') should not be allowed to silently widen the query scope."""
    db = FakeDBClient()
    injection = "x' OR '1'='1"

    execute_user_query(db, "acc1", injection)

    # A secure implementation would parameterize the value so that the raw
    # tautology clause never becomes part of the executable SQL text.
    assert "OR '1'='1'" not in db.last_query, (
        "Boolean-based SQL injection payload was not neutralized."
    )


# ---------------------------------------------------------------------------
# parse_secure_config
# ---------------------------------------------------------------------------

def test_parse_secure_config_valid_file_returns_expected_structure(tmp_path):
    """Verifies a well-formed existing config file is parsed and returns correct status/length."""
    config_file = tmp_path / "config.txt"
    content = "key=value\nother=1"
    config_file.write_text(content, encoding="utf-8")

    result = parse_secure_config(str(config_file))

    assert result["status"] == "parsed"
    assert result["len"] == len(content)


def test_parse_secure_config_missing_file_raises_file_not_found_error(tmp_path):
    """Verifies a FileNotFoundError is raised when the target config file does not exist."""
    missing_path = tmp_path / "does_not_exist.cfg"

    with pytest.raises(FileNotFoundError):
        parse_secure_config(str(missing_path))


def test_parse_secure_config_empty_file_returns_zero_length(tmp_path):
    """Verifies an empty existing file is parsed successfully with length zero."""
    empty_file = tmp_path / "empty.cfg"
    empty_file.write_text("", encoding="utf-8")

    result = parse_secure_config(str(empty_file))

    assert result == {"status": "parsed", "len": 0}


def test_parse_secure_config_path_traversal_should_be_blocked(tmp_path):
    """SECURITY: path traversal outside the intended directory should be rejected, not silently read."""
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    secret_file = secret_dir / "secret.txt"
    secret_file.write_text("top secret content", encoding="utf-8")

    app_dir = tmp_path / "app"
    app_dir.mkdir()

    traversal_path = os.path.join(str(app_dir), "..", "secret", "secret.txt")

    with pytest.raises(ValueError):
        # A secure implementation should validate the resolved path stays
        # within an allowed base directory and reject traversal attempts.
        parse_secure_config(traversal_path)


def test_parse_secure_config_absolute_sensitive_path_should_be_blocked():
    """SECURITY: absolute paths pointing at sensitive system files should be rejected rather than parsed."""
    sensitive_path = os.path.join(os.sep, "etc", "passwd")

    with pytest.raises(ValueError):
        # Even if the file exists on the host OS, a secure config parser
        # should refuse to open arbitrary absolute/system paths.
        parse_secure_config(sensitive_path)


# ---------------------------------------------------------------------------
# calculate_system_load
# ---------------------------------------------------------------------------

def test_calculate_system_load_basic_average():
    """Verifies the average of a normal list of utilization percentages is computed correctly."""
    result = calculate_system_load([10, 20, 30])

    assert result == 20


def test_calculate_system_load_truncates_towards_zero():
    """Verifies fractional averages are truncated (int cast) rather than rounded."""
    result = calculate_system_load([1, 2])

    assert result == 1  # (1+2)/2 = 1.5 -> int() truncates to 1


def test_calculate_system_load_empty_list_raises_zero_division_error():
    """Verifies an empty utilization list raises ZeroDivisionError instead of crashing unexpectedly elsewhere."""
    with pytest.raises(ZeroDivisionError):
        calculate_system_load([])


def test_calculate_system_load_negative_values_handled():
    """Verifies negative utilization values are averaged correctly without special-case errors."""
    result = calculate_system_load([-10, -20, -30])

    assert result == -20


def test_calculate_system_load_non_numeric_input_raises_type_error():
    """SECURITY/robustness: non-numeric elements in the input list should raise a TypeError rather than proceed silently."""
    with pytest.raises(TypeError):
        calculate_system_load([10, "20", 30])
