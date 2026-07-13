import pytest
import requests

from NIC_SecEng_Task import api_client


class FakeResponse:
    """A minimal stand-in for requests.Response used to control test behavior."""

    def __init__(self, json_data=None, status_code=200, raise_exc=None, json_exc=None):
        self._json_data = json_data
        self.status_code = status_code
        self._raise_exc = raise_exc
        self._json_exc = json_exc
        self.request_url = None
        self.request_headers = None

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        if self._json_exc:
            raise self._json_exc
        return self._json_data


def test_fetch_user_profile_success(monkeypatch):
    """Verifies a well-formed response with an 'id' field is returned as-is."""
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse(json_data={"id": "123", "name": "Alice"})

    monkeypatch.setattr(requests, "get", fake_get)

    result = api_client.fetch_user_profile("https://api.example.com", "123", "secret-key")

    assert result == {"id": "123", "name": "Alice"}
    assert captured["url"] == "https://api.example.com/users/123"
    assert captured["headers"] == {"Authorization": "Bearer secret-key"}
    assert captured["timeout"] == 5


def test_fetch_user_profile_empty_user_id_raises(monkeypatch):
    """Ensures an empty string user_id is rejected before any network call."""
    def fake_get(*args, **kwargs):
        raise AssertionError("requests.get should not be called for invalid user_id")

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        api_client.fetch_user_profile("https://api.example.com", "", "key")


def test_fetch_user_profile_none_user_id_raises(monkeypatch):
    """Ensures a None user_id is rejected before any network call."""
    def fake_get(*args, **kwargs):
        raise AssertionError("requests.get should not be called for invalid user_id")

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        api_client.fetch_user_profile("https://api.example.com", None, "key")


def test_fetch_user_profile_non_string_user_id_raises(monkeypatch):
    """Ensures a non-string user_id (e.g. int) is rejected via type validation."""
    def fake_get(*args, **kwargs):
        raise AssertionError("requests.get should not be called for invalid user_id")

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        api_client.fetch_user_profile("https://api.example.com", 12345, "key")


def test_fetch_user_profile_missing_id_field_raises(monkeypatch):
    """Ensures a response body without an 'id' field is treated as malformed and rejected."""
    def fake_get(url, headers=None, timeout=None):
        return FakeResponse(json_data={"name": "Alice"})

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
        api_client.fetch_user_profile("https://api.example.com", "123", "key")


def test_fetch_user_profile_http_error_propagates(monkeypatch):
    """Ensures an HTTP error status from the API surfaces as requests.HTTPError."""
    def fake_get(url, headers=None, timeout=None):
        return FakeResponse(raise_exc=requests.exceptions.HTTPError("404 Not Found"))

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(requests.exceptions.HTTPError):
        api_client.fetch_user_profile("https://api.example.com", "123", "key")


def test_fetch_user_profile_invalid_json_propagates(monkeypatch):
    """Ensures malformed/non-JSON response bodies raise an error rather than being silently accepted."""
    def fake_get(url, headers=None, timeout=None):
        return FakeResponse(json_exc=ValueError("No JSON object could be decoded"))

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(ValueError):
        api_client.fetch_user_profile("https://api.example.com", "123", "key")


def test_fetch_user_profile_network_error_propagates(monkeypatch):
    """Ensures underlying network/connection failures are not swallowed silently."""
    def fake_get(url, headers=None, timeout=None):
        raise requests.exceptions.ConnectionError("Connection refused")

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(requests.exceptions.ConnectionError):
        api_client.fetch_user_profile("https://api.example.com", "123", "key")


def test_fetch_user_profile_timeout_is_bounded(monkeypatch):
    """Ensures a fixed, bounded timeout of 5 seconds is always applied to prevent hanging requests."""
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["timeout"] = timeout
        return FakeResponse(json_data={"id": "1"})

    monkeypatch.setattr(requests, "get", fake_get)

    api_client.fetch_user_profile("https://api.example.com", "1", "key")

    assert captured["timeout"] == 5


def test_fetch_user_profile_path_traversal_user_id_is_not_sanitized(monkeypatch):
    """Exposes that a path-traversal-style user_id is passed directly into the URL without sanitization."""
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return FakeResponse(json_data={"id": "1"})

    monkeypatch.setattr(requests, "get", fake_get)

    malicious_id = "../../admin/secrets"
    api_client.fetch_user_profile("https://api.example.com", malicious_id, "key")

    # SECURITY EXPECTATION: the constructed URL should not contain raw traversal
    # sequences; if this assertion fails, the function is vulnerable to path
    # traversal / endpoint confusion via unsanitized user_id.
    assert "../" not in captured["url"], (
        "Path traversal sequence was passed unsanitized into the request URL"
    )


def test_fetch_user_profile_crlf_injection_in_api_key_is_blocked(monkeypatch):
    """Exposes potential CRLF/header injection risk if api_key contains newline characters."""
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["headers"] = headers
        return FakeResponse(json_data={"id": "1"})

    monkeypatch.setattr(requests, "get", fake_get)

    malicious_key = "validkey\r\nX-Injected-Header: evil"
    api_client.fetch_user_profile("https://api.example.com", "1", malicious_key)

    auth_header = captured["headers"]["Authorization"]
    # SECURITY EXPECTATION: header value should not contain raw CRLF sequences
    # that could enable header injection if propagated to a lower-level transport.
    assert "\r" not in auth_header and "\n" not in auth_header, (
        "CRLF sequence was embedded unsanitized into the Authorization header"
    )


def test_fetch_user_profile_sql_injection_style_user_id_handled_as_literal(monkeypatch):
    """Ensures SQL-injection-style payloads in user_id are treated as opaque path data, not executed."""
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return FakeResponse(json_data={"id": "1"})

    monkeypatch.setattr(requests, "get", fake_get)

    payload = "1' OR '1'='1"
    result = api_client.fetch_user_profile("https://api.example.com", payload, "key")

    assert result == {"id": "1"}
    assert payload in captured["url"]


def test_fetch_user_profile_empty_dict_response_raises(monkeypatch):
    """Ensures a completely empty JSON object is treated as malformed due to missing 'id'."""
    def fake_get(url, headers=None, timeout=None):
        return FakeResponse(json_data={})

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
        api_client.fetch_user_profile("https://api.example.com", "1", "key")


def test_fetch_user_profile_id_field_with_falsy_value_still_accepted(monkeypatch):
    """Confirms an 'id' field present but falsy (e.g. 0) is still treated as valid per membership check."""
    def fake_get(url, headers=None, timeout=None):
        return FakeResponse(json_data={"id": 0})

    monkeypatch.setattr(requests, "get", fake_get)

    result = api_client.fetch_user_profile("https://api.example.com", "1", "key")

    assert result == {"id": 0}
