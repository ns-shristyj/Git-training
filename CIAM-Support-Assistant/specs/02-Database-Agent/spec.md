---
spec_id: SPEC-CIAM-0002
capability: ciam-database-agent
status: Draft
owner: Shristy Jaiswal
reviewers: [Peer]
approver: Rehman
prd: https://confluence.netskope.example/display/GIS/ciam-database-agent-prd  # placeholder — link to docs/confluence/ciam-database-agent/prd.md until Phase 0 lands
jira_epic: GIS-EPIC-CIAM  # placeholder — see docs/jira/ciam-database-agent-epic.md until Phase 0 lands
version: 0.1.0
created: 2026-06-23
last_updated: 2026-06-23
---

# spec.md — CIAM Database Agent (Agent 2)

> This is the **executable contract**. Code, evals, and PR review trace back to
> this file. Acceptance criteria map 1:1 to eval cases under
> `evals/ciam-database-agent/cases/`. Posture/read-only invariants (AC-7, AC-8,
> AC-9) are **gating in CI**: a regression fails the PR.

## 1. Summary

The CIAM Database Agent is a **Layer 1 read-only execution agent** in the CIAM
Support Assistant pipeline. It is invoked by the orchestrator when Agent 1
(Intent Classifier) sets `invoke_agent_2: true` in the routing envelope. It
receives a user email address, queries the `NetskopeID-Accounts` DynamoDB table
— a Salesforce read replica maintained by the platform team's CDC sync pipeline
— and returns a structured account payload to the orchestrator for onward
consumption by Agents 4 (Knowledge Base) and 5 (Response Generator). The agent
performs **no diagnosis, no birthright evaluation, and no response generation**.
It only fetches database records and returns them. Its only permitted AWS
interaction is read-only access to a single DynamoDB table via the
`Auth0DynamoDBAccessRole` IAM execution role; it performs **no writes** to
DynamoDB or any other system.

## 2. Goals / Non-Goals

### Goals

- Accept a user **email address** (and optionally an account name) from the
  orchestrator's routing envelope and return the corresponding Salesforce
  account data from DynamoDB.
- Execute **Tool 1 (`get_account_by_email`)**: query `NetskopeID-Accounts` via
  the `contact_email` GSI and return core account fields.
- Execute **Tool 2 (`get_account_history`)**: query DynamoDB for field-level
  change records on the account within the last 30 days to surface recent
  status mutations.
- Return a single **Pydantic-validated `AccountPayload`** JSON object to the
  orchestrator.
- Surface data-quality signals: flag stale data (`last_synced_at > 24 hours`),
  flag multiple accounts found for the same email, and propagate DynamoDB
  errors without crashing.
- Hold the Phase 1 **read-only posture invariant**: zero DynamoDB writes, zero
  calls to Auth0, Salesforce direct, Jira, Slack, or any other system, both by
  IAM deny *and* by code-side assertion.

### Non-goals

- Diagnosing why a user lacks access (delegated to Agent 4 and Agent 5).
- Evaluating whether a user's birthright is correct (delegated to Agent 4).
- Querying Auth0 for user metadata or login history (delegated to Agent 3).
- Writing, updating, or deleting any DynamoDB record.
- Querying Salesforce directly — the DynamoDB replica is the sole data source
  for this agent (see §1 rationale).
- Populating missing Salesforce data or triggering a sync refresh.
- Member-account or multi-org DynamoDB lookups (out of scope for Phase 1).

## 3. Inputs

| Input | Source | Notes |
| :--- | :--- | :--- |
| `email` | Agent 1 routing envelope (`extracted_email`) | Required. String. The primary lookup key for the `contact_email` GSI on `NetskopeID-Accounts`. |
| `account_name` | Agent 1 routing envelope (optional) | Optional. String. If present, passed directly to Tool 2 (`get_account_history`) to skip the name-resolution step; otherwise derived from Tool 1's response. |
| `intent` | Agent 1 routing envelope (`intent`) | Read-only context. Used to decide whether `get_account_history` is worth calling (called for all intents that invoke Agent 2; see §6.2). |
| `run_id` | AgentCore run header | Propagated to the `AccountPayload` and any posture-violation findings for end-to-end traceability. |

