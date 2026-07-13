import pytest
import requests
from unittest.mock import Mock, patch
from NIC_SecEng_Task.api_client import fetch_user_profile


class TestFetchUserProfile:
    """Test suite for fetch_user_profile function."""

    def test_happy_path_valid_user_profile(self):
        """Sanity check: fetch_user_profile returns parsed JSON with valid inputs."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123", "name": "Alice"}
        
        with patch("requests.get", return_value=mock_response):
            result = fetch_user_profile("https://api.example.com", "user123", "secret_key")
        
        assert result == {"id": "user123", "name": "Alice"}

    def test_user_id_none_raises_value_error(self):
        """Type confusion: None user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("https://api.example.com", None, "secret_key")

    def test_user_id_empty_string_raises_value_error(self):
        """Boundary: empty string user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("https://api.example.com", "", "secret_key")

    def test_user_id_not_string_raises_value_error(self):
        """Type confusion: integer user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("https://api.example.com", 12345, "secret_key")

    def test_user_id_boolean_raises_value_error(self):
        """Type confusion: boolean user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("https://api.example.com", True, "secret_key")

    def test_malformed_response_missing_id_field(self):
        """Exception safety: response without 'id' field raises ValueError."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "Alice", "email": "alice@example.com"}
        
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
                fetch_user_profile("https://api.example.com", "user123", "secret_key")

    def test_http_error_propagates(self):
        """Exception safety: HTTP error status raises HTTPError."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(requests.exceptions.HTTPError):
                fetch_user_profile("https://api.example.com", "user123", "secret_key")

    def test_path_traversal_in_user_id(self):
        """Malicious input: path traversal attempt in user_id is safely encoded in URL."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "../../../etc/passwd"}
        
        with patch("requests.get", return_value=mock_response) as mock_get:
            result = fetch_user_profile("https://api.example.com", "../../../etc/passwd", "secret_key")
        
        # Verify the user_id is passed as part of the URL path, not interpreted as traversal
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "../../../etc/passwd" in call_args[0][0]
        assert result == {"id": "../../../etc/passwd"}

    def test_sql_injection_in_user_id(self):
        """Malicious input: SQL injection fragment in user_id is safely passed."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "' OR 1=1--"}
        
        with patch("requests.get", return_value=mock_response) as mock_get:
            result = fetch_user_profile("https://api.example.com", "' OR 1=1--", "secret_key")
        
        # Verify the injection string is passed as URL parameter, not executed
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "' OR 1=1--" in call_args[0][0]
        assert result == {"id": "' OR 1=1--"}

    def test_shell_metacharacters_in_user_id(self):
        """Malicious input: shell metacharacters in user_id are safely passed."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "$(rm -rf /)"}
        
        with patch("requests.get", return_value=mock_response) as mock_get:
            result = fetch_user_profile("https://api.example.com", "$(rm -rf /)", "secret_key")
        
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "$(rm -rf /)" in call_args[0][0]
        assert result == {"id": "$(rm -rf /)"}

    def test_null_byte_in_user_id(self):
        """Malicious input: null byte in user_id is safely passed."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user\x00admin"}
        
        with patch("requests.get", return_value=mock_response) as mock_get:
            result = fetch_user_profile("https://api.example.com", "user\x00admin", "secret_key")
        
        mock_get.assert_called_once()
        assert result == {"id": "user\x00admin"}

    def test_oversized_user_id(self):
        """Malicious input: extremely long user_id is passed to requests."""
        oversized_id = "x" * 50000
        mock_response = Mock()
        mock_response.json.return_value = {"id": oversized_id}
        
        with patch("requests.get", return_value=mock_response) as mock_get:
            result = fetch_user_profile("https://api.example.com", oversized_id, "secret_key")
        
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert oversized_id in call_args[0][0]
        assert result == {"id": oversized_id}

    def test_unicode_rtl_override_in_user_id(self):
        """Unicode edge case: right-to-left override character in user_id."""
        rtl_id = "user\u202emalicious"
        mock_response = Mock()
        mock_response.json.return_value = {"id": rtl_id}
        
        with patch("requests.get", return_value=mock_response) as mock_get:
            result = fetch_user_profile("https://api.example.com", rtl_id, "secret_key")
        
        mock_get.assert_called_once()
        assert result == {"id": rtl_id}

    def test_zero_width_character_in_user_id(self):
        """Unicode edge case: zero-width character in user_id."""
        zwj_id = "user\u200bname"
        mock_response = Mock()
        mock_response.json.return_value = {"id": zwj_id}
        
        with patch("requests.get", return_value=mock_response) as mock_get:
            result = fetch_user_profile("https://api.example.com", zwj_id, "secret_key")
        
        mock_get.assert_called_once()
        assert result == {"id": zwj_id}

    def test_authorization_header_includes_api_key(self):
        """Verify Authorization header is correctly set with provided api_key."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123"}
        
        with patch("requests.get", return_value=mock_response) as mock_get:
            fetch_user_profile("https://api.example.com", "user123", "my_secret_key")
        
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer my_secret_key"

    def test_timeout_is_set_to_five_seconds(self):
        """Verify timeout parameter is set to 5 seconds."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123"}
        
        with patch("requests.get", return_value=mock_response) as mock_get:
            fetch_user_profile("https://api.example.com", "user123", "api_key")
        
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["timeout"] == 5

    def test_response_json_decode_error(self):
        """Exception safety: invalid JSON response raises JSONDecodeError."""
        mock_response = Mock()
        mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Invalid JSON", "", 0)
        
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(requests.exceptions.JSONDecodeError):
                fetch_user_profile("https://api.example.com", "user123", "secret_key")

    def test_response_with_id_field_present_returns_data(self):
        """Verify response with 'id' field is returned successfully."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "123", "extra": "data"}
        
        with patch("requests.get", return_value=mock_response):
            result = fetch_user_profile("https://api.example.com", "user123", "secret_key")
        
        assert "id" in result
        assert result["id"] == "123"
