"""Unit tests for Agent 3 (Auth0 Agent), mapped to SPEC-CIAM-0003 §9
acceptance criteria. All Auth0 HTTP calls and Secrets Manager calls are
mocked -- there is no real Auth0 M2M app/credentials set up yet, so these
tests validate the agent's logic in isolation, not live integration.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

import agent as agent_module
from agent import (
    fetch_auth0_data,
    get_connection_priority,
    describe_login_type,
    evaluate_sync_staleness,
    derive_failed_login_stats,
    assert_posture,
    assert_http_posture,
    PostureViolationError,
    TokenAcquisitionError,
    LoginEvent,
)


@pytest.fixture(autouse=True)
def reset_token_cache():
    """Prevent token caching from leaking between tests."""
    agent_module._cached_token = None
    agent_module._cached_token_expires_at = None
    yield
    agent_module._cached_token = None
    agent_module._cached_token_expires_at = None


def mock_secret_response():
    return {"SecretString": json.dumps({"client_id": "test_id", "client_secret": "test_secret"})}


def mock_token_response(status_code=200, expires_in=86400):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"access_token": "fake_token", "expires_in": expires_in}
    resp.raise_for_status = MagicMock()
    return resp


def mock_users_response(status_code, body):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def make_auth0_user(email, connection, birthright=None, last_sync=None, user_id=None):
    return {
        "user_id": user_id or f"NetskopeID|{email.split('@')[0]}",
        "email": email,
        "identities": [{"connection": connection}],
        "created_at": "2026-01-01T00:00:00.000Z",
        "last_login": "2026-07-01T00:00:00.000Z",
        "logins_count": 5,
        "app_metadata": {
            "birthright": birthright or [],
            "entitlements": [],
            "last_sync": last_sync,
            "last_daily_sync": last_sync,
        },
    }


# AC-1: Known email returns full user record with birthright populated
def test_ac1_known_email_returns_full_record():
    fresh_sync = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    with patch("agent.get_secrets_client") as mock_sm, patch("agent.requests.post") as mock_post, \
         patch("agent.requests.get") as mock_get:
        mock_sm.return_value.get_secret_value.return_value = mock_secret_response()
        mock_post.return_value = mock_token_response()
        mock_get.side_effect = [
            mock_users_response(200, [make_auth0_user(
                "alice@example.com", "NetskopeID",
                birthright=["Support", "Community", "Academy"], last_sync=fresh_sync,
            )]),
            mock_users_response(200, []),  # login history
        ]

        result = fetch_auth0_data({"email": "alice@example.com"})

    assert result["user_found"] is True
    assert len(result["users"]) == 1
    assert result["users"][0]["birthright"] == ["Support", "Community", "Academy"]
    assert result["sync_stale"] is False
    assert result["error"] is None
    assert "no_metadata" not in result["auth0_warnings"]


# AC-2: Email not found returns user_found false with no error
def test_ac2_email_not_found():
    with patch("agent.get_secrets_client") as mock_sm, patch("agent.requests.post") as mock_post, \
         patch("agent.requests.get") as mock_get:
        mock_sm.return_value.get_secret_value.return_value = mock_secret_response()
        mock_post.return_value = mock_token_response()
        mock_get.return_value = mock_users_response(200, [])

        result = fetch_auth0_data({"email": "unknown@example.com"})

    assert result["user_found"] is False
    assert result["users"] == []
    assert result["login_history"] == []
    assert result["error"] is None


# AC-3: Empty app_metadata flagged with no_metadata warning
def test_ac3_empty_app_metadata_flagged():
    with patch("agent.get_secrets_client") as mock_sm, patch("agent.requests.post") as mock_post, \
         patch("agent.requests.get") as mock_get:
        mock_sm.return_value.get_secret_value.return_value = mock_secret_response()
        mock_post.return_value = mock_token_response()
        user = make_auth0_user("bob@example.com", "NetskopeID")
        user["app_metadata"] = {}
        mock_get.side_effect = [
            mock_users_response(200, [user]),
            mock_users_response(200, []),
        ]

        result = fetch_auth0_data({"email": "bob@example.com"})

    assert result["user_found"] is True
    assert result["users"][0]["birthright"] == []
    assert result["users"][0]["entitlements"] == []
    assert result["sync_stale"] is True
    assert result["sync_stale_reason"] == "sync_has_never_run"
    assert "no_metadata" in result["auth0_warnings"]


def test_regression_empty_string_sync_fields_dont_crash():
    """Regression: found live 2026-08-24 (RJT-34, brad.melchior@cencora.com)
    -- real Auth0 app_metadata stores last_sync/last_daily_sync as an empty
    string "" for a user who has never synced, NOT null/absent. Passing ""
    straight into Auth0UserRecord's Optional[datetime] fields raised an
    uncaught Pydantic ValidationError (Pydantic accepts None for Optional,
    but rejects "" as an invalid datetime), crashing the whole request
    handler as an unhandled HTTP 500."""
    with patch("agent.get_secrets_client") as mock_sm, patch("agent.requests.post") as mock_post, \
         patch("agent.requests.get") as mock_get:
        mock_sm.return_value.get_secret_value.return_value = mock_secret_response()
        mock_post.return_value = mock_token_response()
        user = make_auth0_user("brad.melchior@cencora.com", "NetskopeID", last_sync="")
        mock_get.side_effect = [
            mock_users_response(200, [user]),
            mock_users_response(200, []),
        ]

        result = fetch_auth0_data({"email": "brad.melchior@cencora.com"})

    assert result["user_found"] is True
    assert result["error"] is None
    assert result["users"][0]["last_sync"] is None
    assert result["users"][0]["last_daily_sync"] is None


# AC-4: Sync staleness detected when last_sync exceeds 7 days
def test_ac4_sync_staleness_detected():
    old_sync = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    stale, reason = evaluate_sync_staleness(datetime.fromisoformat(old_sync))
    assert stale is True
    assert reason == "sync_overdue"

    fresh_sync = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    stale, reason = evaluate_sync_staleness(datetime.fromisoformat(fresh_sync))
    assert stale is False
    assert reason is None

    stale, reason = evaluate_sync_staleness(None)
    assert stale is True
    assert reason == "sync_has_never_run"


# AC-5: Failed login events counted and last reason captured
def test_ac5_failed_login_derivation():
    now = datetime.now(timezone.utc)
    events = [
        LoginEvent(date=now - timedelta(days=1), type="s", type_description="Success Login", ip="1.1.1.1"),
        LoginEvent(date=now - timedelta(days=2), type="f", type_description="Failed Login",
                   description="Access Denied: missing 'Support' in birthright", ip="1.1.1.1"),
        LoginEvent(date=now - timedelta(days=3), type="fp", type_description="Failed Login - Wrong Password", ip="1.1.1.1"),
        LoginEvent(date=now - timedelta(days=4), type="fu", type_description="Failed Login - Unknown", ip="1.1.1.1"),
        LoginEvent(date=now - timedelta(days=5), type="s", type_description="Success Login", ip="1.1.1.1"),
    ]
    count, reason = derive_failed_login_stats(events)
    assert count == 3
    assert reason == "Access Denied: missing 'Support' in birthright"


# AC-6: Multiple users for same email: connection priority and selection
def test_ac6_multiple_users_connection_priority():
    assert get_connection_priority("con_aB3xY9kLm2pQ") == 1  # federated
    assert get_connection_priority("NetskopeID") == 2
    assert get_connection_priority("Netskope-Partners") == 3

    with patch("agent.get_secrets_client") as mock_sm, patch("agent.requests.post") as mock_post, \
         patch("agent.requests.get") as mock_get:
        mock_sm.return_value.get_secret_value.return_value = mock_secret_response()
        mock_post.return_value = mock_token_response()
        mock_get.side_effect = [
            mock_users_response(200, [
                make_auth0_user("shared@example.com", "con_aB3xY9kLm2pQ", user_id="federated|1"),
                make_auth0_user("shared@example.com", "NetskopeID", user_id="NetskopeID|1"),
                make_auth0_user("shared@example.com", "Netskope-Partners", user_id="legacy|1"),
            ]),
            mock_users_response(200, []),
        ]
        result = fetch_auth0_data({"email": "shared@example.com"})

    assert result["user_found"] is True
    assert len(result["users"]) == 3
    assert result["users"][0]["connection_priority"] == 1
    assert result["users"][0]["selected"] is True
    assert result["users"][1]["connection_priority"] == 2
    assert result["users"][1]["selected"] is False
    assert result["users"][2]["connection_priority"] == 3
    assert result["users"][2]["selected"] is False
    assert "multiple_users_found" in result["auth0_warnings"]


# AC-6b: Internal Netskope employee federation resolves to priority 1
def test_ac6b_netskope_internal_federation_priority():
    assert get_connection_priority("Netskope") == 1


# AC-7: Tool 2 failure is non-fatal; payload still returned
def test_ac7_login_history_failure_non_fatal():
    with patch("agent.get_secrets_client") as mock_sm, patch("agent.requests.post") as mock_post, \
         patch("agent.requests.get") as mock_get, patch("agent.time.sleep"):
        mock_sm.return_value.get_secret_value.return_value = mock_secret_response()
        mock_post.return_value = mock_token_response()
        rate_limited = mock_users_response(429, {})
        mock_get.side_effect = [
            mock_users_response(200, [make_auth0_user("carl@example.com", "NetskopeID")]),
            rate_limited, rate_limited, rate_limited,  # 3 retries on login history
        ]
        result = fetch_auth0_data({"email": "carl@example.com"})

    assert result["user_found"] is True
    assert result["login_history"] == []
    assert result["login_history_fetch_error"] == "auth0_rate_limit_exceeded"
    assert result["error"] is None


# AC-9: Agent attempts dynamodb:Query (posture invariant)
def test_ac9_dynamodb_action_denied():
    with pytest.raises(PostureViolationError):
        assert_posture("dynamodb:Query")


# AC-9b: Agent attempts bedrock:InvokeModel (posture invariant)
def test_ac9b_bedrock_invoke_model_denied():
    with pytest.raises(PostureViolationError):
        assert_posture("bedrock:InvokeModel")


# AC-10: Schema conformance — invalid email still returns a valid Auth0Payload
def test_ac10_invalid_email_returns_valid_schema():
    result = fetch_auth0_data({"email": "not-an-email"})
    assert result["user_found"] is False
    assert result["error"] == "invalid_email_input"


# Regression test: bad/placeholder credentials cause a real HTTPError from
# the Auth0 token endpoint (raise_for_status()), which previously wasn't
# caught anywhere and crashed the whole invocation with an unhandled
# exception (HTTP 500) instead of the graceful error the spec requires.
def test_regression_bad_credentials_token_failure_is_graceful():
    import requests as requests_module

    with patch("agent.get_secrets_client") as mock_sm, patch("agent.requests.post") as mock_post, \
         patch("agent.time.sleep"):
        mock_sm.return_value.get_secret_value.return_value = mock_secret_response()
        bad_response = MagicMock()
        bad_response.raise_for_status.side_effect = requests_module.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = bad_response

        result = fetch_auth0_data({"email": "someone@example.com"})

    assert result["user_found"] is False
    assert result["error"] == "auth0_token_acquisition_failed"
    assert mock_post.call_count == 3  # exhausted all retries, per spec §8


def test_regression_malformed_secret_shape_is_graceful():
    """Regression: found live 2026-08-24 -- the ciam-agent/auth0 secret was
    overwritten with a different key schema (auth0_client_id/
    auth0_client_secret, both empty) than agent.py expects
    (client_id/client_secret). creds["client_id"] then raised an uncaught
    KeyError inside acquire_token(), which the entrypoint's try/except
    didn't catch (only ClientError/TokenAcquisitionError) -- every live
    invocation crashed with a raw, undiagnosable HTTP 500 instead of the
    graceful error field every other Auth0 failure mode returns."""
    with patch("agent.get_secrets_client") as mock_sm:
        mock_sm.return_value.get_secret_value.return_value = {
            "SecretString": json.dumps({
                "auth0_domain": "netskope-dev.us.auth0.com",
                "auth0_client_id": "",
                "auth0_client_secret": "",
            })
        }

        result = fetch_auth0_data({"email": "someone@example.com"})

    assert result["user_found"] is False
    assert result["error"] == "auth0_token_acquisition_failed"


# AC-12: Secrets Manager unavailable returns structured error
def test_ac12_secrets_manager_unavailable():
    from botocore.exceptions import ClientError
    with patch("agent.get_secrets_client") as mock_sm:
        mock_sm.return_value.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
            "GetSecretValue",
        )
        result = fetch_auth0_data({"email": "dave@example.com"})

    assert result["user_found"] is False
    assert result["error"] == "secrets_manager_unavailable"


# AC-13: Auth0 rate limit on Tool 1 retries and returns error after max attempts
def test_ac13_rate_limit_on_tool1_exhausts_retries():
    with patch("agent.get_secrets_client") as mock_sm, patch("agent.requests.post") as mock_post, \
         patch("agent.requests.get") as mock_get, patch("agent.time.sleep"):
        mock_sm.return_value.get_secret_value.return_value = mock_secret_response()
        mock_post.return_value = mock_token_response()
        rate_limited = mock_users_response(429, {})
        mock_get.side_effect = [rate_limited, rate_limited, rate_limited]

        result = fetch_auth0_data({"email": "eve@example.com"})

    assert result["user_found"] is False
    assert result["error"] == "auth0_rate_limit_exceeded"
    assert mock_get.call_count == 3


# HTTP posture guard: only AUTH0_DOMAIN + allow-listed paths
def test_http_posture_denies_wrong_host():
    with pytest.raises(PostureViolationError):
        assert_http_posture("evil.example.com", "/oauth/token", "POST")


def test_http_posture_denies_wrong_path():
    with pytest.raises(PostureViolationError):
        assert_http_posture("netskope-dev.us.auth0.com", "/api/v2/users", "POST")


def test_http_posture_allows_expected_paths():
    assert_http_posture("netskope-dev.us.auth0.com", "/oauth/token", "POST")
    assert_http_posture("netskope-dev.us.auth0.com", "/api/v2/users-by-email", "GET")
    assert_http_posture("netskope-dev.us.auth0.com", "/api/v2/users/abc123/logs", "GET")


def test_describe_login_type_mapping():
    assert describe_login_type("s") == "Success Login"
    assert describe_login_type("f") == "Failed Login"
    assert describe_login_type("fp") == "Failed Login - Wrong Password"
    assert describe_login_type("fu") == "Failed Login - Unknown"
    assert describe_login_type("zzz") == "Other: zzz"
