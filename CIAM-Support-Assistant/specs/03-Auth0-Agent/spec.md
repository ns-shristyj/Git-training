---
spec_id: SPEC-CIAM-0003
capability: ciam-auth0-agent
status: Draft
owner: Shristy Jaiswal
reviewers: [Peer]
approver: Rehman
prd: https://confluence.netskope.example/display/GIS/ciam-auth0-agent-prd  # placeholder — link to docs/confluence/ciam-auth0-agent/prd.md until Phase 0 lands
jira_epic: GIS-EPIC-CIAM  # placeholder — see docs/jira/ciam-auth0-agent-epic.md until Phase 0 lands
version: 0.1.0
created: 2026-06-23
last_updated: 2026-06-23
---

# spec.md — CIAM Auth0 Agent (Agent 3)

> This is the **executable contract**. Code, evals, and PR review trace back to
> this file. Acceptance criteria map 1:1 to eval cases under
> `evals/ciam-auth0-agent/cases/`. Posture/read-only invariants (AC-8, AC-9,
> AC-10) are **gating in CI**: a regression fails the PR.

## 1. Summary

The CIAM Auth0 Agent is a **Layer 1 read-only execution agent** in the CIAM
Support Assistant pipeline. It is invoked by the orchestrator when Agent 1
(Intent Classifier) sets `invoke_agent_3: true` in the routing envelope. It
receives a user email address, authenticates to the Auth0 Management API for
the `nskp` tenant via M2M Client Credentials (credentials retrieved from AWS
Secrets Manager), fetches user metadata including the critical `app_metadata`
object (birthright array, entitlements array, sync timestamps), and fetches
recent login history. It returns a single structured `Auth0Payload` JSON object
to the orchestrator for onward consumption by Agents 4 (Knowledge Base) and 5
(Response Generator). The agent performs **no diagnosis, no birthright
evaluation, and no response generation**. It only fetches Auth0 records and
returns them. It performs **no writes** to Auth0 — no PATCH, POST, or DELETE on
any user, connection, action, or application object.

## 2. Goals / Non-Goals

### Goals

- Accept a user **email address** from the orchestrator's routing envelope and
  return the corresponding Auth0 identity record for the `nskp` tenant.
- Execute **Tool 1 (`get_user_metadata`)**: call `GET /api/v2/users-by-email`
  and return core identity fields plus the full `app_metadata` object
  (birthright, entitlements, sync timestamps).
- Execute **Tool 2 (`get_login_history`)**: call
  `GET /api/v2/users/{user_id}/logs` and return recent login events with
  success/failure classification and error descriptions.
- Manage the **M2M token lifecycle**: fetch `client_id` and `client_secret`
  from AWS Secrets Manager, obtain a Client Credentials access token from
  Auth0, cache it for the token's lifetime, and refresh it transparently when
  expired — without ever logging or exposing the token.
- Derive and surface **data-quality signals**: `sync_stale` flag when
  `last_sync > 7 days`, `failed_logins_last_7_days` count, and
  `last_failed_login_reason` from the most recent failed login event.
- Return a single **Pydantic-validated `Auth0Payload`** JSON object to the
  orchestrator.
- Hold the Phase 1 **read-only posture invariant**: zero write calls to Auth0
  (`PATCH`, `POST`, `DELETE`), zero access to DynamoDB, Salesforce, Jira, or
  Slack, both by IAM deny and by code-side action-group assertion.

### Non-goals

- Modifying the `birthright` or `entitlements` arrays on any Auth0 user.
  (`birthright` is overwritten hourly by NetskopeID-Sync; `entitlements` may
  only be modified by an authorized L2 remediation flow — out of scope for
  Phase 1.)
- Triggering or replaying an Auth0 login or sync Action.
- Querying Auth0 Actions, Connections, Rules, Applications, or tenant
  configuration.
- Querying DynamoDB or Salesforce (delegated to Agent 2).
- Evaluating whether the birthright is correct for the user's account status
  (delegated to Agent 4).
