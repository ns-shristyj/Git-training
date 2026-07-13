import pytest
from unittest.mock import patch, MagicMock
import requests

from NIC_SecEng_Task.api_client import fetch_user_profile


def make_mock_response(json_data=None, status_ok=True, json_exception=None):
    """Helper to build a mock requests.Response object."""
    mock_resp = MagicMock()
    if status_ok:
        mock_resp.raise_for_status.return_value = None
    else:
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("HTTP error")

    if json_exception is not None:
        mock_resp.json.side_effect = json_exception
    else:
        mock_resp.json.return_value = json_data

    return mock_resp


class TestFetchUserProfileValidation:
    def test_empty_user_id_raises(self):
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("https://api.example.com", "", "key")

    def test_none_user_id_raises(self):
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("https://api.example.com", None, "key")

    def test_non_string_user_id_int_raises(self):
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("https://api.example.com", 123, "key")

    def test_non_string_user_id_list_raises(self):
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("https://api.example.com", ["1"], "key")

    def test_non_string_user_id_dict_raises(self):
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("https://api.example.com", {"id": 1}, "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_zero_int_user_id_raises(self, mock_get):
        # 0 is falsy but also not a string -> should still raise due to isinstance check
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("https://api.example.com", 0, "key")
        mock_get.assert_not_called()


class TestFetchUserProfileSuccess:
    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_successful_fetch_returns_data(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"id": "42", "name": "Alice"})

        result = fetch_user_profile("https://api.example.com", "42", "secret-key")

        assert result == {"id": "42", "name": "Alice"}

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_request_url_constructed_correctly(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com", "1", "secret-key")

        called_url = mock_get.call_args[0][0]
        assert called_url == "https://api.example.com/users/1"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_authorization_header_set_correctly(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com", "1", "my-secret-key")

        headers = mock_get.call_args[1]["headers"]
        assert headers == {"Authorization": "Bearer my-secret-key"}

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_timeout_is_set(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com", "1", "key")

        assert mock_get.call_args[1]["timeout"] == 5

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_id_field_zero_value_still_valid(self, mock_get):
        # id present with falsy value (0) - "in" check should still pass
        mock_get.return_value = make_mock_response(json_data={"id": 0})

        result = fetch_user_profile("https://api.example.com", "1", "key")

        assert result == {"id": 0}

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_id_field_none_value_still_valid(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"id": None})

        result = fetch_user_profile("https://api.example.com", "1", "key")

        assert result == {"id": None}


class TestFetchUserProfileMalformedResponse:
    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_missing_id_field_raises(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"name": "Alice"})

        with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_empty_dict_response_raises(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={})

        with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_non_dict_json_response_list_raises_typeerror_or_value(self, mock_get):
        # If API returns a list instead of dict, "in" works differently
        mock_get.return_value = make_mock_response(json_data=["id", "name"])

        # "id" in ["id", "name"] is True, so it should NOT raise ValueError here
        result = fetch_user_profile("https://api.example.com", "1", "key")
        assert result == ["id", "name"]

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_non_dict_json_response_string_raises(self, mock_get):
        # "id" in "some string without id substring... wait id is substring"
        mock_get.return_value = make_mock_response(json_data="no such field here")

        with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_json_decode_error_propagates(self, mock_get):
        mock_get.return_value = make_mock_response(
            json_exception=requests.exceptions.JSONDecodeError("Expecting value", "", 0)
        )

        with pytest.raises(requests.exceptions.JSONDecodeError):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_non_dict_json_response_int_raises_typeerror(self, mock_get):
        # "in" on an int raises TypeError - this is a real behavior of the code
        mock_get.return_value = make_mock_response(json_data=12345)

        with pytest.raises(TypeError):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_none_json_response_raises_typeerror(self, mock_get):
        mock_get.return_value = make_mock_response(json_data=None)

        with pytest.raises(TypeError):
            fetch_user_profile("https://api.example.com", "1", "key")


class TestFetchUserProfileHttpErrors:
    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_http_error_status_propagates(self, mock_get):
        mock_get.return_value = make_mock_response(status_ok=False)

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_connection_error_propagates(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(requests.exceptions.ConnectionError):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_timeout_error_propagates(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(requests.exceptions.Timeout):
            fetch_user_profile("https://api.example.com", "1", "key")


class TestFetchUserProfileAdversarialInputs:
    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_user_id_with_path_traversal_passed_through(self, mock_get):
        # The function does not sanitize user_id; verify it is inserted verbatim
        # into the URL (highlighting a potential injection/path traversal risk).
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com", "../admin", "key")

        called_url = mock_get.call_args[0][0]
        assert called_url == "https://api.example.com/users/../admin"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_user_id_with_query_string_injection(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com", "1?admin=true", "key")

        called_url = mock_get.call_args[0][0]
        assert called_url == "https://api.example.com/users/1?admin=true"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_user_id_with_crlf_injection_characters(self, mock_get):
        malicious_id = "1\r\nX-Injected-Header: evil"
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com", malicious_id, "key")

        called_url = mock_get.call_args[0][0]
        assert malicious_id in called_url

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_api_key_with_special_characters_in_header(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com", "1", "key\nwith\nnewlines")

        headers = mock_get.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer key\nwith\nnewlines"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_base_url_with_trailing_slash_produces_double_slash(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com/", "1", "key")

        called_url = mock_get.call_args[0][0]
        assert called_url == "https://api.example.com//users/1"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_very_long_user_id_does_not_crash(self, mock_get):
        long_id = "a" * 10000
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        result = fetch_user_profile("https://api.example.com", long_id, "key")

        assert result == {"id": "1"}
        called_url = mock_get.call_args[0][0]
        assert long_id in called_url

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_user_id_with_unicode_characters(self, mock_get):
        unicode_id = "用户_😀"
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com", unicode_id, "key")

        called_url = mock_get.call_args[0][0]
        assert unicode_id in called_url

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_whitespace_only_user_id_is_considered_nonempty(self, mock_get):
        # Whitespace string is truthy and is a string, so validation passes.
        mock_get.return_value = make_mock_response(json_data={"id": "1"})

        result = fetch_user_profile("https://api.example.com", "   ", "key")

        assert result == {"id": "1"}
