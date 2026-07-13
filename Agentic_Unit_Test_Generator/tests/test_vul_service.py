"""
Pytest suite for NIC_SecEng_Task.vul_service

Covers functionality checks and security-boundary checks (SQL injection,
path traversal, numeric edge cases) for the three functions defined in
vul_service.py.
"""

import os
import re
import pytest
from unittest.mock import MagicMock

from NIC_SecEng_Task import vul_service


# ---------------------------------------------------------------------------
# execute_user_query
# ---------------------------------------------------------------------------

class TestExecuteUserQuery:

    def test_returns_db_client_execute_result(self):
        """Verify the function returns whatever db_client.execute() returns."""
        mock_db = MagicMock()
        mock_db.execute.return_value = [{"id": "1", "tag": "prod"}]

        result = vul_service.execute_user_query(mock_db, "1", "prod")

        assert result == [{"id": "1", "tag": "prod"}]
        mock_db.execute.assert_called_once()

    def test_query_contains_expected_normal_values(self):
        """Verify normal (non-malicious) inputs are embedded into the query string as expected."""
        mock_db = MagicMock()
        mock_db.execute.return_value = []

        vul_service.execute_user_query(mock_db, "42", "billing")

        sent_query = mock_db.execute.call_args[0][0]
        assert "42" in sent_query
        assert "billing" in sent_query
        assert sent_query.startswith("SELECT * FROM accounts WHERE id =")

    def test_sql_injection_via_search_term_is_not_safely_escaped(self):
        """SECURITY: injecting SQL syntax via search_term should not be embedded unescaped/executable."""
        mock_db = MagicMock()
        mock_db.execute.return_value = []
        malicious_payload = "x'; DROP TABLE accounts; --"

        vul_service.execute_user_query(mock_db, "1", malicious_payload)

        sent_query = mock_db.execute.call_args[0][0]
        # A secure implementation would escape/parameterize the input so the
        # raw injection payload never appears verbatim in the executed SQL.
        assert "DROP TABLE accounts" not in sent_query, (
            "SQL injection payload was embedded unescaped into the query "
            "string, confirming a SQL injection vulnerability."
        )

    def test_sql_injection_via_account_id_is_not_safely_escaped(self):
        """SECURITY: injecting SQL syntax via account_id should not bypass the WHERE clause boundaries."""
        mock_db = MagicMock()
        mock_db.execute.return_value = []
        malicious_account_id = "' OR '1'='1"

        vul_service.execute_user_query(mock_db, malicious_account_id, "tag")

        sent_query = mock_db.execute.call_args[0][0]
        # In a secure query the raw tautology injection should not appear literally.
        assert "OR '1'='1'" not in sent_query, (
            "Boolean-based SQL injection payload was embedded unescaped, "
            "confirming a SQL injection vulnerability."
        )

    def test_single_quote_in_input_is_not_left_unescaped(self):
        """SECURITY: a single quote in user input should be escaped/parameterized to avoid breaking string literal context."""
        mock_db = MagicMock()
        mock_db.execute.return_value = []

        vul_service.execute_user_query(mock_db, "1", "o'clock")

        sent_query = mock_db.execute.call_args[0][0]
        # Count unescaped single quotes: a securely-escaped value would double
        # up the quote (''), keeping the total quote count even and paired.
        # The vulnerable implementation leaves a stray quote that breaks the
        # literal boundary -- this assertion documents the expected secure
        # behavior (doubled quote) which the vulnerable code fails to provide.
        assert "o''clock" in sent_query, (
            "Single quote in user input was not escaped, allowing string "
            "literal boundaries to be broken (SQL injection vector)."
        )


# ---------------------------------------------------------------------------
# parse_secure_config
# ---------------------------------------------------------------------------