- Diagnosing the root cause of an access issue or generating an L1 response
  (delegated to Agent 5).
- Writing to Jira or Slack.

## 3. Inputs

| Input | Source | Notes |
| :--- | :--- | :--- |
| `email` | Agent 1 routing envelope (`extracted_email`) | Required. String. Used as the lookup key for `GET /api/v2/users-by-email`. |
| `days` | Orchestrator (optional, default `30`) | Integer. Number of days of login history to retrieve. Passed to Tool 2. Phase 1 default is `30`; maximum is `90`. |
| `intent` | Agent 1 routing envelope (`intent`) | Read-only context. Used to decide whether Tool 2 (login history) is called (see §6.1). |
| `run_id` | AgentCore run header | Propagated to the `Auth0Payload` and any posture-violation findings for end-to-end traceability. |

The agent is **stateless between invocations** for all business data. The M2M
access token MAY be cached in process memory for its stated TTL (24 hours) to
avoid redundant Secrets Manager and token-endpoint round trips within a single
container lifetime; this cache is not persisted to any external store.

## 4. Permitted Tools / Authorization Boundary

The agent's IAM execution role MAY perform **only** the AWS actions in this
table. The CDK stack in `infra/aws/ciam-auth0-agent/` MUST instantiate this
exact policy shape; no `*` action wildcards are permitted.

| Service | Action | Resource scope |
| :--- | :--- | :--- |
| Secrets Manager | `secretsmanager:GetSecretValue` | `arn:aws:secretsmanager:*:*:secret:ciam-agent/auth0-*` only |
| KMS | `kms:Decrypt` | CIAM CMK ARN only (resource-conditioned; used to decrypt the Secrets Manager secret) |
| Bedrock | `bedrock:InvokeModel` | Scoped to `claude-haiku-*` model ARN only |

All other AWS service actions — DynamoDB, S3, SNS, SSM, STS, IAM, and all
Secrets Manager paths outside `ciam-agent/auth0-*` — are **not permitted**
and are explicitly denied (see §5).

External HTTPS calls permitted by the action-group allow-list (code layer):

| External endpoint | Method(s) | Purpose |
| :--- | :--- | :--- |
| `https://nskp.auth0.com/oauth/token` | `POST` | M2M Client Credentials token acquisition and refresh. |
| `https://nskp.auth0.com/api/v2/users-by-email` | `GET` | Tool 1: user metadata lookup by email. |
| `https://nskp.auth0.com/api/v2/users/{user_id}/logs` | `GET` | Tool 2: login history by user ID. |

Any HTTPS call to a host other than `nskp.auth0.com`, or any method other
than `GET`/`POST` (token endpoint only), is a **defect and a release blocker**
(see §5).

### 4.1 Auth0 Authentication Flow (M2M Client Credentials)

The agent follows this token lifecycle on every cold start and on token
expiry:

1. **Fetch credentials.** Call `secretsmanager:GetSecretValue` at path
   `ciam-agent/auth0` to retrieve `client_id` and `client_secret`. These
   values are **never logged, never included in any payload field, and never
   surfaced in error messages**.
2. **Request token.** `POST https://nskp.auth0.com/oauth/token` with body:
   ```
   grant_type=client_credentials
   client_id=<client_id>
   client_secret=<client_secret>
   audience=https://nskp.auth0.com/api/v2/
   ```
3. **Cache token.** Store the returned `access_token` in process memory with
   its `expires_in` TTL (24 hours). The token is **never written to S3, DynamoDB,
   SSM, or any external store**.
4. **Use token.** All Management API calls include
   `Authorization: Bearer <access_token>`.
5. **Refresh on expiry.** If a Management API call returns `HTTP 401
   Unauthorized`, discard the cached token and repeat steps 1–3 once before
   retrying. If refresh fails, return `error: "auth0_token_refresh_failed"`.

### 4.2 Tool Definitions

#### Tool 1 — `get_user_metadata(email: str) → Auth0UserRecord | list[Auth0UserRecord] | None`

