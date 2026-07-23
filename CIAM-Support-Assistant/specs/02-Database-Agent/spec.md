---
spec_id: SPEC-CIAM-0002
capability: ciam-database-agent
status: Draft
owner: Shristy Jaiswal
reviewers: [Peer]
approver: Ritwik Mandal
prd: https://confluence.netskope.example/display/GIS/ciam-database-agent-prd  # placeholder — link to docs/confluence/ciam-database-agent/prd.md until Phase 0 lands
jira_epic: GIS-EPIC-CIAM  # placeholder — see docs/jira/ciam-database-agent-epic.md until Phase 0 lands
version: 0.3.0
created: 2026-06-23
last_updated: 2026-07-23
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
receives a user email address, queries the single **`NetskopeID`** DynamoDB
table — a Salesforce/identity read replica maintained by the platform team's
sync pipeline — via the **`email`** GSI, and returns a structured, flattened
account payload to the orchestrator for onward consumption by Agents 4
(Knowledge Base) and 5 (Response Generator). The agent performs **no
diagnosis, no birthright evaluation, and no response generation**. It only
fetches the record and returns it. Its only permitted AWS interaction is
read-only access to the `NetskopeID` table via the
**`CIAMAgentDynamoDBAccessRole`** IAM execution role; it performs **no writes**
to DynamoDB or any other system.

> **Single table, single tool (Phase 1).** There is exactly **one** DynamoDB
> table — `NetskopeID` — and no separate account-history table exists. Agent 2
> therefore exposes exactly **one** tool, `get_account_by_email`. The
> previously-assumed `get_account_history` tool and its 30-day change-log
> feature are **removed from scope** in this revision — see Non-goals and
> OQ-1.

## 2. Goals / Non-Goals

### Goals

- Accept a user **email address** from the orchestrator's routing envelope
  and return the corresponding identity/account record from the `NetskopeID`
  table.
- Execute **Tool 1 (`get_account_by_email`)**: query `NetskopeID` via the
  **`email`** GSI and return the permitted attribute set (see §4.1),
  flattened into a clean `AccountRecord` schema.
- Return a single **Pydantic-validated `AccountPayload`** JSON object to the
  orchestrator.
- Surface data-quality signals as two **independent** warnings: general sync
  staleness (`last_sync` > 24h → `data_may_be_stale`) and birthright/
  entitlement sync staleness (`last_daily_sync` > 24h →
  `birthright_sync_stale`) — see §6.4. These are tracked separately because
  they answer different questions: "is this record stale in general" vs. "is
  the birthright/entitlement data specifically stale" (the latter is the
  direct signal for Agent 1's `SYNC_ISSUE` intent).
- Flag multiple records found for the same email, and propagate DynamoDB
  errors without crashing.
- Hold the Phase 1 **read-only posture invariant**: zero DynamoDB writes, zero
  calls to Auth0, Salesforce direct, Jira, Slack, or any other system, both by
  IAM deny *and* by code-side assertion.

### Non-goals

- Diagnosing why a user lacks access (delegated to Agent 4 and Agent 5).
- Evaluating whether a user's birthright is correct (delegated to Agent 4).
- Querying Auth0 for user metadata or login history (delegated to Agent 3).
- Writing, updating, or deleting any DynamoDB record.
- Querying Salesforce directly — the `NetskopeID` DynamoDB replica is the sole
  data source for this agent (see §1).
- Populating missing Salesforce data or triggering a sync refresh.
- **Account change-history / audit-trail lookups.** There is no history table
  in Phase 1 (see §1). This was assumed in an earlier revision and is now
  explicitly out of scope — see OQ-1 for the condition under which it may be
  reintroduced.
- Member-account or multi-org DynamoDB lookups (out of scope for Phase 1).

## 3. Inputs

| Input | Source | Notes |
| :--- | :--- | :--- |
| `email` | Agent 1 routing envelope (`extracted_email`) | Required. String. The primary lookup key for the `email` GSI on `NetskopeID`. |
| `intent` | Agent 1 routing envelope (`intent`) | Read-only context. Not currently used to branch behavior in Phase 1 — Agent 2 always runs the same single lookup regardless of intent. Retained for future use (e.g. intent-specific field filtering). |
| `run_id` | AgentCore run header | Propagated to the `AccountPayload` and any posture-violation findings for end-to-end traceability. |

