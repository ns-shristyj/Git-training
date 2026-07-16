# test_profile_service.py
import pytest

from NIC_SecEng_Task.user_management.profile_service import ProfileService


class FakeDBClient:
    """A simple in-memory fake for the database client dependency (no mocking library used)."""

    def __init__(self, users=None):
        self.users = users or {}
        self.saved = {}

    def get_user(self, user_id):
        return self.users.get(user_id)

    def save_user(self, user_id, profile):
        self.saved[user_id] = profile


@pytest.fixture
def premium_user_db():
    return FakeDBClient(
        users={
            "u1": {"tier": "premium", "display_name": "Alice", "is_deleted": False}
        }
    )


@pytest.fixture
def free_user_db():
    return FakeDBClient(
        users={
            "u2": {"tier": "free", "display_name": "Bob", "is_deleted": False}
        }
    )


@pytest.fixture
def deleted_user_db():
    return FakeDBClient(
        users={
            "u3": {"tier": "premium", "display_name": "Carl", "is_deleted": True}
        }
    )


def test_empty_user_id_raises_value_error():
    """Empty user_id must be rejected with ValueError to prevent unauthenticated processing."""
    service = ProfileService(FakeDBClient())
    with pytest.raises(ValueError):
        service.process_user_data("", {"display_name": "x"})


def test_none_user_id_raises_value_error():
    """None as user_id must be rejected with ValueError."""
    service = ProfileService(FakeDBClient())
    with pytest.raises(ValueError):
        service.process_user_data(None, {"display_name": "x"})


def test_non_dict_payload_raises_value_error():
    """Passing a non-dict payload (e.g., list) must raise ValueError, preventing type confusion."""
    service = ProfileService(FakeDBClient())
    with pytest.raises(ValueError):
        service.process_user_data("u1", ["not", "a", "dict"])


def test_none_payload_raises_value_error():
    """Passing None as payload must raise ValueError."""
    service = ProfileService(FakeDBClient())
    with pytest.raises(ValueError):
        service.process_user_data("u1", None)


def test_user_not_found_returns_error(premium_user_db):
    """Requesting a nonexistent user_id returns a structured error, not an exception."""
    service = ProfileService(premium_user_db)
    result = service.process_user_data("does_not_exist", {"display_name": "x"})
    assert result == {"status": "error", "message": "User not found"}


def test_premium_tier_allows_exactly_10_custom_fields(premium_user_db):
    """Premium tier boundary: exactly 10 custom fields should succeed."""
    service = ProfileService(premium_user_db)
    fields = {f"f{i}": i for i in range(10)}
    result = service.process_user_data("u1", {"custom_fields": fields})
    assert result["status"] == "success"
    assert result["data"]["custom_fields"] == fields


def test_premium_tier_rejects_11_custom_fields(premium_user_db):
    """Premium tier boundary: 11 custom fields exceeds the limit and must be rejected."""
    service = ProfileService(premium_user_db)
    fields = {f"f{i}": i for i in range(11)}
    result = service.process_user_data("u1", {"custom_fields": fields})
    assert result == {
        "status": "error",
        "message": "Exceeded custom fields limit for account tier",
    }


def test_free_tier_allows_exactly_3_custom_fields(free_user_db):
    """Free tier boundary: exactly 3 custom fields should succeed."""
    service = ProfileService(free_user_db)
    fields = {"a": 1, "b": 2, "c": 3}
    result = service.process_user_data("u2", {"custom_fields": fields})
    assert result["status"] == "success"
    assert result["data"]["custom_fields"] == fields


def test_free_tier_rejects_4_custom_fields(free_user_db):
    """Free tier boundary: 4 custom fields exceeds the limit and must be rejected."""
    service = ProfileService(free_user_db)
    fields = {"a": 1, "b": 2, "c": 3, "d": 4}
    result = service.process_user_data("u2", {"custom_fields": fields})
    assert result == {
        "status": "error",
        "message": "Exceeded custom fields limit for account tier",
    }


def test_missing_tier_defaults_to_non_premium_limit():
    """A user record missing the 'tier' key must default to the stricter non-premium limit of 3."""
    db = FakeDBClient(users={"u4": {"display_name": "NoTier", "is_deleted": False}})
    service = ProfileService(db)
    fields = {"a": 1, "b": 2, "c": 3, "d": 4}
    result = service.process_user_data("u4", {"custom_fields": fields})
    assert result["status"] == "error"