**Auth0 API call:** `GET https://nskp.auth0.com/api/v2/users-by-email?email={email}`
with `Authorization: Bearer <access_token>`.

**Required scopes:** `read:users`.

**Auth0 response → returned field mapping:**

| Auth0 response field | Returned field | Type | Notes |
| :--- | :--- | :--- | :--- |
| `user_id` | `user_id` | `str` | e.g. `"NetskopeID\|oscar.armbruster"` |
| `email` | `email` | `str` | |
| `identities[0].connection` | `connection` | `str` | e.g. `"NetskopeID"`, `"google-oauth2"` |
| `created_at` | `created_at` | `datetime` (UTC) | |
| `last_login` | `last_login` | `datetime \| None` | `null` if user has never logged in |
| `logins_count` | `logins_count` | `int` | |
| `app_metadata.birthright` | `birthright` | `list[str]` | e.g. `["Support", "Community", "Academy"]`; `[]` if key absent |
| `app_metadata.entitlements` | `entitlements` | `list[str]` | manually assigned keywords; `[]` if key absent |
| `app_metadata.last_sync` | `last_sync` | `datetime \| None` | timestamp of last NetskopeID-Sync run for this user |
| `app_metadata.last_daily_sync` | `last_daily_sync` | `datetime \| None` | timestamp of last daily sync |

**Returns:** A single `Auth0UserRecord` if exactly one user matches. If zero
users are found, returns `None` (caller sets `user_found: false`). If multiple
users are found (same email, different connections), returns all as a list and
sets the `multiple_users_found` warning (see §6.3).

#### Tool 2 — `get_login_history(user_id: str, days: int = 30) → list[LoginEvent]`

**Auth0 API calls:**
1. Resolve `user_id` from the Tool 1 result (already available in-process;
   no additional API call required if Tool 1 has already been called in this
   invocation).
2. `GET https://nskp.auth0.com/api/v2/users/{user_id}/logs?per_page=50`
   with `Authorization: Bearer <access_token>`. Filter client-side to events
   where `date >= (now_utc − days)`.

**Required scopes:** `read:logs`.

**Auth0 log event → returned field mapping:**

| Auth0 log field | Returned field | Type | Notes |
| :--- | :--- | :--- | :--- |
| `date` | `date` | `datetime` (UTC) | |
| `type` | `type` | `str` | Raw Auth0 log type code (e.g. `"s"`, `"f"`, `"fp"`, `"fu"`) |
| `type` (derived) | `type_description` | `str` | Human-readable: `"Success Login"`, `"Failed Login"`, `"Failed Login - Wrong Password"`, `"Failed Login - Unknown"` |
| `description` | `description` | `str \| None` | Error message on failure; e.g. `"Access Denied: missing 'Support' in birthright"` |
| `ip` | `ip` | `str` | Source IP address |
| `client_name` | `client_name` | `str \| None` | Portal name; e.g. `"Netskope Support Portal"` |
| `user_agent` | `user_agent` | `str \| None` | Browser/OS string |

**Auth0 log type code → `type_description` mapping (normative):**

| `type` code | `type_description` |
| :--- | :--- |
| `s` | `Success Login` |
| `f` | `Failed Login` |
| `fp` | `Failed Login - Wrong Password` |
| `fu` | `Failed Login - Unknown` |
| any other | `Other: <raw_type_code>` |

**Returns:** An array (possibly empty) of `LoginEvent` objects filtered to the
requested `days` window. An empty array is a valid successful result (no recent
logins). Tool 2 failure is **non-fatal** — see §8.

## 5. Explicit Denies (Phase 1 invariants)

The CDK IAM role MUST attach an explicit `Deny` statement covering the
following AWS actions with `Resource: "*"`. Additionally, the agent's
code-layer action-group (`core/agentcore/action_group.py`) MUST enforce an
explicit HTTP allow-list as defined in §4. These denies are **gating posture
invariants** — CI fails the PR if they are missing or weakened.

