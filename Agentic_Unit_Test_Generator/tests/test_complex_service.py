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
        """Valid dict with only id returns normalized user_id, inactive status, and no email."""
        result = process_user_data({"id": "  User123  "})
        assert result == {"user_id": "user123", "active": False, "email": None}

    def test_valid_full_input_with_active_status(self):
        """Valid dict with id, email, and active status returns correctly normalized fields."""
        result = process_user_data({"id": "Bob", "email": "bob@example.com", "status": "active"})
        assert result == {"user_id": "bob", "active": True, "email": "bob@example.com"}

    def test_non_dict_input_raises_type_error(self):
        """Non-dict input raises TypeError instead of crashing further downstream."""
        with pytest.raises(TypeError):
            process_user_data(["not", "a", "dict"])

    def test_none_input_raises_type_error(self):
        """None input is rejected with a TypeError."""
        with pytest.raises(TypeError):
            process_user_data(None)

    def test_missing_id_raises_value_error(self):
        """Missing 'id' key raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"email": "a@b.com"})

    def test_empty_string_id_raises_value_error(self):
        """Empty string id is falsy and raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": ""})

    def test_non_string_id_raises_value_error(self):
        """Non-string id (integer) raises ValueError due to type check."""
        with pytest.raises(ValueError):
            process_user_data({"id": 12345})

    def test_none_id_raises_value_error(self):
        """None as id value is rejected."""
        with pytest.raises(ValueError):
            process_user_data({"id": None})

    def test_boolean_id_raises_value_error(self):
        """Boolean id (not a str instance) raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": True})

    def test_invalid_email_format_raises_value_error(self):
        """Malformed email without '@' and domain raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "u1", "email": "not-an-email"})

    def test_email_missing_domain_dot_raises_value_error(self):
        """Email missing a dot in the domain part fails validation."""
        with pytest.raises(ValueError):
            process_user_data({"id": "u1", "email": "user@domain"})

    def test_email_none_is_allowed(self):
        """Explicit None email is treated as falsy and skips validation."""
        result = process_user_data({"id": "u1", "email": None})
        assert result["email"] is None

    def test_email_with_script_injection_string_rejected_or_handled(self):
        """Email containing script injection payload without valid format is rejected."""
        payload = "<script>alert(1)</script>@evil.com"
        # This actually matches the loose regex (has @ and a dot), so it should pass through
        # as a raw string without executing anything - confirming no code execution occurs.
        result = process_user_data({"id": "u1", "email": payload})
        assert result["email"] == payload

    def test_status_not_active_string_results_in_false(self):
        """Any status value other than the literal string 'active' results in active=False."""
        result = process_user_data({"id": "u1", "status": "ACTIVE"})
        assert result["active"] is False

    def test_id_with_path_traversal_characters_preserved_safely(self):
        """Path traversal-like id string is only lowercased/stripped, not executed or expanded."""
        result = process_user_data({"id": "../../etc/passwd"})
        assert result["user_id"] == "../../etc/passwd"

    def test_id_with_sql_injection_string_preserved_safely(self):
        """SQL injection-like id string is treated as plain text, not executed."""
        malicious_id = "'; DROP TABLE users; --"
        result = process_user_data({"id": malicious_id})
        assert result["user_id"] == malicious_id.lower()


# ---------------------------
# calculate_risk_score tests
# ---------------------------