The agent is **stateless** between invocations. It holds no cache, no session
state, and no prior-run memory.

## 4. Permitted Tools / Authorization Boundary

The agent's IAM execution role (**`CIAMAgentDynamoDBAccessRole`**) MAY perform
**only** the actions in this table. The CDK stack in
`infra/aws/ciam-database-agent/` MUST instantiate this exact policy shape; no
`*` action wildcards are permitted.

| Service | Action | Resource scope |
| :--- | :--- | :--- |
| DynamoDB | `dynamodb:Query` | `arn:aws:dynamodb:*:*:table/NetskopeID` and its GSI `arn:aws:dynamodb:*:*:table/NetskopeID/index/*` |
| DynamoDB | `dynamodb:GetItem` | `arn:aws:dynamodb:*:*:table/NetskopeID` |

> **No model inference.** Unlike Agent 1, Agent 2 performs a deterministic
> DynamoDB lookup only — there is no ambiguity to resolve and therefore no LLM
> reasoning step. `BedrockAgentCoreApp` is used purely as the AgentCore
> *hosting* framework (the runtime that receives and responds to invocations);
> it does not imply a `bedrock:InvokeModel` call happens inside. Agent 2's IAM
> role and code-level posture guard (`ALLOWED_ACTIONS` in agent.py) therefore
> grant **no** Bedrock model-invocation permission at all — see §5.

All other AWS service actions — including every DynamoDB write action, every
other table ARN, Auth0, Salesforce, SNS, S3, SSM, Jira, and Slack — are
**not permitted** and are explicitly denied (see §5).

Any tool implementation that calls an API not in this table is a **defect and a
release blocker**.

### 4.1 Permitted Attributes

The agent MAY read **only** the following attributes from the `NetskopeID`
item. Any attribute not in this list MUST NOT be read, returned, or logged —
reading an attribute outside this set is a defect even if the IAM/DynamoDB
call itself succeeds, since the restriction is at the application/field level,
not just the table level.

| Attribute | Shape | Notes |
| :--- | :--- | :--- |
| `email` | `str` | GSI partition key for lookup. |
| `username` | `str` | |
| `given_name` | `str` | |
| `family_name` | `str` | |
| `name` | `str` | Full display name. |
| `user_id` | `str` | |
| `fed_og_id` | `str` | Federated/org identifier. |
| `iam_a` | `str` | |
| `company_name` | `str` | |
| `country_name` | `str` | |
| `job_title` | `str` | |
| `state_province` | `str` | |
| `topics_of_interest` | `list[str]` or `str` | Exact shape TBD — see OQ-5. |
| `last_login` | `datetime` | |
| `last_sync` | `datetime` | General record sync timestamp — drives `data_may_be_stale`. |
| `last_daily_sync` | `datetime` | Birthright/entitlement-specific daily sync timestamp — drives `birthright_sync_stale`. |
| `birthright` | nested object/list | Raw birthright data; passed through, evaluated by Agent 4, not this agent. |
| `entitlements` | nested object/list | Raw entitlement data; passed through, evaluated by Agent 4, not this agent. |
| `permissions` | nested object/list | Raw permission data; passed through. |
| `sf_account` | nested object (see §4.2) | Salesforce `Account` mirror. Flattened into `AccountRecord` fields — see §4.2. |
| `sf_contact` | nested object (see §4.2) | Salesforce `Contact` mirror. Flattened into `AccountRecord` fields — see §4.2. |
| `ns_tenants` | nested array (see §4.2) | Netskope tenant-provisioning records. Flattened/summarized — see §4.2. |

### 4.2 Salesforce-Mirror Object Shapes and Flattening

`sf_account`, `sf_contact`, and `ns_tenants` are stored in DynamoDB as nested
JSON mirroring the underlying Salesforce objects, not as flat attributes. This
agent flattens them into the top-level `AccountRecord` fields defined in §7.1
rather than passing the nested objects through as-is, so downstream agents
(4 and 5) consume a stable, simplified shape instead of re-deriving it
themselves on every call.

**`sf_account` (raw shape, per platform spec):**

