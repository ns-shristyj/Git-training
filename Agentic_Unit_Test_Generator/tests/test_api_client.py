import pytest
from unittest.mock import patch, MagicMock
import requests

from NIC_SecEng_Task.api_client import fetch_user_profile


BASE_URL = "https://api.example.com"
API_KEY = "test-api-key-123"


def _make_response(status_code=200, json_data=None, raise_exc=None):
    """Helper to build a mock requests.Response object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if raise_exc:
        mock_resp.raise_for_status.side_effect = raise_exc
    else:
        mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = json_data if json_data is not None else {}
    return mock_resp


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_valid_returns_data(mock_get):
    """Verify a valid response with an 'id' field is returned unmodified."""
    expected_data = {"id": "42", "name": "Alice"}
    mock_get.return_value = _make_response(json_data=expected_data)

    result = fetch_user_profile(BASE_URL, "42", API_KEY)

    assert result == expected_data
    mock_get.assert_called_once()


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_constructs_correct_url(mock_get):
    """Verify the request URL is built using base_url and user_id."""
    mock_get.return_value = _make_response(json_data={"id": "7"})

    fetch_user_profile(BASE_URL, "7", API_KEY)

    called_url = mock_get.call_args[0][0]
    assert called_url == f"{BASE_URL}/users/7"


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_sets_authorization_header(mock_get):
    """Verify the Authorization header is set using the Bearer scheme with the api_key."""
    mock_get.return_value = _make_response(json_data={"id": "1"})

    fetch_user_profile(BASE_URL, "1", API_KEY)

    headers = mock_get.call_args[1]["headers"]
    assert headers["Authorization"] == f"Bearer {API_KEY}"


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_sets_timeout(mock_get):
    """Verify a timeout value is always passed to prevent hanging requests (DoS mitigation)."""
    mock_get.return_value = _make_response(json_data={"id": "1"})

    fetch_user_profile(BASE_URL, "1", API_KEY)

    assert mock_get.call_args[1]["timeout"] == 5


def test_fetch_user_profile_none_user_id_raises_value_error():
    """Verify passing None as user_id raises ValueError without making any network call."""
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile(BASE_URL, None, API_KEY)


def test_fetch_user_profile_empty_string_user_id_raises_value_error():
    """Verify passing an empty string as user_id raises ValueError."""
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile(BASE_URL, "", API_KEY)


def test_fetch_user_profile_non_string_user_id_raises_value_error():
    """Verify passing a non-string (int) user_id raises ValueError instead of being coerced."""
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile(BASE_URL, 12345, API_KEY)


def test_fetch_user_profile_list_user_id_raises_value_error():
    """Verify passing a list as user_id (type confusion attempt) raises ValueError."""
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile(BASE_URL, ["1", "2"], API_KEY)


def test_fetch_user_profile_dict_user_id_raises_value_error():
    """Verify passing a dict as user_id (type confusion attempt) raises ValueError."""
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile(BASE_URL, {"id": "1"}, API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_missing_id_field_raises_value_error(mock_get):
    """Verify a well-formed HTTP response missing the 'id' field is rejected as malformed."""
    mock_get.return_value = _make_response(json_data={"name": "Bob"})

    with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
        fetch_user_profile(BASE_URL, "1", API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_http_error_propagates(mock_get):
    """Verify that an HTTP error status causes requests.HTTPError to propagate to the caller."""
    mock_get.return_value = _make_response(
        status_code=404, raise_exc=requests.exceptions.HTTPError("404 Not Found")
    )

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_user_profile(BASE_URL, "missing-user", API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_connection_error_propagates(mock_get):
    """Verify that a network-level ConnectionError propagates instead of being silently swallowed."""
    mock_get.side_effect = requests.exceptions.ConnectionError("connection failed")

    with pytest.raises(requests.exceptions.ConnectionError):
        fetch_user_profile(BASE_URL, "1", API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_timeout_error_propagates(mock_get):
    """Verify that a Timeout exception from requests propagates to the caller."""
    mock_get.side_effect = requests.exceptions.Timeout("request timed out")

    with pytest.raises(requests.exceptions.Timeout):
        fetch_user_profile(BASE_URL, "1", API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_invalid_json_raises(mock_get):
    """Verify that a response with invalid/non-JSON body causes a JSON decoding error to propagate."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.side_effect = ValueError("No JSON object could be decoded")
    mock_get.return_value = mock_resp

    with pytest.raises(ValueError):
        fetch_user_profile(BASE_URL, "1", API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_path_traversal_user_id_is_passed_literally(mock_get):
    """Verify a path-traversal style user_id ('../../admin') is embedded literally in the URL
    path and not resolved or expanded locally, preventing local file/path traversal semantics."""
    malicious_id = "../../admin"
    mock_get.return_value = _make_response(json_data={"id": "irrelevant"})

    fetch_user_profile(BASE_URL, malicious_id, API_KEY)

    called_url = mock_get.call_args[0][0]
    assert called_url == f"{BASE_URL}/users/{malicious_id}"
    # The dangerous segments must remain as literal text, not resolved into a different path.
    assert "../../admin" in called_url


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_header_injection_attempt_is_contained_in_header_value(mock_get):
    """Verify a CRLF-injection style api_key is passed as a single header value (dict-based
    header construction) rather than being split into additional raw HTTP headers."""
    malicious_key = "validkey\r\nX-Injected-Header: evil"
    mock_get.return_value = _make_response(json_data={"id": "1"})

    fetch_user_profile(BASE_URL, "1", malicious_key)

    headers = mock_get.call_args[1]["headers"]
    # The entire malicious payload must remain confined to the Authorization value.
    assert headers["Authorization"] == f"Bearer {malicious_key}"
    assert list(headers.keys()) == ["Authorization"]
    assert "X-Injected-Header" not in headers


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_sql_injection_style_user_id_is_passed_literally(mock_get):
    """Verify a SQL-injection style user_id is treated as an opaque string in the URL,
    not interpreted or executed by this client code."""
    malicious_id = "1' OR '1'='1"
    mock_get.return_value = _make_response(json_data={"id": "1"})

    fetch_user_profile(BASE_URL, malicious_id, API_KEY)

    called_url = mock_get.call_args[0][0]
    assert called_url == f"{BASE_URL}/users/{malicious_id}"


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_json_with_id_none_value_is_accepted(mock_get):
    """Verify that a response containing an 'id' key set to None still passes the presence check."""
    data = {"id": None, "name": "NullIdUser"}
    mock_get.return_value = _make_response(json_data=data)

    result = fetch_user_profile(BASE_URL, "1", API_KEY)

    assert result == data


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_large_user_id_handled(mock_get):
    """Verify an unusually large user_id string does not crash the function and is passed through."""
    large_id = "a" * 10000
    mock_get.return_value = _make_response(json_data={"id": large_id})

    result = fetch_user_profile(BASE_URL, large_id, API_KEY)

    assert result["id"] == large_id
    called_url = mock_get.call_args[0][0]
    assert called_url.endswith(large_id)
