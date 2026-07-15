# test_profile_service.py
import pytest
from NIC_SecEng_Task.user_management.profile_service import ProfileService


class FakeDBClient:
    """A minimal fake DB client to stand in for the external database dependency."""

    def __init__(self, users=None):
        self.users = users or {}
        self.saved_calls = []

    def get_user(self, user_id):
        return self.users.get(user_id)

    def save_user(self, user_id, profile):
        self.saved_calls.append((user_id, profile))


@pytest.fixture
def db():
    return FakeDBClient()


@pytest.fixture
def service(db):
    return ProfileService(db)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_empty_user_id_raises_value_error(service):
    """Empty user_id must raise ValueError instead of proceeding with invalid input."""
    with pytest.raises(ValueError):
        service.process_user_data("", {"display_name": "Bob"})


def test_none_user_id_raises_value_error(service):
    """None as user_id must raise ValueError instead of silently proceeding."""
    with pytest.raises(ValueError):
        service.process_user_data(None, {"display_name": "Bob"})


def test_non_dict_payload_raises_value_error(service):
    """Payload that is not a dict (e.g. a string) must raise ValueError."""
    with pytest.raises(ValueError):
        service.process_user_data("user1", "not-a-dict")


def test_list_payload_raises_value_error(service):
    """Payload that is a list rather than a dict must raise ValueError."""
    with pytest.raises(ValueError):
        service.process_user_data("user1", ["display_name", "Bob"])


# ---------------------------------------------------------------------------
# User existence handling
# ---------------------------------------------------------------------------

def test_user_not_found_returns_error(service, db):
    """Requesting a nonexistent user_id returns a graceful error, no crash."""
    result = service.process_user_data("ghost", {"display_name": "X"})
    assert result == {"status": "error", "message": "User not found"}
    assert db.saved_calls == []


def test_path_traversal_like_user_id_is_treated_as_opaque_lookup_key(db, service):
    """A path-traversal-like user_id string is safely used only as a lookup key, no crash or bypass."""
    result = service.process_user_data("../../etc/passwd", {"display_name": "X"})
    assert result == {"status": "error", "message": "User not found"}
    assert db.saved_calls == []


# ---------------------------------------------------------------------------
# Tier-based custom fields limit
# ---------------------------------------------------------------------------

def test_premium_user_within_limit_succeeds(db, service):
    """Premium tier user with custom_fields within the 10-field limit succeeds."""
    db.users["u1"] = {"tier": "premium", "display_name": "Alice"}
    payload = {"custom_fields": {f"f{i}": i for i in range(10)}}
    result = service.process_user_data("u1", payload)
    assert result["status"] == "success"
    assert len(result["data"]["custom_fields"]) == 10


def test_premium_user_exceeding_limit_fails(db, service):
    """Premium tier user with more than 10 custom fields is rejected."""
    db.users["u1"] = {"tier": "premium", "display_name": "Alice"}
    payload = {"custom_fields": {f"f{i}": i for i in range(11)}}
    result = service.process_user_data("u1", payload)
    assert result == {"status": "error", "message": "Exceeded custom fields limit for account tier"}
    assert db.saved_calls == []


def test_non_premium_user_within_limit_succeeds(db, service):
    """Non-premium (default) tier user with custom_fields within the 3-field limit succeeds."""
    db.users["u2"] = {"tier": "basic", "display_name": "Bob"}
    payload = {"custom_fields": {"a": 1, "b": 2, "c": 3}}
    result = service.process_user_data("u2", payload)
    assert result["status"] == "success"
    assert len(result["data"]["custom_fields"]) == 3


def test_non_premium_user_exceeding_limit_fails(db, service):
    """Non-premium tier user exceeding the 3-field custom_fields limit is rejected."""
    db.users["u2"] = {"tier": "basic", "display_name": "Bob"}
    payload = {"custom_fields": {"a": 1, "b": 2, "c": 3, "d": 4}}
    result = service.process_user_data("u2", payload)
    assert result == {"status": "error", "message": "Exceeded custom fields limit for account tier"}
    assert db.saved_calls == []


def test_missing_tier_defaults_to_non_premium_limit(db, service):
    """User record without a 'tier' key defaults to the stricter 3-field limit."""
    db.users["u3"] = {"display_name": "Carol"}
    payload = {"custom_fields": {"a": 1, "b": 2, "c": 3, "d": 4}}
    result = service.process_user_data("u3", payload)
    assert result["status"] == "error"


def test_missing_custom_fields_defaults_to_empty_and_succeeds(db, service):
    """Payload without a 'custom_fields' key defaults to empty dict and update succeeds."""
    db.users["u4"] = {"tier": "basic", "display_name": "Dave"}
    result = service.process_user_data("u4", {"display_name": "David"})
    assert result["status"] == "success"
    assert result["data"]["custom_fields"] == {}


# ---------------------------------------------------------------------------
# Soft deletion check
# ---------------------------------------------------------------------------

