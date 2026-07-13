import pytest
from NIC_SecEng_Task.complex_service import (
    process_user_data,
    calculate_risk_score,
    format_api_endpoint,
)


# ---------------------------
# process_user_data
# ---------------------------

class TestProcessUserData:
    def test_non_dict_input_raises_type_error(self):
        """Non-dict input must raise TypeError to prevent type confusion attacks."""
        with pytest.raises(TypeError):
            process_user_data(["id", "value"])

    def test_none_input_raises_type_error(self):
        """None input must raise TypeError rather than crash with AttributeError."""
        with pytest.raises(TypeError):
            process_user_data(None)

    def test_missing_id_raises_value_error(self):
        """Missing 'id' key must raise ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"email": "a@b.com"})

    def test_empty_id_raises_value_error(self):
        """Empty string id (falsy) must raise ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": ""})

    def test_non_string_id_raises_value_error(self):
        """Non-string id (type confusion, e.g. int) must raise ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": 12345})

    def test_id_as_list_raises_value_error(self):
        """List type id must be rejected as invalid profile parameter."""
        with pytest.raises(ValueError):
            process_user_data({"id": ["admin"]})

    def test_valid_minimal_input(self):
        """Valid minimal input with only id returns normalized structure with no email."""
        result = process_user_data({"id": "  UserOne  "})
        assert result == {"user_id": "userone", "active": False, "email": None}

    def test_valid_input_with_active_status(self):
        """Status 'active' correctly maps to active True flag."""
        result = process_user_data({"id": "abc", "status": "active"})
        assert result["active"] is True

    def test_status_other_value_is_inactive(self):
        """Any status value other than 'active' results in active False."""
        result = process_user_data({"id": "abc", "status": "pending"})
        assert result["active"] is False

    def test_valid_email_accepted(self):
        """Properly formatted email passes validation and is returned unchanged."""
        result = process_user_data({"id": "abc", "email": "user@example.com"})
        assert result["email"] == "user@example.com"

    def test_invalid_email_missing_at_raises_value_error(self):
        """Email missing '@' symbol must raise ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "abc", "email": "userexample.com"})

    def test_invalid_email_missing_dot_raises_value_error(self):
        """Email missing domain dot must raise ValueError (blocks malformed injection payloads lacking TLD)."""
        with pytest.raises(ValueError):
            process_user_data({"id": "abc", "email": "attacker@evilserver"})

    def test_empty_email_string_is_treated_as_falsy_and_skipped(self):
        """Empty string email is falsy, so validation is skipped and email stays empty string."""
        result = process_user_data({"id": "abc", "email": ""})
        assert result["email"] == ""

    def test_id_with_special_characters_processed_without_execution(self):
        """Id containing SQL-injection-like payload is treated as inert data string and merely normalized."""
        payload = "'; DROP TABLE users; --"
        result = process_user_data({"id": payload})
        assert result["user_id"] == payload.strip().lower()


# ---------------------------
# calculate_risk_score
# ---------------------------

class TestCalculateRiskScore:
    def test_non_list_input_raises_type_error(self):
        """Non-list input must raise TypeError."""
        with pytest.raises(TypeError):
            calculate_risk_score("50,60,70")

    def test_dict_input_raises_type_error(self):
        """Dict input (iterable but not list) must raise TypeError."""
        with pytest.raises(TypeError):
            calculate_risk_score({"a": 50})

    def test_empty_list_returns_zero(self):
        """Empty metrics list returns 0.0 rather than raising a division error."""
        assert calculate_risk_score([]) == 0.0

    def test_valid_scores_average_correctly(self):
        """Valid numeric scores compute correct arithmetic mean."""
        result = calculate_risk_score([10, 20, 30])
        assert result == 20.0

    def test_boundary_scores_zero_and_hundred_are_valid(self):
        """Boundary values 0 and 100 are inclusive and must not raise."""
        result = calculate_risk_score([0, 100])
        assert result == 50.0

    def test_score_below_zero_raises_value_error(self):
        """Negative score below allowed boundary must raise ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([-1, 50])

    def test_score_above_hundred_raises_value_error(self):
        """Score exceeding 100 must raise ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([101, 50])

    def test_non_numeric_score_raises_value_error(self):
        """Non-numeric element (string) in metrics list must raise ValueError, not silently coerce."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, "60"])

    def test_none_element_raises_value_error(self):
        """None element in metrics list must raise ValueError instead of crashing on comparison."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, None])

    def test_list_with_nested_list_raises_value_error(self):
        """Nested list element (type confusion) must raise ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, [60]])

    def test_boolean_values_are_treated_as_numeric_due_to_int_subclass(self):
        """Booleans (subclass of int) pass isinstance check and are averaged as 0/1 numeric values."""
        result = calculate_risk_score([True, False])
        assert result == 0.5

    def test_float_scores_supported(self):
        """Floating point scores are valid and computed correctly."""
        result = calculate_risk_score([25.5, 74.5])
        assert result == 50.0


# ---------------------------
# format_api_endpoint
# ---------------------------

class TestFormatApiEndpoint:
    def test_empty_base_url_raises_value_error(self):
        """Empty base_url must raise ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("", 1, "users")

    def test_non_string_base_url_raises_value_error(self):
        """Non-string base_url (type confusion) must raise ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint(12345, 1, "users")

    def test_none_base_url_raises_value_error(self):
        """None base_url must raise ValueError rather than crash on string operations."""
        with pytest.raises(ValueError):
            format_api_endpoint(None, 1, "users")

    def test_zero_version_raises_value_error(self):
        """Version of zero (non-positive) must raise ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("http://api.test", 0, "users")

    def test_negative_version_raises_value_error(self):
        """Negative version must raise ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("http://api.test", -5, "users")

    def test_non_int_version_raises_value_error(self):
        """Non-integer version (e.g. float or string) must raise ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("http://api.test", 1.5, "users")

    def test_boolean_version_is_treated_as_int_subclass(self):
        """Boolean True (int subclass, value 1) is accepted as a valid positive version."""
        result = format_api_endpoint("http://api.test", True, "users")
        assert result == "http://api.test/v1/users"

    def test_basic_endpoint_with_resource(self):
        """Base url, version, and resource combine into correctly formatted endpoint."""
        result = format_api_endpoint("http://api.test", 2, "users")
        assert result == "http://api.test/v2/users"

    def test_trailing_slash_on_base_url_is_stripped(self):
        """Trailing slash on base_url is stripped to avoid double slashes."""
        result = format_api_endpoint("http://api.test/", 1, "users")
        assert result == "http://api.test/v1/users"

    def test_leading_slash_on_resource_is_stripped(self):
        """Leading slash on resource is stripped to avoid double slashes in path."""
        result = format_api_endpoint("http://api.test", 1, "/users")
        assert result == "http://api.test/v1/users"

    def test_empty_resource_returns_version_only_endpoint(self):
        """Empty resource string results in endpoint without trailing resource path."""
        result = format_api_endpoint("http://api.test", 1, "")
        assert result == "http://api.test/v1"

    def test_none_resource_returns_version_only_endpoint(self):
        """None resource is handled gracefully and results in version-only endpoint."""
        result = format_api_endpoint("http://api.test", 1, None)
        assert result == "http://api.test/v1"

    def test_whitespace_only_resource_returns_version_only_endpoint(self):
        """Whitespace-only resource strips to empty and yields version-only endpoint."""
        result = format_api_endpoint("http://api.test", 1, "   ")
        assert result == "http://api.test/v1"
