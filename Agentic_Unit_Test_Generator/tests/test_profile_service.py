# test_profile_service.py
import pytest

from NIC_SecEng_Task.user_management.profile_service import ProfileService


class FakeDB:
    """A minimal fake database client that mimics the expected interface
    of the external db_client dependency (get_user/save_user)."""

    def __init__(self, users=None):
        self.users = users or {}
        self.saved_calls = []

    def get_user(self, user_id):
        return self.users.get(user_id)

    def save_user(self, user_id, profile):
        self.saved_calls.append((user_id, profile))
        # simulate persistence
        if user_id in self.users:
            self.users[user_id].update(profile)


@pytest.fixture
def db():
    return FakeDB()


@pytest.fixture
def service(db):
    return ProfileService(db)


# ---------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------

def test_empty_user_id_raises_value_error(service):
    """Empty string user_id must raise ValueError due to falsy check."""
    with pytest.raises(ValueError):
        service.process_user_data("", {"display_name": "x"})


def test_none_user_id_raises_value_error(service):
    """None user_id must raise ValueError due to falsy check."""
    with pytest.raises(ValueError):
        service.process_user_data(None, {"display_name": "x"})


def test_payload_not_dict_raises_value_error(service):
    """Payload that is not a dict (e.g., list) must raise ValueError."""
    with pytest.raises(ValueError):
        service.process_user_data("user1", ["not", "a", "dict"])


def test_payload_string_raises_value_error(service):
    """Payload as a string must raise ValueError - type confusion guard."""
    with pytest.raises(ValueError):
        service.process_user_data("user1", "malicious_string_payload")


def test_payload_none_raises_value_error(service):
    """Payload as None must raise ValueError."""
    with pytest.raises(ValueError):
        service.process_user_data("user1", None)


# ---------------------------------------------------------------------
# User lookup tests
# ---------------------------------------------------------------------

def test_user_not_found_returns_error(service):
    """When db.get_user returns None, function must return an error result."""
    result = service.process_user_data("nonexistent", {"display_name": "Bob"})
    assert result == {"status": "error", "message": "User not found"}


def test_path_traversal_like_user_id_is_treated_as_plain_key(service, db):
    """A path-traversal-like user_id string is safely used only as a dict key, not a filesystem path."""
    db.users["../../etc/passwd"] = {"tier": "regular", "display_name": "x"}
    result = service.process_user_data("../../etc/passwd", {"display_name": "safe"})
    assert result["status"] == "success"
    assert result["data"]["display_name"] == "safe"


# ---------------------------------------------------------------------
# Tier-based custom_fields limit tests
# ---------------------------------------------------------------------

def test_premium_tier_allows_exactly_10_custom_fields(service, db):
    """Premium tier user with exactly 10 custom fields should succeed (boundary)."""
    db.users["u1"] = {"tier": "premium", "display_name": "Alice"}
    fields = {f"f{i}": i for i in range(10)}
    result = service.process_user_data("u1", {"custom_fields": fields})
    assert result["status"] == "success"
    assert result["data"]["custom_fields"] == fields


def test_premium_tier_exceeds_11_custom_fields_returns_error(service, db):
    """Premium tier user with 11 custom fields should be rejected (over limit)."""
    db.users["u1"] = {"tier": "premium", "display_name": "Alice"}
    fields = {f"f{i}": i for i in range(11)}
    result = service.process_user_data("u1", {"custom_fields": fields})
    assert result == {"status": "error", "message": "Exceeded custom fields limit for account tier"}


def test_regular_tier_allows_exactly_3_custom_fields(service, db):
    """Non-premium tier user with exactly 3 custom fields should succeed (boundary)."""
    db.users["u2"] = {"tier": "basic", "display_name": "Bob"}
    fields = {"a": 1, "b": 2, "c": 3}
    result = service.process_user_data("u2", {"custom_fields": fields})
    assert result["status"] == "success"
    assert result["data"]["custom_fields"] == fields


