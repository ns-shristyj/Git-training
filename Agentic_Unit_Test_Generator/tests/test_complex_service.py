import pytest
from NIC_SecEng_Task.complex_service import (
    process_user_data,
    calculate_risk_score,
    format_api_endpoint,
)


# ---------------------------------------------------------------------------
# process_user_data
# ---------------------------------------------------------------------------

class TestProcessUserData:

    def test_valid_minimal_input_returns_expected_structure(self):
        """Verify a minimal valid dict produces the correctly shaped output."""
        result = process_user_data({"id": "User123"})
        assert result == {"user_id": "user123", "active": False, "email": None}

    def test_valid_input_with_active_status(self):
        """Verify status == 'active' correctly sets the active flag to True."""
        result = process_user_data({"id": "abc", "status": "active"})
        assert result["active"] is True

    def test_valid_input_with_valid_email(self):
        """Verify a well formed email passes validation and is returned unchanged."""
        result = process_user_data({"id": "abc", "email": "user@example.com"})
        assert result["email"] == "user@example.com"

    def test_id_is_stripped_and_lowercased(self):
        """Verify the id field is trimmed of whitespace and lowercased."""
        result = process_user_data({"id": "  MixedCase  "})
        assert result["user_id"] == "mixedcase"

    def test_non_dict_input_raises_type_error(self):
        """Verify passing a non-dict input raises TypeError."""
        with pytest.raises(TypeError):
            process_user_data(["id", "value"])

    def test_none_input_raises_type_error(self):
        """Verify passing None raises TypeError rather than crashing."""
        with pytest.raises(TypeError):
            process_user_data(None)

    def test_missing_id_raises_value_error(self):
        """Verify a missing 'id' key raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"email": "user@example.com"})

    def test_empty_string_id_raises_value_error(self):
        """Verify an empty string id is treated as falsy and rejected."""
        with pytest.raises(ValueError):
            process_user_data({"id": ""})

    def test_non_string_id_raises_value_error(self):
        """Verify a non-string id (e.g. int) is rejected with ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": 12345})

    def test_invalid_email_format_raises_value_error(self):
        """Verify an email lacking '@' or domain dot raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "abc", "email": "not-an-email"})

    def test_email_missing_domain_dot_raises_value_error(self):
        """Verify an email without a dot in the domain part is rejected."""
        with pytest.raises(ValueError):
            process_user_data({"id": "abc", "email": "user@localhost"})

    def test_email_header_injection_should_be_rejected(self):
        """Verify a CRLF header-injection payload in the email field is safely rejected."""
        malicious_email = "user@example.com\r\nBcc: attacker@evil.com"
        with pytest.raises(ValueError):
            process_user_data({"id": "abc", "email": malicious_email})

    def test_id_with_script_payload_is_not_executed_or_expanded(self):
        """Verify a script-injection style id is only lowercased/stripped, not executed or expanded."""
        payload = "<script>alert(1)</script>"
        result = process_user_data({"id": payload})
        assert result["user_id"] == payload.lower()

    def test_id_with_path_traversal_string_is_passed_through_unaltered_case(self):
        """Verify path traversal-like id strings are handled as plain text (no filesystem access)."""
        payload = "../../etc/passwd"
        result = process_user_data({"id": payload})
        assert result["user_id"] == payload.lower()

    def test_extra_unknown_keys_are_ignored(self):
        """Verify unexpected extra keys in the input dict do not break processing."""
        result = process_user_data({"id": "abc", "unexpected": "value"})
        assert result["user_id"] == "abc"


# ---------------------------------------------------------------------------
# calculate_risk_score
# ---------------------------------------------------------------------------

class TestCalculateRiskScore:

    def test_empty_list_returns_zero(self):
        """Verify an empty metrics list returns 0.0 without error."""
        assert calculate_risk_score([]) == 0.0

    def test_valid_scores_average_correctly(self):
        """Verify the average of valid numeric scores is computed correctly."""
        result = calculate_risk_score([10, 20, 30])
        assert result == 20.0

    def test_single_score_returns_that_score(self):
        """Verify a list with a single score returns that score as float."""
        result = calculate_risk_score([50])
        assert result == 50.0

    def test_boundary_values_zero_and_hundred_are_accepted(self):
        """Verify boundary values 0 and 100 are valid and included in the average."""
        result = calculate_risk_score([0, 100])
        assert result == 50.0

    def test_non_list_input_raises_type_error(self):
        """Verify a non-list metrics parameter raises TypeError."""
        with pytest.raises(TypeError):
            calculate_risk_score("not a list")

    def test_none_input_raises_type_error(self):
        """Verify None metrics parameter raises TypeError."""
        with pytest.raises(TypeError):
            calculate_risk_score(None)

    def test_non_numeric_entry_raises_value_error(self):
        """Verify a non-numeric entry in the metrics list raises ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([10, "high", 30])

    def test_negative_score_raises_value_error(self):
        """Verify a score below the 0 lower bound raises ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([-1, 50])

    def test_score_above_hundred_raises_value_error(self):
        """Verify a score above the 100 upper bound raises ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, 101])

    def test_dict_entry_raises_value_error(self):
        """Verify a dict/object masquerading as a metric entry is rejected."""
        with pytest.raises(ValueError):
            calculate_risk_score([{"score": 50}])

    def test_none_entry_in_list_raises_value_error(self):
        """Verify a None entry within the metrics list raises ValueError, not a crash."""
        with pytest.raises(ValueError):
            calculate_risk_score([10, None, 30])

    def test_boolean_values_are_treated_as_numeric_due_to_int_subclass(self):
        """Verify boolean entries (int subclass) are accepted, documenting a type-confusion edge case."""
        result = calculate_risk_score([True, False])
        assert result == 0.5


