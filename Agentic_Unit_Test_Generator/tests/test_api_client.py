import pytest
from unittest.mock import MagicMock, patch

from NIC_SecEng_Task.api_client import fetch_user_profile


BASE_URL = "https://api.example.com"
VALID_API_KEY = "test-api-key"


def _make_mock_response(json_data, status_code=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# --- Sanity check ---

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_happy_path(mock_get):
    mock_get.return_value = _make_mock_response({"id": "42", "name": "Alice"})
    result = fetch_user_profile(BASE_URL, "42", VALID_API_KEY)
    assert result == {"id": "42", "name": "Alice"}
    mock_get.assert_called_once_with(
        f"{BASE_URL}/users/42",
        headers={"Authorization": f"Bearer {VALID_API_KEY}"},
        timeout=5,
    )


# --- Type confusion ---

def test_fetch_user_profile_none_user_id_raises():
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile(BASE_URL, None, VALID_API_KEY)


def test_fetch_user_profile_int_user_id_raises():
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile(BASE_URL, 123, VALID_API_KEY)


def test_fetch_user_profile_bool_user_id_raises():
    # bool is a subclass of int, not str — should be rejected
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile(BASE_URL, True, VALID_API_KEY)


# --- Boundary values ---

def test_fetch_user_profile_empty_string_user_id_raises():
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile(BASE_URL, "", VALID_API_KEY)


# --- Malformed API response ---

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_missing_id_field_raises(mock_get):
    mock_get.return_value = _make_mock_response({"name": "Alice"})
    with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
        fetch_user_profile(BASE_URL, "42", VALID_API_KEY)


# --- HTTP error propagation ---

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_http_error_propagates(mock_get):
    import requests as req
    mock_resp = _make_mock_response({}, status_code=403)
    mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("403 Forbidden")
    mock_get.return_value = mock_resp
    with pytest.raises(req.exceptions.HTTPError):
        fetch_user_profile(BASE_URL, "42", VALID_API_KEY)


# --- Adversarial / security inputs ---

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_path_traversal_user_id(mock_get):
    """Path traversal in user_id should be passed to requests.get as-is (no silent sanitisation)."""
    mock_get.return_value = _make_mock_response({"id": "../../../etc/passwd"})
    result = fetch_user_profile(BASE_URL, "../../../etc/passwd", VALID_API_KEY)
    # Verify the raw traversal string was forwarded to the HTTP layer
    called_url = mock_get.call_args[0][0]
    assert "../../../etc/passwd" in called_url
    assert result["id"] == "../../../etc/passwd"


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_sql_injection_user_id(mock_get):
    payload = "' OR 1=1--"
    mock_get.return_value = _make_mock_response({"id": payload})
    result = fetch_user_profile(BASE_URL, payload, VALID_API_KEY)
    called_url = mock_get.call_args[0][0]
    assert payload in called_url


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_oversized_user_id(mock_get):
    large_id = "A" * 10_000
    mock_get.return_value = _make_mock_response({"id": large_id})
    result = fetch_user_profile(BASE_URL, large_id, VALID_API_KEY)
    assert result["id"] == large_id


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_null_byte_user_id(mock_get):
    payload = "user\x00admin"
    mock_get.return_value = _make_mock_response({"id": payload})
    result = fetch_user_profile(BASE_URL, payload, VALID_API_KEY)
    called_url = mock_get.call_args[0][0]
    assert "\x00" in called_url


# --- Unicode edge cases ---

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_unicode_rtlo_user_id(mock_get):
    """Right-to-left override character in user_id should not be silently stripped."""
    payload = "user\u202Eid"
    mock_get.return_value = _make_mock_response({"id": payload})
    result = fetch_user_profile(BASE_URL, payload, VALID_API_KEY)
    called_url = mock_get.call_args[0][0]
    assert "\u202E" in called_url


# --- Network / timeout error ---

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_timeout_propagates(mock_get):
    import requests as req
    mock_get.side_effect = req.exceptions.Timeout("timed out")
    with pytest.raises(req.exceptions.Timeout):
        fetch_user_profile(BASE_URL, "42", VALID_API_KEY)
