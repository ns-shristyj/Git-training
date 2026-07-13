import pytest
from unittest.mock import patch, MagicMock

from NIC_SecEng_Task.api_client import fetch_user_profile


def _make_mock_response(json_data, status_ok=True):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    if status_ok:
        mock_resp.raise_for_status.return_value = None
    else:
        mock_resp.raise_for_status.side_effect = requests.HTTPError("HTTP error")
    return mock_resp


import requests  # placed after helper to keep import grouping clean for patch target


def test_fetch_user_profile_happy_path():
    expected_data = {"id": "123", "name": "Alice"}
    mock_resp = _make_mock_response(expected_data)
    with patch("NIC_SecEng_Task.api_client.requests.get", return_value=mock_resp) as mock_get:
        result = fetch_user_profile("https://api.example.com", "123", "secret-key")

    assert result == expected_data
    mock_get.assert_called_once_with(
        "https://api.example.com/users/123",
        headers={"Authorization": "Bearer secret-key"},
        timeout=5,
    )


def test_fetch_user_profile_none_user_id_raises_value_error():
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile("https://api.example.com", None, "key")


def test_fetch_user_profile_wrong_type_user_id_raises_value_error():
    # boolean is not a str instance despite being int-like
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile("https://api.example.com", True, "key")


def test_fetch_user_profile_empty_string_user_id_raises_value_error():
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        fetch_user_profile("https://api.example.com", "", "key")


def test_fetch_user_profile_malformed_response_missing_id():
    mock_resp = _make_mock_response({"name": "Bob"})
    with patch("NIC_SecEng_Task.api_client.requests.get", return_value=mock_resp):
        with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
            fetch_user_profile("https://api.example.com", "123", "secret-key")


def test_fetch_user_profile_http_error_propagates():
    mock_resp = _make_mock_response({"id": "123"}, status_ok=False)
    with patch("NIC_SecEng_Task.api_client.requests.get", return_value=mock_resp):
        with pytest.raises(requests.HTTPError):
            fetch_user_profile("https://api.example.com", "123", "secret-key")


def test_fetch_user_profile_adversarial_user_id_passed_through():
    malicious_id = "../../../etc/passwd; rm -rf / #' OR 1=1--"
    expected_data = {"id": malicious_id}
    mock_resp = _make_mock_response(expected_data)
    with patch("NIC_SecEng_Task.api_client.requests.get", return_value=mock_resp) as mock_get:
        result = fetch_user_profile("https://api.example.com", malicious_id, "key")

    assert result == expected_data
    called_url = mock_get.call_args.args[0]
    assert malicious_id in called_url


def test_fetch_user_profile_oversized_user_id_does_not_crash():
    oversized_id = "a" * 10000
    expected_data = {"id": oversized_id}
    mock_resp = _make_mock_response(expected_data)
    with patch("NIC_SecEng_Task.api_client.requests.get", return_value=mock_resp):
        result = fetch_user_profile("https://api.example.com", oversized_id, "key")

    assert result == expected_data