The agent is **stateless** between invocations. It holds no cache, no session
state, and no prior-run memory.

## 4. Permitted Tools / Authorization Boundary

The agent's IAM execution role (`Auth0DynamoDBAccessRole`) MAY perform **only**
the actions in this table. The CDK stack in `infra/aws/ciam-database-agent/`
MUST instantiate this exact policy shape; no `*` action wildcards are permitted.

| Service | Action | Resource scope |
| :--- | :--- | :--- |
| DynamoDB | `dynamodb:Query` | `arn:aws:dynamodb:*:*:table/NetskopeID-Accounts` and its GSI `arn:aws:dynamodb:*:*:table/NetskopeID-Accounts/index/*` |
| DynamoDB | `dynamodb:GetItem` | `arn:aws:dynamodb:*:*:table/NetskopeID-Accounts` |
| Bedrock | `bedrock:InvokeModel` | Scoped to `claude-haiku-*` model ARN only |

All other AWS service actions — including every DynamoDB write action, every
other table ARN, Auth0, Salesforce, SNS, S3, SSM, Jira, and Slack — are
**not permitted** and are explicitly denied (see §5).

Any tool implementation that calls an API not in this table is a **defect and a
release blocker**.

### 4.1 Tool Definitions

#### Tool 1 — `get_account_by_email(email: str) → AccountRecord | None`

Queries `NetskopeID-Accounts` using the `contact_email` GSI.

**DynamoDB call:** `dynamodb:Query` on index `contact_email-index`,
`KeyConditionExpression: contact_email = :email`.

**Salesforce field mapping** (DynamoDB attribute → returned field):

| DynamoDB attribute | Returned field | Type | Salesforce source |
| :--- | :--- | :--- | :--- |
| `account_name` | `account_name` | `str` | `Account.Name` |
| `account_status` | `account_status` | `AccountStatus` enum | `Account.Account_Status__c` |
| `customer_status` | `customer_status` | `CustomerStatus` enum | `Account.Customer_Status__c` |
| `active_tenant_count` | `active_tenant_count` | `int` | `Tenant_Request__c` (count) |
| `tenant_url` | `tenant_url` | `str \| None` | `Tenant_Request__c` (URL) |
| `sf_user_exists` | `sf_user_exists` | `bool` | `User` object presence |
| `sf_user_active` | `sf_user_active` | `bool` | `User.IsActive` |
| `last_synced_at` | `last_synced_at` | `datetime` (UTC) | CDC pipeline metadata |

**`AccountStatus` enum values:** `Customer`, `Prospect - Net New`,
`Prospect - Churned`, `Partner`, `Former Customer`.

**`CustomerStatus` enum values:** `Active`, `Churned`, `Inactive`.

**Returns:** A single `AccountRecord` if exactly one match is found. If zero
records match, returns `None` (caller sets `account_found: false`). If multiple
records match, returns all as a list and sets the `multiple_accounts_found`
warning (see §6.3).

#### Tool 2 — `get_account_history(account_name: str) → list[ChangeRecord]`

Queries DynamoDB for field-level change log records on the given account,
filtered to records where `changed_date >= (now − 30 days)`.

**DynamoDB call:** `dynamodb:Query` on the account history table partition key
`account_name`, with a `changed_date` range condition.

**Returns:** An array (possibly empty) of `ChangeRecord` objects:

```python
class ChangeRecord(BaseModel):
    field_name: str        # e.g. "account_status"
    old_value: str
    new_value: str
    changed_date: datetime # UTC
    changed_by: str        # Salesforce user or sync pipeline identifier
```

An empty array is a valid successful result (no recent changes). A DynamoDB
error on this tool does NOT abort the invocation — the `AccountPayload` is
returned with `recent_changes: []` and the error surfaced in
`history_fetch_error` (see §7).

## 5. Explicit Denies (Phase 1 invariants)

The CDK IAM role MUST attach an explicit `Deny` statement covering the
following actions with `Resource: "*"`. These denies are **gating posture
invariants** — CI fails the PR if they are missing or weakened.