| Denied action | Reason |
| :--- | :--- |
| `dynamodb:*` (all actions) | Account data is owned by Agent 2. No DynamoDB access from this agent. |
| `s3:*` (all actions) | No audit bucket, baseline, or state storage needed. |
| `ssm:GetParameter` (any path) | Credentials are in Secrets Manager only; no SSM reads. |
| `secretsmanager:GetSecretValue` on any path outside `ciam-agent/auth0-*` | Scoped to CIAM Auth0 credentials only. |
| `sts:AssumeRole` | No cross-account or cross-service role assumption. |
| `iam:*` | No IAM reads or writes. |
| `sns:Publish` | The orchestrator, not this agent, owns alert fanout. |
| Auth0 `PATCH /api/v2/users/{id}` | No write to user records. `birthright` and `entitlements` must never be modified by this agent. |
| Auth0 `DELETE /api/v2/users/{id}` | No user deletion. |
| Auth0 `POST /api/v2/users` | No user creation. |
| Auth0 Management API paths outside `/oauth/token`, `/api/v2/users-by-email`, `/api/v2/users/{id}/logs` | Scope-limited to identity and login data only; Actions, Connections, Rules, Applications are out of scope. |

Defense in depth: the code-layer action-group MUST contain an explicit
allow-list of exactly three permitted external call patterns (token endpoint,
users-by-email, user logs). Any HTTP call to a host other than `nskp.auth0.com`
or to an un-listed path raises `PostureViolationError` *before* the HTTP
request is issued, emits a `posture-violation` finding (CRITICAL), and aborts
the invocation.

## 6. Behavior

An invocation proceeds in the following deterministic steps:

1. **Validate input.** Confirm the routing envelope contains a non-empty,
   syntactically valid `email` field. If absent or malformed, return an
   `Auth0Payload` with `user_found: false`, all user fields `null`, and
   `error: "invalid_email_input"` without calling any Auth0 endpoint.

2. **Acquire M2M token.** If a valid (non-expired) token is cached in process
   memory, use it. Otherwise execute the token acquisition flow in §4.1.
   On Secrets Manager failure, return `error: "secrets_manager_unavailable"`.
   On Auth0 token endpoint failure (after 3 retries), return
   `error: "auth0_token_acquisition_failed"`.

3. **Fetch user metadata (Tool 1).** Call `get_user_metadata(email)`.
   - On success with one result → populate all user fields; compute
     `sync_stale` (see §6.2); proceed to step 4.
   - On zero results → set `user_found: false`, all user fields `null`;
     skip step 4; proceed to step 5.
   - On multiple results → set `user_found: true`, populate `users` as a
     typed array of all `Auth0UserRecord` objects, append
     `"multiple_users_found"` to `auth0_warnings`; use the **first** user's
     `user_id` for step 4.
   - On `HTTP 401` → attempt one token refresh (§4.1 step 5) and retry once.
     On repeated failure, return `error: "auth0_token_refresh_failed"`.
   - On `HTTP 429` → retry with exponential backoff, max 3 attempts. On max
     retries exceeded, return `error: "auth0_rate_limit_exceeded"`.
   - On other Auth0 API error → return `error: "<http_status>_<error_code>"`.

4. **Fetch login history (Tool 2).** Call `get_login_history(user_id, days)`.
   Apply the same retry and 401-refresh logic as step 3. Derive
   `failed_logins_last_7_days` and `last_failed_login_reason` from the
   returned events (see §6.4). On Tool 2 failure, set `login_history: []`,
   `failed_logins_last_7_days: 0`, `last_failed_login_reason: null`, and
   populate `login_history_fetch_error` — do **not** abort the invocation.

5. **Assemble and validate payload.** Construct the `Auth0Payload` (schema
   in §7). Validate against Pydantic strict mode. On validation failure, return
   `error: "payload_validation_error"` with the validation message.

6. **Return payload.** Return the complete `Auth0Payload` to the orchestrator.
   No writes to Auth0 or any other system occur at any step.

### 6.1 Tool Call Conditionality