def test_regular_tier_exceeds_4_custom_fields_returns_error(service, db):
    """Non-premium tier user with 4 custom fields should be rejected (over limit)."""
    db.users["u2"] = {"tier": "basic", "display_name": "Bob"}
    fields = {"a": 1, "b": 2, "c": 3, "d": 4}
    result = service.process_user_data("u2", {"custom_fields": fields})
    assert result == {"status": "error", "message": "Exceeded custom fields limit for account tier"}


def test_missing_tier_defaults_to_regular_limit(service, db):
    """User dict missing 'tier' key defaults to the regular (3-field) limit."""
    db.users["u3"] = {"display_name": "Carl"}
    fields = {"a": 1, "b": 2, "c": 3, "d": 4}
    result = service.process_user_data("u3", {"custom_fields": fields})
    assert result["status"] == "error"


def test_custom_fields_missing_defaults_to_empty_dict(service, db):
    """Payload without custom_fields key defaults to empty dict and passes limit check."""
    db.users["u4"] = {"tier": "basic", "display_name": "Dana"}
    result = service.process_user_data("u4", {"display_name": "Dana2"})
    assert result["status"] == "success"
    assert result["data"]["custom_fields"] == {}


# ---------------------------------------------------------------------
# Soft deletion tests
# ---------------------------------------------------------------------

def test_deactivated_account_blocks_update(service, db):
    """Soft-deleted user (is_deleted=True) must not be updateable."""
    db.users["u5"] = {"tier": "basic", "is_deleted": True, "display_name": "Eve"}
    result = service.process_user_data("u5", {"display_name": "New Name"})
    assert result == {"status": "error", "message": "Cannot update a deactivated account"}


def test_deactivated_check_happens_after_field_limit_check(service, db):
    """Verify field-limit check (Branch 1) takes precedence over deletion check (Branch 2)."""
    db.users["u6"] = {"tier": "basic", "is_deleted": True, "display_name": "Frank"}
    fields = {"a": 1, "b": 2, "c": 3, "d": 4}
    result = service.process_user_data("u6", {"custom_fields": fields})
    assert result["message"] == "Exceeded custom fields limit for account tier"


def test_active_account_with_is_deleted_false_updates_successfully(service, db):
    """User explicitly marked is_deleted=False should update normally."""
    db.users["u7"] = {"tier": "basic", "is_deleted": False, "display_name": "Grace"}
    result = service.process_user_data("u7", {"display_name": "Grace2"})
    assert result["status"] == "success"


def test_missing_is_deleted_defaults_to_active(service, db):
    """User dict missing 'is_deleted' key defaults to active (False) and allows update."""
    db.users["u8"] = {"tier": "basic", "display_name": "Hank"}
    result = service.process_user_data("u8", {"display_name": "Hank2"})
    assert result["status"] == "success"


# ---------------------------------------------------------------------
# Update application tests
# ---------------------------------------------------------------------

def test_display_name_updated_when_provided(service, db):
    """Providing display_name in payload should override the existing value."""
    db.users["u9"] = {"tier": "basic", "display_name": "OldName"}
    result = service.process_user_data("u9", {"display_name": "NewName"})
    assert result["data"]["display_name"] == "NewName"


def test_display_name_defaults_to_existing_when_not_provided(service, db):
    """Omitting display_name in payload should preserve the existing user value."""
    db.users["u10"] = {"tier": "basic", "display_name": "KeepMe"}
    result = service.process_user_data("u10", {"custom_fields": {"a": 1}})
    assert result["data"]["display_name"] == "KeepMe"


def test_last_modified_field_is_set(service, db):
    """The last_modified field should always be set to the fixed date string."""
    db.users["u11"] = {"tier": "basic", "display_name": "Ivy"}
    result = service.process_user_data("u11", {})
    assert result["data"]["last_modified"] == "2026-07-15"


def test_save_user_called_with_correct_arguments(service, db):
    """db.save_user must be invoked with the correct user_id and updated profile."""
    db.users["u12"] = {"tier": "basic", "display_name": "Jack"}
    service.process_user_data("u12", {"display_name": "Jack2", "custom_fields": {"x": 1}})
    assert len(db.saved_calls) == 1
    saved_id, saved_profile = db.saved_calls[0]
    assert saved_id == "u12"
    assert saved_profile["display_name"] == "Jack2"
    assert saved_profile["custom_fields"] == {"x": 1}


