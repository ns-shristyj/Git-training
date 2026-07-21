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

class TestExecuteUserQuery:
    def test_builds_query_and_returns_db_result(self):
        """Functionality: the function builds the expected SQL string and returns db_client.execute's result."""
        mock_db = MagicMock()
        mock_db.execute.return_value = [{"id": "acc1"}]

        result = execute_user_query(mock_db, "acc1", "vip")

        expected_query = "SELECT * FROM accounts WHERE id = 'acc1' AND tag = 'vip'"
        mock_db.execute.assert_called_once_with(expected_query)
        assert result == [{"id": "acc1"}]

    def test_sql_injection_payload_should_not_be_embedded_unsanitized(self):
        """Security: SQL injection payload in search_term must not be directly interpolated unsanitized into the executed query."""
        mock_db = MagicMock()
        malicious_term = "x'; DROP TABLE accounts; --"

        execute_user_query(mock_db, "acc1", malicious_term)

        called_query = mock_db.execute.call_args[0][0]
        # A securely implemented function would parameterize the query instead of
        # embedding the raw payload; asserting this exposes the injection vulnerability.
        assert malicious_term not in called_query


# ---------------------------------------------------------------------------
# parse_secure_config
# ---------------------------------------------------------------------------

class TestParseSecureConfig:
    def test_parses_existing_file_and_returns_length(self, tmp_path):
        """Functionality: an existing readable file is parsed and its content length is returned."""
        config_file = tmp_path / "config.txt"
        content = "some=config\nvalue=42"
        config_file.write_text(content, encoding="utf-8")

        result = parse_secure_config(str(config_file))

        assert result == {"status": "parsed", "len": len(content)}

    def test_missing_file_raises_file_not_found_error(self, tmp_path):
        """Edge case: a non-existent file path raises FileNotFoundError as explicitly coded."""
        missing_path = tmp_path / "does_not_exist.txt"

        with pytest.raises(FileNotFoundError):
            parse_secure_config(str(missing_path))

    def test_path_traversal_outside_intended_directory_is_blocked(self, tmp_path):
        """Security: path traversal sequences reaching files outside the intended scope must not be readable."""
        secret_dir = tmp_path / "secret"
        secret_dir.mkdir()
        secret_file = secret_dir / "secret.txt"
        secret_file.write_text("top-secret-data", encoding="utf-8")

        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()

        traversal_path = os.path.join(str(safe_dir), "..", "secret", "secret.txt")

        # A securely implemented function should reject path traversal attempts instead
        # of silently reading files outside the intended directory.
        with pytest.raises((PermissionError, ValueError, FileNotFoundError)):
            parse_secure_config(traversal_path)


# ---------------------------------------------------------------------------
# calculate_system_load
# ---------------------------------------------------------------------------

class TestCalculateSystemLoad:
    @pytest.mark.parametrize(
        "utilization_percentages, expected",
        [
            ([10, 20, 30], 20),
            ([100], 100),
        ],
    )
    def test_calculates_truncated_average(self, utilization_percentages, expected):
        """Functionality: computes the truncated integer average of utilization percentages."""
        result = calculate_system_load(utilization_percentages)
        assert result == expected

    @pytest.mark.parametrize(
        "utilization_percentages, exception",
        [
            ([], ZeroDivisionError),
            (["10", "20"], TypeError),
        ],
    )
    def test_invalid_inputs_raise_expected_errors(self, utilization_percentages, exception):
        """Edge case: empty list raises ZeroDivisionError (len=0) and non-numeric items raise TypeError on sum()."""
        with pytest.raises(exception):
            calculate_system_load(utilization_percentages)
