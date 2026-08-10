"""Unit tests for config.py's input builders. _agent4_input_builder in
particular now forwards several new fields (CIAM ops feedback: login
timing, multi-account ambiguity) beyond what it used to -- these tests lock
down that the wiring from Agent 2/Agent 3's raw output_fields dicts into
Agent 4's payload is correct and doesn't silently regress.
"""

from ciam_orchestrator.config import _agent4_input_builder
from ciam_orchestrator.schemas import JiraTicket


def make_ticket():
    return JiraTicket(issue_key="CIAM-1", summary="test", description="test desc")


def test_agent4_input_forwards_last_login_and_recent_changes():
    envelope = {"intent": "ACCESS_DENIED"}
    output_fields = {
        "account_payload": {
            "accounts": [{"account_status": "Customer", "active_tenant_count": 1}],
            "recent_changes": [
                {"field_name": "account_status", "changed_date": "2026-08-05T00:00:00+00:00"}
            ],
            "data_warnings": [],
        },
        "auth0_payload": {
            "user_found": True,
            "users": [
                {
                    "birthright": ["Community"],
                    "entitlements": [],
                    "last_sync": "2026-08-01T00:00:00+00:00",
                    "last_login": "2026-08-01T00:00:00+00:00",
                }
            ],
            "auth0_warnings": [],
        },
    }

    result = _agent4_input_builder(envelope, output_fields, make_ticket())

    assert result["last_login"] == "2026-08-01T00:00:00+00:00"
    assert result["recent_changes"] == [
        {"field_name": "account_status", "changed_date": "2026-08-05T00:00:00+00:00"}
    ]
    assert result["accounts_count"] == 1
    assert result["auth0_users_count"] == 1
    assert result["account_data_warnings"] == []
    assert result["auth0_warnings"] == []


def test_agent4_input_forwards_ambiguity_counts_and_warnings():
    envelope = {"intent": "ACCESS_DENIED"}
    output_fields = {
        "account_payload": {
            "accounts": [
                {"account_status": "Customer", "active_tenant_count": 1},
                {"account_status": "Partner", "active_tenant_count": 2},
            ],
            "data_warnings": ["multiple_accounts_found"],
        },
        "auth0_payload": {
            "user_found": True,
            "users": [
                {"birthright": [], "entitlements": []},
                {"birthright": [], "entitlements": []},
            ],
            "auth0_warnings": ["multiple_users_found"],
        },
    }

    result = _agent4_input_builder(envelope, output_fields, make_ticket())

    assert result["accounts_count"] == 2
    assert result["auth0_users_count"] == 2
    assert result["account_data_warnings"] == ["multiple_accounts_found"]
    assert result["auth0_warnings"] == ["multiple_users_found"]


def test_agent4_input_missing_upstream_data_defaults_safely():
    """No account_payload/auth0_payload at all (e.g. earlier agent errored)
    must not crash the input builder -- every new field must default to an
    empty/zero value, not raise."""
    result = _agent4_input_builder({"intent": "ACCESS_DENIED"}, {}, make_ticket())

    assert result["last_login"] is None
    assert result["recent_changes"] == []
    assert result["accounts_count"] == 0
    assert result["auth0_users_count"] == 0
    assert result["account_data_warnings"] == []
    assert result["auth0_warnings"] == []