Tool 2 (`get_login_history`) is called **only** when Tool 1 returns at least
one user record (i.e., `user_found: true`). It is also called regardless of
`intent` — login history is relevant to `ACCESS_DENIED`, `SSO_ERROR`, and
`SYNC_ISSUE` intents alike, and the cost of the extra API call is negligible
given the Haiku model cost. If Tool 1 returns `user_found: false`, Tool 2 is
skipped and `login_history` is set to `[]`.

### 6.2 Sync Staleness Evaluation

After Tool 1 returns, the agent computes `sync_stale` as follows:

- If `last_sync` is `null` or an empty string → `sync_stale: true`,
  `sync_stale_reason: "sync_has_never_run"`.
- If `(now_utc − last_sync) > 7 days` → `sync_stale: true`,
  `sync_stale_reason: "sync_overdue"`.
- Otherwise → `sync_stale: false`, `sync_stale_reason: null`.

The 7-day threshold is the Phase 1 default and is not configurable at
runtime.

### 6.3 Multiple Users Edge Case

Auth0 allows the same email address to exist across multiple connections (e.g.,
`NetskopeID` and `google-oauth2`). When Tool 1 returns more than one
`Auth0UserRecord`:

- Set `user_found: true`.
- Populate `users` as a typed array of all matching records (not a single
  `Auth0UserRecord`).
- Append `"multiple_users_found"` to `auth0_warnings`.
- Use the **first** user's `user_id` for Tool 2.
- Apply a **connection preference order** when selecting the primary record for
  derived fields: `NetskopeID` > `Username-Password-Authentication` >
  `google-oauth2` > any other. The preferred record is placed first in the
  `users` array.
- Do **not** attempt to merge or deduplicate the birthright or entitlements
  arrays across records — that determination is deferred to Agent 5.

### 6.4 Failed Login Derivation

After Tool 2 returns, the agent derives two fields:

- `failed_logins_last_7_days`: count of `LoginEvent` records where
  `type != "s"` (i.e., any non-success type) and
  `date >= (now_utc − 7 days)`.
- `last_failed_login_reason`: the `description` field of the most recent
  `LoginEvent` where `type != "s"`. `null` if no failed logins exist in the
  history window.

## 7. Outputs

### 7.1 Auth0 Payload Schema

The agent returns exactly one `Auth0Payload` object to the orchestrator.

```python
class Auth0Payload(BaseModel):
    schema_version: Literal["1.0"]
    spec_id:        Literal["SPEC-CIAM-0003"]
    agent:          Literal["ciam-auth0-agent"]
    run_id:         str                         # uuid4, from AgentCore run header
    fetched_at:     datetime                    # UTC, isoformat

    # --- Primary lookup result ---
    user_found:     bool
    users:          list[Auth0UserRecord]        # length 0 (not found), 1 (normal),
                                                # or N>1 (multiple_users_found)

    # --- Login history ---
    login_history:              list[LoginEvent]  # filtered to requested days window
    failed_logins_last_7_days:  int               # derived; 0 when not fetched
    last_failed_login_reason:   str | None        # from most recent failed login
    login_history_fetch_error:  str | None        # non-null if Tool 2 failed

    # --- Data quality signals ---
    sync_stale:       bool
    sync_stale_reason: str | None               # "sync_has_never_run" | "sync_overdue" | null
    auth0_warnings:   list[str]                 # e.g. ["multiple_users_found",
                                                #        "no_metadata"]

    # --- Error ---
    error:            str | None                # null on full success


class Auth0UserRecord(BaseModel):
    user_id:       str
    email:         str
    connection:    str
    created_at:    datetime
    last_login:    datetime | None
    logins_count:  int
    birthright:    list[str]                    # [] if app_metadata absent
    entitlements:  list[str]                    # [] if app_metadata absent
    last_sync:     datetime | None
    last_daily_sync: datetime | None


class LoginEvent(BaseModel):
    date:             datetime
    type:             str                       # raw Auth0 type code
    type_description: str                       # human-readable (see §4.2 mapping)
    description:      str | None
    ip:               str
    client_name:      str | None
    user_agent:       str | None
```