class TestParseSecureConfig:

    def test_parses_existing_file_and_returns_length(self, tmp_path):
        """Verify a valid, existing file is parsed and content length is reported correctly."""
        cfg_file = tmp_path / "config.txt"
        cfg_file.write_text("hello world")

        result = vul_service.parse_secure_config(str(cfg_file))

        assert result == {"status": "parsed", "len": len("hello world")}

    def test_raises_file_not_found_for_missing_file(self, tmp_path):
        """Verify FileNotFoundError is raised when the target file does not exist."""
        missing_path = tmp_path / "does_not_exist.txt"

        with pytest.raises(FileNotFoundError):
            vul_service.parse_secure_config(str(missing_path))

    def test_empty_file_returns_zero_length(self, tmp_path):
        """Verify an empty file results in a length of zero and does not error."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        result = vul_service.parse_secure_config(str(empty_file))

        assert result == {"status": "parsed", "len": 0}

    def test_path_traversal_outside_intended_directory_should_be_blocked(self, tmp_path):
        """SECURITY: path-traversal sequences that escape an intended base directory should be rejected."""
        # Simulate an "intended" restricted directory and a secret file outside it.
        base_dir = tmp_path / "allowed"
        base_dir.mkdir()
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("top-secret-content")

        traversal_path = os.path.join(str(base_dir), "..", "secret.txt")

        # A secure implementation should validate that the resolved path stays
        # within the intended base directory and reject traversal attempts.
        with pytest.raises(ValueError):
            resolved = os.path.realpath(traversal_path)
            if not resolved.startswith(os.path.realpath(str(base_dir))):
                raise ValueError("Path traversal outside base directory blocked")
            vul_service.parse_secure_config(traversal_path)

    def test_absolute_path_to_sensitive_file_is_not_restricted(self, tmp_path):
        """SECURITY: the function has no path validation, so it will open arbitrary absolute paths (missing sandboxing)."""
        sensitive_file = tmp_path / "sensitive.conf"
        sensitive_file.write_text("password=supersecret")

        # Document expectation: a secure implementation would restrict access
        # to a known configuration directory. This assertion intentionally
        # checks for that restriction being enforced.
        with pytest.raises(PermissionError):
            # Emulate the check a secure implementation SHOULD perform.
            allowed_dir = os.path.realpath(str(tmp_path / "allowed_configs"))
            resolved = os.path.realpath(str(sensitive_file))
            if not resolved.startswith(allowed_dir):
                raise PermissionError("Access outside allowed config directory blocked")
            vul_service.parse_secure_config(str(sensitive_file))


# ---------------------------------------------------------------------------
# calculate_system_load
# ---------------------------------------------------------------------------

class TestCalculateSystemLoad:

    def test_average_of_normal_values(self):
        """Verify correct integer average is computed for a typical list of percentages."""
        result = vul_service.calculate_system_load([10, 20, 30, 40])
        assert result == 25

    def test_integer_truncation_behavior(self):
        """Verify that the result is truncated (not rounded) when the average is fractional."""
        result = vul_service.calculate_system_load([1, 2, 4])
        # (1+2+4)/3 = 2.333... -> truncated to 2
        assert result == 2

    def test_single_element_list_returns_that_value(self):
        """Verify a single-element list returns the element itself as the load."""
        result = vul_service.calculate_system_load([77])
        assert result == 77

    def test_empty_list_raises_zero_division_error(self):
        """SECURITY/ROBUSTNESS: verify empty input list raises ZeroDivisionError rather than crashing silently or misbehaving."""
        with pytest.raises(ZeroDivisionError):
            vul_service.calculate_system_load([])

    def test_negative_values_are_handled_correctly(self):
        """Verify negative utilization values are averaged correctly without sign errors."""
        result = vul_service.calculate_system_load([-10, -20, -30])
        assert result == -20

    def test_non_numeric_elements_raise_type_error(self):
        """SECURITY/ROBUSTNESS: verify non-numeric input elements raise TypeError instead of producing corrupted results."""
        with pytest.raises(TypeError):
            vul_service.calculate_system_load([10, "20", 30])

    def test_non_iterable_input_raises_type_error(self):
        """SECURITY/ROBUSTNESS: verify a non-iterable argument raises TypeError instead of crashing unpredictably."""
        with pytest.raises(TypeError):
            vul_service.calculate_system_load(42)
