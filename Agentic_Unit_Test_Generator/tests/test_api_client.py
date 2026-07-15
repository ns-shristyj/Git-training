import pytest
import requests
from unittest.mock import patch, MagicMock

from NIC_SecEng_Task.api_client import fetch_user_profile


def _make_mock_response(json_data=None, status_ok=True, json_side_effect=None):
    """Helper to build a mock requests.Response-like object."""
    mock_resp = MagicMock()
    if status_ok:
        mock_resp.raise_for_status.return_value = None
    else:
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("HTTP error")
    if json_side_effect is not None:
        mock_resp.json.side_effect = json_side_effect
    else:
        mock_resp.json.return_value = json_data
    return mock_resp


class TestFetchUserProfileValidation:
    def test_empty_string_user_id_raises_value_error(self):
        """Verify an empty string user_id is rejected before any network call."""
        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", "", "secret-key")

    def test_none_user_id_raises_value_error(self):
        """Verify None as user_id is rejected with a ValueError."""
        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", None, "secret-key")

    def test_integer_user_id_raises_value_error(self):
        """Verify non-string (int) user_id triggers type validation failure."""
        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", 12345, "secret-key")

    def test_list_user_id_raises_value_error(self):
        """Verify a list type user_id is rejected as invalid input type."""
        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", ["1"], "secret-key")

    def test_zero_int_user_id_raises_value_error(self):
        """Verify falsy non-string input (0) still raises ValueError due to type check."""
        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", 0, "secret-key")


class TestFetchUserProfileSuccess:
    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_successful_fetch_returns_parsed_json(self, mock_get):
        """Verify a well-formed response with 'id' field is returned as parsed dict."""
        mock_get.return_value = _make_mock_response(json_data={"id": "123", "name": "Alice"})

        result = fetch_user_profile("https://api.example.com", "123", "secret-key")

        assert result == {"id": "123", "name": "Alice"}

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_correct_url_constructed(self, mock_get):
        """Verify the request URL is correctly built from base_url and user_id."""
        mock_get.return_value = _make_mock_response(json_data={"id": "42"})

        fetch_user_profile("https://api.example.com", "42", "secret-key")

        called_url = mock_get.call_args[0][0]
        assert called_url == "https://api.example.com/users/42"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_authorization_header_set_correctly(self, mock_get):
        """Verify the Authorization header carries the Bearer token with the given api_key."""
        mock_get.return_value = _make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com", "1", "my-secret-token")

        headers = mock_get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer my-secret-token"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_timeout_is_set_to_five_seconds(self, mock_get):
        """Verify the outgoing request enforces a 5-second timeout to prevent hanging requests."""
        mock_get.return_value = _make_mock_response(json_data={"id": "1"})

        fetch_user_profile("https://api.example.com", "1", "key")

        assert mock_get.call_args.kwargs["timeout"] == 5


class TestFetchUserProfileErrorHandling:
    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_missing_id_field_raises_value_error(self, mock_get):
        """Verify a malformed API response lacking 'id' field raises ValueError, not silently accepted."""
        mock_get.return_value = _make_mock_response(json_data={"name": "Bob"})

        with pytest.raises(ValueError, match="Malformed API response"):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_http_error_propagates(self, mock_get):
        """Verify HTTP-level failures (e.g. 404/500) raise HTTPError and are not swallowed."""
        mock_get.return_value = _make_mock_response(status_ok=False)

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_invalid_json_response_propagates_error(self, mock_get):
        """Verify that an unparsable JSON body raises an error rather than returning corrupt data."""
        mock_get.return_value = _make_mock_response(
            json_side_effect=ValueError("Expecting value")
        )

        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_network_exception_propagates(self, mock_get):
        """Verify network-level exceptions (timeouts/connection errors) are not silently ignored."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        with pytest.raises(requests.exceptions.ConnectionError):
            fetch_user_profile("https://api.example.com", "1", "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_empty_json_dict_missing_id_raises(self, mock_get):
        """Verify an entirely empty JSON object response is treated as malformed."""
        mock_get.return_value = _make_mock_response(json_data={})

        with pytest.raises(ValueError, match="Malformed API response"):
            fetch_user_profile("https://api.example.com", "1", "key")


class TestFetchUserProfileSecurityBoundaries:
    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_path_traversal_in_user_id_is_rejected_or_contained(self, mock_get):
        """Verify path-traversal sequences in user_id are rejected, preventing escape from the /users/ endpoint."""
        mock_get.return_value = _make_mock_response(json_data={"id": "x"})
        malicious_user_id = "../../etc/passwd"

        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", malicious_user_id, "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_url_injection_via_user_id_is_rejected(self, mock_get):
        """Verify an attempt to inject a new host via user_id (URL injection) is rejected, not silently sent."""
        mock_get.return_value = _make_mock_response(json_data={"id": "x"})
        malicious_user_id = "@evil.com/steal"

        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", malicious_user_id, "key")

    def test_crlf_injection_in_api_key_is_blocked_by_header_validation(self):
        """Verify CRLF injection attempt in api_key is blocked by HTTP header validation, preventing header/request splitting."""
        malicious_api_key = "validtoken\r\nX-Injected-Header: evil"

        with pytest.raises(
            (requests.exceptions.InvalidHeader, ValueError, UnicodeEncodeError)
        ):
            fetch_user_profile("https://api.example.com", "1", malicious_api_key)

    def test_newline_only_in_api_key_is_blocked(self):
        """Verify a bare newline in api_key value is blocked by header validation to prevent header injection."""
        malicious_api_key = "token\ninjected: value"

        with pytest.raises(
            (requests.exceptions.InvalidHeader, ValueError, UnicodeEncodeError)
        ):
            fetch_user_profile("https://api.example.com", "1", malicious_api_key)

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_script_injection_string_user_id_treated_as_opaque_value(self, mock_get):
        """Verify script/HTML injection payload in user_id does not cause code execution and is rejected as invalid identifier."""
        mock_get.return_value = _make_mock_response(json_data={"id": "x"})
        malicious_user_id = "<script>alert(1)</script>"

        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", malicious_user_id, "key")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_sql_injection_like_user_id_rejected(self, mock_get):
        """Verify SQL-injection-style payload in user_id is rejected rather than forwarded verbatim."""
        mock_get.return_value = _make_mock_response(json_data={"id": "x"})
        malicious_user_id = "1' OR '1'='1"

        with pytest.raises(ValueError):
            fetch_user_profile("https://api.example.com", malicious_user_id, "key")
