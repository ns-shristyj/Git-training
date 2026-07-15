import pytest
from NIC_SecEng_Task.complex_service import (
    process_user_data,
    calculate_risk_score,
    format_api_endpoint,
)


# ---------------------------
# process_user_data tests
# ---------------------------

class TestProcessUserData:
    def test_valid_minimal_input(self):
        """Valid dict with only id returns normalized user_id, inactive status, no email."""
        result = process_user_data({"id": "  User123  "})
        assert result == {"user_id": "user123", "active": False, "email": None}

    def test_valid_full_input_active_status(self):
        """Valid dict with id, email, and active status returns correct structure."""
        result = process_user_data({"id": "Alice", "email": "alice@example.com", "status": "active"})
        assert result["user_id"] == "alice"
        assert result["active"] is True
        assert result["email"] == "alice@example.com"

    def test_non_dict_input_raises_type_error(self):
        """Non-dict input (e.g. list) raises TypeError to prevent type confusion."""
        with pytest.raises(TypeError):
            process_user_data(["id", "email"])

    def test_string_input_raises_type_error(self):
        """String input raises TypeError since dict is required."""
        with pytest.raises(TypeError):
            process_user_data("id=1")

    def test_none_input_raises_type_error(self):
        """None input raises TypeError as it is not a dict."""
        with pytest.raises(TypeError):
            process_user_data(None)

    def test_missing_id_raises_value_error(self):
        """Missing 'id' key raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"email": "a@b.com"})

    def test_empty_string_id_raises_value_error(self):
        """Empty string 'id' raises ValueError since it is falsy."""
        with pytest.raises(ValueError):
            process_user_data({"id": ""})

    def test_non_string_id_raises_value_error(self):
        """Non-string 'id' (e.g. int) raises ValueError due to type check."""
        with pytest.raises(ValueError):
            process_user_data({"id": 12345})

    def test_none_id_raises_value_error(self):
        """None 'id' raises ValueError since it is falsy."""
        with pytest.raises(ValueError):
            process_user_data({"id": None})

    def test_invalid_email_format_raises_value_error(self):
        """Malformed email without '@' and domain raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "u1", "email": "not-an-email"})

    def test_email_missing_at_symbol_raises_value_error(self):
        """Email missing '@' symbol fails regex validation and raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "u1", "email": "userexample.com"})

    def test_email_missing_domain_dot_raises_value_error(self):
        """Email missing dot in domain portion raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "u1", "email": "user@examplecom"})

    def test_empty_email_string_is_allowed(self):
        """Empty string email is falsy and skips regex validation, returned as-is."""
        result = process_user_data({"id": "u1", "email": ""})
        assert result["email"] == ""

    def test_id_with_injection_like_content_is_normalized_safely(self):
        """SQL-injection-like string in id is treated as plain data and safely lowercased/stripped."""
        malicious_id = "  ' OR '1'='1  "
        result = process_user_data({"id": malicious_id})
        assert result["user_id"] == "' or '1'='1"
        assert isinstance(result["user_id"], str)

    def test_email_with_header_injection_like_newlines_rejected_or_passed_safely(self):
        """Email containing newline injection attempt either fails regex or is passed through unmodified without execution."""
        malicious_email = "a@b.com\nBcc: attacker@evil.com"
        # Regex uses re.match which anchors at start but not end; newline may still match first line.
        # Ensure no exception execution side effects occur and value is returned unmodified as string.
        result = process_user_data({"id": "u1", "email": malicious_email})
        assert result["email"] == malicious_email
        assert isinstance(result["email"], str)

    def test_status_not_active_results_in_inactive(self):
        """Any status value other than 'active' results in active flag False."""
        result = process_user_data({"id": "u1", "status": "disabled"})
        assert result["active"] is False

    def test_id_with_unicode_characters_normalized(self):
        """Unicode characters in id are safely lowercased and stripped without crashing."""
        result = process_user_data({"id": "  ÜserÑame  "})
        assert result["user_id"] == "üserñame"


# ---------------------------
# calculate_risk_score tests
# ---------------------------

