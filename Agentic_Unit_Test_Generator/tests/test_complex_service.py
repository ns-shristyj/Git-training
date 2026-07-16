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
        """Valid dict with only id returns normalized user_id, active False, email None."""
        result = process_user_data({"id": "  User123  "})
        assert result == {"user_id": "user123", "active": False, "email": None}

    def test_valid_full_input_active_status(self):
        """Valid dict with id, email, and active status returns correct normalized structure."""
        result = process_user_data({"id": "Alice", "email": "alice@example.com", "status": "active"})
        assert result == {"user_id": "alice", "active": True, "email": "alice@example.com"}

    def test_status_not_active_sets_active_false(self):
        """Non-'active' status values result in active=False."""
        result = process_user_data({"id": "bob", "status": "inactive"})
        assert result["active"] is False

    def test_non_dict_input_raises_typeerror(self):
        """Non-dict input raises TypeError instead of crashing."""
        with pytest.raises(TypeError):
            process_user_data(["id", "value"])

    def test_none_input_raises_typeerror(self):
        """None input raises TypeError safely."""
        with pytest.raises(TypeError):
            process_user_data(None)

    def test_missing_id_raises_valueerror(self):
        """Missing 'id' key raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"email": "a@b.com"})

    def test_empty_string_id_raises_valueerror(self):
        """Empty string id is falsy and raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": ""})

    def test_non_string_id_raises_valueerror(self):
        """Non-string id (e.g., int) raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": 12345})

    def test_invalid_email_format_raises_valueerror(self):
        """Malformed email address raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "user1", "email": "not-an-email"})

    def test_email_missing_at_symbol_raises_valueerror(self):
        """Email missing '@' raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "user1", "email": "userexample.com"})

    def test_email_missing_domain_dot_raises_valueerror(self):
        """Email missing dot in domain raises ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "user1", "email": "user@examplecom"})

    def test_email_none_is_allowed(self):
        """Absent/None email is allowed and passed through as None."""
        result = process_user_data({"id": "user1", "email": None})
        assert result["email"] is None

    def test_id_with_injection_payload_is_treated_as_plain_string(self):
        """SQL/script injection-like string in id is safely treated as a plain string, not executed."""
        payload = "'; DROP TABLE users; --"
        result = process_user_data({"id": payload})
        assert result["user_id"] == payload.strip().lower()

    def test_email_header_injection_pattern_rejected_or_passed_safely(self):
        """Email with header injection newline characters is rejected by pattern or passed through unmodified without execution."""
        payload = "test@example.com\nBcc:attacker@evil.com"
        # The regex allows this since it matches loosely; ensure it's returned as data, not executed.
        result = process_user_data({"id": "user1", "email": payload})
        assert result["email"] == payload

    def test_id_boolean_true_raises_valueerror(self):
        """Boolean True as id (not a string) raises ValueError due to isinstance check."""
        with pytest.raises(ValueError):
            process_user_data({"id": True})


# ---------------------------
# calculate_risk_score tests
# ---------------------------