```json
{
  "Id": "...",
  "IsDeleted": "...",
  "Name": "...",
  "Type": "...",
  "ParentId": "...",
  "OwnerId": "...",
  "Account_Status__c": "...",
  "Customer_Status__c": "...",
  "Primary_Partner_Type__c": "...",
  "Secondary_Partner_Type__c": "...",
  "Tertiary_Partner_Type__c": "..."
}
```

**`sf_contact` (raw shape, per platform spec):**

```json
{
  "Id": "...",
  "AccountId": "...",
  "Name": "...",
  "FirstName": "...",
  "LastName": "...",
  "Email": "...",
  "Title": "...",
  "IsDeleted": "...",
  "CreatedDate": "..."
}
```

**`ns_tenants` (raw shape, per platform spec — an array):**

```json
[
  {
    "Tenant Ticket": "...",
    "Account_Id__c": "...",
    "Tenant_Type_Formula__c": "...",
    "Deprovisioning_done__c": "...",
    "Tenant_Provision_Status__c": "..."
  }
]
```

**Flattening map (nested attribute → `AccountRecord` field):**

| Source object.field | Returned `AccountRecord` field | Type | Notes |
| :--- | :--- | :--- | :--- |
| `sf_account.Name` | `account_name` | `str` | |
| `sf_account.Account_Status__c` | `account_status` | `str` | Raw Salesforce picklist value; not constrained to a fixed enum in Phase 1 — see OQ-3. |
| `sf_account.Customer_Status__c` | `customer_status` | `str` | Raw Salesforce picklist value — see OQ-3. |
| `sf_account.Type` | `account_type` | `str \| None` | |
| `sf_account.Primary_Partner_Type__c` | `primary_partner_type` | `str \| None` | |
| `sf_account.IsDeleted` | `account_is_deleted` | `bool` | |
| `sf_contact.Email` | `contact_email` | `str` | Should match the top-level `email` GSI value; mismatch is logged as a warning — see §6.4. |
| `sf_contact.FirstName`, `sf_contact.LastName` | `contact_full_name` | `str` | Concatenated for display. |
| `sf_contact.Title` | `contact_title` | `str \| None` | |
| `sf_contact.IsDeleted` | `contact_is_deleted` | `bool` | |
| `ns_tenants[*].Tenant_Provision_Status__c` | `active_tenant_count` | `int` | Count of entries where provisioning is complete and deprovisioning is not — exact predicate pending OQ-4. |
| `ns_tenants[*]` | `tenants` | `list[TenantSummary]` | One `TenantSummary` per tenant entry (see §7.1); full list returned, not just the count. |

This mapping is the contract: if the platform team changes the raw Salesforce
field names inside `sf_account`/`sf_contact`/`ns_tenants`, this table — not
just the code — must be updated and re-reviewed, since the mapping is exactly
what makes the field-level renames in §7.1 traceable back to source.

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
| All Salesforce API calls | The `NetskopeID` DynamoDB replica is the only permitted data path. |
| `bedrock:InvokeModel` (any model ARN) | Agent 2 does no reasoning — it is a deterministic lookup, not an LLM-backed agent. No Bedrock model invocation permission is granted. |
| `sns:Publish` | The orchestrator, not this agent, owns alert fanout. |
| `s3:*` | No audit bucket or baseline access needed for data lookup. |
| `ssm:GetParameter` (any path) | No SSM config reads; all config is in DynamoDB. |
| `sts:AssumeRole` | No cross-account or cross-service role assumption. |
| `iam:*` | No IAM reads or writes. |

Defense in depth: in addition to these IAM denies, the agent's own code (see
`agent.py`) MUST contain an `ALLOWED_ACTIONS` allow-list of permitted AWS
**actions** — currently `{"dynamodb:Query", "dynamodb:GetItem"}` — checked via
an `assert_posture(action)` tripwire called before every AWS SDK call. Any
attempt to call an action outside this set (e.g. a reintroduced
`dynamodb:Scan` or any `bedrock:InvokeModel` call) raises
`PostureViolationError` *before* the SDK call is issued, and the violation is
recorded as a `posture-violation` finding (CRITICAL) for the Oversight Agent
to surface. The application-level attribute restriction in §4.1 MUST also be
enforced in code: the DynamoDB response is filtered down to the permitted
attribute set before any downstream processing, even though IAM cannot
express field-level restrictions natively.

