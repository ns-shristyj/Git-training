---
spec_id: SPEC-CIAM-0004
capability: ciam-knowledge-base-agent
status: Draft
owner: Shristy Jaiswal
reviewers: [Peer]
approver: Ritwik Mandal
prd: https://confluence.netskope.example/display/GIS/ciam-knowledge-base-agent-prd  # placeholder — link to docs/confluence/ciam-knowledge-base-agent/prd.md until Phase 0 lands
jira_epic: GIS-EPIC-CIAM  # placeholder — see docs/jira/ciam-knowledge-base-agent-epic.md until Phase 0 lands
version: 0.3.0
created: 2026-06-23
last_updated: 2026-07-23
---

# spec.md — CIAM Knowledge Base Agent (Agent 4)

> This is the **executable contract**. Code, evals, and PR review trace back to
> this file. Acceptance criteria map 1:1 to eval cases under
> `evals/ciam-knowledge-base-agent/cases/`. Posture/read-only invariants
> (AC-9, AC-10, AC-11) are **gating in CI**: a regression fails the PR.

## 1. Summary

The CIAM Knowledge Base Agent is a **Layer 2 evaluation-and-enrichment agent**
in the CIAM Support Assistant pipeline. It is invoked by the orchestrator when
Agent 1 (Intent Classifier) sets `invoke_agent_4: true` in the routing
envelope. It receives pre-fetched account data from Agent 2 (Database Agent)
and identity data from Agent 3 (Auth0 Agent), and does two things in sequence:
first, it applies the Birthright & Entitlements Guide rules as **pure local
logic** to calculate what access a user should have and compare it against what
they actually have; second, it queries the Amazon Bedrock Knowledge Base (RAG
over Confluence docs, L1 runbooks, and past resolved TQI tickets) to surface
relevant documentation and similar past issues. It returns a single structured
`KnowledgeBasePayload` JSON object to the orchestrator for consumption by
Agent 5 (Response Generator). The agent **does not fetch data from Auth0 or
DynamoDB**, **does not generate the final L1 response**, and **does not write
to any system**. Its only external call is a read-only query to the Bedrock
Knowledge Base.

> **⚠ Provisional rule table — pending source verification.** The
> persona-derivation and expected-birthright table in §4.1 Tool 1 is
> **not yet confirmed against an authoritative source** and MUST be treated
> as provisional, not normative, until one of the following is supplied and
> reconciled against it:
>
> 1. The actual **Birthright & Entitlements Guide** (exported as a `.docx`
>    so it can be attached to this spec and reviewed line-by-line), and/or
> 2. The actual **sync function source code** that computes birthright in
>    production — which, if supplied, is the higher-fidelity source of the
>    two, since code defines real runtime behavior whereas documentation can
>    drift out of date. Where the guide and the code disagree, the code wins
>    unless a reviewer determines the code itself has a bug.
>
> The current table was drafted without either source and has already been
> flagged as producing incorrect results (e.g. it previously listed a
> `Prospect - Churned` account status that does not exist in the real data —
> corrected in this revision, but this is exactly the class of error the
> table is at risk of repeating elsewhere). Do not implement Tool 1 against
> this table as-is; see OQ-6 and OQ-7.

## 2. Goals / Non-Goals

### Goals

- Accept structured account data (Agent 2) and identity data (Agent 3) from
  the orchestrator and apply them as inputs to the evaluation tools.
- Execute **Tool 1 (`evaluate_birthright`)**: apply the Birthright &
  Entitlements Guide rules as pure local logic to calculate the expected
  birthright array, compare it against the actual birthright and entitlements
  arrays, and return a complete gap analysis including missing keywords, extra
  keywords, and a `persona` classification.
- Execute **Tool 3 (`classify_fix_complexity`)**: apply pure local logic to
  determine whether the identified gap is a `SIMPLE_FIX` (add keywords to
  entitlements in Phase 2) or `ESCALATE_TO_L2` (security risk, provisioning
  issue, or ambiguous state), and return an array of recommended actions.
- Execute **Tool 2 (`query_knowledge_base`)**: call the Bedrock Knowledge Base
  `RetrieveAndGenerate` API to surface relevant SOPs, Confluence docs, and
  similar past resolved TQI tickets for the diagnosed issue.
- Execute **Tool 4 (`identify_failing_workflow`)** — **PLACEHOLDER, NOT YET
  IMPLEMENTED.** Once real Auth0 Action/Rule/Flow scripts are supplied, this
  tool will map a failed step (from Agent 3's login-flow data or Tool 1's
  gap analysis) to the *specific* Auth0 workflow script responsible, so
  Agent 5 can point to the precise remediation location rather than just a
  step name or missing keyword. Until those scripts are supplied, this tool
  always returns a stub result (`workflow_identified: false`) and never
  blocks or fails the invocation — see §4.1 Tool 4 and OQ-8.
- Detect and flag **special conditions**: `no_access_configured`,
  `explicit_block_detected`, `sync_never_ran`, `sync_stale`, and
  `birthright_correct_but_access_denied`.
- Return a single **Pydantic-validated `KnowledgeBasePayload`** JSON object to
  the orchestrator.
- Treat a Knowledge Base query failure as **non-fatal**: the birthright
  evaluation result is always returned regardless of Bedrock availability.
- Hold the Phase 1 **read-only posture invariant**: zero calls to Auth0,
  DynamoDB, Salesforce, Jira, or Slack; no writes to the Bedrock Knowledge
  Base or any other system — by IAM deny and by code-side action-group
  assertion.

### Non-goals

- Fetching account data from DynamoDB (delegated to Agent 2).
- Fetching user metadata or login history from Auth0 (delegated to Agent 3).
- Generating the final L1 response or recommendation narrative for the
  engineer (delegated to Agent 5).