class TestCalculateRiskScore:

    def test_empty_list_returns_zero(self):
        """Empty metrics list returns 0.0 without division by zero."""
        assert calculate_risk_score([]) == 0.0

    def test_valid_scores_average(self):
        """Valid numeric scores return correct average."""
        result = calculate_risk_score([10, 20, 30])
        assert result == 20.0

    def test_single_score(self):
        """Single valid score returns that score as float."""
        result = calculate_risk_score([50])
        assert result == 50.0

    def test_boundary_values_zero_and_hundred(self):
        """Boundary values 0 and 100 are accepted as valid inclusive bounds."""
        result = calculate_risk_score([0, 100])
        assert result == 50.0

    def test_float_scores_accepted(self):
        """Float type scores are valid and averaged correctly."""
        result = calculate_risk_score([25.5, 74.5])
        assert result == 50.0

    def test_non_list_input_raises_typeerror(self):
        """Non-list input (e.g., dict) raises TypeError."""
        with pytest.raises(TypeError):
            calculate_risk_score({"a": 1})

    def test_string_input_raises_typeerror(self):
        """String input raises TypeError instead of being iterated as chars."""
        with pytest.raises(TypeError):
            calculate_risk_score("12345")

    def test_negative_score_raises_valueerror(self):
        """Score below 0 raises ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([-1, 50])

    def test_score_above_100_raises_valueerror(self):
        """Score above 100 raises ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, 101])

    def test_non_numeric_score_raises_valueerror(self):
        """Non-numeric score (string) raises ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, "80"])

    def test_boolean_score_accepted_as_numeric(self):
        """Boolean is technically an int subclass; ensure it does not crash the function."""
        # bool is instance of int, so True(1)/False(0) pass isinstance check
        result = calculate_risk_score([True, False])
        assert result == 0.5

    def test_none_in_list_raises_valueerror(self):
        """None value in metrics list raises ValueError instead of crashing on comparison."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, None])

    def test_nested_list_raises_valueerror(self):
        """Nested list as a score element raises ValueError, not silently ignored."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, [1, 2]])


# ---------------------------
# format_api_endpoint tests
# ---------------------------

class TestFormatApiEndpoint:

    def test_basic_endpoint_construction(self):
        """Basic valid inputs produce correctly formatted URL with version and resource."""
        result = format_api_endpoint("https://api.example.com", 1, "users")
        assert result == "https://api.example.com/v1/users"

    def test_trailing_slash_base_url_is_stripped(self):
        """Trailing slash(es) in base_url are stripped before constructing endpoint."""
        result = format_api_endpoint("https://api.example.com/", 2, "orders")
        assert result == "https://api.example.com/v2/orders"

    def test_resource_with_leading_slash_is_stripped(self):
        """Leading slash in resource is stripped to avoid double slashes."""
        result = format_api_endpoint("https://api.example.com", 1, "/items")
        assert result == "https://api.example.com/v1/items"

    def test_no_resource_returns_base_and_version_only(self):
        """Empty resource string returns base URL with version only, no trailing slash artifact."""
        result = format_api_endpoint("https://api.example.com", 3, "")
        assert result == "https://api.example.com/v3"

    def test_none_resource_returns_base_and_version_only(self):
        """None resource is handled gracefully and returns version-only endpoint."""
        result = format_api_endpoint("https://api.example.com", 1, None)
        assert result == "https://api.example.com/v1"

    def test_empty_base_url_raises_valueerror(self):
        """Empty string base_url raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("", 1, "users")

    def test_none_base_url_raises_valueerror(self):
        """None base_url raises ValueError instead of crashing on rstrip."""
        with pytest.raises(ValueError):
            format_api_endpoint(None, 1, "users")

    def test_non_string_base_url_raises_valueerror(self):
        """Non-string base_url (e.g., int) raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint(12345, 1, "users")

    def test_zero_version_raises_valueerror(self):
        """Version of zero raises ValueError due to positive integer requirement."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 0, "users")

    def test_negative_version_raises_valueerror(self):
        """Negative version raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", -1, "users")

    def test_non_integer_version_raises_valueerror(self):
        """Non-integer version (string) raises ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", "1", "users")

    def test_float_version_raises_valueerror(self):
        """Float version is rejected as not a strict int instance."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 1.5, "users")

    def test_path_traversal_resource_not_sanitized_but_passed_as_literal_string(self):
        """Path traversal sequence in resource is preserved literally (no special filesystem interpretation) and does not raise."""
        result = format_api_endpoint("https://api.example.com", 1, "../../etc/passwd")
        # Ensure it's just treated as a literal string in the URL path, not executed or altered beyond strip
        assert result == "https://api.example.com/v1/../../etc/passwd"

    def test_resource_with_whitespace_is_stripped(self):
        """Whitespace around resource string is stripped before use."""
        result = format_api_endpoint("https://api.example.com", 1, "   items   ")
        assert result == "https://api.example.com/v1/items"

    def test_multiple_trailing_slashes_stripped_from_base(self):
        """Multiple trailing slashes in base_url are all stripped."""
        result = format_api_endpoint("https://api.example.com///", 1, "users")
        assert result == "https://api.example.com/v1/users"
