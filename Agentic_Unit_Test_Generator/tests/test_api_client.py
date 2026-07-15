import pytest
import requests
from unittest.mock import patch, MagicMock

from NIC_SecEng_Task.api_client import fetch_user_profile


BASE_URL = "https://api.example.com"
API_KEY = "test-api-key-123"


def _make_mock_response(json_data, status_ok=True):
    """Helper to build a mock requests.Response object."""
    mock_response = MagicMock()
    mock_response.json.return_value = json_data
    if status_ok:
        mock_response.raise_for_status.return_value = None
    else:
        mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP error")
    return mock_response


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_success_returns_parsed_json(mock_get):
    """Verifies a successful response with an 'id' field is returned unchanged."""
    expected_data = {"id": "u123", "name": "Alice"}
    mock_get.return_value = _make_mock_response(expected_data)

    result = fetch_user_profile(BASE_URL, "u123", API_KEY)

    assert result == expected_data
    mock_get.assert_called_once()


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_constructs_correct_url(mock_get):
    """Verifies the request URL is correctly built from base_url and user_id."""
    mock_get.return_value = _make_mock_response({"id": "u123"})

    fetch_user_profile(BASE_URL, "u123", API_KEY)

    called_url = mock_get.call_args[0][0]
    assert called_url == f"{BASE_URL}/users/u123"


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_sends_bearer_authorization_header(mock_get):
    """Verifies the Authorization header is correctly formatted with the Bearer scheme and API key."""
    mock_get.return_value = _make_mock_response({"id": "u123"})

    fetch_user_profile(BASE_URL, "u123", API_KEY)

    headers = mock_get.call_args[1]["headers"]
    assert headers["Authorization"] == f"Bearer {API_KEY}"


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_uses_fixed_timeout(mock_get):
    """Verifies the request is issued with a bounded timeout to prevent indefinite hangs."""
    mock_get.return_value = _make_mock_response({"id": "u123"})

    fetch_user_profile(BASE_URL, "u123", API_KEY)

    assert mock_get.call_args[1]["timeout"] == 5


def test_fetch_user_profile_raises_on_empty_user_id():
    """Verifies an empty string user_id is rejected before any network call is made."""
    with pytest.raises(ValueError):
        fetch_user_profile(BASE_URL, "", API_KEY)


def test_fetch_user_profile_raises_on_none_user_id():
    """Verifies a None user_id is rejected with a ValueError."""
    with pytest.raises(ValueError):
        fetch_user_profile(BASE_URL, None, API_KEY)


def test_fetch_user_profile_raises_on_integer_user_id():
    """Verifies a non-string (int) user_id triggers type validation failure."""
    with pytest.raises(ValueError):
        fetch_user_profile(BASE_URL, 12345, API_KEY)


def test_fetch_user_profile_raises_on_list_user_id():
    """Verifies a non-string (list) user_id triggers type validation failure."""
    with pytest.raises(ValueError):
        fetch_user_profile(BASE_URL, ["u123"], API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_raises_on_missing_id_field(mock_get):
    """Verifies a malformed API response lacking the 'id' field raises ValueError."""
    mock_get.return_value = _make_mock_response({"name": "Alice"})

    with pytest.raises(ValueError, match="Malformed API response"):
        fetch_user_profile(BASE_URL, "u123", API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_propagates_http_error(mock_get):
    """Verifies that HTTP error status codes cause an HTTPError to propagate instead of being silently ignored."""
    mock_get.return_value = _make_mock_response({"id": "u123"}, status_ok=False)

    with pytest.raises(requests.HTTPError):
        fetch_user_profile(BASE_URL, "u123", API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_propagates_json_decode_error(mock_get):
    """Verifies that an invalid/non-JSON response body causes the underlying error to propagate rather than being masked."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = ValueError("No JSON object could be decoded")
    mock_get.return_value = mock_response

    with pytest.raises(ValueError):
        fetch_user_profile(BASE_URL, "u123", API_KEY)


def test_fetch_user_profile_rejects_path_traversal_user_id():
    """Ensures a path traversal payload in user_id is rejected rather than silently embedded into the request URL."""
    malicious_user_id = "../../../etc/passwd"
    with pytest.raises(ValueError):
        fetch_user_profile(BASE_URL, malicious_user_id, API_KEY)


def test_fetch_user_profile_rejects_crlf_injection_in_user_id():
    """Ensures a CRLF/header-injection payload embedded in user_id is rejected instead of being passed through to the URL."""
    malicious_user_id = "u123\r\nX-Injected-Header: evil"
    with pytest.raises(ValueError):
        fetch_user_profile(BASE_URL, malicious_user_id, API_KEY)


def test_fetch_user_profile_rejects_sql_injection_like_user_id():
    """Ensures an SQL-injection-style payload passed as user_id is rejected by input validation."""
    malicious_user_id = "u123' OR '1'='1"
    with pytest.raises(ValueError):
        fetch_user_profile(BASE_URL, malicious_user_id, API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_rejects_null_byte_in_user_id(mock_get):
    """Ensures a null-byte payload in user_id is rejected instead of being forwarded into the request URL unchanged."""
    malicious_user_id = "u123\x00extra"
    mock_get.return_value = _make_mock_response({"id": "u123"})

    with pytest.raises(ValueError):
        fetch_user_profile(BASE_URL, malicious_user_id, API_KEY)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_does_not_leak_id_mismatch(mock_get):
    """Verifies the function does not validate that the returned 'id' matches the requested user_id, documenting current trust behavior."""
    mismatched_data = {"id": "someone-else"}
    mock_get.return_value = _make_mock_response(mismatched_data)

    result = fetch_user_profile(BASE_URL, "u123", API_KEY)

    assert result["id"] == "someone-else"