def test_deactivated_account_cannot_be_updated(db, service):
    """Soft-deleted (is_deleted=True) accounts must not be updated, even with valid payload."""
    db.users["u5"] = {"tier": "basic", "is_deleted": True, "display_name": "Eve"}
    result = service.process_user_data("u5", {"display_name": "New Eve"})
    assert result == {"status": "error", "message": "Cannot update a deactivated account"}
    assert db.saved_calls == []


def test_deactivated_check_happens_after_field_limit_check(db, service):
    """Custom field limit validation occurs before the soft-deletion check (documents check ordering)."""
    db.users["u6"] = {"tier": "basic", "is_deleted": True, "display_name": "Frank"}
    payload = {"custom_fields": {"a": 1, "b": 2, "c": 3, "d": 4}}  # exceeds non-premium limit
    result = service.process_user_data("u6", payload)
    # Field-limit error should surface first, not the deactivation error.
    assert result == {"status": "error", "message": "Exceeded custom fields limit for account tier"}


def test_not_deleted_field_absent_defaults_to_active(db, service):
    """A user record without an 'is_deleted' key is treated as active and can be updated."""
    db.users["u7"] = {"tier": "basic", "display_name": "Grace"}
    result = service.process_user_data("u7", {"display_name": "Grace2"})
    assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Field application and persistence
# ---------------------------------------------------------------------------

def test_display_name_defaults_to_existing_value_when_not_supplied(db, service):
    """If payload omits 'display_name', the existing user display_name is preserved."""
    db.users["u8"] = {"tier": "basic", "display_name": "Henry"}
    result = service.process_user_data("u8", {"custom_fields": {}})
    assert result["data"]["display_name"] == "Henry"


def test_display_name_is_overridden_when_supplied(db, service):
    """If payload supplies 'display_name', it overrides the existing stored value."""
    db.users["u9"] = {"tier": "basic", "display_name": "Ian"}
    result = service.process_user_data("u9", {"display_name": "Ivan"})
    assert result["data"]["display_name"] == "Ivan"


def test_successful_update_persists_via_save_user(db, service):
    """A successful update must call save_user exactly once with the expected profile data."""
    db.users["u10"] = {"tier": "basic", "display_name": "Jack"}
    payload = {"display_name": "Jackson", "custom_fields": {"x": 1}}
    result = service.process_user_data("u10", payload)

    assert len(db.saved_calls) == 1
    saved_user_id, saved_profile = db.saved_calls[0]
    assert saved_user_id == "u10"
    assert saved_profile == result["data"]
    assert saved_profile["display_name"] == "Jackson"
    assert saved_profile["custom_fields"] == {"x": 1}
    assert saved_profile["last_modified"] == "2026-07-15"


def test_error_paths_never_call_save_user_for_missing_user(db, service):
    """When user is not found, save_user must never be invoked (no unintended persistence)."""
    service.process_user_data("nope", {"display_name": "X"})
    assert db.saved_calls == []


# ---------------------------------------------------------------------------
# Type confusion / boundary edge cases for custom_fields
# ---------------------------------------------------------------------------

def test_custom_fields_as_string_type_confusion_is_rejected():
    """custom_fields provided as a non-dict (string) type must be rejected, not silently accepted."""
    db = FakeDBClient(users={"u11": {"tier": "basic", "display_name": "Kim"}})
    service = ProfileService(db)
    payload = {"custom_fields": "ab"}  # len("ab") == 2, passes numeric check but is not a dict
    result = service.process_user_data("u11", payload)
    # A secure implementation should reject non-dict custom_fields rather than store them as-is.
    assert result["status"] == "error" or not isinstance(result.get("data", {}).get("custom_fields"), str)


def test_custom_fields_as_oversized_string_is_rejected_by_limit_check():
    """An oversized string passed as custom_fields is rejected via the length-based limit check."""
    db = FakeDBClient(users={"u12": {"tier": "basic", "display_name": "Leo"}})
    service = ProfileService(db)
    payload = {"custom_fields": "abcd"}  # length 4 > non-premium limit of 3
    result = service.process_user_data("u12", payload)
    assert result == {"status": "error", "message": "Exceeded custom fields limit for account tier"}


def test_custom_fields_exact_boundary_premium_limit(db, service):
    """Exactly at the premium boundary (10 fields) the update must succeed, not fail."""
    db.users["u13"] = {"tier": "premium", "display_name": "Mona"}
    payload = {"custom_fields": {f"k{i}": i for i in range(10)}}
    result = service.process_user_data("u13", payload)
    assert result["status"] == "success"


def test_custom_fields_exact_boundary_non_premium_limit(db, service):
    """Exactly at the non-premium boundary (3 fields) the update must succeed, not fail."""
    db.users["u14"] = {"tier": "basic", "display_name": "Nina"}
    payload = {"custom_fields": {"a": 1, "b": 2, "c": 3}}
    result = service.process_user_data("u14", payload)
    assert result["status"] == "success"