### 7.2 Posture Violation Finding

If the agent's code attempts any denied action (DynamoDB read, Auth0 write,
out-of-scope HTTP call, etc.), it MUST emit a `PostureViolationFinding`
conforming to `core/findings/schema.py` and abort the invocation. No
`Auth0Payload` is returned in this case.

```python
class PostureViolationFinding(BaseModel):
    schema_version: Literal["1.0"]
    spec_id:        Literal["SPEC-CIAM-0003"]
    agent:          Literal["ciam-auth0-agent"]
    run_id:         str
    detected_at:    datetime
    category:       Literal["posture-violation"]
    severity:       Literal["CRITICAL"]
    evidence:       dict[str, Any]  # {"attempted_action": "PATCH /api/v2/users/{id}"}
                                    # credentials are NEVER included in evidence
```

## 8. Failure Handling

- **Secrets Manager unavailable.** Return `Auth0Payload` with
  `user_found: false`, `error: "secrets_manager_unavailable"`. Do not raise
  an unhandled exception.
- **Auth0 token acquisition failed** (after 3 retries on token endpoint).
  Return `error: "auth0_token_acquisition_failed"`.
- **Auth0 token expired mid-invocation (`HTTP 401`).** Attempt one automatic
  refresh (§4.1 step 5). On repeated `401`, return
  `error: "auth0_token_refresh_failed"`.
- **Auth0 rate limit (`HTTP 429`) on Tool 1.** Retry with exponential backoff
  (base 1 s, multiplier 2×), max 3 attempts. After max retries, return
  `error: "auth0_rate_limit_exceeded"`.
- **Auth0 API timeout on Tool 1.** SDK timeout set to 5 s. After timeout and
  max retries, return `error: "auth0_timeout"`.
- **Auth0 API error on Tool 2 (login history).** Non-fatal. Return
  `login_history: []`, `failed_logins_last_7_days: 0`,
  `last_failed_login_reason: null`, and set `login_history_fetch_error` to the
  error description. The `Auth0Payload` is still returned with all Tool 1
  fields populated.
- **Email not found in Auth0.** Return `user_found: false`, `users: []`,
  `login_history: []`, `error: null`. Not-found is a valid expected result for
  `ACCOUNT_NOT_FOUND` intents.
- **`app_metadata` absent or empty on a found user.** Non-fatal. Set
  `birthright: []`, `entitlements: []`, `last_sync: null`,
  `last_daily_sync: null`, append `"no_metadata"` to `auth0_warnings`.
  Compute `sync_stale: true` with `sync_stale_reason: "sync_has_never_run"`.
- **Payload validation failure.** Return `error: "payload_validation_error"`
  with the Pydantic validation detail. Do not return a partially-constructed
  payload.
- **Posture violation (tripwire).** Any code path that attempts a denied
  action raises `PostureViolationError`, emits a `posture-violation` finding
  (CRITICAL), and aborts the invocation with no `Auth0Payload` returned. This
  is a release-blocker defect.

## 9. Acceptance Criteria (Given/When/Then)

Each AC maps 1:1 to an eval case at `evals/ciam-auth0-agent/cases/ac-N.yaml`.
ACs marked **GATING** fail the PR in CI if they regress.

### AC-1 — Known email returns full user record with birthright populated

- **Given** a routing envelope with `email: "alice@example.com"` and an Auth0
  fixture returning one user with `connection: "NetskopeID"`,
  `birthright: ["Support", "Community", "Academy"]`, and a valid `last_sync`
  timestamp within 7 days,
- **When** the agent runs,
- **Then** the `Auth0Payload` has `user_found: true`, `users` contains exactly
  one `Auth0UserRecord` with all fields matching the fixture, `sync_stale:
  false`, `error: null`, and `auth0_warnings` does not contain `"no_metadata"`.

### AC-2 — Email not found returns user_found false with no error

- **Given** a routing envelope with `email: "unknown@example.com"` and an
  Auth0 fixture returning an empty array for the users-by-email endpoint,
