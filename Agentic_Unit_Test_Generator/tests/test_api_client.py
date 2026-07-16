import pytest
import requests
from unittest.mock import patch

from NIC_SecEng_Task.api_client import fetch_user_profile


class FakeResponse:
    """A minimal stand-in for requests.Response used to avoid real network calls."""

    def __init__(self, json_data=None, status_code=200, raise_exc=None):
        self._json_data = json_data
        self.status_code = status_code
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._json_data


def test_valid_user_profile_returns_data():
    """Verify that a valid response with an 'id' field is returned unchanged."""
    fake_data = {"id": "123", "name": "Alice"}
    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(json_data=fake_data)
        result = fetch_user_profile("https://api.example.com", "123", "secret-key")
    assert result == fake_data


def test_empty_user_id_raises_value_error():
    """Ensure an empty string user_id is rejected before making any network call."""
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", "", "secret-key")


def test_none_user_id_raises_value_error():
    """Ensure a None user_id is rejected by the input validation guard."""
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", None, "secret-key")


def test_non_string_user_id_raises_value_error():
    """Ensure a non-string (int) user_id is rejected to prevent type confusion."""
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", 123, "secret-key")


def test_missing_id_field_raises_value_error():
    """Ensure a malformed API response missing the 'id' field raises ValueError."""
    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(json_data={"name": "Alice"})
        with pytest.raises(ValueError, match="Malformed API response"):
            fetch_user_profile("https://api.example.com", "123", "secret-key")


def test_http_error_propagates():
    """Ensure an HTTP error status triggers requests.HTTPError via raise_for_status."""
    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(
            status_code=404, raise_exc=requests.exceptions.HTTPError("Not Found")
        )
        with pytest.raises(requests.exceptions.HTTPError):
            fetch_user_profile("https://api.example.com", "123", "secret-key")


def test_authorization_header_contains_api_key():
    """Verify the Authorization header is correctly formatted with the Bearer token."""
    fake_data = {"id": "123"}
    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(json_data=fake_data)
        fetch_user_profile("https://api.example.com", "123", "my-api-key")
        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer my-api-key"


def test_request_timeout_is_set():
    """Verify that the request enforces a 5-second timeout to prevent indefinite hangs."""
    fake_data = {"id": "123"}
    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(json_data=fake_data)
        fetch_user_profile("https://api.example.com", "123", "my-api-key")
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 5


def test_url_constructed_with_user_id():
    """Verify the request URL is correctly built from base_url and user_id."""
    fake_data = {"id": "123"}
    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(json_data=fake_data)
        fetch_user_profile("https://api.example.com", "123", "my-api-key")
        args, _ = mock_get.call_args
        assert args[0] == "https://api.example.com/users/123"


def test_path_traversal_user_id_is_rejected():
    """Ensure a path-traversal payload in user_id is rejected rather than embedded verbatim in the URL."""
    malicious_id = "../../admin/secrets"
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", malicious_id, "secret-key")


def test_header_injection_via_api_key_is_rejected():
    """Ensure a CRLF header-injection payload in api_key is rejected rather than embedded unsanitized in headers."""
    malicious_key = "validkey\r\nX-Injected-Header: evil"
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", "123", malicious_key)


def test_json_decode_error_propagates():
    """Ensure an invalid JSON response raises an exception rather than being silently swallowed."""

    class BadJsonResponse(FakeResponse):
        def json(self):
            raise ValueError("Expecting value: line 1 column 1 (char 0)")

    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.return_value = BadJsonResponse(json_data=None)
        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", "123", "secret-key")


def test_whitespace_user_id_is_accepted_by_non_empty_check():
    """Verify a whitespace-only string user_id passes the current non-empty validation check."""
    fake_data = {"id": "123"}
    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(json_data=fake_data)
        result = fetch_user_profile("https://api.example.com", " ", "secret-key")
    assert result == fake_data


def test_empty_api_key_still_sends_request():
    """Verify an empty api_key results in a Bearer header with an empty token rather than crashing."""
    fake_data = {"id": "123"}
    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(json_data=fake_data)
        fetch_user_profile("https://api.example.com", "123", "")
        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer "


def test_connection_error_propagates():
    """Ensure a network-level ConnectionError from requests.get propagates unhandled."""
    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        with pytest.raises(requests.exceptions.ConnectionError):
            fetch_user_profile("https://api.example.com", "123", "secret-key")


def test_id_field_with_falsy_value_still_accepted():
    """Verify that an 'id' field present but falsy (e.g. 0) still passes the 'in' membership check."""
    fake_data = {"id": 0}
    with patch("NIC_SecEng_Task.api_client.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(json_data=fake_data)
        result = fetch_user_profile("https://api.example.com", "123", "secret-key")
    assert result == fake_data