class TestCalculateRiskScore:

    def test_empty_list_returns_zero(self):
        """Empty metrics list returns 0.0 without error."""
        assert calculate_risk_score([]) == 0.0

    def test_valid_scores_average(self):
        """Average of valid numeric scores within range is computed correctly."""
        assert calculate_risk_score([10, 20, 30]) == 20.0

    def test_single_score(self):
        """Single valid score returns itself as the average."""
        assert calculate_risk_score([55]) == 55.0

    def test_boundary_zero_and_hundred_are_valid(self):
        """Boundary values 0 and 100 are inclusive and valid."""
        result = calculate_risk_score([0, 100])
        assert result == 50.0

    def test_non_list_input_raises_type_error(self):
        """Non-list input (dict) raises TypeError."""
        with pytest.raises(TypeError):
            calculate_risk_score({"a": 1})

    def test_string_input_raises_type_error(self):
        """String input, though iterable, is rejected as not a list."""
        with pytest.raises(TypeError):
            calculate_risk_score("12345")

    def test_non_numeric_element_raises_value_error(self):
        """A non-numeric element (string) in the list raises ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([10, "bad", 30])

    def test_negative_score_raises_value_error(self):
        """A negative score raises ValueError due to boundary violation."""
        with pytest.raises(ValueError):
            calculate_risk_score([-1, 50])

    def test_score_above_hundred_raises_value_error(self):
        """A score above 100 raises ValueError due to boundary violation."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, 101])

    def test_none_element_raises_value_error(self):
        """A None element in the metrics list is rejected as non-numeric."""
        with pytest.raises(ValueError):
            calculate_risk_score([10, None])

    def test_boolean_elements_are_treated_as_numeric(self):
        """Booleans are instances of int in Python, so they pass numeric validation."""
        result = calculate_risk_score([True, False])
        assert result == 0.5

    def test_float_scores_are_valid(self):
        """Floating point scores within range are averaged correctly."""
        result = calculate_risk_score([12.5, 87.5])
        assert result == 50.0


# ---------------------------
# format_api_endpoint tests
# ---------------------------

class TestFormatApiEndpoint:

    def test_basic_endpoint_construction(self):
        """Base URL, version, and resource are combined into a well-formed endpoint."""
        result = format_api_endpoint("https://api.example.com", 1, "users")
        assert result == "https://api.example.com/v1/users"

    def test_trailing_slash_on_base_is_stripped(self):
        """Trailing slash(es) on base_url are removed before constructing the endpoint."""
        result = format_api_endpoint("https://api.example.com/", 2, "items")
        assert result == "https://api.example.com/v2/items"

    def test_leading_slash_on_resource_is_stripped(self):
        """Leading slash on resource path is stripped to avoid double slashes."""
        result = format_api_endpoint("https://api.example.com", 1, "/orders")
        assert result == "https://api.example.com/v1/orders"

    def test_empty_resource_returns_base_and_version_only(self):
        """Empty resource string results in endpoint without trailing resource segment."""
        result = format_api_endpoint("https://api.example.com", 3, "")
        assert result == "https://api.example.com/v3"

    def test_none_resource_returns_base_and_version_only(self):
        """None resource is handled gracefully, returning only base and version."""
        result = format_api_endpoint("https://api.example.com", 3, None)
        assert result == "https://api.example.com/v3"

    def test_empty_base_url_raises_value_error(self):
        """Empty base_url string raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("", 1, "users")

    def test_none_base_url_raises_value_error(self):
        """None base_url raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint(None, 1, "users")

    def test_non_string_base_url_raises_value_error(self):
        """Non-string base_url (integer) raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint(12345, 1, "users")

    def test_zero_version_raises_value_error(self):
        """Version of zero is invalid and raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 0, "users")

    def test_negative_version_raises_value_error(self):
        """Negative version number raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", -1, "users")

    def test_non_integer_version_raises_value_error(self):
        """Non-integer version (string) raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", "1", "users")

    def test_float_version_raises_value_error(self):
        """Float version, not strictly int, raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 1.5, "users")

    def test_resource_with_path_traversal_is_preserved_as_literal_text(self):
        """Path traversal payload in resource is only stripped, not sanitized or blocked, confirming raw text output for callers to handle."""
        result = format_api_endpoint("https://api.example.com", 1, "../../etc/passwd")
        assert result == "https://api.example.com/v1/../../etc/passwd"

    def test_resource_with_whitespace_is_stripped(self):
        """Resource string with surrounding whitespace is trimmed before use."""
        result = format_api_endpoint("https://api.example.com", 1, "  users  ")
        assert result == "https://api.example.com/v1/users"

    def test_multiple_trailing_slashes_on_base_are_all_stripped(self):
        """Multiple trailing slashes on base_url are fully stripped by rstrip."""
        result = format_api_endpoint("https://api.example.com///", 1, "users")
        assert result == "https://api.example.com/v1/users"
