import pytest
from unittest.mock import patch, MagicMock
import requests

from NIC_SecEng_Task.api_client import fetch_user_profile


def _make_mock_response(json_data=None, raise_exc=None):
    mock_resp = MagicMock()
    if raise_exc:
        mock_resp.raise_for_status.side_effect = raise_exc
    else:
        mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = json_data
    return mock_resp


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_happy_path(mock_get):
    mock_get.return_value = _make_mock_response(json_data={"id": "123", "name": "Alice"})

    result = fetch_user_profile("https://api.example.com", "123", "secret-key")

    assert result == {"id": "123", "name": "Alice"}
    mock_get.assert_called_once_with(
        "https://api.example.com/users/123",
        headers={"Authorization": "Bearer secret-key"},
        timeout=5,
    )


@pytest.mark.parametrize("bad_user_id", [None, 123, True, [], {}])
def test_fetch_user_profile_type_confusion_raises_value_error(bad_user_id):
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile("https://api.example.com", bad_user_id, "secret-key")


def test_fetch_user_profile_empty_string_user_id_raises_value_error():
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile("https://api.example.com", "", "secret-key")


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_malicious_path_traversal_user_id(mock_get):
    mock_get.return_value = _make_mock_response(json_data={"id": "../../../etc/passwd"})

    malicious_id = "../../../etc/passwd"
    result = fetch_user_profile("https://api.example.com", malicious_id, "secret-key")

    assert result == {"id": "../../../etc/passwd"}
    mock_get.assert_called_once_with(
        f"https://api.example.com/users/{malicious_id}",
        headers={"Authorization": "Bearer secret-key"},
        timeout=5,
    )


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_http_error_propagates(mock_get):
    mock_get.return_value = _make_mock_response(
        raise_exc=requests.exceptions.HTTPError("404 Client Error")
    )

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_user_profile("https://api.example.com", "unknown-user", "secret-key")


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_malformed_response_missing_id_raises_value_error(mock_get):
    mock_get.return_value = _make_mock_response(json_data={"name": "Alice"})

    with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
        fetch_user_profile("https://api.example.com", "123", "secret-key")


@patch("NIC_SecEng_Task.api_client.requests.get")
def test_fetch_user_profile_unicode_user_id(mock_get):
    unicode_id = "user\u202e\u200b\U0001F600"
    mock_get.return_value = _make_mock_response(json_data={"id": unicode_id})

    result = fetch_user_profile("https://api.example.com", unicode_id, "secret-key")

    assert result == {"id": unicode_id}
    mock_get.assert_called_once_with(
        f"https://api.example.com/users/{unicode_id}",
        headers={"Authorization": "Bearer secret-key"},
        timeout=5,
    )