def test_success_result_structure(service, db):
    """A successful update should return a dict with status 'success' and 'data' key."""
    db.users["u13"] = {"tier": "premium", "display_name": "Kim"}
    result = service.process_user_data("u13", {"display_name": "Kim2"})
    assert result["status"] == "success"
    assert set(result["data"].keys()) == {"display_name", "custom_fields", "last_modified"}


# ---------------------------------------------------------------------
# Adversarial / injection-style inputs treated as inert data
# ---------------------------------------------------------------------

def test_sql_injection_like_display_name_is_stored_as_literal_data(service, db):
    """A SQL-injection-like string in display_name is stored verbatim as inert data, not executed."""
    db.users["u14"] = {"tier": "basic", "display_name": "Original"}
    malicious = "'; DROP TABLE users; --"
    result = service.process_user_data("u14", {"display_name": malicious})
    assert result["status"] == "success"
    assert result["data"]["display_name"] == malicious


def test_script_injection_like_display_name_is_stored_as_literal_data(service, db):
    """An XSS-like script string in display_name is stored verbatim without execution."""
    db.users["u15"] = {"tier": "basic", "display_name": "Original"}
    malicious = "<script>alert('xss')</script>"
    result = service.process_user_data("u15", {"display_name": malicious})
    assert result["status"] == "success"
    assert result["data"]["display_name"] == malicious


def test_custom_fields_with_dunder_keys_handled_safely(service, db):
    """Custom field keys like '__proto__' are just regular dict keys in Python, no prototype pollution risk."""
    db.users["u16"] = {"tier": "basic", "display_name": "Leo"}
    fields = {"__proto__": "polluted", "constructor": "x"}
    result = service.process_user_data("u16", {"custom_fields": fields})
    assert result["status"] == "success"
    assert result["data"]["custom_fields"] == fields


def test_custom_fields_as_non_dict_iterable_is_counted_by_length(service, db):
    """If custom_fields is a list rather than a dict, len() still works and limit logic applies."""
    db.users["u17"] = {"tier": "basic", "display_name": "Mia"}
    fields = ["a", "b", "c", "d"]  # length 4, exceeds regular limit of 3
    result = service.process_user_data("u17", {"custom_fields": fields})
    assert result == {"status": "error", "message": "Exceeded custom fields limit for account tier"}


def test_custom_fields_as_string_counted_by_character_length(service, db):
    """If custom_fields is a string, len() counts characters, potentially triggering unexpected limit behavior."""
    db.users["u18"] = {"tier": "basic", "display_name": "Nina"}
    fields = "abcd"  # length 4 > regular limit of 3
    result = service.process_user_data("u18", {"custom_fields": fields})
    assert result["status"] == "error"


def test_extremely_long_display_name_does_not_crash(service, db):
    """A very large display_name string should be handled without crashing."""
    db.users["u19"] = {"tier": "basic", "display_name": "Old"}
    long_name = "A" * 100000
    result = service.process_user_data("u19", {"display_name": long_name})
    assert result["status"] == "success"
    assert result["data"]["display_name"] == long_name


def test_numeric_user_id_type_used_as_key(service, db):
    """A numeric (int) user_id, though not a string, should be used as-is for lookup without crashing."""
    db.users[123] = {"tier": "basic", "display_name": "Oscar"}
    result = service.process_user_data(123, {"display_name": "Oscar2"})
    assert result["status"] == "success"


def test_zero_as_user_id_raises_value_error(service):
    """Falsy but valid-looking user_id (0) should raise ValueError since it is falsy."""
    with pytest.raises(ValueError):
        service.process_user_data(0, {"display_name": "x"})


def test_empty_dict_payload_succeeds_with_defaults(service, db):
    """An empty payload dict should still succeed, using defaults from existing user data."""
    db.users["u20"] = {"tier": "basic", "display_name": "Paul"}
    result = service.process_user_data("u20", {})
    assert result["status"] == "success"
    assert result["data"]["display_name"] == "Paul"
    assert result["data"]["custom_fields"] == {}