- Executing any remediation action — adding keywords to `entitlements`,
  triggering a sync, or creating a Jira ticket (out of scope for Phase 1).
- Maintaining, updating, or re-ingesting the Knowledge Base content (owned by
  the platform team's Lambda ingestion pipeline — out of scope for this spec).
- Evaluating Auth0 Action code correctness or diagnosing Auth0 configuration
  errors (ESCALATE_TO_L2 is the correct response in those cases).
- **Treating the current §4.1 persona/expected-birthright table as
  authoritative.** It is explicitly provisional pending verification against
  the real Birthright & Entitlements Guide and, optionally, the sync function
  source code — see §1 caveat, OQ-6, OQ-7. Implementing Tool 1 against this
  table without that verification step is out of scope for a production
  release.

## 3. Inputs

| Input | Source | Notes |
| :--- | :--- | :--- |
| `account_status` | Agent 2 `AccountPayload.accounts[0].account_status` | Required for Tool 1 and Tool 3. String (enum). If `account_found: false` in Agent 2 output, this field is `null` and persona defaults to `"UNKNOWN"`. |
| `active_tenant_count` | Agent 2 `AccountPayload.accounts[0].active_tenant_count` | Required for Tool 1 to distinguish Prospect-with-tenant from Prospect-without-tenant. Integer. |
| `actual_birthright` | Agent 3 `Auth0Payload.users[0].birthright` | Required for Tool 1. Array of strings. `[]` if `no_metadata` was flagged by Agent 3. |
| `entitlements` | Agent 3 `Auth0Payload.users[0].entitlements` | Required for Tool 1 and Tool 3. Array of strings. `[]` if `no_metadata` was flagged by Agent 3. |
| `user_found_in_auth0` | Agent 3 `Auth0Payload.user_found` | Required for Tool 3. Boolean. |
| `last_sync` | Agent 3 `Auth0Payload.users[0].last_sync` | Used to derive `sync_never_ran` and `sync_stale` flags. `null` if never synced. |
| `intent` | Agent 1 `RoutingEnvelope.intent` | Used to tune the Knowledge Base query string and to decide which special conditions are worth checking. |
| `raw_input` | Orchestrator (original L1 message text) | Passed as additional context to Tool 2 to improve RAG query relevance. |
| `run_id` | AgentCore run header | Propagated to the `KnowledgeBasePayload` and any posture-violation findings. |

The agent is **stateless** between invocations. All inputs must be supplied in
the orchestrator call; no prior-run memory is used.

## 4. Permitted Tools / Authorization Boundary

The agent's IAM execution role MAY perform **only** the AWS actions in this
table. The CDK stack in `infra/aws/ciam-knowledge-base-agent/` MUST instantiate
this exact policy shape; no `*` action wildcards are permitted.

| Service | Action | Resource scope |
| :--- | :--- | :--- |
| Bedrock | `bedrock:Retrieve` | Scoped to the CIAM Knowledge Base ARN only (`arn:aws:bedrock:*:*:knowledge-base/ciam-kb-*`) |
| Bedrock | `bedrock:RetrieveAndGenerate` | Scoped to the CIAM Knowledge Base ARN only |
| Bedrock | `bedrock:InvokeModel` | Scoped to `claude-haiku-*` model ARN only |

All other AWS service actions — DynamoDB, S3, SNS, SSM, Secrets Manager, STS,
IAM, and all Bedrock Knowledge Base ARNs outside `ciam-kb-*` — are **not
permitted** and are explicitly denied (see §5). Tools 1 and 3 are pure local
functions; they make zero network calls and require no IAM permissions of their
own.

Any tool implementation that calls an API not in this table is a **defect and a
release blocker**.

### 4.1 Tool Definitions

#### Tool 1 — `evaluate_birthright(account_status, active_tenant_count, actual_birthright, entitlements) → BirthrightEvaluation`

**Pure local logic — zero external calls.**

Applies the Birthright & Entitlements Guide rules to derive the expected
birthright array for the user's persona, compares it against the actual
birthright and entitlements arrays, and returns a complete gap analysis.

**Persona derivation and expected birthright (PROVISIONAL — see the caveat in
§1; not yet verified against the real Birthright & Entitlements Guide or sync
function source):**

| `account_status` | `active_tenant_count` | Persona | Expected birthright |
| :--- | :---: | :--- | :--- |
| `Customer` | any | `Customer` | `["Support", "Community", "Academy", "Notification", "Dashboard"]` |
| `Prospect - Net New` | `>= 1` | `Prospect with Tenant` | `["Support", "Community", "Academy", "Notification", "Dashboard"]` |
| `Prospect - Net New` | `0` | `Prospect without Tenant` | `["Community", "Academy", "Dashboard"]` |
| `Partner` | any | `Partner` | `["Community", "Academy", "Dashboard"]` |
| `Former Customer` | any | `Former Customer` | `["Community", "Academy", "Dashboard"]` |
| any other / `null` | any | `UNKNOWN` | `[]` (cannot determine; escalate) |

> **Note.** An earlier revision of this table included a row for
> `account_status: "Prospect - Churned"`. This status **does not exist** in
> the real account data and has been removed. This correction is itself
> evidence that the rest of this table — including the four remaining named
> statuses, the tenant-count branching, and the expected-birthright arrays —
> has not been independently verified against the real Salesforce picklist
> or the actual Birthright & Entitlements Guide, and should not be assumed
> correct merely because this one error was caught. See OQ-6.

**Comparison logic:**

1. Compute `effective_access = set(actual_birthright) ∪ set(entitlements)`.
   The Gatekeeper Action grants access if the required keyword is present in
   **either** array; this tool must reflect the same union semantics.
2. Compute `missing_keywords = set(expected_birthright) − effective_access`.
3. Compute `extra_keywords = set(actual_birthright) − set(expected_birthright)`.
   Extra keywords in `entitlements` alone are not flagged here — only extras in
   the `birthright` array itself are surfaced (since `entitlements` is the
   legitimate manual override channel).
4. Set `match = true` if and only if `missing_keywords` is empty **and**
   `extra_keywords` is empty.
5. Set `entitlements_compensate = true` if `missing_keywords` (before union)
   would be non-empty based on `actual_birthright` alone, but the union with
   `entitlements` results in no missing keywords.

**Block keyword detection (pre-check before comparison):**

Before the comparison in steps 1–5, scan `entitlements` for any string matching
the pattern `"block_<Keyword>"` where `<Keyword>` is a known portal keyword
(`Support`, `Community`, `Academy`, `Notification`, `Dashboard`). If any block
keyword is found, set `explicit_block_detected: true` and treat the blocked
portal as inaccessible regardless of birthright (block keywords override grants
per Gatekeeper logic). This condition always sets `complexity: "ESCALATE_TO_L2"`
in Tool 3 (see §4.1 Tool 3).

**Returns:** a `BirthrightEvaluation` object (schema in §7).

#### Tool 2 — `query_knowledge_base(query: str, top_k: int = 3) → KnowledgeBaseResults`

**Calls Amazon Bedrock Knowledge Base — internal AWS call within VPC.**

Calls `bedrock:RetrieveAndGenerate` on the CIAM Knowledge Base, which contains:

| Source | Ingestion path | Content |
| :--- | :--- | :--- |
| Confluence ISI space | Lambda 12hr cron → Markdown → S3 → Bedrock | Birthright & Entitlements Guide, CIAM L1 Common Issues & Fixes, Assign & Revoke Entitlement SOP, Force A NetskopeID Sync SOP, SOP: User Creation in Auth0, Auth0 Action code documentation |
| Past resolved TQI tickets | Lambda 12hr cron → Markdown export → S3 → Bedrock | Jira TQI tickets with `status: Done` and resolution notes |

The agent constructs the query string by combining the `intent`, the identified
`missing_keywords` from Tool 1, and the `raw_input` text to maximize retrieval
relevance. The `top_k` parameter defaults to `3`; the orchestrator may override
it up to a maximum of `10`.

**Returns:** a `KnowledgeBaseResults` object containing `relevant_docs` (SOPs,
guides, Confluence pages) and `similar_past_tickets` (resolved TQI tickets),
separated by source type based on the returned document metadata.

A Knowledge Base query failure (Bedrock timeout, throttle, or service error)
is **non-fatal** — see §8.

#### Tool 4 — `identify_failing_workflow(failed_step: str | None) → WorkflowIdentification` — **PLACEHOLDER**

**Pure local logic — zero external calls. NOT YET IMPLEMENTED.**

This tool is scaffolded now with a stable output shape so downstream
consumers (Agent 5, this payload's schema) don't need a breaking change
later, but its body is intentionally a stub until the real Auth0
Action/Rule/Flow source scripts for the `nskp` tenant are supplied (see
OQ-8). Once supplied, this tool will:

- Accept a `failed_step` identifier (e.g. from Agent 3's login-flow
  telemetry, or derived from Tool 1's `missing_keywords`/`explicit_block_detected`)
- Match it against the real Auth0 workflow source to identify the specific
  Action/Rule/Flow responsible
- Return the workflow's name and a reference (e.g. Auth0 dashboard deep
  link, or a script file path) so Agent 5 can cite the exact remediation
  location

**Current stub behavior (until real scripts are supplied):**

```python
def identify_failing_workflow(failed_step: str | None) -> "WorkflowIdentification":
    return WorkflowIdentification(
        workflow_identified=False,
        workflow_name=None,
        workflow_script_ref=None,
        note="Auth0 workflow scripts not yet provided -- placeholder only",
    )
```

This tool is **always called** (it has no failure mode — it's a stub) and
its result is always non-blocking: no `complexity` classification or
routing decision depends on its output while it remains a placeholder.

#### Tool 3 — `classify_fix_complexity(missing_keywords, extra_keywords, account_status, user_found_in_auth0, explicit_block_detected) → FixClassification`

**Pure local logic — zero external calls.**

Applies a deterministic decision tree to classify the identified issue as
`SIMPLE_FIX` or `ESCALATE_TO_L2` and generate recommended actions.

**`SIMPLE_FIX` — ALL of the following must be true:**

| Criterion | Value required |
| :--- | :--- |
| `missing_keywords` | Non-empty (there is something to add) |
| `extra_keywords` | Empty (no over-provisioning) |
| `explicit_block_detected` | `false` |
| `missing_keywords` values | All within `["Support", "Community", "Academy", "Notification", "Dashboard"]` |
| `account_status` | `"Customer"` or `"Prospect - Net New"` with `active_tenant_count >= 1` |
| `user_found_in_auth0` | `true` |
| Fix action | Add keywords to `entitlements` array only (reversible) |

**`ESCALATE_TO_L2` — ANY single condition triggers escalation:**

| Trigger | Reason |
| :--- | :--- |
| `extra_keywords` non-empty | User has more access than entitled — security risk; must not auto-remediate. |
| `explicit_block_detected: true` | Explicit block keyword in `entitlements`; security-sensitive; requires L2 review. |
| `account_status` is `"UNKNOWN"` or `null` | Cannot safely determine correct entitlement without confirmed account data. |
| `user_found_in_auth0: false` | Provisioning issue; entitlement add is insufficient — user needs to be created. |
| `intent` is `"SSO_ERROR"` | Requires Auth0 Connection or federation config review; out of agent scope. |
| `missing_keywords` contains an unrecognized value | Unexpected keyword not in the known portal list; requires human review. |
| `birthright_correct_but_access_denied: true` | Mismatch between Auth0 data and Gatekeeper behaviour; likely Auth0 Action code issue. |

**`recommended_actions` array (normative per complexity):**

- For `SIMPLE_FIX`: `["Add <missing_keywords> to entitlements array via Auth0 Management API", "Verify access after update", "Monitor next sync to confirm birthright recalculation does not remove entitlement"]`
- For `ESCALATE_TO_L2` with `extra_keywords`: `["Review over-provisioned keywords", "Do not modify entitlements without L2 approval", "Escalate to L2 with birthright evaluation attached"]`
- For `ESCALATE_TO_L2` with `user_found_in_auth0: false`: `["Create user in Auth0 per SOP: User Creation in Auth0", "Escalate to L2 for provisioning"]`
- For `ESCALATE_TO_L2` with `explicit_block_detected`: `["Identify who added block keyword and why", "Escalate to L2 for block keyword review"]`
- For all other `ESCALATE_TO_L2` cases: `["Gather additional context", "Escalate to L2 with full KnowledgeBasePayload attached"]`

**Returns:** a `FixClassification` object (schema in §7).

## 5. Explicit Denies (Phase 1 invariants)

The CDK IAM role MUST attach an explicit `Deny` statement covering the
following actions with `Resource: "*"`. These denies are **gating posture
invariants** — CI fails the PR if they are missing or weakened.

| Denied action | Reason |
| :--- | :--- |
| `dynamodb:*` (all actions) | Account data is read by Agent 2; no DynamoDB access from this agent. |
| `secretsmanager:GetSecretValue` (any path) | No credentials to fetch; this agent uses IAM role only. |
| `s3:*` (all actions) | The agent reads the KB via Bedrock, not S3 directly. |
| `bedrock:Retrieve` / `bedrock:RetrieveAndGenerate` on any ARN outside `ciam-kb-*` | Scoped to the CIAM Knowledge Base only; no access to other KB instances. |
| `bedrock:CreateKnowledgeBase`, `bedrock:UpdateKnowledgeBase`, `bedrock:DeleteKnowledgeBase` | No write or administrative access to the Knowledge Base. |
| `bedrock:IngestKnowledgeBaseDocuments`, `bedrock:StartIngestionJob` | Content ingestion is owned by the platform team's Lambda pipeline. |
| `sns:Publish` | The orchestrator, not this agent, owns alert fanout. |
| `sts:AssumeRole` | No cross-account or cross-service role assumption. |
| `iam:*` | No IAM reads or writes. |

Defense in depth: the code-layer action-group (`core/agentcore/action_group.py`)
MUST contain an explicit allow-list of exactly four permitted tool names —
`evaluate_birthright`, `query_knowledge_base`, `classify_fix_complexity`, and
`identify_failing_workflow` (the last is a local-only placeholder stub, but
is still named explicitly rather than left implicit). Any invocation of a
tool name outside this list raises `PostureViolationError`
*before* any network or SDK call is issued, emits a `posture-violation` finding
(CRITICAL), and aborts the invocation.

## 6. Behavior

An invocation proceeds in the following deterministic steps:

1. **Validate inputs.** Confirm the payload contains `actual_birthright`
   (array, may be empty), `entitlements` (array, may be empty),
   `user_found_in_auth0` (boolean), and `intent` (string). If any required
   field is absent or of the wrong type, return a `KnowledgeBasePayload` with
   `error: "invalid_input"` and all evaluation fields set to their null/empty
   defaults. If `account_status` is absent or `null`, set persona to
   `"UNKNOWN"` and proceed — this is a valid degraded-input path.

2. **Derive sync flags.** Inspect `last_sync`:
   - If `null` or empty string → set `sync_never_ran: true`.
   - If `(now_utc − last_sync) > 7 days` → set `sync_stale: true`.
   - Otherwise both flags are `false`.
   These flags are surfaced in `birthright_evaluation` and passed as context
   to Tool 2's query string construction.

3. **Evaluate birthright (Tool 1).** Call `evaluate_birthright(...)` with all
   required inputs. This call is **always made** — it does not depend on
   Knowledge Base availability. Detect all special conditions:
   - If `actual_birthright == [] and entitlements == []` → set
     `no_access_configured: true`.
   - If any `"block_<Keyword>"` pattern is found in `entitlements` → set
     `explicit_block_detected: true` (handled inside Tool 1; surfaced in
     the returned `BirthrightEvaluation`).
   - If `match: true` but `intent` is `"ACCESS_DENIED"` → set
     `birthright_correct_but_access_denied: true`; this overrides complexity
     to `ESCALATE_TO_L2` in step 4.

4. **Classify fix complexity (Tool 3).** Call
   `classify_fix_complexity(...)` using the output of Tool 1. Pass
   `birthright_correct_but_access_denied` as an additional input flag.
   This call is **always made** regardless of Knowledge Base availability.

5. **Query Knowledge Base (Tool 2).** Construct the query string from:
   - The `intent` value (e.g., `"ACCESS_DENIED"`)
   - The `missing_keywords` array from Tool 1 (e.g., `"missing Support"`)
   - The `persona` from Tool 1 (e.g., `"Customer"`)
   - The `raw_input` (truncated to 500 chars)
   - The `complexity` from Tool 3 (to bias toward escalation SOPs if needed)

   Call `query_knowledge_base(query, top_k=3)`. On Bedrock error or timeout,
   set `knowledge_base_results` to its null/empty default and populate
   `knowledge_base_error` — do **not** abort the invocation (see §8).

6. **Identify failing workflow (Tool 4 — placeholder).** Call
   `identify_failing_workflow(failed_step)` where `failed_step` is derived
   from `explicit_block_detected` or the first entry in `missing_keywords`
   if present, else `null`. This call always succeeds (it is a stub) and its
   result never affects `complexity` or any routing decision while
   placeholder.

7. **Assemble and validate payload.** Construct the `KnowledgeBasePayload`
   (schema in §7). Validate against Pydantic strict mode. On validation
   failure, return `error: "payload_validation_error"` with the validation
   message.

8. **Return payload.** Return the complete `KnowledgeBasePayload` to the
   orchestrator. No writes to any external system occur at any step.

### 6.1 Tool Call Order and Conditionality

Tools 1 and 3 are **always called** — they are pure local functions with no
failure modes beyond invalid inputs, and the birthright evaluation result is
the primary output of this agent. Tool 2 is **always attempted** when
`user_found_in_auth0: true`, but its failure is non-fatal and does not block
the return of the payload. When `user_found_in_auth0: false`, Tool 2 is still
called because Knowledge Base results about the user-creation SOP are directly
relevant to that case.

### 6.2 Birthright Rule Precedence

The Gatekeeper Action checks both `birthright` and `entitlements` arrays using
OR logic. Tool 1 implements the same union semantics (`effective_access =
birthright ∪ entitlements`) to avoid false-positive `missing_keywords` reports.
Block keywords in `entitlements` (e.g., `"block_Support"`) override the union
grant — this is handled as a pre-check in Tool 1 before the union comparison.
Block keywords in the `birthright` array itself are not a defined concept in
the Gatekeeper Action; if encountered, they are treated as an unrecognized
keyword and surfaced in `extra_keywords`.

### 6.3 Knowledge Base Query Construction

The query string sent to Bedrock is constructed deterministically from the
inputs as follows (in this order, space-separated):

```
<intent> <persona> missing:<missing_keywords_csv> extra:<extra_keywords_csv> <raw_input_truncated_500>
```

Example for an `ACCESS_DENIED` Customer missing `Support`:

```
ACCESS_DENIED Customer missing:Support extra: user reports access denied on support portal for john@example.com
```

This query format is versioned at `prompts/ciam-knowledge-base-agent/v1.md`
alongside the agent prompt. Changes to query construction require a prompt
version bump.

## 7. Outputs

### 7.1 Knowledge Base Payload Schema

The agent returns exactly one `KnowledgeBasePayload` object to the orchestrator.

```python
class KnowledgeBasePayload(BaseModel):
    schema_version: Literal["1.0"]
    spec_id:        Literal["SPEC-CIAM-0004"]
    agent:          Literal["ciam-knowledge-base-agent"]
    run_id:         str                          # uuid4, from AgentCore run header
    evaluated_at:   datetime                     # UTC, isoformat

    # --- Birthright evaluation ---
    birthright_evaluation: BirthrightEvaluation

    # --- Fix classification ---
    fix_classification: FixClassification

    # --- Auth0 workflow identification (PLACEHOLDER -- see Tool 4) ---
    workflow_identification: WorkflowIdentification

    # --- Knowledge Base results ---
    knowledge_base_results: KnowledgeBaseResults
    knowledge_base_error:   str | None           # non-null if Tool 2 failed

    # --- Top-level error ---
    error: str | None                            # null on full success


class BirthrightEvaluation(BaseModel):
    match:                          bool
    persona:                        str          # "Customer" | "Prospect with Tenant" |
                                                 # "Prospect without Tenant" | "Partner" |
                                                 # "Former Customer" | "UNKNOWN"
    expected_birthright:            list[str]
    actual_birthright:              list[str]
    entitlements:                   list[str]
    missing_keywords:               list[str]    # in expected but not in effective_access
    extra_keywords:                 list[str]    # in actual_birthright but not in expected
    entitlements_compensate:        bool         # true if entitlements cover missing birthright
    explicit_block_detected:        bool
    block_keywords_found:           list[str]    # e.g. ["block_Support"]
    no_access_configured:           bool
    birthright_correct_but_access_denied: bool
    sync_never_ran:                 bool
    sync_stale:                     bool


class FixClassification(BaseModel):
    complexity:          Literal["SIMPLE_FIX", "ESCALATE_TO_L2", "NO_GAP"]
    reason:              str                     # human-readable explanation
    recommended_actions: list[str]
    confidence:          Literal["HIGH", "MEDIUM", "LOW"]


class WorkflowIdentification(BaseModel):
    """PLACEHOLDER schema -- see Tool 4. Always returns the stub values below
    until real Auth0 Action/Rule/Flow scripts are supplied (OQ-8)."""
    workflow_identified:   bool                    # always false until implemented
    workflow_name:         str | None              # always null until implemented
    workflow_script_ref:   str | None              # always null until implemented
    note:                  str                     # explains placeholder status


class KnowledgeBaseResults(BaseModel):
    relevant_docs:        list[KBDocument]       # SOPs, guides, Confluence pages
    similar_past_tickets: list[KBTicket]         # resolved TQI tickets


class KBDocument(BaseModel):
    title:           str
    url:             str | None
    excerpt:         str                         # retrieved chunk text (≤ 500 chars)
    relevance_score: float                       # 0.0–1.0 from Bedrock


class KBTicket(BaseModel):
    ticket_key:      str                         # e.g. "TQI-1234"
    summary:         str
    resolution:      str | None
    relevance_score: float
```

### 7.2 Posture Violation Finding

If the agent's code attempts any denied action (DynamoDB read, Auth0 call,
Bedrock write, out-of-scope tool invocation), it MUST emit a
`PostureViolationFinding` conforming to `core/findings/schema.py` and abort
the invocation. No `KnowledgeBasePayload` is returned in this case.

```python
class PostureViolationFinding(BaseModel):
    schema_version: Literal["1.0"]
    spec_id:        Literal["SPEC-CIAM-0004"]
    agent:          Literal["ciam-knowledge-base-agent"]
    run_id:         str
    detected_at:    datetime
    category:       Literal["posture-violation"]
    severity:       Literal["CRITICAL"]
    evidence:       dict[str, Any]   # {"attempted_action": "<tool_or_api_name>"}
```

## 8. Failure Handling

- **Invalid or missing required inputs.** Return `KnowledgeBasePayload` with
  `error: "invalid_input"`, `birthright_evaluation` and `fix_classification`
  set to their null/empty defaults. Do not raise an unhandled exception.
- **`account_status` absent or `null`.** Non-fatal degraded path. Set
  `persona: "UNKNOWN"`, `expected_birthright: []`, `complexity:
  "ESCALATE_TO_L2"`, `reason: "account_status_unknown"`. Tools 1 and 3 still
  run and return meaningful output for the fields that are available.
- **Bedrock Knowledge Base timeout.** SDK timeout set to 10 s. Return
  `knowledge_base_results` with `relevant_docs: []` and
  `similar_past_tickets: []`. Set `knowledge_base_error: "bedrock_timeout"`.
  The `BirthrightEvaluation` and `FixClassification` results are unaffected
  and are returned normally.
- **Bedrock Knowledge Base throttle (`ThrottlingException`).** Retry with
  exponential backoff (base 1 s, multiplier 2×), max 3 attempts. On max
  retries exceeded, return `knowledge_base_error: "bedrock_throttled"` and
  empty results — non-fatal.
- **Bedrock Knowledge Base returns no results.** Valid successful result.
  Return `relevant_docs: []`, `similar_past_tickets: []`,
  `knowledge_base_error: null`. This is the expected behaviour when the KB
  does not contain relevant content for the query.
- **`explicit_block_detected: true`.** Non-fatal condition, but always forces
  `complexity: "ESCALATE_TO_L2"`. The full payload is returned normally with
  the flag set; no exception is raised.
- **`birthright_correct_but_access_denied: true`.** Non-fatal condition.
  Forces `complexity: "ESCALATE_TO_L2"`. The Knowledge Base query is biased
  toward Gatekeeper Action logs and Auth0 Action debugging docs.
- **Payload validation failure.** Return `error: "payload_validation_error"`
  with the Pydantic validation detail. Do not return a partially-constructed
  payload.
- **Posture violation (tripwire).** Any code path that attempts a denied
  action raises `PostureViolationError`, emits a `posture-violation` finding
  (CRITICAL), and aborts the invocation with no `KnowledgeBasePayload`
  returned. This is a release-blocker defect.

## 9. Acceptance Criteria (Given/When/Then)

Each AC maps 1:1 to an eval case at
`evals/ciam-knowledge-base-agent/cases/ac-N.yaml`. ACs marked **GATING** fail
the PR in CI if they regress.

### AC-1 — Customer with missing Support keyword: SIMPLE_FIX classified

- **Given** inputs with `account_status: "Customer"`, `active_tenant_count: 2`,
  `actual_birthright: ["Community", "Academy", "Notification", "Dashboard"]`,
  `entitlements: []`, `user_found_in_auth0: true`,
- **When** the agent runs,
- **Then** the `KnowledgeBasePayload` has
  `birthright_evaluation.missing_keywords: ["Support"]`,
  `birthright_evaluation.match: false`,
  `birthright_evaluation.persona: "Customer"`,
  `fix_classification.complexity: "SIMPLE_FIX"`, and
  `fix_classification.recommended_actions` contains a string referencing
  adding `"Support"` to the entitlements array.

### AC-2 — Entitlements compensate for missing birthright keyword

- **Given** inputs with `account_status: "Customer"`,
  `actual_birthright: ["Community", "Academy", "Notification", "Dashboard"]`,
  `entitlements: ["Support"]`, `user_found_in_auth0: true`,
- **When** the agent runs,
- **Then** `birthright_evaluation.missing_keywords: []`,
  `birthright_evaluation.match: true`,
  `birthright_evaluation.entitlements_compensate: true`, and
  `fix_classification.complexity: "NO_GAP"` (not `"SIMPLE_FIX"` — `match:
  true` with no missing keywords means no fix is needed), with `reason:
  "no_gap_detected"`.

### AC-3 — Prospect without tenant gets reduced expected birthright

- **Given** inputs with `account_status: "Prospect - Net New"`,
  `active_tenant_count: 0`,
  `actual_birthright: ["Community", "Academy", "Dashboard"]`,
  `entitlements: []`, `user_found_in_auth0: true`,
- **When** the agent runs,
- **Then** `birthright_evaluation.expected_birthright: ["Community",
  "Academy", "Dashboard"]`, `birthright_evaluation.match: true`, and
  `fix_classification.complexity: "NO_GAP"`.

### AC-4 — Extra keywords in birthright force ESCALATE_TO_L2

- **Given** inputs with `account_status: "Former Customer"`,
  `actual_birthright: ["Community", "Academy", "Dashboard", "Support"]`,
  `entitlements: []`, `user_found_in_auth0: true`,
- **When** the agent runs,
- **Then** `birthright_evaluation.extra_keywords: ["Support"]`,
  `birthright_evaluation.match: false`,
  `fix_classification.complexity: "ESCALATE_TO_L2"`, and `fix_classification.reason`
  references over-provisioning.

### AC-5 — Block keyword detected forces ESCALATE_TO_L2

- **Given** inputs with `account_status: "Customer"`,
  `actual_birthright: ["Support", "Community", "Academy", "Notification", "Dashboard"]`,
  `entitlements: ["block_Support"]`, `user_found_in_auth0: true`,
- **When** the agent runs,
- **Then** `birthright_evaluation.explicit_block_detected: true`,
  `birthright_evaluation.block_keywords_found: ["block_Support"]`,
  `fix_classification.complexity: "ESCALATE_TO_L2"`, and
  `fix_classification.reason` references the explicit block.

### AC-6 — User not found in Auth0 forces ESCALATE_TO_L2

- **Given** inputs with `account_status: "Customer"`, `actual_birthright: []`,
  `entitlements: []`, `user_found_in_auth0: false`,
- **When** the agent runs,
- **Then** `fix_classification.complexity: "ESCALATE_TO_L2"`,
  `fix_classification.reason` references provisioning, and
  `fix_classification.recommended_actions` contains a reference to the
  User Creation SOP.

### AC-7 — Birthright correct but ACCESS_DENIED forces ESCALATE_TO_L2

- **Given** inputs with `account_status: "Customer"`,
  `actual_birthright: ["Support", "Community", "Academy", "Notification", "Dashboard"]`,
  `entitlements: []`, `user_found_in_auth0: true`, `intent: "ACCESS_DENIED"`,
- **When** the agent runs,
- **Then** `birthright_evaluation.match: true`,
  `birthright_evaluation.birthright_correct_but_access_denied: true`,
  `fix_classification.complexity: "ESCALATE_TO_L2"`, and
  `fix_classification.reason` references a potential Gatekeeper Action issue.

### AC-8 — Knowledge Base timeout is non-fatal; evaluation still returned

- **Given** valid inputs and a simulated Bedrock `RetrieveAndGenerate` timeout
  after the SDK timeout threshold,
- **When** the agent runs,
- **Then** `birthright_evaluation` and `fix_classification` are fully
  populated, `knowledge_base_results.relevant_docs: []`,
  `knowledge_base_results.similar_past_tickets: []`,
  `knowledge_base_error: "bedrock_timeout"`, and `error: null`.

### AC-9 — Agent attempts `dynamodb:Query` (GATING — posture invariant)

- **Given** a malformed tool call or code path that attempts a DynamoDB query
  from within this agent,
- **When** the agent processes the invocation,
- **Then** `PostureViolationError` is raised *before* any AWS SDK call is made,
  no `KnowledgeBasePayload` is returned, and a `posture-violation` (CRITICAL)
  finding is emitted. **Gating in CI.**

### AC-10 — Agent attempts `bedrock:StartIngestionJob` (GATING — posture invariant)

- **Given** a malformed tool call or code path that attempts a Bedrock
  Knowledge Base write action (`StartIngestionJob`),
- **When** the agent processes the invocation,
- **Then** `PostureViolationError` is raised before any AWS SDK call is made,
  no `KnowledgeBasePayload` is returned, and a `posture-violation` (CRITICAL)
  finding is emitted. **Gating in CI.**

### AC-11 — Schema conformance (GATING — schema invariant)

- **Given** any invocation that produces a `KnowledgeBasePayload`,
- **When** the payload is validated against `KnowledgeBasePayload` (Pydantic
  strict mode),
- **Then** it passes validation without error; any failure fails the run and
  the CI gate. **Gating in CI.**

### AC-12 — Unknown account_status returns UNKNOWN persona and escalates

- **Given** inputs with `account_status: null`, `actual_birthright: []`,
  `entitlements: []`, `user_found_in_auth0: true`,
- **When** the agent runs,
- **Then** `birthright_evaluation.persona: "UNKNOWN"`,
  `birthright_evaluation.expected_birthright: []`,
  `fix_classification.complexity: "ESCALATE_TO_L2"`, and `error: null`.

### AC-13 — no_access_configured flagged when both arrays are empty

- **Given** inputs with `account_status: "Customer"`, `actual_birthright: []`,
  `entitlements: []`, `user_found_in_auth0: true`,
- **When** the agent runs,
- **Then** `birthright_evaluation.no_access_configured: true`,
  `birthright_evaluation.missing_keywords` equals the full Customer expected
  birthright, and `fix_classification.complexity: "SIMPLE_FIX"` (all portals
  can be added via entitlements, user exists in Auth0).

### AC-14 — Bedrock Knowledge Base returns relevant docs and past tickets

- **Given** valid inputs and a Bedrock fixture returning 2 document chunks
  (one from Confluence, one from a past TQI ticket),
- **When** the agent runs,
- **Then** `knowledge_base_results.relevant_docs` has length 1 (the Confluence
  chunk), `knowledge_base_results.similar_past_tickets` has length 1 (the TQI
  chunk), all `KBDocument` and `KBTicket` fields are non-null, and
  `knowledge_base_error: null`.

### AC-15 — Workflow identification always returns the placeholder stub

- **Given** any valid input, regardless of `missing_keywords` or
  `explicit_block_detected` value,
- **When** the agent runs,
- **Then** `workflow_identification.workflow_identified: false`,
  `workflow_identification.workflow_name: null`,
  `workflow_identification.workflow_script_ref: null`, and
  `fix_classification.complexity` is unaffected by this field (Tool 4 is
  non-blocking while placeholder — see Tool 4 and OQ-8).

## 10. Eval Mapping Table

| AC | Eval case file | Type | Gating |
| :--- | :--- | :--- | :--- |
| AC-1 | `evals/ciam-knowledge-base-agent/cases/ac-1.yaml` | structured-assertion | no |
| AC-2 | `evals/ciam-knowledge-base-agent/cases/ac-2.yaml` | structured-assertion | no |
| AC-3 | `evals/ciam-knowledge-base-agent/cases/ac-3.yaml` | structured-assertion | no |
| AC-4 | `evals/ciam-knowledge-base-agent/cases/ac-4.yaml` | structured-assertion | no |
| AC-5 | `evals/ciam-knowledge-base-agent/cases/ac-5.yaml` | structured-assertion | no |
| AC-6 | `evals/ciam-knowledge-base-agent/cases/ac-6.yaml` | structured-assertion | no |
| AC-7 | `evals/ciam-knowledge-base-agent/cases/ac-7.yaml` | structured-assertion | no |
| AC-8 | `evals/ciam-knowledge-base-agent/cases/ac-8.yaml` | failure-mode | no |
| AC-9 | `evals/ciam-knowledge-base-agent/cases/ac-9.yaml` | posture-invariant | **yes** |
| AC-10 | `evals/ciam-knowledge-base-agent/cases/ac-10.yaml` | posture-invariant | **yes** |
| AC-11 | `evals/ciam-knowledge-base-agent/cases/ac-11.yaml` | schema-invariant | **yes** |
| AC-12 | `evals/ciam-knowledge-base-agent/cases/ac-12.yaml` | structured-assertion | no |
| AC-13 | `evals/ciam-knowledge-base-agent/cases/ac-13.yaml` | structured-assertion | no |
| AC-14 | `evals/ciam-knowledge-base-agent/cases/ac-14.yaml` | structured-assertion | no |
| AC-15 | `evals/ciam-knowledge-base-agent/cases/ac-15.yaml` | structured-assertion | no |

## 11. Open Questions

- **OQ-1 (resolved).** Bedrock Knowledge Base ARN: the real KB is
  `ciam-kb`, Knowledge Base ID `O4XMWIIEHS`, ARN
  `arn:aws:bedrock:us-east-1:786063285476:knowledge-base/O4XMWIIEHS` --
  matches the `ciam-kb-*` ARN pattern this spec already used. It was
  provisioned as a **Managed Knowledge Base** (Bedrock's fully-managed
  vector store) rather than a customer-managed OpenSearch Serverless
  collection -- an account-level restriction blocked direct OpenSearch
  Serverless index creation via CLI/API, but the AWS Console's "Quick
  create a new vector store" flow succeeded using Bedrock's own internal
  managed-vector-store automation instead. Functionally equivalent for
  Tool 2's purposes (`bedrock:Retrieve` works identically either way);
  noted here since it differs from the originally-assumed self-managed
  OpenSearch Serverless architecture.
- **OQ-2.** `top_k` ceiling: the spec permits the orchestrator to override
  `top_k` up to `10`. Confirm whether a higher ceiling is needed for the
  Response Generator (Agent 5) to produce high-quality recommendations, or
  whether `3` is sufficient for Phase 1.
- **OQ-3.** Document vs. ticket classification: Tool 2 separates results into
  `relevant_docs` and `similar_past_tickets` based on document metadata from
  Bedrock. Confirm the metadata field name and value used to distinguish
  Confluence pages from TQI ticket exports in the Knowledge Base ingestion
  pipeline, so the classification logic can be implemented correctly.
- **OQ-4.** `confidence` field in `FixClassification`: this spec defines
  `confidence` as `"HIGH"` | `"MEDIUM"` | `"LOW"` but does not specify the
  derivation rules (e.g., `HIGH` when account_status and user_found are both
  unambiguous, `LOW` when either is null). Define the confidence scoring
  rubric before Phase 1 implementation to ensure eval AC cases can assert
  against it.
- **OQ-5.** Block keyword vocabulary: this spec defines block keywords as
  `"block_<Keyword>"` for the five known portal keywords. Confirm with the
  CIAM platform team whether any other block keyword patterns exist in the
  `nskp` tenant's `entitlements` data before finalising the pre-check regex
  in Tool 1.
- **OQ-6.** Birthright & Entitlements Guide as source of truth: §4.1 Tool 1's
  persona/expected-birthright table is currently **provisional** (see the
  caveat in §1) and was not derived from the actual Birthright & Entitlements
  Guide. The guide should be exported as a `.docx`, attached to this spec
  (or linked from `docs/` per the placement-guide convention), and used to
  re-derive the persona table line-by-line before Tool 1 is implemented. Any
  discrepancy between the current provisional table and the real guide is
  assumed to be a defect in the table, not the guide, until reviewed.
- **OQ-7.** Sync function source code as a higher-fidelity reference: in
  addition to the guide (OQ-6), the actual source code of the function that
  computes/provisions birthright in production may be available to supply as
  additional context. If supplied, it should be treated as the higher-
  priority source of the two for resolving Tool 1's logic, since the guide
  is documentation that can drift from what the code actually does, while the
  code defines real runtime behavior directly. If the guide and the code
  disagree on any point, default to the code's actual behavior unless a
  reviewer identifies the code itself as buggy (in which case that
  discrepancy is itself a finding worth raising with the platform team,
  separate from this spec). This is an open option, not yet exercised — track
  here so it isn't lost if the code is supplied in a future revision.
- **OQ-8.** Auth0 workflow script source: Tool 4
  (`identify_failing_workflow`) is currently a placeholder stub — see §4.1
  Tool 4. It needs the actual Auth0 Action/Rule/Flow scripts for the `nskp`
  tenant (the 9-step login-flow implementation) supplied and reconciled
  before it can do real workflow-to-script mapping. Until then it always
  returns `workflow_identified: false`. Track here so this isn't forgotten
  once those scripts become available.