def test_deactivated_account_blocks_update_even_for_premium(deleted_user_db):
    """A soft-deleted (is_deleted=True) account must reject updates regardless of tier."""
    service = ProfileService(deleted_user_db)
    result = service.process_user_data("u3", {"display_name": "New Name"})
    assert result == {
        "status": "error",
        "message": "Cannot update a deactivated account",
    }


def test_deactivated_check_happens_after_field_limit_check(deleted_user_db):
    """Field-limit violation on a deactivated account still reports the field-limit error (branch order)."""
    service = ProfileService(deleted_user_db)
    fields = {f"f{i}": i for i in range(11)}
    result = service.process_user_data("u3", {"custom_fields": fields})
    assert result["message"] == "Exceeded custom fields limit for account tier"


def test_display_name_preserved_when_not_provided(premium_user_db):
    """If display_name is omitted from payload, the existing user's display_name must be retained."""
    service = ProfileService(premium_user_db)
    result = service.process_user_data("u1", {"custom_fields": {}})
    assert result["data"]["display_name"] == "Alice"


def test_display_name_updated_when_provided(premium_user_db):
    """A provided display_name in the payload must overwrite the existing value."""
    service = ProfileService(premium_user_db)
    result = service.process_user_data("u1", {"display_name": "Alicia"})
    assert result["data"]["display_name"] == "Alicia"


def test_custom_fields_defaults_to_empty_dict_when_absent(premium_user_db):
    """If custom_fields is not supplied, it must default to an empty dict rather than raise or leak data."""
    service = ProfileService(premium_user_db)
    result = service.process_user_data("u1", {"display_name": "Alicia"})
    assert result["data"]["custom_fields"] == {}


def test_save_user_called_with_expected_profile(premium_user_db):
    """On success, db.save_user must be invoked with exactly the sanitized updated profile fields."""
    service = ProfileService(premium_user_db)
    result = service.process_user_data("u1", {"display_name": "Alicia", "custom_fields": {"x": 1}})
    saved = premium_user_db.saved.get("u1")
    assert saved is not None
    assert saved == result["data"]
    assert set(saved.keys()) == {"display_name", "custom_fields", "last_modified"}


def test_extra_payload_keys_are_not_mass_assigned(premium_user_db):
    """Unexpected extra keys in payload (mass-assignment attempt) must not appear in the saved profile."""
    service = ProfileService(premium_user_db)
    malicious_payload = {
        "display_name": "Alicia",
        "custom_fields": {},
        "tier": "premium_hacked",
        "is_deleted": True,
        "__proto__": "evil",
    }
    result = service.process_user_data("u1", malicious_payload)
    assert "tier" not in result["data"]
    assert "is_deleted" not in result["data"]
    assert "__proto__" not in result["data"]
    assert set(result["data"].keys()) == {"display_name", "custom_fields", "last_modified"}


def test_custom_fields_with_injection_like_content_stored_as_plain_data(premium_user_db):
    """Custom field values resembling SQL/script injection are stored as plain data, not executed or altered."""
    service = ProfileService(premium_user_db)
    payload = {
        "custom_fields": {
            "note": "'; DROP TABLE users; --",
            "xss": "<script>alert(1)</script>",
        }
    }
    result = service.process_user_data("u1", payload)
    assert result["status"] == "success"
    assert result["data"]["custom_fields"]["note"] == "'; DROP TABLE users; --"
    assert result["data"]["custom_fields"]["xss"] == "<script>alert(1)</script>"


def test_path_traversal_like_user_id_is_passed_through_unmodified_not_executed():
    """A path-traversal-like user_id string is treated as an opaque lookup key, not resolved as a path."""
    db = FakeDBClient(users={})
    service = ProfileService(db)
    result = service.process_user_data("../../etc/passwd", {"display_name": "x"})
    assert result == {"status": "error", "message": "User not found"}


def test_user_id_non_string_but_truthy_is_processed(premium_user_db):
    """A non-string but truthy user_id (e.g., integer) bypasses the falsy check and is used as a lookup key."""
    db = FakeDBClient(users={1: {"tier": "premium", "display_name": "Num", "is_deleted": False}})
    service = ProfileService(db)
    result = service.process_user_data(1, {"display_name": "Num2"})
    assert result["status"] == "success"


def test_empty_dict_payload_returns_success_with_defaults(free_user_db):
    """An empty payload dict is valid input and should return success using existing user defaults."""
    service = ProfileService(free_user_db)
    result = service.process_user_data("u2", {})
    assert result["status"] == "success"
    assert result["data"]["display_name"] == "Bob"
    assert result["data"]["custom_fields"] == {}
