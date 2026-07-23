"""
Pytest test suite for the CIAM Database Agent (Agent 2) entrypoint module.

Because the module lives under a hyphenated path (`02-database-agent`) that is not a
valid Python package/import identifier, we load it directly from its file path.
"""

import importlib.util
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError


def _load_agent_module():
    """Loads agent.py from disk since its directory name contains a hyphen and a digit."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "CIAM-Support-Assistant", "agents", "02-database-agent", "agent.py"),
        os.path.join(here, "..", "CIAM-Support-Assistant", "agents", "02-database-agent", "agent.py"),
        os.path.join(here, "..", "..", "CIAM-Support-Assistant", "agents", "02-database-agent", "agent.py"),
        os.path.join(os.getcwd(), "CIAM-Support-Assistant", "agents", "02-database-agent", "agent.py"),
    ]
    for path in candidates:
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location("ciam_database_agent", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules["ciam_database_agent"] = module
            spec.loader.exec_module(module)
            return module
    raise ImportError(
        "Could not locate agent.py for CIAM database agent in any expected location: "
        + ", ".join(candidates)
    )


agent = _load_agent_module()


# ---------------------------------------------------------------------------
# assert_posture
# ---------------------------------------------------------------------------

def test_assert_posture_allows_whitelisted_action():
    """Verifies an allowed DynamoDB read action passes the posture check without raising."""
    assert agent.assert_posture("dynamodb:Query") is None


@pytest.mark.parametrize("action", ["dynamodb:PutItem", "s3:GetObject", ""])
def test_assert_posture_rejects_disallowed_actions(action):
    """Verifies non-whitelisted actions raise PostureViolationError (write/other-service denial)."""
    with pytest.raises(agent.PostureViolationError):
        agent.assert_posture(action)


# ---------------------------------------------------------------------------
# is_valid_email
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "email,expected",
    [
        ("user@example.com", True),
        ("", False),
        (None, False),
        ("noatsign", False),
    ],
)
def test_is_valid_email_various_inputs(email, expected):
    """Verifies email validation distinguishes valid emails from empty/None/malformed ones."""
    assert bool(agent.is_valid_email(email)) is expected


# ---------------------------------------------------------------------------
# calculate_freshness
# ---------------------------------------------------------------------------

def test_calculate_freshness_none_and_recent_timestamp():
    """Verifies calculate_freshness returns default for None and correct staleness for a recent time."""
    default_result = agent.calculate_freshness(None)
    assert default_result.last_synced_at is None
    assert default_result.is_stale is False

    recent = datetime.now(timezone.utc)
    result = agent.calculate_freshness(recent)
    assert result.is_stale is False
    assert result.age_hours is not None and result.age_hours >= 0


# ---------------------------------------------------------------------------
# get_account_by_email
# ---------------------------------------------------------------------------

def test_get_account_by_email_returns_parsed_accounts(monkeypatch):
    """Verifies a successful DynamoDB query is parsed into AccountRecord objects."""
    mock_client = MagicMock()
    mock_client.query.return_value = {
        "Items": [
            {
                "account_name": {"S": "Acme Corp"},
                "account_status": {"S": "Customer"},
                "customer_status": {"S": "Active"},
                "active_tenant_count": {"N": "3"},
                "tenant_url": {"S": "https://acme.example.com"},
                "sf_user_exists": {"BOOL": True},
                "sf_user_active": {"BOOL": True},
            }
        ]
    }
    monkeypatch.setattr(agent, "get_dynamodb_client", lambda: mock_client)

    accounts, error = agent.get_account_by_email("user@acme.com")

    assert error is None
    assert len(accounts) == 1
    assert accounts[0].account_name == "Acme Corp"
    assert accounts[0].active_tenant_count == 3


def test_get_account_by_email_handles_client_error(monkeypatch):
    """Verifies a DynamoDB ClientError is caught and surfaced as a safe error string, not raised."""
    mock_client = MagicMock()
    mock_client.query.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
        "Query",
    )
    monkeypatch.setattr(agent, "get_dynamodb_client", lambda: mock_client)

    accounts, error = agent.get_account_by_email("user@acme.com")

    assert accounts is None
    assert error == "dynamodb_error: ResourceNotFoundException"


def test_get_account_by_email_treats_injection_like_email_as_plain_value(monkeypatch):
    """Verifies a malicious-looking email is passed only as a parameterized value, not query-injected."""
    mock_client = MagicMock()
    mock_client.query.return_value = {"Items": []}
    monkeypatch.setattr(agent, "get_dynamodb_client", lambda: mock_client)

    malicious_email = "attacker' OR '1'='1"
    accounts, error = agent.get_account_by_email(malicious_email)

    assert accounts is None
    assert error is None
    call_kwargs = mock_client.query.call_args.kwargs
    assert call_kwargs["ExpressionAttributeValues"][":email"]["S"] == malicious_email
    assert "OR" not in call_kwargs["KeyConditionExpression"]


# ---------------------------------------------------------------------------
# fetch_account (entrypoint)
# ---------------------------------------------------------------------------

def test_fetch_account_happy_path_returns_account_payload(monkeypatch):
    """Verifies fetch_account returns a populated AccountPayload dict when an account is found."""
    account = agent.AccountRecord(
        account_name="Acme Corp",
        account_status="Customer",
        customer_status="Active",
        active_tenant_count=1,
        tenant_url=None,
        sf_user_exists=True,
        sf_user_active=True,
    )
    monkeypatch.setattr(agent, "get_account_by_email", lambda email: ([account], None))
    monkeypatch.setattr(agent, "get_account_history", lambda name: ([], None))

    result = agent.fetch_account({"email": "USER@Example.com "})

    assert result["account_found"] is True
    assert result["error"] is None
    assert result["accounts"][0]["account_name"] == "Acme Corp"


def test_fetch_account_invalid_email_returns_error_without_querying(monkeypatch):
    """Verifies fetch_account rejects invalid/missing email input before any DynamoDB call."""
    mock_query = MagicMock()
    monkeypatch.setattr(agent, "get_account_by_email", mock_query)

    result = agent.fetch_account({"email": "not-an-email"})

    assert result["account_found"] is False
    assert result["error"] == "invalid_email_input"
    mock_query.assert_not_called()


def test_fetch_account_sanitizes_non_string_and_injection_payloads(monkeypatch):
    """Verifies non-string/malicious payload fields are safely coerced instead of crashing or leaking."""
    mock_query = MagicMock()
    monkeypatch.setattr(agent, "get_account_by_email", mock_query)

    # non-string email/account_name should be treated as empty strings, not raise TypeError
    result = agent.fetch_account({"email": 12345, "account_name": {"$ne": None}})

    assert result["account_found"] is False
    assert result["error"] == "invalid_email_input"
    mock_query.assert_not_called()