| Action | Reason |
| :--- | :--- |
| `dynamodb:PutItem` | No agent may write account records. |
| `dynamodb:UpdateItem` | No agent may mutate existing records. |
| `dynamodb:DeleteItem` | No agent may delete records. |
| `dynamodb:BatchWriteItem` | No agent may bulk-write records. |
| `dynamodb:TransactWriteItems` | No transactional writes permitted. |
| `dynamodb:CreateTable` | No schema changes permitted. |
| `dynamodb:DeleteTable` | No schema changes permitted. |
| All `auth0:*` equivalent HTTP calls | Auth0 is owned by Agent 3; no direct calls from this agent. |
| All Salesforce API calls | DynamoDB replica is the only permitted data path. |
| `sns:Publish` | The orchestrator, not this agent, owns alert fanout. |
| `s3:*` | No audit bucket or baseline access needed for data lookup. |
| `ssm:GetParameter` (any path) | No SSM config reads; all config is in DynamoDB. |
| `sts:AssumeRole` | No cross-account or cross-service role assumption. |
| `iam:*` | No IAM reads or writes. |

Defense in depth: in addition to these IAM denies, the agent's tool layer
(`core/agentcore/action_group.py`) MUST contain an explicit allow-list of
exactly two permitted tool names — `get_account_by_email` and
`get_account_history`. Any invocation of a tool name outside this list raises
`PostureViolationError` *before* any SDK call is issued, and the violation is
recorded as a `posture-violation` finding (CRITICAL) for the Oversight Agent
to surface.

## 6. Behavior

An invocation proceeds in the following deterministic steps:

1. **Validate input.** Confirm the routing envelope contains a non-empty,
   syntactically valid `email` field. If `email` is absent or malformed (no
   `@` character, empty string), return an `AccountPayload` with
   `account_found: false`, all account fields `null`, and
   `error: "invalid_email_input"` without querying DynamoDB.

2. **Fetch account record (Tool 1).** Call `get_account_by_email(email)`.
   - On success with one result → populate all account fields; proceed to
     step 3.
   - On zero results → set `account_found: false`, all account fields `null`;
     skip step 3; proceed to step 4.
   - On multiple results → set `account_found: true`, populate
     `accounts` as an array of all matching `AccountRecord` objects, set
     `data_warnings: ["multiple_accounts_found"]`; use the **first** account's
     `account_name` for step 3.
   - On DynamoDB error → set `account_found: false`, `error` to the error
     message; skip step 3; proceed to step 4.

3. **Fetch account history (Tool 2).** Call
   `get_account_history(account_name)` using the `account_name` resolved in
   step 2 (or the `account_name` supplied directly in the routing envelope if
   present). Populate `recent_changes` with the returned array. On DynamoDB
   error, set `recent_changes: []` and `history_fetch_error` to the error
   message; do **not** abort the invocation.

4. **Evaluate data freshness.** Inspect `last_synced_at` from the Tool 1
   result. If `(now_utc − last_synced_at) > 24 hours`, append
   `"data_may_be_stale"` to `data_warnings`.

5. **Assemble and validate payload.** Construct the `AccountPayload` (schema
   in §7). Validate against Pydantic strict mode. On validation failure, return
   `error: "payload_validation_error"` with the validation message; do not
   return a partially-built payload.

6. **Return payload.** Return the complete `AccountPayload` to the
   orchestrator. No writes to any external system occur at any step.

### 6.1 Tool Call Order and Conditionality

Tool 2 (`get_account_history`) is called **only** when Tool 1 returns at least
one account record (i.e., `account_found: true`). It is skipped — and
`recent_changes` is set to `[]` — in the following cases:

- Email not found in DynamoDB.
- Tool 1 returns a DynamoDB error.
- `account_name` cannot be resolved from Tool 1 output or the routing
  envelope.

### 6.2 History Fetch Scope

Tool 2 always queries for changes in the **last 30 calendar days** relative to
the invocation timestamp. This window is not configurable in Phase 1. The
primary signal consumed by downstream agents is any change to `account_status`
within this window, which explains stale birthright conditions.

### 6.3 Multiple Accounts Edge Case

When Tool 1 returns more than one `AccountRecord` for the same email (e.g., a
contact associated with multiple Salesforce accounts), the agent:

- Sets `account_found: true`.
- Populates `accounts` as a typed array of all matching records (not a single
  `AccountRecord`).
- Appends `"multiple_accounts_found"` to `data_warnings`.
- Passes the **first** account's `account_name` to Tool 2.
- Does **not** attempt to arbitrate which account is "correct" — that
  determination is deferred to Agent 5 (Response Generator).

## 7. Outputs

### 7.1 Account Payload Schema

The agent returns exactly one `AccountPayload` object to the orchestrator.

```python
class AccountPayload(BaseModel):
    schema_version: Literal["1.0"]
    spec_id:        Literal["SPEC-CIAM-0002"]
    agent:          Literal["ciam-database-agent"]
    run_id:         str                        # uuid4, from AgentCore run header
    fetched_at:     datetime                   # UTC, isoformat

    # --- Primary lookup result ---
    account_found:       bool
    accounts:            list[AccountRecord]   # length 0 (not found), 1 (normal),
                                               # or N>1 (multiple_accounts_found)

    # --- Change history ---
    recent_changes:      list[ChangeRecord]    # last 30 days; [] when not fetched
    history_fetch_error: str | None            # non-null if Tool 2 failed

    # --- Data quality signals ---
    data_freshness:      DataFreshness         # see below
    data_warnings:       list[str]             # e.g. ["data_may_be_stale",
                                               #        "multiple_accounts_found"]

    # --- Error ---
    error:               str | None            # null on full success;
                                               # message string on Tool 1 failure

class AccountRecord(BaseModel):
    account_name:        str
    account_status:      Literal[
                             "Customer",
                             "Prospect - Net New",
                             "Prospect - Churned",
                             "Partner",
                             "Former Customer",
                         ]
    customer_status:     Literal["Active", "Churned", "Inactive"]
    active_tenant_count: int
    tenant_url:          str | None
    sf_user_exists:      bool
    sf_user_active:      bool

class DataFreshness(BaseModel):
    last_synced_at:      datetime | None       # null when account_found is false
    age_hours:           float | None          # (now − last_synced_at) in hours
    is_stale:            bool                  # true when age_hours > 24
```

### 7.2 Posture Violation Finding

If the agent's code attempts any denied action (DynamoDB write, Auth0 call,
etc.), it MUST emit a `PostureViolationFinding` conforming to
`core/findings/schema.py` and abort the invocation. No `AccountPayload` is
returned in this case.

```python
class PostureViolationFinding(BaseModel):
    schema_version: Literal["1.0"]
    spec_id:        Literal["SPEC-CIAM-0002"]
    agent:          Literal["ciam-database-agent"]
    run_id:         str
    detected_at:    datetime
    category:       Literal["posture-violation"]
    severity:       Literal["CRITICAL"]
    evidence:       dict[str, Any]  # {"attempted_action": "<dynamodb:PutItem|...>"}
```

## 8. Failure Handling

- **DynamoDB timeout (Tool 1).** If `dynamodb:Query` on `get_account_by_email`
  exceeds the SDK timeout (max 5 s, 3 retries with exponential backoff and
  jitter), return `AccountPayload` with `account_found: false`,
  `error: "dynamodb_timeout"`, and all account fields `null`. The invocation
  does not raise an unhandled exception.
- **DynamoDB throttle / `ProvisionedThroughputExceededException` (Tool 1).**
  Retry up to 3 times with exponential backoff. After max retries, return
  `error: "dynamodb_throttled"`.
- **DynamoDB error (Tool 2).** Tool 2 failure is **non-fatal**. Return
  `recent_changes: []` and set `history_fetch_error` to the error class name.
  The `AccountPayload` is still returned with all Tool 1 fields populated.
- **Email not found.** Return `account_found: false`, `accounts: []`,
  `recent_changes: []`, `error: null` (not-found is not an error; it is a
  valid, expected result for `ACCOUNT_NOT_FOUND` intents).
- **Multiple accounts found.** Non-fatal. See §6.3. No exception is raised.
- **Stale data.** Non-fatal. `"data_may_be_stale"` is added to `data_warnings`
  and `data_freshness.is_stale` is set to `true`. The payload is returned
  normally.
