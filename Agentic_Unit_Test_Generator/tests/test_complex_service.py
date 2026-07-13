import pytest
from NIC_SecEng_Task.complex_service import (
    process_user_data,
    calculate_risk_score,
    format_api_endpoint,
)


# ---------- process_user_data ----------

def test_process_user_data_happy_path():
    result = process_user_data({"id": " User1 ", "email": "user@example.com", "status": "active"})
    assert result == {"user_id": "user1", "active": True, "email": "user@example.com"}


def test_process_user_data_type_confusion_not_dict():
    with pytest.raises(TypeError, match="Input must be a dictionary configuration layout."):
        process_user_data("not_a_dict")


def test_process_user_data_missing_id_raises_value_error():
    with pytest.raises(ValueError, match="Missing or invalid 'id' parameter profile."):
        process_user_data({"email": "user@example.com"})


def test_process_user_data_id_wrong_type_raises_value_error():
    with pytest.raises(ValueError, match="Missing or invalid 'id' parameter profile."):
        process_user_data({"id": 12345})


def test_process_user_data_invalid_email_format_raises_value_error():
    with pytest.raises(ValueError, match="Provided email address profile violates formatting rules."):
        process_user_data({"id": "user1", "email": "not-an-email"})


def test_process_user_data_malicious_email_sql_injection_rejected():
    with pytest.raises(ValueError, match="Provided email address profile violates formatting rules."):
        process_user_data({"id": "user1", "email": "' OR 1=1--"})


def test_process_user_data_no_email_returns_none():
    result = process_user_data({"id": "user1"})
    assert result["email"] is None


# ---------- calculate_risk_score ----------

def test_calculate_risk_score_happy_path():
    assert calculate_risk_score([10, 20, 30]) == 20.0


def test_calculate_risk_score_type_confusion_not_list():
    with pytest.raises(TypeError, match="Metrics parameter tracking stream must be a sequential list layout."):
        calculate_risk_score("not_a_list")


def test_calculate_risk_score_empty_list_returns_zero():
    assert calculate_risk_score([]) == 0.0


def test_calculate_risk_score_boundary_values_allowed():
    assert calculate_risk_score([0, 100]) == 50.0


def test_calculate_risk_score_out_of_boundary_raises_value_error():
    with pytest.raises(ValueError, match="Evaluation metrics boundaries must fall squarely within 0 to 100."):
        calculate_risk_score([101])


def test_calculate_risk_score_negative_value_raises_value_error():
    with pytest.raises(ValueError, match="Evaluation metrics boundaries must fall squarely within 0 to 100."):
        calculate_risk_score([-1])


def test_calculate_risk_score_non_numeric_element_raises_value_error():
    with pytest.raises(ValueError, match="Encountered non-numeric evaluation matrix parameter."):
        calculate_risk_score([10, "50", 30])


def test_calculate_risk_score_bool_treated_as_numeric():
    # bool is a subclass of int in Python, so isinstance check passes
    assert calculate_risk_score([True, False]) == 0.5


# ---------- format_api_endpoint ----------

def test_format_api_endpoint_happy_path():
    result = format_api_endpoint("https://example.com", 1, "users")
    assert result == "https://example.com/v1/users"


def test_format_api_endpoint_empty_base_url_raises_value_error():
    with pytest.raises(ValueError, match="Base target network string path cannot be empty layout."):
        format_api_endpoint("", 1, "users")


def test_format_api_endpoint_base_url_wrong_type_raises_value_error():
    with pytest.raises(ValueError, match="Base target network string path cannot be empty layout."):
        format_api_endpoint(12345, 1, "users")


def test_format_api_endpoint_version_zero_raises_value_error():
    with pytest.raises(ValueError, match="Target API deployment release engine matrix must be a valid positive integer."):
        format_api_endpoint("https://example.com", 0, "users")


def test_format_api_endpoint_version_negative_raises_value_error():
    with pytest.raises(ValueError, match="Target API deployment release engine matrix must be a valid positive integer."):
        format_api_endpoint("https://example.com", -1, "users")


def test_format_api_endpoint_version_wrong_type_raises_value_error():
    with pytest.raises(ValueError, match="Target API deployment release engine matrix must be a valid positive integer."):
        format_api_endpoint("https://example.com", "1", "users")


def test_format_api_endpoint_no_resource_returns_base_with_version_only():
    result = format_api_endpoint("https://example.com/", 2, "")
    assert result == "https://example.com/v2"


def test_format_api_endpoint_path_traversal_resource_is_preserved_literally():
    result = format_api_endpoint("https://example.com", 1, "../../../etc/passwd")
    assert result == "https://example.com/v1/../../../etc/passwd"


def test_format_api_endpoint_oversized_resource_input():
    huge_resource = "a" * 10000
    result = format_api_endpoint("https://example.com", 1, huge_resource)
    assert result == f"https://example.com/v1/{huge_resource}"
