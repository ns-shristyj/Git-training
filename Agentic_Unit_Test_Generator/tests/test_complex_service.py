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

    def test_valid_full_profile(self):
        result = process_user_data(
            {"id": "  UserOne  ", "email": "user@example.com", "status": "active"}
        )
        assert result == {
            "user_id": "userone",
            "active": True,
            "email": "user@example.com",
        }

    def test_valid_without_email(self):
        result = process_user_data({"id": "abc", "status": "active"})
        assert result["email"] is None
        assert result["active"] is True

    def test_status_not_active(self):
        result = process_user_data({"id": "abc", "status": "inactive"})
        assert result["active"] is False

    def test_missing_status_defaults_inactive(self):
        result = process_user_data({"id": "abc"})
        assert result["active"] is False

    def test_non_dict_input_raises_type_error(self):
        with pytest.raises(TypeError):
            process_user_data(["id", "email"])

    def test_none_input_raises_type_error(self):
        with pytest.raises(TypeError):
            process_user_data(None)

    def test_missing_id_raises_value_error(self):
        with pytest.raises(ValueError):
            process_user_data({"email": "user@example.com"})

    def test_empty_id_raises_value_error(self):
        with pytest.raises(ValueError):
            process_user_data({"id": ""})

    def test_non_string_id_raises_value_error(self):
        with pytest.raises(ValueError):
            process_user_data({"id": 12345})

    def test_id_as_none_raises_value_error(self):
        with pytest.raises(ValueError):
            process_user_data({"id": None})

    @pytest.mark.parametrize(
        "bad_email",
        [
            "not-an-email",
            "missing-at.com",
            "@missing-local.com",
            "missing-domain@",
            "user@domain",  # no TLD dot
        ],
    )
    def test_invalid_email_formats_raise_value_error(self, bad_email):
        with pytest.raises(ValueError):
            process_user_data({"id": "abc", "email": bad_email})

    def test_id_is_normalized_case_and_whitespace(self):
        result = process_user_data({"id": " MixedCase "})
        assert result["user_id"] == "mixedcase"

    def test_email_none_is_allowed(self):
        result = process_user_data({"id": "abc", "email": None})
        assert result["email"] is None

    def test_sql_injection_like_id_is_not_executed_but_normalized(self):
        # Ensure the function only normalizes the string, does not evaluate it
        malicious_id = "abc'; DROP TABLE users;--"
        result = process_user_data({"id": malicious_id})
        assert result["user_id"] == malicious_id.strip().lower()
        assert isinstance(result["user_id"], str)


# ---------------------------------------------------------------------------
# calculate_risk_score
# ---------------------------------------------------------------------------

class TestCalculateRiskScore:

    def test_empty_list_returns_zero(self):
        assert calculate_risk_score([]) == 0.0

    def test_valid_scores_average(self):
        result = calculate_risk_score([10, 20, 30])
        assert result == pytest.approx(20.0)

    def test_valid_float_scores(self):
        result = calculate_risk_score([0.0, 100.0])
        assert result == pytest.approx(50.0)

    def test_boundary_values_are_accepted(self):
        result = calculate_risk_score([0, 100])
        assert result == pytest.approx(50.0)

    def test_non_list_input_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_risk_score("not a list")

    def test_dict_input_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_risk_score({"score": 50})

    def test_none_input_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_risk_score(None)

    def test_non_numeric_item_raises_value_error(self):
        with pytest.raises(ValueError):
            calculate_risk_score([10, "bad", 30])

    def test_none_item_raises_value_error(self):
        with pytest.raises(ValueError):
            calculate_risk_score([10, None])

    def test_negative_score_raises_value_error(self):
        with pytest.raises(ValueError):
            calculate_risk_score([-1, 50])

    def test_score_above_100_raises_value_error(self):
        with pytest.raises(ValueError):
            calculate_risk_score([50, 100.1])

    def test_single_score(self):
        assert calculate_risk_score([42]) == pytest.approx(42.0)

    def test_boolean_scores_are_treated_as_numeric(self):
        # isinstance(True, int) is True in Python; document actual behavior
        result = calculate_risk_score([True, False])
        assert result == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# format_api_endpoint
# ---------------------------------------------------------------------------

class TestFormatApiEndpoint:

    def test_basic_endpoint_with_resource(self):
        result = format_api_endpoint("https://api.example.com", 1, "users")
        assert result == "https://api.example.com/v1/users"

    def test_endpoint_without_resource(self):
        result = format_api_endpoint("https://api.example.com", 2, "")
        assert result == "https://api.example.com/v2"

    def test_endpoint_resource_none(self):
        result = format_api_endpoint("https://api.example.com", 2, None)
        assert result == "https://api.example.com/v2"

    def test_trailing_slash_base_url_is_stripped(self):
        result = format_api_endpoint("https://api.example.com/", 1, "users")
        assert result == "https://api.example.com/v1/users"

    def test_leading_slash_resource_is_stripped(self):
        result = format_api_endpoint("https://api.example.com", 1, "/users")
        assert result == "https://api.example.com/v1/users"

    def test_resource_with_surrounding_whitespace(self):
        result = format_api_endpoint("https://api.example.com", 1, "  users  ")
        assert result == "https://api.example.com/v1/users"

    def test_empty_base_url_raises_value_error(self):
        with pytest.raises(ValueError):
            format_api_endpoint("", 1, "users")

    def test_none_base_url_raises_value_error(self):
        with pytest.raises(ValueError):
            format_api_endpoint(None, 1, "users")

    def test_non_string_base_url_raises_value_error(self):
        with pytest.raises(ValueError):
            format_api_endpoint(12345, 1, "users")

    def test_zero_version_raises_value_error(self):
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 0, "users")

    def test_negative_version_raises_value_error(self):
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", -1, "users")

    def test_non_int_version_raises_value_error(self):
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", "1", "users")

    def test_float_version_raises_value_error(self):
        with pytest.raises(ValueError):
            format_api_endpoint("https://api.example.com", 1.5, "users")

    def test_path_traversal_resource_is_not_sanitized_out_of_scope(self):
        # The function should not allow directory traversal sequences to
        # propagate unmodified into the constructed endpoint. If this
        # assertion fails, the underlying implementation is vulnerable to
        # path traversal injection via the 'resource' parameter.
        malicious_resource = "../../etc/passwd"
        result = format_api_endpoint("https://api.example.com", 1, malicious_resource)
        assert ".." not in result, (
            "Path traversal sequence was not sanitized from the resource "
            "component of the generated API endpoint."
        )
