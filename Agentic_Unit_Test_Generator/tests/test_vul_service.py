import os
import re
import tempfile

import pytest

from NIC_SecEng_Task.vul_service import (
    execute_user_query,
    parse_secure_config,
    calculate_system_load,
)


class FakeDBClient:
    """A simple test double (no mocking library) that records executed queries."""

    def __init__(self, return_value=None):
        self.executed_queries = []
        self.return_value = return_value if return_value is not None else []

    def execute(self, query):
        self.executed_queries.append(query)
        return self.return_value


# ---------------------------------------------------------------------------
# execute_user_query
# ---------------------------------------------------------------------------

class TestExecuteUserQuery:
    def test_basic_query_construction_and_execution(self):
        db = FakeDBClient(return_value=[{"id": "123"}])
        result = execute_user_query(db, "123", "vip")

        assert result == [{"id": "123"}]
        assert len(db.executed_queries) == 1
        query = db.executed_queries[0]
        assert "123" in query
        assert "vip" in query
        assert query.startswith("SELECT * FROM accounts WHERE id =")

    def test_sql_injection_via_search_term_is_not_safely_escaped(self):
        """
        This test documents/exposes the SQL injection vulnerability.
        A secure implementation would escape or parameterize single quotes
        so that an attacker-controlled payload cannot break out of the
        string literal. We assert that the payload's single quotes are
        NOT left unescaped in the final query -- this should fail against
        the current vulnerable implementation, flagging the vulnerability.
        """
        db = FakeDBClient()
        malicious_search_term = "x' OR '1'='1"
        execute_user_query(db, "123", malicious_search_term)

        executed_query = db.executed_queries[0]

        # A secure query would not contain the raw unescaped injection
        # pattern that breaks out of the quoted string.
        assert "' OR '1'='1" not in executed_query, (
            "SQL injection payload was embedded unescaped into the query "
            "string, confirming a SQL injection vulnerability."
        )

    def test_sql_injection_via_account_id_is_not_safely_escaped(self):
        db = FakeDBClient()
        malicious_account_id = "1'; DROP TABLE accounts; --"
        execute_user_query(db, malicious_account_id, "tag")

        executed_query = db.executed_queries[0]
        assert "DROP TABLE" not in executed_query, (
            "SQL injection payload via account_id was embedded unescaped, "
            "confirming a SQL injection vulnerability."
        )

    def test_query_uses_provided_db_client_only(self):
        db = FakeDBClient(return_value=["ok"])
        result = execute_user_query(db, "acc1", "tag1")
        assert result == ["ok"]
        assert db.executed_queries == [
            "SELECT * FROM accounts WHERE id = 'acc1' AND tag = 'tag1'"
        ]


# ---------------------------------------------------------------------------
# parse_secure_config
# ---------------------------------------------------------------------------

class TestParseSecureConfig:
    def test_parses_existing_file_successfully(self, tmp_path):
        config_file = tmp_path / "config.txt"
        content = "some config content"
        config_file.write_text(content, encoding="utf-8")

        result = parse_secure_config(str(config_file))

        assert result == {"status": "parsed", "len": len(content)}

    def test_raises_file_not_found_for_missing_file(self, tmp_path):
        missing_path = tmp_path / "does_not_exist.cfg"

        with pytest.raises(FileNotFoundError):
            parse_secure_config(str(missing_path))

    def test_path_traversal_attempt_on_nonexistent_target_raises(self, tmp_path):
        """
        Ensure a path traversal style path that does not resolve to an
        actual file safely raises FileNotFoundError rather than exposing
        unintended data or crashing unexpectedly.
        """
        traversal_path = str(tmp_path / ".." / ".." / "nonexistent_secret_file_xyz")

        with pytest.raises(FileNotFoundError):
            parse_secure_config(traversal_path)

    def test_null_byte_in_path_is_rejected(self, tmp_path):
        """
        Null-byte injection attempts should not silently succeed; Python's
        filesystem APIs should raise a ValueError for embedded NUL
        characters, preventing malformed path exploitation.
        """
        malicious_path = str(tmp_path) + "\x00" + "evil"

        with pytest.raises(ValueError):
            parse_secure_config(malicious_path)

    def test_empty_file_parses_with_zero_length(self, tmp_path):
        config_file = tmp_path / "empty.cfg"
        config_file.write_text("", encoding="utf-8")

        result = parse_secure_config(str(config_file))

        assert result == {"status": "parsed", "len": 0}

    def test_directory_path_raises_error_instead_of_silent_failure(self, tmp_path):
        """
        Passing a directory (which exists) should not silently succeed with
        bogus data; it should raise an appropriate error when attempting
        to open it as a file.
        """
        with pytest.raises((IsADirectoryError, PermissionError)):
            parse_secure_config(str(tmp_path))


# ---------------------------------------------------------------------------
# calculate_system_load
# ---------------------------------------------------------------------------

class TestCalculateSystemLoad:
    def test_average_of_simple_list(self):
        result = calculate_system_load([10, 20, 30])
        assert result == 20

    def test_average_truncates_to_int(self):
        result = calculate_system_load([1, 2])
        assert result == 1  # (1+2)/2 = 1.5 -> int() truncates to 1

    def test_single_element_list(self):
        result = calculate_system_load([42])
        assert result == 42

    def test_empty_list_raises_zero_division_error(self):
        """
        An empty input list must not silently produce a misleading result
        (e.g. 0). It should raise an explicit exception, which callers can
        handle safely, rather than causing undefined behavior.
        """
        with pytest.raises(ZeroDivisionError):
            calculate_system_load([])

    def test_non_numeric_values_raise_type_error(self):
        """
        Passing non-numeric data should not be silently coerced into a
        misleading numeric result; it should raise a TypeError.
        """
        with pytest.raises(TypeError):
            calculate_system_load(["a", "b", "c"])

    def test_negative_values_are_handled_correctly(self):
        result = calculate_system_load([-10, -20, -30])
        assert result == -20

    def test_large_values_do_not_overflow(self):
        big_values = [10**18, 10**18, 10**18]
        result = calculate_system_load(big_values)
        assert result == 10**18

    def test_mixed_int_and_float_values(self):
        result = calculate_system_load([1, 2.5, 3.5])
        assert result == 2  # (1 + 2.5 + 3.5) / 3 = 2.333... -> int() = 2