## 6. Behavior

An invocation proceeds in the following deterministic steps:

1. **Validate input.** Confirm the routing envelope contains a non-empty,
   syntactically valid `email` field. If `email` is absent or malformed (no
   `@` character, empty string), return an `AccountPayload` with
   `account_found: false`, all account fields `null`, and
   `error: "invalid_email_input"` without querying DynamoDB.

2. **Fetch record (Tool 1).** Call `get_account_by_email(email)`.
   - On success with one result → filter the response to the permitted
     attribute set (§4.1), flatten `sf_account`/`sf_contact`/`ns_tenants` per
     §4.2, populate all account fields; proceed to step 3.
   - On zero results → set `account_found: false`, all account fields `null`;
     proceed to step 4.
   - On multiple results → set `account_found: true`, populate `accounts` as
     an array of all matching flattened `AccountRecord` objects, set
     `data_warnings: ["multiple_accounts_found"]`; proceed to step 3 using the
     **first** record for freshness evaluation.
   - On DynamoDB error → set `account_found: false`, `error` to the error
     message; proceed to step 4.

3. **Evaluate data freshness (two independent checks).** See §6.4.

4. **Assemble and validate payload.** Construct the `AccountPayload` (schema
   in §7). Validate against Pydantic strict mode. On validation failure,
   return `error: "payload_validation_error"` with the validation message; do
   not return a partially-built payload.

5. **Return payload.** Return the complete `AccountPayload` to the
   orchestrator. No writes to any external system occur at any step.

### 6.1 Multiple Records Edge Case

When Tool 1 returns more than one record for the same email, the agent:

- Sets `account_found: true`.
- Populates `accounts` as a typed array of all matching flattened
  `AccountRecord` objects (not a single object).
- Appends `"multiple_accounts_found"` to `data_warnings`.
- Evaluates freshness (§6.4) against the **first** record only.
- Does **not** attempt to arbitrate which record is "correct" — that
  determination is deferred to Agent 5 (Response Generator), consistent with
  the prior revision's approach (see OQ-2).

### 6.2 Email Cross-Check

If `sf_contact.Email` (flattened to `contact_email`) is present and differs
from the top-level `email` attribute used as the GSI lookup key, append
`"email_mismatch"` to `data_warnings`. This is non-fatal; the record is still
returned, since the mismatch itself may be diagnostically useful to Agent 5
(e.g. evidence of a stale Salesforce sync).

### 6.3 No History Lookups in Phase 1

There is no second tool call in this revision. The previously-specified
`get_account_history` tool, its 30-day change-window logic, and the
`ChangeRecord` schema are removed — see §1 and Non-goals. The `AccountPayload`
schema in §7 reflects this: there is no `recent_changes` field.

### 6.4 Data Freshness — Two Independent Signals

Unlike the prior revision (which used a single `last_synced_at` field), the
real schema exposes **two distinct sync timestamps**, and this agent evaluates
them **independently** rather than merging them into one signal, since they
answer different diagnostic questions:

- **`last_sync` staleness.** If `(now_utc − last_sync) > 24 hours`, append
  `"data_may_be_stale"` to `data_warnings`. This is the general
  "is this record current" signal.
- **`last_daily_sync` staleness.** If `(now_utc − last_daily_sync) > 24
  hours`, append `"birthright_sync_stale"` to `data_warnings`. This is the
  birthright/entitlement-specific signal, and is the direct evidentiary input
  for Agent 1's `SYNC_ISSUE` intent and Agent 4's birthright evaluation — a
  ticket reporting "I'm missing access that I should have" is far more
  actionable if this specific flag is set than if only the general
  `last_sync` flag is set.

Both checks run independently and both warnings may be present
simultaneously, exactly one of them, or neither. `data_freshness` in the
payload (§7.1) carries both ages and both booleans so Agent 5 can distinguish
"the record is generally stale" from "specifically, birthright/entitlements
may be out of sync" when composing its diagnosis.

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

    # --- Data quality signals ---
    data_freshness:      DataFreshness         # see below — two independent checks
    data_warnings:       list[str]             # e.g. ["data_may_be_stale",
                                               #        "birthright_sync_stale",
                                               #        "multiple_accounts_found",
                                               #        "email_mismatch"]

    # --- Error ---
    error:               str | None            # null on full success;
                                               # message string on Tool 1 failure