- **Payload validation failure.** If Pydantic validation of the assembled
  `AccountPayload` fails (unexpected DynamoDB attribute type, enum value not in
  schema, etc.), return `error: "payload_validation_error"` with the validation
  detail. Do not return a partially-constructed payload.
- **Posture violation (tripwire).** Any code path that attempts a denied action
  raises `PostureViolationError`, emits a `posture-violation` finding
  (CRITICAL), and aborts the invocation with no `AccountPayload` returned.
  This is a release-blocker defect.

## 9. Acceptance Criteria (Given/When/Then)

Each AC maps 1:1 to an eval case at `evals/ciam-database-agent/cases/ac-N.yaml`.
ACs marked **GATING** fail the PR in CI if they regress.

### AC-1 — Known email returns full account record

- **Given** a routing envelope with `email: "alice@example.com"` and a
  DynamoDB fixture containing exactly one matching record with
  `account_status: "Customer"`, `customer_status: "Active"`,
  `active_tenant_count: 2`, and `sf_user_exists: true`,
- **When** the agent runs,
- **Then** the `AccountPayload` has `account_found: true`, `accounts` contains
  exactly one `AccountRecord` with all fields matching the fixture,
  `error: null`, and `data_warnings` does not contain `"multiple_accounts_found"`.

### AC-2 — Email not found returns account_found false with no error

- **Given** a routing envelope with `email: "unknown@example.com"` and a
  DynamoDB fixture containing no matching record,
- **When** the agent runs,
- **Then** the `AccountPayload` has `account_found: false`, `accounts: []`,
  `recent_changes: []`, and `error: null`.

### AC-3 — Recent account_status change appears in history

- **Given** a routing envelope with a known email and a DynamoDB history
  fixture containing one `ChangeRecord` with `field_name: "account_status"`,
  `old_value: "Customer"`, `new_value: "Former Customer"`, and `changed_date`
  within the last 30 days,
- **When** the agent runs,
- **Then** `recent_changes` contains exactly that `ChangeRecord` with all
  fields populated correctly.

### AC-4 — Stale data flagged when last_synced_at exceeds 24 hours

- **Given** a DynamoDB fixture where `last_synced_at` is 25 hours before the
  invocation timestamp,
- **When** the agent runs,
- **Then** `data_warnings` contains `"data_may_be_stale"`,
  `data_freshness.is_stale: true`, and `data_freshness.age_hours >= 25.0`.

### AC-5 — Multiple accounts for same email flagged and all returned

- **Given** a DynamoDB fixture where two `AccountRecord` objects share the
  same `contact_email`,
- **When** the agent runs,
- **Then** `account_found: true`, `accounts` has length 2,
  `data_warnings` contains `"multiple_accounts_found"`, and no exception is
  raised.

### AC-6 — Tool 2 failure is non-fatal; payload still returned

- **Given** a known email with a valid Tool 1 DynamoDB fixture and a simulated
  `ProvisionedThroughputExceededException` on the Tool 2 history query,
- **When** the agent runs,
- **Then** `account_found: true` with all Tool 1 fields populated,
  `recent_changes: []`, `history_fetch_error` is non-null, and `error: null`.

### AC-7 — Agent attempts `dynamodb:PutItem` (GATING — posture invariant)

- **Given** a malformed tool call or code path that attempts
  `dynamodb:PutItem` on `NetskopeID-Accounts`,
- **When** the agent processes the invocation,
- **Then** `PostureViolationError` is raised *before* any DynamoDB SDK call
  is made, no `AccountPayload` is returned, and a `posture-violation`
  (CRITICAL) finding is emitted. **Gating in CI.**

### AC-8 — Agent attempts Auth0 API call (GATING — posture invariant)

- **Given** a malformed tool call or code path that attempts an HTTP request
  to the Auth0 Management API from within this agent,
- **When** the agent processes the invocation,
- **Then** `PostureViolationError` is raised before any HTTP call is made, no
  `AccountPayload` is returned, and a `posture-violation` (CRITICAL) finding
  is emitted. **Gating in CI.**

### AC-9 — Schema conformance (GATING — schema invariant)

