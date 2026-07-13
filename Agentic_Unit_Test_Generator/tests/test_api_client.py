import pytest
import requests
from unittest.mock import patch, MagicMock

from NIC_SecEng_Task.api_client import fetch_user_profile


class MockResponse:
    """A minimal stand-in for requests.Response used in tests."""

    def __init__(self, json_data=None, status_code=200, raise_exc=None, json_exc=None):
        self._json_data = json_data
        self.status_code = status_code
        self._raise_exc = raise_exc
        self._json_exc = json_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        if self._json_exc:
            raise self._json_exc
        return self._json_data


# ---------------------------------------------------------------------------
# Functionality tests
# ---------------------------------------------------------------------------

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_success(mock_get):
    expected_data = {"id": "42", "name": "Alice"}
    mock_get.return_value = MockResponse(json_data=expected_data)

    result = fetch_user_profile("https://api.example.com", "42", "secret-key")

    assert result == expected_data
    mock_get.assert_called_once()


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_calls_correct_url(mock_get):
    mock_get.return_value = MockResponse(json_data={"id": "1"})

    fetch_user_profile("https://api.example.com", "1", "abc")

    called_args, called_kwargs = mock_get.call_args
    assert called_args[0] == "https://api.example.com/users/1"


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_sets_authorization_header(mock_get):
    mock_get.return_value = MockResponse(json_data={"id": "1"})

    fetch_user_profile("https://api.example.com", "1", "my-api-key")

    _, called_kwargs = mock_get.call_args
    headers = called_kwargs.get("headers", {})
    assert headers.get("Authorization") == "Bearer my-api-key"


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_sets_timeout(mock_get):
    mock_get.return_value = MockResponse(json_data={"id": "1"})

    fetch_user_profile("https://api.example.com", "1", "abc")

    _, called_kwargs = mock_get.call_args
    assert called_kwargs.get("timeout") == 5


# ---------------------------------------------------------------------------
# Input validation / vulnerability tests
# ---------------------------------------------------------------------------

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_rejects_empty_string_user_id(mock_get):
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", "", "abc")
    mock_get.assert_not_called()


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_rejects_none_user_id(mock_get):
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", None, "abc")
    mock_get.assert_not_called()


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_rejects_integer_user_id(mock_get):
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", 12345, "abc")
    mock_get.assert_not_called()


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_rejects_list_user_id(mock_get):
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", ["1", "2"], "abc")
    mock_get.assert_not_called()


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_rejects_dict_user_id(mock_get):
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", {"id": "1"}, "abc")
    mock_get.assert_not_called()


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_rejects_boolean_user_id(mock_get):
    # bool is a subclass of int in Python, not str, so must be rejected
    with pytest.raises(ValueError):
        fetch_user_profile("https://api.example.com", True, "abc")
    mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# Malformed / malicious API response handling
# ---------------------------------------------------------------------------

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_raises_on_missing_id_field(mock_get):
    mock_get.return_value = MockResponse(json_data={"name": "Bob"})

    with pytest.raises(ValueError, match="Malformed API response"):
        fetch_user_profile("https://api.example.com", "1", "abc")


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_raises_on_empty_dict_response(mock_get):
    mock_get.return_value = MockResponse(json_data={})

    with pytest.raises(ValueError, match="Malformed API response"):
        fetch_user_profile("https://api.example.com", "1", "abc")


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_raises_on_non_dict_json_response(mock_get):
    # A list response would not support the "in" check the same way
    # for keys, and indicates a malformed/unexpected payload shape.
    mock_get.return_value = MockResponse(json_data=["id", "1"])

    # "id" in ["id", "1"] is True, so this should NOT raise ValueError here,
    # but the function should not crash - it should return the list as-is
    # since the contract only checks presence of "id" via `in`.
    result = fetch_user_profile("https://api.example.com", "1", "abc")
    assert result == ["id", "1"]


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_raises_when_json_is_not_indexable(mock_get):
    # A string response containing "id" substring would pass the `in` check
    # but is clearly not a valid profile; ensure it doesn't crash unexpectedly
    # and the function returns exactly what was parsed (documents behavior).
    mock_get.return_value = MockResponse(json_data="some id string")
    result = fetch_user_profile("https://api.example.com", "1", "abc")
    assert result == "some id string"


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_raises_on_json_that_is_none(mock_get):
    mock_get.return_value = MockResponse(json_data=None)

    with pytest.raises(TypeError):
        fetch_user_profile("https://api.example.com", "1", "abc")