class AccountRecord(BaseModel):
    # --- Identity fields (top-level NetskopeID attributes) ---
    email:                str
    username:             str
    given_name:           str
    family_name:          str
    name:                 str
    user_id:              str
    fed_og_id:            str
    company_name:         str | None
    country_name:         str | None
    job_title:            str | None
    state_province:       str | None
    topics_of_interest:   list[str] | None     # exact shape pending OQ-5

    # --- Sync / activity timestamps ---
    last_login:           datetime | None
    last_sync:            datetime | None
    last_daily_sync:      datetime | None

    # --- Flattened sf_account fields (see §4.2) ---
    account_name:          str | None
    account_status:        str | None          # raw SF picklist value — see OQ-3
    customer_status:       str | None          # raw SF picklist value — see OQ-3
    account_type:          str | None
    primary_partner_type:  str | None
    account_is_deleted:    bool

    # --- Flattened sf_contact fields (see §4.2) ---
    contact_email:         str | None
    contact_full_name:     str | None
    contact_title:         str | None
    contact_is_deleted:    bool

    # --- Flattened ns_tenants fields (see §4.2) ---
    active_tenant_count:   int
    tenants:               list[TenantSummary]

    # --- Raw pass-through (evaluated by Agent 4, not this agent) ---
    birthright:            Any                 # raw structure, opaque to Agent 2
    entitlements:          Any                 # raw structure, opaque to Agent 2
    permissions:           Any                 # raw structure, opaque to Agent 2

class TenantSummary(BaseModel):
    tenant_ticket:               str | None
    account_id:                  str | None
    tenant_type:                 str | None
    deprovisioning_done:         bool | None
    tenant_provision_status:     str | None

class DataFreshness(BaseModel):
    last_sync:                datetime | None   # null when account_found is false
    last_sync_age_hours:      float | None
    is_stale:                  bool              # true when last_sync_age_hours > 24
    last_daily_sync:           datetime | None
    last_daily_sync_age_hours: float | None
    is_birthright_sync_stale:  bool              # true when last_daily_sync_age_hours > 24