- **When** the agent runs,
- **Then** the `Auth0Payload` has `user_found: false`, `users: []`,
  `login_history: []`, and `error: null`.

### AC-3 — Empty app_metadata flagged with no_metadata warning

- **Given** an Auth0 fixture where the user exists but `app_metadata` is an
  empty object `{}`,
- **When** the agent runs,
- **Then** `user_found: true`, `birthright: []`, `entitlements: []`,
  `last_sync: null`, `sync_stale: true`,
  `sync_stale_reason: "sync_has_never_run"`, and `auth0_warnings` contains
  `"no_metadata"`.

### AC-4 — Sync staleness detected when last_sync exceeds 7 days

- **Given** an Auth0 fixture where `app_metadata.last_sync` is 8 days before
  the invocation timestamp,
- **When** the agent runs,
- **Then** `sync_stale: true`, `sync_stale_reason: "sync_overdue"`, and
  `user_found: true` with all other fields correctly populated.

### AC-5 — Failed login events counted and last reason captured

- **Given** an Auth0 fixture where the login history contains 3 failed login
  events within the last 7 days, the most recent with
  `description: "Access Denied: missing 'Support' in birthright"`, and 2
  successful logins,
- **When** the agent runs,
- **Then** `failed_logins_last_7_days: 3`,
  `last_failed_login_reason: "Access Denied: missing 'Support' in birthright"`,
  and `login_history` contains all 5 events.

### AC-6 — Multiple users for same email: preference order and warning set

- **Given** an Auth0 fixture returning two users for the same email — one with
  `connection: "google-oauth2"` and one with `connection: "NetskopeID"`,
- **When** the agent runs,
- **Then** `user_found: true`, `users` has length 2, the `NetskopeID` user
  appears first in the `users` array, `auth0_warnings` contains
  `"multiple_users_found"`, and no exception is raised.

### AC-7 — Tool 2 failure is non-fatal; payload still returned

- **Given** a known email with a valid Tool 1 Auth0 fixture and a simulated
  `HTTP 429` on the login history endpoint after max retries,
- **When** the agent runs,
- **Then** `user_found: true` with all Tool 1 fields populated,
  `login_history: []`, `login_history_fetch_error` is non-null, and
  `error: null`.

### AC-8 — Agent attempts `PATCH /api/v2/users/{id}` (GATING — posture invariant)

- **Given** a malformed tool call or code path that attempts an HTTP `PATCH`
  to the Auth0 Management API to modify a user record,
- **When** the agent processes the invocation,
- **Then** `PostureViolationError` is raised *before* any HTTP call is made, no
  `Auth0Payload` is returned, and a `posture-violation` (CRITICAL) finding is
  emitted. Credentials are not present in the finding's `evidence`. **Gating
  in CI.**

### AC-9 — Agent attempts `dynamodb:Query` (GATING — posture invariant)

- **Given** a malformed tool call or code path that attempts a DynamoDB query
  from within this agent,
- **When** the agent processes the invocation,
- **Then** `PostureViolationError` is raised before any AWS SDK call is made,
  no `Auth0Payload` is returned, and a `posture-violation` (CRITICAL) finding
  is emitted. **Gating in CI.**

### AC-10 — Schema conformance (GATING — schema invariant)

- **Given** any invocation that produces an `Auth0Payload`,
- **When** the payload is validated against `Auth0Payload` (Pydantic strict
  mode),
- **Then** it passes validation without error; any failure fails the run and
  the CI gate. **Gating in CI.**

### AC-11 — Expired M2M token triggers refresh and succeeds

- **Given** a valid user email, a cached M2M token that has expired, and an
  Auth0 fixture that returns `HTTP 401` on the first Management API call and
  succeeds after a fresh token is obtained,
- **When** the agent runs,
- **Then** the `Auth0Payload` is returned with `user_found: true`, `error:
  null`, and exactly one token-refresh round trip is recorded (verified by
  mock call count assertion in the eval fixture).

### AC-12 — Secrets Manager unavailable returns structured error