class TestCalculateRiskScore:
    def test_empty_list_returns_zero(self):
        """Empty metrics list returns 0.0 as a base case."""
        assert calculate_risk_score([]) == 0.0

    def test_valid_scores_average(self):
        """Valid list of numeric scores returns correct average."""
        result = calculate_risk_score([10, 20, 30])
        assert result == pytest.approx(20.0)

    def test_valid_float_scores_average(self):
        """List of float scores computes correct average."""
        result = calculate_risk_score([50.5, 49.5])
        assert result == pytest.approx(50.0)

    def test_boundary_values_zero_and_hundred(self):
        """Boundary values 0 and 100 are accepted as valid within inclusive range."""
        result = calculate_risk_score([0, 100])
        assert result == pytest.approx(50.0)

    def test_non_list_input_raises_type_error(self):
        """Non-list input (e.g. dict) raises TypeError."""
        with pytest.raises(TypeError):
            calculate_risk_score({"score": 50})

    def test_string_input_raises_type_error(self):
        """String input raises TypeError since it's not a list."""
        with pytest.raises(TypeError):
            calculate_risk_score("50,60,70")

    def test_non_numeric_element_raises_value_error(self):
        """List containing a non-numeric element raises ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([10, "bad", 30])

    def test_boolean_elements_are_accepted_as_numeric(self):
        """Boolean values are instances of int in Python and thus accepted, exposing type-confusion edge case."""
        result = calculate_risk_score([True, False])
        assert result == pytest.approx(0.5)

    def test_negative_score_raises_value_error(self):
        """Negative score below 0 raises ValueError due to boundary violation."""
        with pytest.raises(ValueError):
            calculate_risk_score([-1, 50])

    def test_score_above_hundred_raises_value_error(self):
        """Score above 100 raises ValueError due to boundary violation."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, 101])

    def test_none_in_list_raises_value_error(self):
        """None value inside metrics list raises ValueError since it's not numeric."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, None])

    def test_nested_list_element_raises_value_error(self):
        """Nested list as an element raises ValueError since it's not numeric type."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, [1, 2]])


# ---------------------------
# format_api_endpoint tests
# ---------------------------

class TestFormatApiEndpoint:
    def test_basic_valid_endpoint_construction(self):
        """Valid base_url, version, and resource produce correctly formatted endpoint."""
        result = format_api_endpoint("https://api.example.com", 1, "users")
        assert result == "https://api.example.com/v1/users"

    def test_trailing_slash_in_base_url_is_stripped(self):
        """Trailing slash in base_url is stripped to avoid double slashes."""
        result = format_api_endpoint("https://api.example.com/", 2, "orders")
        assert result == "https://api.example.com/v2/orders"

    def test_leading_slash_in_resource_is_stripped(self):
        """Leading slash in resource path is stripped to avoid double slashes."""
        result = format_api_endpoint("https://api.example.com", 1, "/users")
        assert result == "https://api.example.com/v1/users"

    def test_empty_resource_omits_resource_segment(self):
        """Empty resource string results in endpoint without a resource segment."""
        result = format_api_endpoint("https://api.example.com", 3, "")
        assert result == "https://api.example.com/v3"

    def test_none_resource_omits_resource_segment(self):
        """None resource results in endpoint without a resource segment."""
        result = format_api_endpoint("https://api.example.com", 1, None)
        assert result == "https://api.example.com/v1"

    def test_empty_base_url_raises_value_error(self):
        """Empty base_url string raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("", 1, "users")

    def test_none_base_url_raises_value_error(self):
        """None base_url raises ValueError since it's falsy."""
        with pytest.raises(ValueError):
            format_api_endpoint(None, 1, "users")

    def test_non_string_base_url_raises_value_error(self):
        """Non-string base_url (e.g. int) raises ValueError due to type check."""
        with pytest.raises(ValueError):
            format_api_endpoint(12345, 1, "users")

    def test_zero_version_raises_value_error(self):
        """Version equal to zero raises ValueError since it must be positive."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 0, "users")

    def test_negative_version_raises_value_error(self):
        """Negative version raises ValueError since it must be positive."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", -5, "users")

    def test_non_integer_version_raises_value_error(self):
        """Non-integer version (e.g. string) raises ValueError due to type check."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", "1", "users")

    def test_float_version_raises_value_error(self):
        """Float version raises ValueError since isinstance(version, int) is False for floats."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 1.5, "users")

    def test_path_traversal_in_resource_is_preserved_literally_not_executed(self):
        """Path traversal sequence in resource is preserved literally as a string, not resolved or executed."""
        result = format_api_endpoint("https://api.example.com", 1, "../../etc/passwd")
        assert result == "https://api.example.com/v1/../../etc/passwd"
        # Ensure no filesystem resolution occurred; output remains a plain string endpoint.
        assert isinstance(result, str)

    def test_resource_with_whitespace_is_stripped(self):
        """Resource string with surrounding whitespace is stripped before insertion."""
        result = format_api_endpoint("https://api.example.com", 1, "  users  ")
        assert result == "https://api.example.com/v1/users"

    def test_resource_with_only_slashes_results_in_empty_segment(self):
        """Resource consisting only of slashes strips down to empty and omits resource segment."""
        result = format_api_endpoint("https://api.example.com", 1, "///")
        assert result == "https://api.example.com/v1"