- **Given** any invocation that produces an `AccountPayload`,
- **When** the payload is validated against `AccountPayload` (Pydantic strict
  mode),
- **Then** it passes validation without error; any failure fails the run and
  the CI gate. **Gating in CI.**

### AC-10 — DynamoDB timeout on Tool 1 returns structured error payload

- **Given** a simulated DynamoDB SDK timeout on `get_account_by_email` after
  max retries,
- **When** the agent runs,
- **Then** the `AccountPayload` has `account_found: false`,
  `error: "dynamodb_timeout"`, `accounts: []`, `recent_changes: []`, and no
  unhandled exception is raised.

### AC-11 — account_name from routing envelope bypasses name resolution

- **Given** a routing envelope with both a valid `email` and an
  `account_name: "Acme Corp"`, and a DynamoDB fixture that would resolve to a
  different name from the Tool 1 result,
- **When** the agent runs,
- **Then** Tool 2 is called with `account_name: "Acme Corp"` (the supplied
  value), not the value derived from the Tool 1 result.

### AC-12 — No history records in last 30 days returns empty array

- **Given** a known email with a valid Tool 1 result and a DynamoDB history
  fixture containing only records older than 30 days,
- **When** the agent runs,
- **Then** `recent_changes: []` and `history_fetch_error: null`.

## 10. Eval Mapping Table

| AC | Eval case file | Type | Gating |
| :--- | :--- | :--- | :--- |
| AC-1 | `evals/ciam-database-agent/cases/ac-1.yaml` | structured-assertion | no |
| AC-2 | `evals/ciam-database-agent/cases/ac-2.yaml` | structured-assertion | no |
| AC-3 | `evals/ciam-database-agent/cases/ac-3.yaml` | structured-assertion | no |
| AC-4 | `evals/ciam-database-agent/cases/ac-4.yaml` | structured-assertion | no |
| AC-5 | `evals/ciam-database-agent/cases/ac-5.yaml` | structured-assertion | no |
| AC-6 | `evals/ciam-database-agent/cases/ac-6.yaml` | failure-mode | no |
| AC-7 | `evals/ciam-database-agent/cases/ac-7.yaml` | posture-invariant | **yes** |
| AC-8 | `evals/ciam-database-agent/cases/ac-8.yaml` | posture-invariant | **yes** |
| AC-9 | `evals/ciam-database-agent/cases/ac-9.yaml` | schema-invariant | **yes** |
| AC-10 | `evals/ciam-database-agent/cases/ac-10.yaml` | failure-mode | no |
| AC-11 | `evals/ciam-database-agent/cases/ac-11.yaml` | structured-assertion | no |
| AC-12 | `evals/ciam-database-agent/cases/ac-12.yaml` | structured-assertion | no |

## 11. Open Questions

- **OQ-1.** History table name and partition key: this spec assumes the account
  history resides in a separate DynamoDB table partitioned by `account_name`.
  Confirm the exact table name, partition key, and sort key schema with the
  platform team before implementation.
- **OQ-2.** GSI name: this spec refers to the email lookup index as
  `contact_email-index`. Confirm the exact GSI name deployed in the
  `NetskopeID-Accounts` table.
- **OQ-3.** Multiple-accounts arbitration: when two `AccountRecord` objects are
  returned for the same email, Agent 5 (Response Generator) currently receives
  both with no ranking. Should Agent 2 apply a preference rule (e.g., prefer
  `account_status: "Customer"` over `"Former Customer"`) or remain neutral and
  leave arbitration entirely to Agent 5? Pending design decision.
- **OQ-4.** History window: 30 days is the Phase 1 default. Should this be
  made configurable via SSM Parameter Store (e.g.,
  `/ciam/database-agent/history-window-days`) to allow tuning without a
  deployment, or is a hardcoded default sufficient for Phase 1?
- **OQ-5.** `tenant_url` cardinality: `Tenant_Request__c` is a related list on
  the Salesforce Account object, meaning a single account may have multiple
  tenant URLs. Confirm whether the DynamoDB replica stores only the primary
  tenant URL (string) or an array of URLs, and update the `AccountRecord`
  schema accordingly before Phase 1 implementation.