- **Given** a simulated `secretsmanager:GetSecretValue` failure (access
  denied or service error),
- **When** the agent runs,
- **Then** the `Auth0Payload` has `user_found: false`,
  `error: "secrets_manager_unavailable"`, and no unhandled exception is raised.

### AC-13 — Auth0 rate limit on Tool 1 retries and returns error after max attempts

- **Given** a valid email and an Auth0 fixture that returns `HTTP 429` on all
  3 retry attempts for the users-by-email endpoint,
- **When** the agent runs,
- **Then** the `Auth0Payload` has `user_found: false`,
  `error: "auth0_rate_limit_exceeded"`, and exactly 3 HTTP attempts are
  recorded in the eval fixture.

## 10. Eval Mapping Table

| AC | Eval case file | Type | Gating |
| :--- | :--- | :--- | :--- |
| AC-1 | `evals/ciam-auth0-agent/cases/ac-1.yaml` | structured-assertion | no |
| AC-2 | `evals/ciam-auth0-agent/cases/ac-2.yaml` | structured-assertion | no |
| AC-3 | `evals/ciam-auth0-agent/cases/ac-3.yaml` | structured-assertion | no |
| AC-4 | `evals/ciam-auth0-agent/cases/ac-4.yaml` | structured-assertion | no |
| AC-5 | `evals/ciam-auth0-agent/cases/ac-5.yaml` | structured-assertion | no |
| AC-6 | `evals/ciam-auth0-agent/cases/ac-6.yaml` | structured-assertion | no |
| AC-7 | `evals/ciam-auth0-agent/cases/ac-7.yaml` | failure-mode | no |
| AC-8 | `evals/ciam-auth0-agent/cases/ac-8.yaml` | posture-invariant | **yes** |
| AC-9 | `evals/ciam-auth0-agent/cases/ac-9.yaml` | posture-invariant | **yes** |
| AC-10 | `evals/ciam-auth0-agent/cases/ac-10.yaml` | schema-invariant | **yes** |
| AC-11 | `evals/ciam-auth0-agent/cases/ac-11.yaml` | failure-mode | no |
| AC-12 | `evals/ciam-auth0-agent/cases/ac-12.yaml` | failure-mode | no |
| AC-13 | `evals/ciam-auth0-agent/cases/ac-13.yaml` | failure-mode | no |

## 11. Open Questions

- **OQ-1.** Token caching scope: this spec permits caching the M2M token in
  process memory for its TTL. If the agent is deployed as a Lambda function
  (ephemeral container), the cache provides no benefit across invocations.
  Confirm the deployment target (Lambda vs. ECS long-running container) to
  determine whether an SSM-backed or ElastiCache token cache is warranted to
  avoid per-invocation Secrets Manager and token-endpoint round trips.
- **OQ-2.** `per_page` ceiling: this spec uses `per_page=50` for the login
  history endpoint. If a user has more than 50 events in the requested `days`
  window, older events within the window are silently dropped. Confirm whether
  pagination (following Auth0's `next` link header) is required for Phase 1,
  or whether 50 events is an acceptable ceiling.
- **OQ-3.** Connection preference order: §6.3 defines
  `NetskopeID > Username-Password-Authentication > google-oauth2`. Confirm this
  ranking is correct for the `nskp` tenant with the CIAM platform team;
  other social or enterprise connections (SAML, ADFS) may need to be added to
  the ranking before implementation.
- **OQ-4.** Sync staleness threshold: 7 days is the Phase 1 default for
  `sync_stale`. Should this be made configurable via SSM Parameter Store (e.g.,
  `/ciam/auth0-agent/sync-stale-days`) to allow tuning without a deployment?
- **OQ-5.** `entitlements` write path: this spec explicitly denies all writes
  to the `entitlements` array. The remediation path (adding a keyword to grant
  access) belongs to a future write-enabled agent or L2 action outside this
  pipeline. Confirm with the team that this boundary is correct for Phase 1
  and document the out-of-band entitlement modification procedure in
  `docs/adr/` before launch.
