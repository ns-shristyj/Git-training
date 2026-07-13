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
    def test_valid_minimal_input(self):
        result = process_user_data({"id": "User123"})
        assert result == {"user_id": "user123", "active": False, "email": None}

    def test_valid_with_active_status(self):
        result = process_user_data({"id": "abc", "status": "active"})
        assert result["active"] is True

    def test_valid_with_valid_email(self):
        result = process_user_data({"id": "abc", "email": "test@example.com"})
        assert result["email"] == "test@example.com"

    def test_id_is_stripped_and_lowercased(self):
        result = process_user_data({"id": "  MixedCase  "})
        assert result["user_id"] == "mixedcase"

    def test_non_dict_input_raises_typeerror(self):
        with pytest.raises(TypeError):
            process_user_data(["id", "abc"])

    def test_none_input_raises_typeerror(self):
        with pytest.raises(TypeError):
            process_user_data(None)

    def test_missing_id_raises_valueerror(self):
        with pytest.raises(ValueError):
            process_user_data({"email": "test@example.com"})

    def test_empty_string_id_raises_valueerror(self):
        with pytest.raises(ValueError):
            process_user_data({"id": ""})

    def test_non_string_id_raises_valueerror(self):
        with pytest.raises(ValueError):
            process_user_data({"id": 12345})

    def test_none_id_raises_valueerror(self):
        with pytest.raises(ValueError):
            process_user_data({"id": None})

    def test_invalid_email_format_raises_valueerror(self):
        with pytest.raises(ValueError):
            process_user_data({"id": "abc", "email": "not-an-email"})

    def test_invalid_email_missing_domain_dot(self):
        with pytest.raises(ValueError):
            process_user_data({"id": "abc", "email": "user@domain"})

    def test_status_not_active_results_in_false(self):
        result = process_user_data({"id": "abc", "status": "inactive"})
        assert result["active"] is False

    def test_empty_email_treated_as_falsy_skips_validation(self):
        result = process_user_data({"id": "abc", "email": ""})
        assert result["email"] == ""

    def test_id_with_bool_type_raises_valueerror(self):
        # bool is subclass of int, not str -> should raise
        with pytest.raises(ValueError):
            process_user_data({"id": True})

    def test_email_with_multiple_at_signs_still_matches_partial(self):
        # regex is not anchored; verify behavior with unusual email
        result = process_user_data({"id": "abc", "email": "a@b@c.com"})
        assert result["email"] == "a@b@c.com"

    def test_extra_keys_are_ignored(self):
        result = process_user_data({"id": "abc", "extra": "ignored_field"})
        assert "extra" not in result


# ---------------------------
# calculate_risk_score
# ---------------------------

class TestCalculateRiskScore:
    def test_empty_list_returns_zero(self):
        assert calculate_risk_score([]) == 0.0

    def test_single_score(self):
        assert calculate_risk_score([50]) == 50.0

    def test_average_of_multiple_scores(self):
        assert calculate_risk_score([0, 100]) == 50.0

    def test_float_scores(self):
        result = calculate_risk_score([10.5, 20.5])
        assert result == 15.5

    def test_boundary_zero_is_valid(self):
        assert calculate_risk_score([0]) == 0.0

    def test_boundary_hundred_is_valid(self):
        assert calculate_risk_score([100]) == 100.0

    def test_non_list_input_raises_typeerror(self):
        with pytest.raises(TypeError):
            calculate_risk_score("not a list")

    def test_none_input_raises_typeerror(self):
        with pytest.raises(TypeError):
            calculate_risk_score(None)

    def test_dict_input_raises_typeerror(self):
        with pytest.raises(TypeError):
            calculate_risk_score({"score": 50})

    def test_non_numeric_element_raises_valueerror(self):
        with pytest.raises(ValueError):
            calculate_risk_score([10, "bad", 30])

    def test_none_element_raises_valueerror(self):
        with pytest.raises(ValueError):
            calculate_risk_score([10, None])

    def test_negative_score_raises_valueerror(self):
        with pytest.raises(ValueError):
            calculate_risk_score([-1, 50])

    def test_score_above_hundred_raises_valueerror(self):
        with pytest.raises(ValueError):
            calculate_risk_score([50, 101])

    def test_bool_elements_are_accepted_as_numeric(self):
        # bool is subclass of int -> allowed since isinstance check passes
        result = calculate_risk_score([True, False])
        assert result == 0.5

    def test_mixed_int_and_float(self):
        result = calculate_risk_score([10, 20.0, 30])
        assert result == 20.0

    def test_nested_list_raises_valueerror(self):
        with pytest.raises(ValueError):
            calculate_risk_score([10, [20]])


# ---------------------------
# format_api_endpoint
# ---------------------------

class TestFormatApiEndpoint:
    def test_basic_endpoint_construction(self):
        result = format_api_endpoint("https://api.example.com", 1, "users")
        assert result == "https://api.example.com/v1/users"

    def test_base_url_trailing_slash_stripped(self):
        result = format_api_endpoint("https://api.example.com/", 2, "orders")
        assert result == "https://api.example.com/v2/orders"

    def test_resource_leading_slash_stripped(self):
        result = format_api_endpoint("https://api.example.com", 1, "/users")
        assert result == "https://api.example.com/v1/users"

    def test_resource_whitespace_stripped(self):
        result = format_api_endpoint("https://api.example.com", 1, "  users  ")
        assert result == "https://api.example.com/v1/users"

    def test_no_resource_returns_version_only(self):
        result = format_api_endpoint("https://api.example.com", 3, "")
        assert result == "https://api.example.com/v3"

    def test_none_resource_returns_version_only(self):
        result = format_api_endpoint("https://api.example.com", 3, None)
        assert result == "https://api.example.com/v3"

    def test_empty_base_url_raises_valueerror(self):
        with pytest.raises(ValueError):
            format_api_endpoint("", 1, "users")

    def test_none_base_url_raises_valueerror(self):
        with pytest.raises(ValueError):
            format_api_endpoint(None, 1, "users")

    def test_non_string_base_url_raises_valueerror(self):
        with pytest.raises(ValueError):
            format_api_endpoint(12345, 1, "users")

    def test_zero_version_raises_valueerror(self):
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 0, "users")

    def test_negative_version_raises_valueerror(self):
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", -5, "users")

    def test_non_int_version_raises_valueerror(self):
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", "1", "users")

    def test_float_version_raises_valueerror(self):
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 1.5, "users")

    def test_multiple_trailing_slashes_in_base_url(self):
        result = format_api_endpoint("https://api.example.com///", 1, "users")
        assert result == "https://api.example.com/v1/users"

    def test_resource_with_path_traversal_is_preserved(self):
        # Function does not sanitize path traversal sequences
        result = format_api_endpoint("https://api.example.com", 1, "../../etc/passwd")
        assert result == "https://api.example.com/v1/../../etc/passwd"

    def test_resource_with_only_slashes_returns_version_only(self):
        result = format_api_endpoint("https://api.example.com", 1, "///")
        assert result == "https://api.example.com/v1"

    def test_bool_version_true_treated_as_valid_int(self):
        # bool is subclass of int, True == 1 and > 0
        result = format_api_endpoint("https://api.example.com", True, "users")
        assert result == "https://api.example.com/vTrue/users"
