# test_profile_service.py
import pytest
from NIC_SecEng_Task.user_management.profile_service import ProfileService


class FakeDBClient:
    """A minimal in-memory stand-in for the real database client dependency."""

    def __init__(self, users=None):
        self.users = users or {}
        self.saved_calls = []

    def get_user(self, user_id):
        return self.users.get(user_id)

    def save_user(self, user_id, profile):
        self.saved_calls.append((user_id, profile))
        self.users[user_id] = profile


@pytest.fixture
def premium_user_db():
    return FakeDBClient(
        users={
            "user1": {"tier": "premium", "display_name": "Alice", "is_deleted": False}
        }
    )


@pytest.fixture
def basic_user_db():
    return FakeDBClient(
        users={
            "user2": {"tier": "basic", "display_name": "Bob", "is_deleted": False}
        }
    )


@pytest.fixture
def deleted_user_db():
    return FakeDBClient(
        users={
            "user3": {"tier": "premium", "display_name": "Carl", "is_deleted": True}
        }
    )


def test_invalid_empty_user_id_raises_value_error(premium_user_db):
    """Empty string user_id must be rejected with ValueError before touching the DB."""
    service = ProfileService(premium_user_db)
    with pytest.raises(ValueError):
        service.process_user_data("", {"display_name": "X"})


def test_invalid_none_user_id_raises_value_error(premium_user_db):
    """None user_id must be rejected with ValueError."""
    service = ProfileService(premium_user_db)
    with pytest.raises(ValueError):
        service.process_user_data(None, {"display_name": "X"})


def test_invalid_non_dict_payload_raises_value_error(premium_user_db):
    """A non-dict payload (e.g. a list) must be rejected with ValueError."""
    service = ProfileService(premium_user_db)
    with pytest.raises(ValueError):
        service.process_user_data("user1", ["not", "a", "dict"])


def test_invalid_none_payload_raises_value_error(premium_user_db):
    """None payload must be rejected with ValueError."""
    service = ProfileService(premium_user_db)
    with pytest.raises(ValueError):
        service.process_user_data("user1", None)


def test_user_not_found_returns_error_status():
    """A user_id that does not exist in the DB must return a safe error response, not crash."""
    db = FakeDBClient(users={})
    service = ProfileService(db)
    result = service.process_user_data("ghost", {"display_name": "X"})
    assert result == {"status": "error", "message": "User not found"}


def test_whitespace_user_id_treated_as_valid_but_not_found():
    """A whitespace-only user_id passes the truthiness check but is safely handled as 'not found'."""
    db = FakeDBClient(users={})
    service = ProfileService(db)
    result = service.process_user_data("   ", {"display_name": "X"})
    assert result == {"status": "error", "message": "User not found"}


def test_premium_tier_allows_up_to_ten_custom_fields(premium_user_db):
    """Premium tier accounts may have exactly the max allowed 10 custom fields."""
    service = ProfileService(premium_user_db)
    custom_fields = {f"f{i}": i for i in range(10)}
    result = service.process_user_data("user1", {"custom_fields": custom_fields})
    assert result["status"] == "success"
    assert result["data"]["custom_fields"] == custom_fields


def test_premium_tier_exceeding_limit_returns_error(premium_user_db):
    """Premium tier accounts exceeding 10 custom fields must be rejected."""
    service = ProfileService(premium_user_db)
    custom_fields = {f"f{i}": i for i in range(11)}
    result = service.process_user_data("user1", {"custom_fields": custom_fields})
    assert result == {"status": "error", "message": "Exceeded custom fields limit for account tier"}


def test_basic_tier_allows_up_to_three_custom_fields(basic_user_db):
    """Non-premium tier accounts may have exactly the max allowed 3 custom fields."""
    service = ProfileService(basic_user_db)
    custom_fields = {"a": 1, "b": 2, "c": 3}
    result = service.process_user_data("user2", {"custom_fields": custom_fields})
    assert result["status"] == "success"
    assert result["data"]["custom_fields"] == custom_fields


def test_basic_tier_exceeding_limit_returns_error(basic_user_db):
    """Non-premium tier accounts exceeding 3 custom fields must be rejected."""
    service = ProfileService(basic_user_db)
    custom_fields = {"a": 1, "b": 2, "c": 3, "d": 4}
    result = service.process_user_data("user2", {"custom_fields": custom_fields})
    assert result == {"status": "error", "message": "Exceeded custom fields limit for account tier"}


def test_missing_tier_defaults_to_basic_limit():
    """A user record with no 'tier' key must be treated as non-premium (limit of 3)."""
    db = FakeDBClient(users={"u": {"display_name": "NoTier"}})
    service = ProfileService(db)
    custom_fields = {"a": 1, "b": 2, "c": 3, "d": 4}
    result = service.process_user_data("u", {"custom_fields": custom_fields})
    assert result["status"] == "error"


