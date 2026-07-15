import os
import re
import pytest
from unittest.mock import Mock

from NIC_SecEng_Task.vul_service import (
    execute_user_query,
    parse_secure_config,
    calculate_system_load,
)


# ---------------------------------------------------------------------------
# execute_user_query
# ---------------------------------------------------------------------------

class TestExecuteUserQuery:

    def test_builds_expected_query_with_benign_input(self):
        """Verifies the query string is constructed with the expected structure for normal input."""
        mock_db = Mock()
        mock_db.execute.return_value = [{"id": "123", "tag": "vip"}]

        result = execute_user_query(mock_db, "123", "vip")

        called_query = mock_db.execute.call_args[0][0]
        assert "id = '123'" in called_query
        assert "tag = 'vip'" in called_query
        assert result == [{"id": "123", "tag": "vip"}]

    def test_returns_db_client_execute_result(self):
        """Verifies the function returns exactly what db_client.execute returns."""
        mock_db = Mock()
        expected = [{"row": 1}]
        mock_db.execute.return_value = expected

        result = execute_user_query(mock_db, "acc1", "term1")

        assert result is expected

    def test_calls_execute_exactly_once(self):
        """Verifies db_client.execute is invoked exactly once per call."""
        mock_db = Mock()
        mock_db.execute.return_value = []

        execute_user_query(mock_db, "acc1", "term1")

        mock_db.execute.assert_called_once()

    def test_sql_injection_via_account_id_should_not_alter_query_semantics(self):
        """Exposes SQL injection: a malicious account_id must not be able to inject additional SQL logic unsanitized."""
        mock_db = Mock()
        mock_db.execute.return_value = []
        malicious_account_id = "' OR '1'='1"

        execute_user_query(mock_db, malicious_account_id, "safe_tag")

        called_query = mock_db.execute.call_args[0][0]
        # A secure implementation would sanitize/parameterize input so injected
        # SQL logic cannot appear verbatim in the executed query.
        assert "OR '1'='1'" not in called_query, (
            "SQL injection payload was embedded unsanitized in the executed query"
        )

    def test_sql_injection_via_search_term_should_not_alter_query_semantics(self):
        """Exposes SQL injection: a malicious search_term must not inject a DROP/UNION style payload unsanitized."""
        mock_db = Mock()
        mock_db.execute.return_value = []
        malicious_term = "'; DROP TABLE accounts; --"

        execute_user_query(mock_db, "acc1", malicious_term)

        called_query = mock_db.execute.call_args[0][0]
        assert "DROP TABLE" not in called_query, (
            "SQL injection payload was embedded unsanitized in the executed query"
        )

    def test_empty_string_inputs_do_not_break_query_structure(self):
        """Verifies empty string inputs still produce a syntactically bounded query without raising."""
        mock_db = Mock()
        mock_db.execute.return_value = []

        execute_user_query(mock_db, "", "")

        called_query = mock_db.execute.call_args[0][0]
        assert "id = ''" in called_query
        assert "tag = ''" in called_query


# ---------------------------------------------------------------------------
# parse_secure_config
# ---------------------------------------------------------------------------

class TestParseSecureConfig:

    def test_parses_existing_file_and_returns_length(self, tmp_path):
        """Verifies a valid config file is parsed and its content length is reported correctly."""
        config_file = tmp_path / "config.txt"
        content = "key=value\nother=1"
        config_file.write_text(content, encoding="utf-8")

        result = parse_secure_config(str(config_file))

        assert result == {"status": "parsed", "len": len(content)}

    def test_nonexistent_file_raises_file_not_found(self, tmp_path):
        """Verifies FileNotFoundError is raised for a path that does not exist."""
        missing_path = tmp_path / "does_not_exist.txt"

        with pytest.raises(FileNotFoundError):
            parse_secure_config(str(missing_path))

    def test_directory_path_raises_error_instead_of_parsing(self, tmp_path):
        """Verifies passing a directory (instead of a file) raises an error rather than silently succeeding."""
        with pytest.raises((IsADirectoryError, PermissionError, OSError)):
            parse_secure_config(str(tmp_path))

    def test_path_traversal_outside_intended_directory_should_be_blocked(self, tmp_path):
        """Exposes path traversal: reading a file outside an intended 'safe' directory via '..' should be rejected."""
        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("TOP_SECRET_DATA", encoding="utf-8")

        traversal_path = str(safe_dir / ".." / "secret.txt")

        # A secure implementation should reject traversal outside the sanctioned
        # directory rather than transparently reading the target file.
        with pytest.raises(ValueError):
            parse_secure_config(traversal_path)

    def test_null_byte_in_path_is_rejected(self):
        """Verifies embedded null bytes in the file path are safely rejected instead of causing undefined behavior."""
        malicious_path = "config.txt\x00.png"

        with pytest.raises((ValueError, FileNotFoundError, OSError)):
            parse_secure_config(malicious_path)

    def test_empty_file_returns_zero_length(self, tmp_path):
        """Verifies an empty config file yields a length of zero without error."""
        config_file = tmp_path / "empty.txt"
        config_file.write_text("", encoding="utf-8")

        result = parse_secure_config(str(config_file))

        assert result == {"status": "parsed", "len": 0}


# ---------------------------------------------------------------------------
# calculate_system_load
# ---------------------------------------------------------------------------

class TestCalculateSystemLoad:

    def test_calculates_average_of_positive_values(self):
        """Verifies the average is computed correctly and truncated to an int for typical positive input."""
        result = calculate_system_load([10, 20, 30])
        assert result == 20

    def test_truncates_towards_zero_for_fractional_average(self):
        """Verifies fractional averages are truncated (not rounded) as per int() semantics."""
        result = calculate_system_load([1, 2, 4])
        # sum=7, len=3 -> 2.333... -> int() truncates to 2
        assert result == 2

    def test_empty_list_raises_zero_division_error(self):
        """Verifies an empty utilization list raises ZeroDivisionError instead of crashing silently or returning garbage."""
        with pytest.raises(ZeroDivisionError):
            calculate_system_load([])

    def test_non_numeric_values_raise_type_error(self):
        """Verifies type confusion input (non-numeric list elements) raises TypeError rather than corrupting results."""
        with pytest.raises(TypeError):
            calculate_system_load(["a", "b", "c"])

    def test_negative_values_are_handled_correctly(self):
        """Verifies negative utilization values are averaged correctly without special-case failures."""
        result = calculate_system_load([-10, -20, -30])
        assert result == -20

    def test_single_element_list_returns_that_value(self):
        """Verifies a single-element list returns that element as the average."""
        result = calculate_system_load([42])
        assert result == 42

    def test_non_list_iterable_input_is_supported(self):
        """Verifies the function works with any iterable supported by sum()/len(), such as a tuple."""
        result = calculate_system_load((10, 20))
        assert result == 15

    def test_non_iterable_input_raises_type_error(self):
        """Verifies passing a non-iterable (e.g., an integer) raises TypeError instead of undefined behavior."""
        with pytest.raises(TypeError):
            calculate_system_load(42)