```

### 7.2 Posture Violation Finding

If the agent's code attempts any denied action (DynamoDB write, Auth0 call,
reading an attribute outside §4.1, calling a tool outside the one-tool
allow-list, etc.), it MUST emit a `PostureViolationFinding` conforming to
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
- **Email not found.** Return `account_found: false`, `accounts: []`,
  `error: null` (not-found is not an error; it is a valid, expected result for
  `ACCOUNT_NOT_FOUND` intents).
- **Multiple accounts found.** Non-fatal. See §6.1. No exception is raised.
- **Stale data (either signal).** Non-fatal. The relevant warning(s) are
  added to `data_warnings` and the relevant `DataFreshness` booleans are set.
  The payload is returned normally.
- **Email mismatch (§6.2).** Non-fatal. `"email_mismatch"` is added to
  `data_warnings`. The payload is returned normally.
- **Payload validation failure.** If Pydantic validation of the assembled
  `AccountPayload` fails (unexpected DynamoDB attribute type, etc.), return
  `error: "payload_validation_error"` with the validation detail. Do not
  return a partially-constructed payload.
- **Posture violation (tripwire).** Any code path that attempts a denied
  action — including reading an attribute outside §4.1 or invoking any tool
  name other than `get_account_by_email` — raises `PostureViolationError`,
  emits a `posture-violation` finding (CRITICAL), and aborts the invocation
  with no `AccountPayload` returned. This is a release-blocker defect.

## 9. Acceptance Criteria (Given/When/Then)

Each AC maps 1:1 to an eval case at `evals/ciam-database-agent/cases/ac-N.yaml`.
ACs marked **GATING** fail the PR in CI if they regress.

### AC-1 — Known email returns full, flattened account record

- **Given** a routing envelope with `email: "alice@example.com"` and a
  `NetskopeID` fixture containing exactly one matching item with
  `sf_account.Account_Status__c: "Customer"`,
  `sf_account.Customer_Status__c: "Active"`, two `ns_tenants` entries with
  `Tenant_Provision_Status__c: "Provisioned"`, and `sf_contact.Email` matching
  the top-level `email`,
- **When** the agent runs,
- **Then** the `AccountPayload` has `account_found: true`, `accounts`
  contains exactly one `AccountRecord` with `account_status: "Customer"`,
  `customer_status: "Active"`, `active_tenant_count: 2`, `error: null`, and
  `data_warnings` does not contain `"multiple_accounts_found"` or
  `"email_mismatch"`.

### AC-2 — Email not found returns account_found false with no error

- **Given** a routing envelope with `email: "unknown@example.com"` and a
  `NetskopeID` fixture containing no matching item,
- **When** the agent runs,
- **Then** the `AccountPayload` has `account_found: false`, `accounts: []`,
  and `error: null`.

### AC-3 — last_sync stale flags data_may_be_stale only

- **Given** a `NetskopeID` fixture where `last_sync` is 25 hours before the
  invocation timestamp and `last_daily_sync` is 2 hours before the invocation
  timestamp,
- **When** the agent runs,
- **Then** `data_warnings` contains `"data_may_be_stale"` and does **not**
  contain `"birthright_sync_stale"`, `data_freshness.is_stale: true`, and
  `data_freshness.is_birthright_sync_stale: false`.

### AC-4 — last_daily_sync stale flags birthright_sync_stale only

- **Given** a `NetskopeID` fixture where `last_daily_sync` is 30 hours before
  the invocation timestamp and `last_sync` is 1 hour before the invocation
  timestamp,
- **When** the agent runs,
- **Then** `data_warnings` contains `"birthright_sync_stale"` and does **not**
  contain `"data_may_be_stale"`, `data_freshness.is_birthright_sync_stale:
  true`, and `data_freshness.is_stale: false`.

### AC-5 — Both staleness signals can fire simultaneously

- **Given** a `NetskopeID` fixture where both `last_sync` and
  `last_daily_sync` are more than 24 hours before the invocation timestamp,
- **When** the agent runs,
- **Then** `data_warnings` contains both `"data_may_be_stale"` and
  `"birthright_sync_stale"`, and both `DataFreshness` booleans are `true`.

### AC-6 — Multiple accounts for same email flagged and all returned

- **Given** a `NetskopeID` fixture where two items share the same `email`,
- **When** the agent runs,
- **Then** `account_found: true`, `accounts` has length 2, `data_warnings`
  contains `"multiple_accounts_found"`, and no exception is raised.

### AC-7 — Agent attempts `dynamodb:PutItem` (GATING — posture invariant)

- **Given** a malformed tool call or code path that attempts
  `dynamodb:PutItem` on `NetskopeID`,
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
  `error: "dynamodb_timeout"`, `accounts: []`, and no unhandled exception is
  raised.

### AC-11 — Attribute outside the permitted set is never returned (GATING — posture invariant)

- **Given** a `NetskopeID` fixture item that (due to a fixture/test error or a
  future schema change) contains an attribute not listed in §4.1,
- **When** the agent runs,
- **Then** the returned `AccountRecord` does not contain that attribute under
  any field name, and if the code path that would read it is exercised
  directly, `PostureViolationError` is raised. **Gating in CI.**

### AC-12 — Email mismatch between top-level email and sf_contact.Email is flagged

- **Given** a `NetskopeID` fixture where the top-level `email` attribute
  differs from `sf_contact.Email`,
- **When** the agent runs,
- **Then** `data_warnings` contains `"email_mismatch"`, `account_found:
  true`, and `error: null`.

### AC-13 — Only actions in `ALLOWED_ACTIONS` may be called (GATING — posture invariant)

- **Given** a code path that attempts any AWS action other than
  `dynamodb:Query` or `dynamodb:GetItem` (e.g. `dynamodb:Scan`,
  `dynamodb:PutItem`, or `bedrock:InvokeModel`),
- **When** `assert_posture(action)` is evaluated for that action,
- **Then** `PostureViolationError` is raised before any SDK call is made, no
  `AccountPayload` is returned, and a `posture-violation` (CRITICAL) finding
  is emitted. **Gating in CI.**

## 10. Eval Mapping Table

| AC | Eval case file | Type | Gating |
| :--- | :--- | :--- | :--- |
| AC-1 | `evals/ciam-database-agent/cases/ac-1.yaml` | structured-assertion | no |
| AC-2 | `evals/ciam-database-agent/cases/ac-2.yaml` | structured-assertion | no |
| AC-3 | `evals/ciam-database-agent/cases/ac-3.yaml` | structured-assertion | no |
| AC-4 | `evals/ciam-database-agent/cases/ac-4.yaml` | structured-assertion | no |
| AC-5 | `evals/ciam-database-agent/cases/ac-5.yaml` | structured-assertion | no |
| AC-6 | `evals/ciam-database-agent/cases/ac-6.yaml` | structured-assertion | no |
| AC-7 | `evals/ciam-database-agent/cases/ac-7.yaml` | posture-invariant | **yes** |
| AC-8 | `evals/ciam-database-agent/cases/ac-8.yaml` | posture-invariant | **yes** |
| AC-9 | `evals/ciam-database-agent/cases/ac-9.yaml` | schema-invariant | **yes** |
| AC-10 | `evals/ciam-database-agent/cases/ac-10.yaml` | failure-mode | no |
| AC-11 | `evals/ciam-database-agent/cases/ac-11.yaml` | posture-invariant | **yes** |
| AC-12 | `evals/ciam-database-agent/cases/ac-12.yaml` | structured-assertion | no |
| AC-13 | `evals/ciam-database-agent/cases/ac-13.yaml` | posture-invariant | **yes** |

## 11. Open Questions

- **OQ-1.** Account-history feature: an earlier revision of this spec assumed
  a second DynamoDB table for field-level change history (`get_account_history`,
  30-day window). The platform team has confirmed **no such table exists** in
  Phase 1. This feature is removed from scope (see §1, §6.3, Non-goals). If a
  history table is introduced in a later phase, this spec will need a new
  tool definition, IAM grant, and corresponding ACs reintroduced — tracked
  here so it isn't silently reintroduced without a spec revision.
- **OQ-2.** Multiple-accounts arbitration: when two `AccountRecord` objects
  are returned for the same email, Agent 5 (Response Generator) currently
  receives both with no ranking. Should Agent 2 apply a preference rule (e.g.,
  prefer `account_status: "Customer"` over a churned/former status) or remain
  neutral and leave arbitration entirely to Agent 5? Pending design decision.
- **OQ-3.** `account_status` / `customer_status` value set: §7.1 currently
  types these as raw `str` rather than a fixed enum, since the actual set of
  Salesforce picklist values for `Account_Status__c` and
  `Customer_Status__c` has not been confirmed against the live org. Confirm
  the full value list with the Salesforce/platform team and convert these to
  `Literal[...]` enums before Phase 1 implementation, mirroring the rigor of
  the original draft's (now-unconfirmed) enum approach.
- **OQ-4.** `active_tenant_count` predicate: §4.2 counts `ns_tenants` entries
  where provisioning is complete and deprovisioning is not, but the exact
  condition (which `Tenant_Provision_Status__c` values count as "active",
  and whether `Deprovisioning_done__c` is a boolean or a string flag) needs
  confirmation against real fixture data before implementation.
- **OQ-5.** `topics_of_interest` shape: confirm whether this attribute is
  stored as a DynamoDB string set, a list, or a comma-delimited string, so
  `AccountRecord.topics_of_interest` can be typed precisely rather than as
  `list[str] | None`.
- **OQ-6.** GSI name: this spec assumes the email lookup index exists as a
  GSI on the `email` attribute but does not assume a specific index name.
  Confirm the exact GSI name deployed on `NetskopeID` with the platform team
  before implementation (analogous to the unconfirmed GSI name in the prior
  revision, now corrected to the right attribute but still needing the
  literal index name).
- **OQ-7.** `birthright`, `entitlements`, and `permissions` internal shape:
  these are passed through opaquely (`Any`) in §7.1 since Agent 2 does not
  interpret them — only Agent 4 does. If Agent 4's spec ends up requiring a
  specific typed shape for these fields, this spec may need a corresponding
  typed model added so the contract between Agent 2 and Agent 4 is explicit
  rather than `Any`.
