import pytest
import requests
from unittest.mock import Mock, patch
from NIC_SecEng_Task.api_client import fetch_user_profile


class TestFetchUserProfileInputValidation:
    """Test input validation for fetch_user_profile."""

    def test_user_id_none_raises_value_error(self):
        """Test that None user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("http://example.com", None, "key123")

    def test_user_id_empty_string_raises_value_error(self):
        """Test that empty string user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("http://example.com", "", "key123")

    def test_user_id_not_string_raises_value_error(self):
        """Test that non-string user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("http://example.com", 123, "key123")

    def test_user_id_integer_raises_value_error(self):
        """Test that integer user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("http://example.com", 456, "key123")

    def test_user_id_list_raises_value_error(self):
        """Test that list user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("http://example.com", ["user1"], "key123")

    def test_user_id_dict_raises_value_error(self):
        """Test that dict user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("http://example.com", {"id": "user1"}, "key123")

    def test_user_id_boolean_raises_value_error(self):
        """Test that boolean user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fetch_user_profile("http://example.com", True, "key123")


class TestFetchUserProfileValidInput:
    """Test successful API calls with valid input."""

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_successful_fetch_with_valid_user_id(self, mock_get):
        """Test successful fetch with valid user_id."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123", "name": "John Doe"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "user123", "key123")

        assert result == {"id": "user123", "name": "John Doe"}
        mock_get.assert_called_once_with(
            "http://example.com/users/user123",
            headers={"Authorization": "Bearer key123"},
            timeout=5,
        )

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_fetch_with_numeric_string_user_id(self, mock_get):
        """Test fetch with numeric string user_id."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "456", "name": "Jane"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "456", "key123")

        assert result == {"id": "456", "name": "Jane"}

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_fetch_with_special_characters_in_user_id(self, mock_get):
        """Test fetch with special characters in user_id."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user-123_abc", "name": "Test"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "user-123_abc", "key123")

        assert result == {"id": "user-123_abc", "name": "Test"}

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_fetch_with_unicode_user_id(self, mock_get):
        """Test fetch with unicode characters in user_id."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "用户123", "name": "User"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "用户123", "key123")

        assert result == {"id": "用户123", "name": "User"}


class TestFetchUserProfileResponseHandling:
    """Test response parsing and error handling."""

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_missing_id_field_raises_value_error(self, mock_get):
        """Test that missing 'id' field in response raises ValueError."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "John Doe"}
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Malformed API response: missing 'id' field"):
            fetch_user_profile("http://example.com", "user123", "key123")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_response_with_id_field_and_extra_fields(self, mock_get):
        """Test response with id field and additional fields."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "user123",
            "name": "John",
            "email": "john@example.com",
            "age": 30,
        }
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "user123", "key123")

        assert result["id"] == "user123"
        assert result["name"] == "John"
        assert result["email"] == "john@example.com"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_response_with_null_id_field(self, mock_get):
        """Test response with null id field."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": None, "name": "John"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "user123", "key123")

        assert result["id"] is None

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_response_with_empty_string_id(self, mock_get):
        """Test response with empty string id field."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "", "name": "John"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "user123", "key123")

        assert result["id"] == ""

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_http_error_raises_exception(self, mock_get):
        """Test that HTTP errors are raised."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_user_profile("http://example.com", "user123", "key123")

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_json_decode_error_raises_exception(self, mock_get):
        """Test that JSON decode errors are raised."""
        mock_response = Mock()
        mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.JSONDecodeError):
            fetch_user_profile("http://example.com", "user123", "key123")


class TestFetchUserProfileURLConstruction:
    """Test URL construction and header handling."""

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_correct_url_construction(self, mock_get):
        """Test that URL is correctly constructed."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123"}
        mock_get.return_value = mock_response

        fetch_user_profile("http://api.example.com", "user123", "key123")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "http://api.example.com/users/user123"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_authorization_header_set_correctly(self, mock_get):
        """Test that Authorization header is set correctly."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123"}
        mock_get.return_value = mock_response

        fetch_user_profile("http://example.com", "user123", "myapikey")

        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer myapikey"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_timeout_set_to_five_seconds(self, mock_get):
        """Test that timeout is set to 5 seconds."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123"}
        mock_get.return_value = mock_response

        fetch_user_profile("http://example.com", "user123", "key123")

        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == 5

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_url_with_trailing_slash_in_base_url(self, mock_get):
        """Test URL construction with trailing slash in base_url."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123"}
        mock_get.return_value = mock_response

        fetch_user_profile("http://example.com/", "user123", "key123")

        call_args = mock_get.call_args
        assert call_args[0][0] == "http://example.com//users/user123"


class TestFetchUserProfileSecurityEdgeCases:
    """Test security-relevant edge cases."""

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_user_id_with_path_traversal_attempt(self, mock_get):
        """Test that path traversal-like user_id is passed through (URL encoding handled by requests)."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "../admin"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "../admin", "key123")

        assert result["id"] == "../admin"
        call_args = mock_get.call_args
        assert "../admin" in call_args[0][0]

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_user_id_with_url_encoded_characters(self, mock_get):
        """Test user_id with URL-encoded-like characters."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user%20name"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "user%20name", "key123")

        assert result["id"] == "user%20name"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_user_id_with_sql_injection_like_string(self, mock_get):
        """Test user_id with SQL injection-like string."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "'; DROP TABLE users; --"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "'; DROP TABLE users; --", "key123")

        assert result["id"] == "'; DROP TABLE users; --"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_user_id_with_very_long_string(self, mock_get):
        """Test user_id with very long string."""
        long_user_id = "a" * 10000
        mock_response = Mock()
        mock_response.json.return_value = {"id": long_user_id}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", long_user_id, "key123")

        assert result["id"] == long_user_id

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_api_key_with_special_characters(self, mock_get):
        """Test that api_key with special characters is passed correctly."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123"}
        mock_get.return_value = mock_response

        special_key = "key+with/special=chars"
        fetch_user_profile("http://example.com", "user123", special_key)

        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {special_key}"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_response_with_nested_structure(self, mock_get):
        """Test response with nested JSON structure."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "user123",
            "profile": {"nested": {"data": "value"}},
        }
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "user123", "key123")

        assert result["id"] == "user123"
        assert result["profile"]["nested"]["data"] == "value"


class TestFetchUserProfileBoundaryValues:
    """Test boundary values and edge cases."""

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_single_character_user_id(self, mock_get):
        """Test with single character user_id."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "a"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "a", "key123")

        assert result["id"] == "a"

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_whitespace_only_user_id_is_valid_string(self, mock_get):
        """Test that whitespace-only user_id is a valid non-empty string."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "   "}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "   ", "key123")

        assert result["id"] == "   "

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_response_with_only_id_field(self, mock_get):
        """Test response containing only the id field."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123"}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "user123", "key123")

        assert result == {"id": "user123"}

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_response_with_numeric_id_value(self, mock_get):
        """Test response with numeric id value."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": 12345}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "user123", "key123")

        assert result["id"] == 12345

    @patch("NIC_SecEng_Task.api_client.requests.get")
    def test_response_with_boolean_id_value(self, mock_get):
        """Test response with boolean id value."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": True}
        mock_get.return_value = mock_response

        result = fetch_user_profile("http://example.com", "user123", "key123")

        assert result["id"] is True