# ---------------------------------------------------------------------------
# format_api_endpoint
# ---------------------------------------------------------------------------

class TestFormatApiEndpoint:

    def test_basic_endpoint_without_resource(self):
        """Verify base URL and version alone produce a well-formed endpoint."""
        result = format_api_endpoint("https://api.example.com", 1, "")
        assert result == "https://api.example.com/v1"

    def test_endpoint_with_resource_appends_correctly(self):
        """Verify a resource path is appended correctly after the version segment."""
        result = format_api_endpoint("https://api.example.com", 2, "users")
        assert result == "https://api.example.com/v2/users"

    def test_trailing_slash_on_base_url_is_stripped(self):
        """Verify trailing slashes on the base URL are removed before concatenation."""
        result = format_api_endpoint("https://api.example.com/", 1, "users")
        assert result == "https://api.example.com/v1/users"

    def test_leading_slash_on_resource_is_stripped(self):
        """Verify a leading slash on the resource path does not create a double slash."""
        result = format_api_endpoint("https://api.example.com", 1, "/users")
        assert result == "https://api.example.com/v1/users"

    def test_empty_base_url_raises_value_error(self):
        """Verify an empty base URL raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("", 1, "users")

    def test_non_string_base_url_raises_value_error(self):
        """Verify a non-string base URL raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint(12345, 1, "users")

    def test_zero_version_raises_value_error(self):
        """Verify a version of zero is rejected as not strictly positive."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 0, "users")

    def test_negative_version_raises_value_error(self):
        """Verify a negative version number raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", -3, "users")

    def test_non_integer_version_raises_value_error(self):
        """Verify a non-integer version (e.g. string) raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", "1", "users")

    def test_resource_with_path_traversal_is_not_sanitized_should_be_blocked(self):
        """Verify a path-traversal payload in the resource segment is safely blocked or stripped."""
        result = format_api_endpoint("https://api.example.com", 1, "../../admin")
        assert ".." not in result

    def test_none_resource_returns_endpoint_without_resource_segment(self):
        """Verify a None resource value falls back to the version-only endpoint."""
        result = format_api_endpoint("https://api.example.com", 1, None)
        assert result == "https://api.example.com/v1"

    def test_whitespace_only_resource_returns_endpoint_without_resource_segment(self):
        """Verify a whitespace-only resource string collapses to the version-only endpoint."""
        result = format_api_endpoint("https://api.example.com", 1, "   ")
        assert result == "https://api.example.com/v1"