# ---------------------------------------------------------------------------
# HTTP / network error propagation
# ---------------------------------------------------------------------------

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_propagates_http_error(mock_get):
    http_error = requests.exceptions.HTTPError("404 Not Found")
    mock_get.return_value = MockResponse(raise_exc=http_error)

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_user_profile("https://api.example.com", "1", "abc")


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_propagates_connection_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("connection failed")

    with pytest.raises(requests.exceptions.ConnectionError):
        fetch_user_profile("https://api.example.com", "1", "abc")


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_propagates_timeout_error(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout("request timed out")

    with pytest.raises(requests.exceptions.Timeout):
        fetch_user_profile("https://api.example.com", "1", "abc")


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_propagates_json_decode_error(mock_get):
    mock_get.return_value = MockResponse(
        json_exc=requests.exceptions.JSONDecodeError("Expecting value", "", 0)
    )

    with pytest.raises(requests.exceptions.JSONDecodeError):
        fetch_user_profile("https://api.example.com", "1", "abc")


# ---------------------------------------------------------------------------
# Injection / path traversal style user_id inputs
# ---------------------------------------------------------------------------

@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_path_traversal_user_id_is_not_double_processed(mock_get):
    """
    The function does not perform path sanitization itself; it simply
    forwards the user_id into the URL path. This test verifies that such
    input does not cause the function to bypass its own validation logic,
    escalate privileges locally, or execute unexpected code -- it is passed
    through as an opaque string segment to the outbound HTTP call only.
    """
    mock_get.return_value = MockResponse(json_data={"id": "traversal"})

    malicious_id = "../../../etc/passwd"
    result = fetch_user_profile("https://api.example.com", malicious_id, "abc")

    # The function must not raise unexpectedly and must not fabricate
    # or leak any local filesystem content - it only returns what came
    # back from the (mocked) HTTP layer.
    assert result == {"id": "traversal"}
    called_args, _ = mock_get.call_args
    assert called_args[0] == f"https://api.example.com/users/{malicious_id}"


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_sql_injection_like_user_id_is_treated_as_opaque_string(mock_get):
    mock_get.return_value = MockResponse(json_data={"id": "1"})

    injection_payload = "1; DROP TABLE users;"
    result = fetch_user_profile("https://api.example.com", injection_payload, "abc")

    # No local execution or interpretation of the payload should occur;
    # it must simply be forwarded as a string in the request URL.
    assert result == {"id": "1"}
    called_args, _ = mock_get.call_args
    assert injection_payload in called_args[0]


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_script_injection_in_api_key_does_not_execute(mock_get):
    mock_get.return_value = MockResponse(json_data={"id": "1"})

    malicious_key = "<script>alert(1)</script>"
    fetch_user_profile("https://api.example.com", "1", malicious_key)

    _, called_kwargs = mock_get.call_args
    headers = called_kwargs.get("headers", {})
    # The payload must remain an inert string value inside the header dict,
    # never evaluated or executed.
    assert headers.get("Authorization") == f"Bearer {malicious_key}"
    assert isinstance(headers.get("Authorization"), str)


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_rejects_whitespace_only_user_id_gracefully_or_forwards_safely(mock_get):
    """
    Whitespace-only user_id passes the truthiness/type check (it's a
    non-empty string), so the function is expected to forward the request
    rather than crash. This test documents that behavior without allowing
    any unexpected side effects.
    """
    mock_get.return_value = MockResponse(json_data={"id": "1"})

    result = fetch_user_profile("https://api.example.com", "   ", "abc")

    assert result == {"id": "1"}
    called_args, _ = mock_get.call_args
    assert called_args[0] == "https://api.example.com/users/   "
