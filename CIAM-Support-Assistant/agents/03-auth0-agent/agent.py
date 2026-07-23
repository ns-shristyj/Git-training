"""
CIAM Auth0 Agent — Agent 3
Spec:    SPEC-CIAM-0003
Version: 0.3.0

What this file does
-------------------
This is the entrypoint file that Amazon Bedrock AgentCore runs when the
orchestrator invokes Agent 3. It:

  1. Receives a user email from the routing envelope (Agent 1 output)
  2. Authenticates to the Auth0 Management API (nskp tenant) via M2M
     Client Credentials, with the client_id/client_secret pulled from
     AWS Secrets Manager
  3. Fetches user metadata (birthright, entitlements, sync timestamps)
     and recent login history
  4. Returns a structured Auth0Payload to the orchestrator

Security model
--------------
The agent may call ONLY:
  - secretsmanager:GetSecretValue (scoped to ciam-agent/auth0-* only)
  - kms:Decrypt (scoped to the CIAM CMK, to decrypt the secret)
  - HTTPS calls to https://nskp.auth0.com — token endpoint, users-by-email,
    and user login-history endpoints only
No writes to Auth0 (PATCH/POST/DELETE), no DynamoDB, no Bedrock model
invocation — Agent 3 does deterministic lookups only, same as Agent 2.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, List, Any

import boto3
import requests
from botocore.exceptions import ClientError
from bedrock_agentcore import BedrockAgentCoreApp
from pydantic import BaseModel

# Configuration
AWS_REGION = "us-east-1"
AUTH0_DOMAIN = "nskp.auth0.com"
AUTH0_SECRET_PATH = "ciam-agent/auth0"
SYNC_STALE_DAYS = 7
DEFAULT_LOGIN_HISTORY_DAYS = 30
MAX_LOGIN_HISTORY_DAYS = 90
LOGIN_HISTORY_PER_PAGE = 50
HTTP_TIMEOUT_SECONDS = 5
MAX_RETRIES = 3

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ciam-auth0-agent")

# Posture Guard — deterministic lookup agent, no Bedrock model invocation
# permitted (mirrors Agent 2's pattern: see SPEC-CIAM-0003 §4 note).
ALLOWED_ACTIONS = frozenset({"secretsmanager:GetSecretValue", "kms:Decrypt"})

# HTTP allow-list: exactly three permitted external call patterns (§4, §5)
ALLOWED_HTTP_HOSTS = frozenset({AUTH0_DOMAIN})
ALLOWED_HTTP_PATHS = frozenset({
    "/oauth/token",
    "/api/v2/users-by-email",
})
ALLOWED_HTTP_PATH_PREFIXES = ("/api/v2/users/",)  # for /api/v2/users/{id}/logs


class PostureViolationError(RuntimeError):
    pass


def assert_posture(action: str) -> None:
    if action not in ALLOWED_ACTIONS:
        raise PostureViolationError(
            f"Posture violation: '{action}' not permitted. Allowed: {ALLOWED_ACTIONS}"
        )


def assert_http_posture(host: str, path: str, method: str) -> None:
    if host != AUTH0_DOMAIN:
        raise PostureViolationError(f"Posture violation: host '{host}' not permitted")
    if path in ALLOWED_HTTP_PATHS:
        return
    if any(path.startswith(p) and path.endswith("/logs") for p in ALLOWED_HTTP_PATH_PREFIXES):
        return
    raise PostureViolationError(f"Posture violation: path '{path}' not permitted")


# Schemas
class Auth0UserRecord(BaseModel):
    user_id: str
    email: str
    connection: str
    connection_priority: int
    selected: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    logins_count: int
    birthright: List[str] = []
    entitlements: List[str] = []
    last_sync: Optional[datetime] = None
    last_daily_sync: Optional[datetime] = None


class LoginEvent(BaseModel):
    date: datetime
    type: str
    type_description: str
    description: Optional[str] = None
    ip: str
    client_name: Optional[str] = None
    user_agent: Optional[str] = None


class Auth0Payload(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    spec_id: Literal["SPEC-CIAM-0003"] = "SPEC-CIAM-0003"
    agent: Literal["ciam-auth0-agent"] = "ciam-auth0-agent"
    run_id: str
    fetched_at: datetime

    user_found: bool = False
    users: List[Auth0UserRecord] = []

    login_history: List[LoginEvent] = []
    failed_logins_last_7_days: int = 0
    last_failed_login_reason: Optional[str] = None
    login_history_fetch_error: Optional[str] = None

    sync_stale: bool = False
    sync_stale_reason: Optional[str] = None
    auth0_warnings: List[str] = []

    error: Optional[str] = None


# M2M Token Lifecycle (§4.1)
_secrets_client = None
_cached_token: Optional[str] = None
_cached_token_expires_at: Optional[datetime] = None


def get_secrets_client():
    global _secrets_client
    if _secrets_client is None:
        _secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)
    return _secrets_client


def get_auth0_credentials() -> dict:
    assert_posture("secretsmanager:GetSecretValue")
    client = get_secrets_client()
    response = client.get_secret_value(SecretId=AUTH0_SECRET_PATH)
    return json.loads(response["SecretString"])


def acquire_token() -> str:
    """Fetch credentials and request a fresh M2M access token (§4.1 steps 1-2)."""
    creds = get_auth0_credentials()
    assert_http_posture(AUTH0_DOMAIN, "/oauth/token", "POST")

    response = requests.post(
        f"https://{AUTH0_DOMAIN}/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "audience": f"https://{AUTH0_DOMAIN}/api/v2/",
        },
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    body = response.json()
    return body["access_token"], body.get("expires_in", 86400)


def get_valid_token() -> str:
    """Use cached token if still valid; otherwise acquire a fresh one (§4.1 steps 3-4)."""
    global _cached_token, _cached_token_expires_at
    now = datetime.now(timezone.utc)
    if _cached_token and _cached_token_expires_at and now < _cached_token_expires_at:
        return _cached_token

    token, expires_in = acquire_token()
    _cached_token = token
    _cached_token_expires_at = now + timedelta(seconds=expires_in)
    return token


def refresh_token() -> str:
    """Discard cached token and acquire a fresh one (§4.1 step 5)."""
    global _cached_token, _cached_token_expires_at
    _cached_token = None
    _cached_token_expires_at = None
    return get_valid_token()


# Connection Priority (§6.3)
def get_connection_priority(connection_name: str) -> int:
    """Returns priority rank (lower = higher priority / more preferred).
    Order: federated > NetskopeID > Netskope-Partners."""
    if connection_name == "NetskopeID":
        return 2
    elif connection_name == "Netskope-Partners":
        return 3
    else:
        return 1


TYPE_DESCRIPTION_MAP = {
    "s": "Success Login",
    "f": "Failed Login",
    "fp": "Failed Login - Wrong Password",
    "fu": "Failed Login - Unknown",
}


def describe_login_type(type_code: str) -> str:
    return TYPE_DESCRIPTION_MAP.get(type_code, f"Other: {type_code}")


# Tools
def get_user_metadata(email: str) -> tuple:
    """Tool 1: GET /api/v2/users-by-email — returns (list[Auth0UserRecord], error)."""
    assert_http_posture(AUTH0_DOMAIN, "/api/v2/users-by-email", "GET")
    token = get_valid_token()

    attempt = 0
    while True:
        attempt += 1
        try:
            response = requests.get(
                f"https://{AUTH0_DOMAIN}/api/v2/users-by-email",
                params={"email": email},
                headers={"Authorization": f"Bearer {token}"},
                timeout=HTTP_TIMEOUT_SECONDS,
            )

            if response.status_code == 401:
                logger.warning("Auth0 401 on users-by-email, attempting token refresh")
                token = refresh_token()
                if attempt >= 2:
                    return None, "auth0_token_refresh_failed"
                continue

            if response.status_code == 429:
                if attempt >= MAX_RETRIES:
                    return None, "auth0_rate_limit_exceeded"
                time.sleep(2 ** (attempt - 1))
                continue

            response.raise_for_status()
            raw_users = response.json()
            break

        except requests.exceptions.Timeout:
            if attempt >= MAX_RETRIES:
                return None, "auth0_timeout"
            continue
        except requests.exceptions.RequestException as e:
            return None, f"{type(e).__name__}"

    if not raw_users:
        return [], None

    users = []
    for raw in raw_users:
        app_metadata = raw.get("app_metadata") or {}
        connection = (raw.get("identities") or [{}])[0].get("connection", "unknown")
        users.append(Auth0UserRecord(
            user_id=raw.get("user_id", ""),
            email=raw.get("email", email),
            connection=connection,
            connection_priority=get_connection_priority(connection),
            selected=False,
            created_at=raw.get("created_at"),
            last_login=raw.get("last_login"),
            logins_count=raw.get("logins_count", 0),
            birthright=app_metadata.get("birthright", []),
            entitlements=app_metadata.get("entitlements", []),
            last_sync=app_metadata.get("last_sync"),
            last_daily_sync=app_metadata.get("last_daily_sync"),
        ))

    # Resolve selection: lowest priority number wins; first match on ties
    best_priority = min(u.connection_priority for u in users)
    selected_marked = False
    for u in users:
        if u.connection_priority == best_priority and not selected_marked:
            u.selected = True
            selected_marked = True

    # Sort so selected record is first
    users.sort(key=lambda u: (not u.selected, u.connection_priority))

    return users, None


def get_login_history(user_id: str, days: int) -> tuple:
    """Tool 2: GET /api/v2/users/{user_id}/logs — returns (list[LoginEvent], error)."""
    path = f"/api/v2/users/{user_id}/logs"
    assert_http_posture(AUTH0_DOMAIN, path, "GET")
    token = get_valid_token()

    attempt = 0
    while True:
        attempt += 1
        try:
            response = requests.get(
                f"https://{AUTH0_DOMAIN}{path}",
                params={"per_page": LOGIN_HISTORY_PER_PAGE},
                headers={"Authorization": f"Bearer {token}"},
                timeout=HTTP_TIMEOUT_SECONDS,
            )

            if response.status_code == 401:
                token = refresh_token()
                if attempt >= 2:
                    return [], "auth0_token_refresh_failed"
                continue

            if response.status_code == 429:
                if attempt >= MAX_RETRIES:
                    return [], "auth0_rate_limit_exceeded"
                time.sleep(2 ** (attempt - 1))
                continue

            response.raise_for_status()
            raw_logs = response.json()
            break

        except requests.exceptions.Timeout:
            return [], "auth0_timeout"
        except requests.exceptions.RequestException as e:
            return [], f"{type(e).__name__}"

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = []
    for raw in raw_logs:
        event_date = raw.get("date")
        if isinstance(event_date, str):
            parsed_date = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
        else:
            parsed_date = event_date
        if parsed_date < cutoff:
            continue
        type_code = raw.get("type", "")
        events.append(LoginEvent(
            date=parsed_date,
            type=type_code,
            type_description=describe_login_type(type_code),
            description=raw.get("description"),
            ip=raw.get("ip", ""),
            client_name=raw.get("client_name"),
            user_agent=raw.get("user_agent"),
        ))

    return events, None


# Helpers
def now_utc_iso() -> datetime:
    return datetime.now(timezone.utc)


def is_valid_email(email: str) -> bool:
    return bool(email) and "@" in email and len(email.strip()) > 2


def evaluate_sync_staleness(last_sync: Optional[datetime]) -> tuple:
    """§6.2"""
    if not last_sync:
        return True, "sync_has_never_run"
    now = now_utc_iso()
    if (now - last_sync) > timedelta(days=SYNC_STALE_DAYS):
        return True, "sync_overdue"
    return False, None


def derive_failed_login_stats(login_history: List[LoginEvent]) -> tuple:
    """§6.4"""
    now = now_utc_iso()
    cutoff = now - timedelta(days=7)
    failed_events = [e for e in login_history if e.type != "s" and e.date >= cutoff]
    count = len(failed_events)

    all_failed = sorted(
        [e for e in login_history if e.type != "s"], key=lambda e: e.date, reverse=True
    )
    last_reason = all_failed[0].description if all_failed else None

    return count, last_reason


# Main
app = BedrockAgentCoreApp()


@app.entrypoint
def fetch_auth0_data(payload: dict) -> dict:
    run_id = str(uuid.uuid4())
    fetched_at = now_utc_iso()
    auth0_warnings = []

    logger.info(f"[{run_id}] Agent 3 invoked. Keys: {list(payload.keys())}")

    raw_email = payload.get("email")
    email = raw_email.strip().lower() if isinstance(raw_email, str) else ""

    raw_days = payload.get("days", DEFAULT_LOGIN_HISTORY_DAYS)
    days = raw_days if isinstance(raw_days, int) else DEFAULT_LOGIN_HISTORY_DAYS
    days = min(days, MAX_LOGIN_HISTORY_DAYS)

    # Step 1: validate input
    if not is_valid_email(email):
        logger.warning(f"[{run_id}] Invalid email: {email}")
        return Auth0Payload(
            run_id=run_id,
            fetched_at=fetched_at,
            user_found=False,
            error="invalid_email_input",
        ).model_dump()

    # Step 2: token acquisition happens lazily inside get_user_metadata via get_valid_token()
    try:
        # Step 3: fetch user metadata (Tool 1)
        users, tool1_error = get_user_metadata(email)
    except ClientError:
        logger.error(f"[{run_id}] Secrets Manager unavailable")
        return Auth0Payload(
            run_id=run_id,
            fetched_at=fetched_at,
            user_found=False,
            error="secrets_manager_unavailable",
        ).model_dump()

    if tool1_error:
        logger.error(f"[{run_id}] Tool 1 failed: {tool1_error}")
        return Auth0Payload(
            run_id=run_id,
            fetched_at=fetched_at,
            user_found=False,
            error=tool1_error,
        ).model_dump()

    if not users:
        logger.info(f"[{run_id}] No Auth0 user found for email: {email}")
        return Auth0Payload(
            run_id=run_id,
            fetched_at=fetched_at,
            user_found=False,
            users=[],
            login_history=[],
            error=None,
        ).model_dump()

    if len(users) > 1:
        auth0_warnings.append("multiple_users_found")

    selected_user = next((u for u in users if u.selected), users[0])

    sync_stale, sync_stale_reason = evaluate_sync_staleness(selected_user.last_sync)
    if not selected_user.last_sync and not selected_user.birthright and not selected_user.entitlements:
        auth0_warnings.append("no_metadata")

    # Step 4: fetch login history (Tool 2) — only if user found (§6.1)
    login_history, tool2_error = get_login_history(selected_user.user_id, days)

    failed_logins_last_7_days, last_failed_login_reason = derive_failed_login_stats(login_history)

    logger.info(
        f"[{run_id}] Done. user_found=True users={len(users)} "
        f"login_events={len(login_history)}"
    )

    return Auth0Payload(
        run_id=run_id,
        fetched_at=fetched_at,
        user_found=True,
        users=users,
        login_history=login_history,
        failed_logins_last_7_days=failed_logins_last_7_days,
        last_failed_login_reason=last_failed_login_reason,
        login_history_fetch_error=tool2_error,
        sync_stale=sync_stale,
        sync_stale_reason=sync_stale_reason,
        auth0_warnings=auth0_warnings,
        error=None,
    ).model_dump()


if __name__ == "__main__":
    app.run()
