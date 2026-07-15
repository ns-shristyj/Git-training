import pytest
from NIC_SecEng_Task.complex_service import (
    process_user_data,
    calculate_risk_score,
    format_api_endpoint,
)


# ---------------------------------------------------------------------------
# process_user_data
# ---------------------------------------------------------------------------

def test_process_user_data_valid_minimal():
    """Valid dict with only id returns normalized user_id, active False, and email None."""
    result = process_user_data({"id": "  UserABC  "})
    assert result == {"user_id": "userabc", "active": False, "email": None}


def test_process_user_data_active_status():
    """Status 'active' correctly sets the active flag to True."""
    result = process_user_data({"id": "user1", "status": "active"})
    assert result["active"] is True


def test_process_user_data_inactive_status():
    """Any non-'active' status value results in active flag being False."""
    result = process_user_data({"id": "user1", "status": "disabled"})
    assert result["active"] is False


def test_process_user_data_valid_email():
    """A properly formatted email address is accepted and returned unchanged."""
    result = process_user_data({"id": "user1", "email": "test@example.com"})
    assert result["email"] == "test@example.com"


def test_process_user_data_non_dict_raises_type_error():
    """Passing a non-dict input raises TypeError as a type-confusion guard."""
    with pytest.raises(TypeError):
        process_user_data(["id", "value"])


def test_process_user_data_missing_id_raises_value_error():
    """Missing 'id' key raises ValueError due to required field validation."""
    with pytest.raises(ValueError):
        process_user_data({"email": "test@example.com"})


def test_process_user_data_empty_id_raises_value_error():
    """Empty string id is falsy and raises ValueError."""
    with pytest.raises(ValueError):
        process_user_data({"id": ""})


def test_process_user_data_non_string_id_raises_value_error():
    """Non-string id (e.g. integer) raises ValueError for invalid type."""
    with pytest.raises(ValueError):
        process_user_data({"id": 12345})


def test_process_user_data_invalid_email_format_raises_value_error():
    """Malformed email missing '@' and domain raises ValueError."""
    with pytest.raises(ValueError):
        process_user_data({"id": "user1", "email": "not-an-email"})


def test_process_user_data_email_missing_domain_dot_raises_value_error():
    """Email without a dot in domain portion fails the format validation."""
    with pytest.raises(ValueError):
        process_user_data({"id": "user1", "email": "user@domain"})


def test_process_user_data_email_header_injection_should_be_rejected():
    """Email containing CRLF header-injection payload must be rejected, not silently accepted."""
    malicious_email = "victim@example.com\r\nBcc:attacker@evil.com"
    with pytest.raises(ValueError):
        process_user_data({"id": "user1", "email": malicious_email})


def test_process_user_data_id_with_none_raises_value_error():
    """Explicit None id is treated as missing and raises ValueError."""
    with pytest.raises(ValueError):
        process_user_data({"id": None})


# ---------------------------------------------------------------------------
# calculate_risk_score
# ---------------------------------------------------------------------------

def test_calculate_risk_score_empty_list_returns_zero():
    """An empty metrics list short-circuits to a risk score of 0.0."""
    assert calculate_risk_score([]) == 0.0


def test_calculate_risk_score_valid_average():
    """Average of valid numeric scores within bounds is computed correctly."""
    result = calculate_risk_score([10, 20, 30])
    assert result == pytest.approx(20.0)


def test_calculate_risk_score_boundary_values_accepted():
    """Scores exactly at boundary values 0 and 100 are accepted without error."""
    result = calculate_risk_score([0, 100])
    assert result == pytest.approx(50.0)


def test_calculate_risk_score_non_list_raises_type_error():
    """Passing a non-list (e.g., dict) raises TypeError for type confusion guard."""
    with pytest.raises(TypeError):
        calculate_risk_score({"score": 50})


def test_calculate_risk_score_non_numeric_value_raises_value_error():
    """A string embedded in the metrics list raises ValueError for non-numeric entries."""
    with pytest.raises(ValueError):
        calculate_risk_score([10, "50", 30])


def test_calculate_risk_score_negative_value_raises_value_error():
    """A negative score below the allowed range raises ValueError."""
    with pytest.raises(ValueError):
        calculate_risk_score([-1, 50])


def test_calculate_risk_score_above_max_raises_value_error():
    """A score above 100 raises ValueError for out-of-range boundary violation."""
    with pytest.raises(ValueError):
        calculate_risk_score([50, 101])


def test_calculate_risk_score_none_in_list_raises_value_error():
    """A None value embedded in the metrics list raises ValueError, not a TypeError crash."""
    with pytest.raises(ValueError):
        calculate_risk_score([10, None, 30])


# ---------------------------------------------------------------------------
# format_api_endpoint
# ---------------------------------------------------------------------------

def test_format_api_endpoint_basic_construction():
    """Standard inputs construct the expected versioned endpoint URL."""
    result = format_api_endpoint("https://api.example.com", 2, "users")
    assert result == "https://api.example.com/v2/users"


def test_format_api_endpoint_strips_trailing_slash_on_base():
    """Trailing slash on base_url is stripped before constructing the endpoint."""
    result = format_api_endpoint("https://api.example.com/", 1, "items")
    assert result == "https://api.example.com/v1/items"


def test_format_api_endpoint_strips_leading_slash_on_resource():
    """Leading slash on resource path is stripped to avoid double slashes."""
    result = format_api_endpoint("https://api.example.com", 1, "/items")
    assert result == "https://api.example.com/v1/items"


def test_format_api_endpoint_no_resource_returns_version_only():
    """Empty or None resource results in an endpoint containing only the version segment."""
    result = format_api_endpoint("https://api.example.com", 3, "")
    assert result == "https://api.example.com/v3"


def test_format_api_endpoint_empty_base_url_raises_value_error():
    """Empty base_url string raises ValueError as required field validation."""
    with pytest.raises(ValueError):
        format_api_endpoint("", 1, "resource")


def test_format_api_endpoint_non_string_base_url_raises_value_error():
    """Non-string base_url (e.g., integer) raises ValueError for type validation."""
    with pytest.raises(ValueError):
        format_api_endpoint(12345, 1, "resource")


def test_format_api_endpoint_zero_version_raises_value_error():
    """Version of zero is not a valid positive integer and raises ValueError."""
    with pytest.raises(ValueError):
        format_api_endpoint("https://api.example.com", 0, "resource")


def test_format_api_endpoint_negative_version_raises_value_error():
    """Negative version number raises ValueError for boundary validation."""
    with pytest.raises(ValueError):
        format_api_endpoint("https://api.example.com", -5, "resource")


def test_format_api_endpoint_non_int_version_raises_value_error():
    """Non-integer version (e.g., string) raises ValueError for type validation."""
    with pytest.raises(ValueError):
        format_api_endpoint("https://api.example.com", "2", "resource")


def test_format_api_endpoint_path_traversal_resource_should_be_sanitized():
    """Resource containing path traversal sequences must not be passed through unsanitized."""
    result = format_api_endpoint("https://api.example.com", 1, "../../etc/passwd")
    assert "../" not in result, "Path traversal sequence must be sanitized from resource path"


def test_format_api_endpoint_crlf_injection_in_base_url_should_be_sanitized():
    """base_url containing CRLF injection characters must not be reflected unsanitized in output."""
    malicious_base = "https://api.example.com\r\nX-Injected-Header: true"
    result = format_api_endpoint(malicious_base, 1, "resource")
    assert "\r" not in result and "\n" not in result, "CRLF sequences must be stripped from constructed endpoint"