def test_deactivated_account_cannot_be_updated(deleted_user_db):
    """A soft-deleted (is_deleted=True) account must reject updates."""
    service = ProfileService(deleted_user_db)
    result = service.process_user_data("user3", {"display_name": "NewName"})
    assert result == {"status": "error", "message": "Cannot update a deactivated account"}


def test_custom_field_limit_check_happens_before_deletion_check():
    """Field-limit validation is evaluated before the soft-deletion check, per code order."""
    db = FakeDBClient(
        users={"u": {"tier": "basic", "is_deleted": True}}
    )
    service = ProfileService(db)
    custom_fields = {"a": 1, "b": 2, "c": 3, "d": 4}
    result = service.process_user_data("u", {"custom_fields": custom_fields})
    assert result["message"] == "Exceeded custom fields limit for account tier"


def test_successful_update_uses_provided_display_name(basic_user_db):
    """When display_name is supplied in the payload, it overrides the stored value."""
    service = ProfileService(basic_user_db)
    result = service.process_user_data("user2", {"display_name": "NewBob"})
    assert result["status"] == "success"
    assert result["data"]["display_name"] == "NewBob"


def test_successful_update_falls_back_to_existing_display_name(basic_user_db):
    """When display_name is absent from the payload, the existing stored name is preserved."""
    service = ProfileService(basic_user_db)
    result = service.process_user_data("user2", {})
    assert result["data"]["display_name"] == "Bob"


def test_custom_fields_default_to_empty_dict_when_absent(basic_user_db):
    """Omitting custom_fields entirely must default to an empty dict, not error out."""
    service = ProfileService(basic_user_db)
    result = service.process_user_data("user2", {})
    assert result["data"]["custom_fields"] == {}


def test_save_user_called_with_expected_profile(basic_user_db):
    """A successful update must persist exactly the sanitized profile fields via save_user."""
    service = ProfileService(basic_user_db)
    result = service.process_user_data("user2", {"display_name": "Persisted"})
    assert basic_user_db.saved_calls == [
        ("user2", {
            "display_name": "Persisted",
            "custom_fields": {},
            "last_modified": "2026-07-15",
        })
    ]
    assert result["status"] == "success"


def test_extra_unexpected_payload_keys_are_not_persisted(basic_user_db):
    """Malicious/extraneous payload keys (e.g. privilege-escalation attempts) must not leak into the saved profile."""
    service = ProfileService(basic_user_db)
    payload = {
        "display_name": "Bob",
        "is_admin": True,
        "tier": "premium",
        "__proto__": {"evil": "payload"},
    }
    result = service.process_user_data("user2", payload)
    assert "is_admin" not in result["data"]
    assert "tier" not in result["data"]
    assert "__proto__" not in result["data"]
    saved_id, saved_profile = basic_user_db.saved_calls[0]
    assert set(saved_profile.keys()) == {"display_name", "custom_fields", "last_modified"}


def test_sql_injection_style_user_id_is_treated_as_opaque_string():
    """A SQL-injection-style user_id string is passed through as-is and safely results in 'not found', not a crash."""
    db = FakeDBClient(users={})
    service = ProfileService(db)
    malicious_id = "'; DROP TABLE users; --"
    result = service.process_user_data(malicious_id, {"display_name": "X"})
    assert result == {"status": "error", "message": "User not found"}


def test_path_traversal_style_user_id_is_treated_as_opaque_string():
    """A path-traversal-style user_id is passed through as an opaque key, not interpreted as a filesystem path."""
    db = FakeDBClient(users={})
    service = ProfileService(db)
    malicious_id = "../../etc/passwd"
    result = service.process_user_data(malicious_id, {"display_name": "X"})
    assert result == {"status": "error", "message": "User not found"}


def test_non_iterable_custom_fields_raises_type_error_instead_of_silently_corrupting_data(basic_user_db):
    """An integer custom_fields value (unsupported type) triggers a loud TypeError rather than being silently accepted."""
    service = ProfileService(basic_user_db)
    with pytest.raises(TypeError):
        service.process_user_data("user2", {"custom_fields": 12345})


def test_string_custom_fields_length_is_evaluated_by_character_count(basic_user_db):
    """A string passed as custom_fields is measured by len(), so a long string is safely rejected instead of accepted as valid fields."""
    service = ProfileService(basic_user_db)
    long_string = "x" * 50
    result = service.process_user_data("user2", {"custom_fields": long_string})
    assert result == {"status": "error", "message": "Exceeded custom fields limit for account tier"}
