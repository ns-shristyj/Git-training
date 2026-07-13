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
    def test_valid_minimal_input_returns_expected_shape(self):
        """A minimal valid dict with only an id produces normalized output with active False."""
        result = process_user_data({"id": "  UserABC  "})
        assert result == {"user_id": "userabc", "active": False, "email": None}

    def test_status_active_sets_active_true(self):
        """Status field equal to 'active' flips the active flag to True."""
        result = process_user_data({"id": "u1", "status": "active"})
        assert result["active"] is True

    def test_status_other_value_sets_active_false(self):
        """Any status other than the literal string 'active' results in active False."""
        result = process_user_data({"id": "u1", "status": "inactive"})
        assert result["active"] is False

    def test_valid_email_is_preserved(self):
        """A syntactically valid email passes validation and is returned unchanged."""
        result = process_user_data({"id": "u1", "email": "test@example.com"})
        assert result["email"] == "test@example.com"

    def test_non_dict_input_raises_type_error(self):
        """Passing a non-dict object must raise TypeError rather than crash unexpectedly."""
        with pytest.raises(TypeError):
            process_user_data(["id", "email"])

    def test_none_input_raises_type_error(self):
        """Passing None must raise TypeError instead of an AttributeError deep in the function."""
        with pytest.raises(TypeError):
            process_user_data(None)

    def test_missing_id_raises_value_error(self):
        """A dict without an 'id' key must raise ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"email": "a@b.com"})

    def test_empty_string_id_raises_value_error(self):
        """An empty string id is falsy and must raise ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": ""})

    def test_non_string_id_raises_value_error(self):
        """A numeric id (non-string type) must raise ValueError, guarding against type confusion."""
        with pytest.raises(ValueError):
            process_user_data({"id": 12345})

    def test_invalid_email_format_raises_value_error(self):
        """An email without an '@' or domain segment must raise ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "u1", "email": "not-an-email"})

    def test_email_missing_domain_dot_raises_value_error(self):
        """An email lacking a dot in the domain part must raise ValueError."""
        with pytest.raises(ValueError):
            process_user_data({"id": "u1", "email": "user@domaincom"})

    def test_email_with_embedded_newline_is_rejected(self):
        """An email containing a newline (possible header-injection payload) must be rejected, not partially matched."""
        malicious_email = "victim@example.com\nBCC: attacker@evil.com"
        with pytest.raises(ValueError):
            process_user_data({"id": "u1", "email": malicious_email})

    def test_id_with_script_payload_is_only_normalized_not_executed(self):
        """A script-injection style id string is safely treated as inert text (stripped/lowered), no execution occurs."""
        payload = "  <script>alert(1)</script>  "
        result = process_user_data({"id": payload})
        assert result["user_id"] == payload.strip().lower()
        assert "<script>" in result["user_id"]  # confirms it is stored as data, not executed

    def test_falsy_email_none_is_accepted_without_validation(self):
        """A None email should not trigger regex validation and should pass through as None."""
        result = process_user_data({"id": "u1", "email": None})
        assert result["email"] is None


# ---------------------------------------------------------------------------
# calculate_risk_score
# ---------------------------------------------------------------------------

class TestCalculateRiskScore:
    def test_empty_list_returns_zero(self):
        """An empty metrics list returns 0.0 without error."""
        assert calculate_risk_score([]) == 0.0

    def test_valid_scores_returns_average(self):
        """A list of valid numeric scores returns their arithmetic mean."""
        result = calculate_risk_score([10, 20, 30])
        assert result == pytest.approx(20.0)

    def test_boundary_scores_zero_and_hundred_are_accepted(self):
        """Boundary values 0 and 100 are within the allowed inclusive range."""
        result = calculate_risk_score([0, 100])
        assert result == pytest.approx(50.0)

    def test_non_list_input_raises_type_error(self):
        """Passing a non-list (e.g. a dict) must raise TypeError."""
        with pytest.raises(TypeError):
            calculate_risk_score({"score": 10})

    def test_non_numeric_score_raises_value_error(self):
        """A non-numeric entry in the metrics list must raise ValueError."""
        with pytest.raises(ValueError):
            calculate_risk_score([10, "50", 30])

    def test_score_below_zero_raises_value_error(self):
        """A negative score must raise ValueError due to boundary violation."""
        with pytest.raises(ValueError):
            calculate_risk_score([-1, 50])

    def test_score_above_hundred_raises_value_error(self):
        """A score above 100 must raise ValueError due to boundary violation."""
        with pytest.raises(ValueError):
            calculate_risk_score([50, 101])

    def test_nan_score_is_rejected_or_safely_handled(self):
        """A NaN float bypasses naive range checks; result must not silently be NaN in output."""
        result = calculate_risk_score([50.0, float("nan")])
        # A NaN in the input must not be allowed to corrupt the aggregate result silently.
        assert result == result, "Result is NaN: unsanitized NaN input corrupted the risk score computation."

    def test_boolean_values_are_treated_as_numeric_due_to_int_subclass(self):
        """Booleans (subclass of int) are accepted as valid scores, documenting a type-confusion edge case."""
        result = calculate_risk_score([True, False])
        assert result == pytest.approx(0.5)

    def test_single_element_list_returns_that_value(self):
        """A single-element list returns that element's value as the average."""
        assert calculate_risk_score([42]) == pytest.approx(42.0)


# ---------------------------------------------------------------------------
# format_api_endpoint
# ---------------------------------------------------------------------------

class TestFormatApiEndpoint:
    def test_basic_valid_construction(self):
        """A standard base_url, version, and resource are joined into the expected endpoint string."""
        result = format_api_endpoint("https://api.example.com", 2, "users")
        assert result == "https://api.example.com/v2/users"

    def test_trailing_slash_on_base_is_stripped(self):
        """Trailing slashes on base_url are removed before constructing the endpoint."""
        result = format_api_endpoint("https://api.example.com/", 1, "items")
        assert result == "https://api.example.com/v1/items"

    def test_leading_slash_on_resource_is_stripped(self):
        """Leading slashes on resource are removed before constructing the endpoint."""
        result = format_api_endpoint("https://api.example.com", 1, "/items")
        assert result == "https://api.example.com/v1/items"

    def test_empty_resource_returns_version_only_endpoint(self):
        """An empty resource string returns just the base and version segment."""
        result = format_api_endpoint("https://api.example.com", 3, "")
        assert result == "https://api.example.com/v3"

    def test_none_resource_returns_version_only_endpoint(self):
        """A None resource is treated the same as empty and returns version-only endpoint."""
        result = format_api_endpoint("https://api.example.com", 3, None)
        assert result == "https://api.example.com/v3"

    def test_empty_base_url_raises_value_error(self):
        """An empty base_url must raise ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("", 1, "res")

    def test_non_string_base_url_raises_value_error(self):
        """A non-string base_url (e.g. int) must raise ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint(12345, 1, "res")

    def test_zero_version_raises_value_error(self):
        """A version of zero is not a valid positive integer and must raise ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 0, "res")

    def test_negative_version_raises_value_error(self):
        """A negative version must raise ValueError."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", -1, "res")

    def test_non_integer_version_raises_value_error(self):
        """A float version must raise ValueError, since strict int type is required."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 1.5, "res")

    def test_path_traversal_in_resource_is_not_left_unsanitized(self):
        """A path-traversal payload in resource must be rejected or sanitized, not embedded verbatim into the endpoint."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 1, "../../etc/passwd")

    def test_resource_with_query_or_fragment_injection_is_rejected(self):
        """A resource containing raw query/fragment injection characters must be rejected, not concatenated blindly."""
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 1, "users?admin=true#override")
