---
spec_id: SPEC-CIAM-0005
capability: ciam-response-generator
status: Draft
owner: Shristy Jaiswal
reviewers: [Peer]
approver: Ritwik Mandal
prd: https://confluence.netskope.example/display/GIS/ciam-response-generator-prd  # placeholder — link to docs/confluence/ciam-response-generator/prd.md until Phase 0 lands
jira_epic: GIS-EPIC-CIAM  # placeholder — see docs/jira/ciam-response-generator-epic.md until Phase 0 lands
version: 0.2.0
created: 2026-06-23
last_updated: 2026-06-30
---

# spec.md — CIAM Response Generator (Agent 5)

> This is the **executable contract**. Code, evals, and PR review trace back to
> this file. Acceptance criteria map 1:1 to eval cases under
> `evals/ciam-response-generator/cases/`. Posture invariants (AC-10, AC-11,
> AC-12, AC-15) are **gating in CI**: a regression fails the PR.

## 1. Summary

The CIAM Response Generator is the **final synthesis agent** in the CIAM
Support Assistant pipeline. It is invoked by the orchestrator after Agents 2,
3, and 4 have completed their payloads. It receives Pydantic-validated
structured JSON from all upstream agents — account data from Agent 2 (Database
Agent), identity and birthright data from Agent 3 (Auth0 Agent), birthright
evaluation and fix classification from Agent 4 (Knowledge Base Agent) — and
synthesizes them into a coherent diagnosis using Claude Sonnet 4.5, the only
agent in the pipeline that uses the high-reasoning model. It produces a
**split output** (§ RAW DATA + § AI DIAGNOSIS + § Metadata) and delivers it to
the appropriate output channel: a Slack thread reply (via `post_slack_reply`),
a Jira internal note (via `post_jira_internal_note`), or both, depending on
the source. It also applies Jira classification labels (via `add_jira_labels`)
and writes a complete audit log to CloudWatch and S3.

This agent performs **no data fetching** from Auth0, DynamoDB, Salesforce, or
any upstream system. It **only synthesizes, generates, and delivers**. It is
the **only agent in the pipeline authorised to write to Slack and Jira**.

## 2. Goals / Non-Goals

### Goals

- Receive all upstream agent payloads from the orchestrator and validate their
  presence; handle partial inputs gracefully when one or more sub-agents
  returned an error.
- Correlate multi-source data — DynamoDB account state, Auth0 identity state,
  and the Knowledge Base evaluation — to determine the single most-likely root
  cause of the reported issue.
- Set a **confidence level** (`HIGH` / `MEDIUM` / `LOW`) that reflects data
  consistency across sources, and override `SIMPLE_FIX` to `ESCALATE_TO_L2`
  when confidence is `LOW`.
- Generate a **split output** composed of three sections: `§ RAW DATA` (unmodified
  facts attributed to their source), `§ AI DIAGNOSIS` (root cause, confidence,
  classification, numbered recommended actions, KB references), and
  `§ METADATA` (run audit fields).
- Execute **Tool 1 (`post_slack_reply`)** when `source == "slack"` to deliver
  the split output as a Slack Block Kit message in the original thread,
  including interactive `✅ Approve Fix` / `❌ Escalate Instead` buttons when
  `complexity == "SIMPLE_FIX"`.
- Execute **Tool 2 (`post_jira_internal_note`)** when `source == "jira"` (or
  when a `ticket_key` is present in a Slack-sourced request) to post the split
  output as an internal note on the TQI ticket.
- Execute **Tool 3 (`add_jira_labels`)** when `source == "jira"` to apply the
  classification labels `"ciam-agent-diagnosed"` and either
  `"ciam-agent-fixable"` or `"ciam-agent-escalate"` to the ticket.
- Write a complete structured audit log to CloudWatch Logs and to the
  `governor-audit-logs-*` S3 bucket for every invocation.
- Enforce **synthesis rules** (§6.3) to prevent hallucination: never add
  information not present in sub-agent payloads, never guess null values,
  always attribute each fact to its source.
- Guarantee that internal identifiers, credentials, and infrastructure
  details — both upstream `user_id` values (Auth0's and the NetskopeID
  table's), `client_id`/`client_secret`/`access_token`, the Auth0 tenant
  domain, and AWS resource identifiers — **never** appear in any output
  delivered to the L1 engineer (Slack message or Jira note), per the
  normative field list in §6.5. This is enforced at the schema level via
  explicit per-source field allow-lists — not merely by prompt instruction —
  and verified by a dedicated gating test (AC-15).
- Hold the Phase 1 **output-only posture invariant**: zero reads from Auth0,
  DynamoDB, Salesforce, Bedrock KB, or any upstream data source; write
  permissions scoped exclusively to Slack (`chat:write`), Jira (comment +
  labels), CloudWatch Logs, and the S3 audit bucket — by IAM deny and
  code-side assertion.

### Non-goals

- Fetching account data from DynamoDB (delegated to Agent 2).
- Fetching user metadata or login history from Auth0 (delegated to Agent 3).
- Evaluating birthright or classifying fix complexity (delegated to Agent 4).
- Classifying the L1 engineer's intent (delegated to Agent 1).
- Executing any remediation action — adding keywords to `entitlements`,
  triggering a sync, or resetting MFA (out of scope for Phase 1; a future
  write-enabled remediation agent will handle approved `SIMPLE_FIX` actions).
- Creating or transitioning Jira tickets (the agent posts internal notes and
  labels only; it does not change ticket status, assignee, or priority).
- Sending direct Slack messages (DMs) to end-users or customers — output is
  directed at L1 engineers only.

## 3. Inputs

| Input | Source | Notes |
| :--- | :--- | :--- |
| `account_payload` | Agent 2 `AccountPayload` | Full Pydantic object. If `error` is non-null, the agent uses partial data and flags `db_unavailable: true`. |
| `auth0_payload` | Agent 3 `Auth0Payload` | Full Pydantic object. If `error` is non-null, the agent uses partial data and flags `auth0_unavailable: true`. |
| `kb_payload` | Agent 4 `KnowledgeBasePayload` | Full Pydantic object. If `error` is non-null, the agent uses partial data and flags `kb_unavailable: true`. |
| `intent` | Agent 1 `RoutingEnvelope.intent` | Passed through by orchestrator. Used in the § AI DIAGNOSIS section heading and to tune root-cause framing. |
| `extracted_email` | Agent 1 `RoutingEnvelope.extracted_email` | Passed through. Used as the subject identifier in the output. |
| `extracted_portal` | Agent 1 `RoutingEnvelope.extracted_portal` | Passed through. `null` if not detected. Used to narrow recommended actions to the specific portal. |
| `source` | Agent 1 `RoutingEnvelope.source` | `"slack"` or `"jira"`. Controls which output tools are invoked (see §6.2). |
| `source_metadata` | Orchestrator | Object containing `channel_id`, `thread_ts` (Slack) and/or `ticket_key` (Jira). |
| `raw_input` | Orchestrator | Original L1 message text. Used in `§ METADATA` for context; never interpreted or surfaced in the diagnosis. |
| `run_id` | AgentCore run header | Propagated to the `ResponsePayload`, audit log, and all delivery tool calls. |
| `pipeline_start_at` | Orchestrator | UTC timestamp when Agent 1 was first invoked. Used to compute `total_latency_ms` in `§ METADATA`. |

All upstream payloads are **required** in the orchestrator call. A missing
payload (as opposed to a payload with a non-null `error` field) is itself an
error — see §8.

## 4. Permitted Tools / Authorization Boundary

The agent's IAM execution role MAY perform **only** the AWS actions in this
table. The CDK stack in `infra/aws/ciam-response-generator/` MUST instantiate
this exact policy shape; no `*` action wildcards are permitted.

| Service | Action | Resource scope |
| :--- | :--- | :--- |
| Secrets Manager | `secretsmanager:GetSecretValue` | `arn:aws:secretsmanager:*:*:secret:ciam-agent/slack-*` and `arn:aws:secretsmanager:*:*:secret:ciam-agent/jira-*` only |
| KMS | `kms:Decrypt` | CIAM CMK ARN only (resource-conditioned; used to decrypt Secrets Manager secrets) |
| S3 | `s3:PutObject` | `arn:aws:s3:::governor-audit-logs-*/*` (audit bucket only) |
| CloudWatch Logs | `logs:PutLogEvents`, `logs:CreateLogStream` | CIAM agent log group only (`/ciam/response-generator/*`) |
| Bedrock | `bedrock:InvokeModel` | Scoped to `claude-sonnet-4-5-*` model ARN only |

All other AWS service actions — DynamoDB, Bedrock KB (`Retrieve`,
`RetrieveAndGenerate`), Bedrock model ARNs outside `claude-sonnet-4-5-*`,
SNS, SSM, STS, and IAM — are **not permitted** and are explicitly denied
(see §5).

External HTTPS calls permitted by the action-group allow-list (code layer):

| External endpoint | Method(s) | Tool | Purpose |
| :--- | :--- | :--- | :--- |
| `https://slack.com/api/chat.postMessage` | `POST` | Tool 1 | Post split output to Slack thread. |
| `https://<netskope-jira-host>/rest/api/3/issue/{ticket_key}/comment` | `POST` | Tool 2 | Post internal note on TQI ticket. |
| `https://<netskope-jira-host>/rest/api/3/issue/{ticket_key}` | `PUT` | Tool 3 | Apply classification labels. |

Any HTTPS call to a host outside `slack.com` or the Netskope Jira host, or to
an un-listed path or HTTP method, raises `PostureViolationError` before the
request is issued and is a **defect and a release blocker** (see §5).

### 4.1 Tool Definitions

#### Tool 1 — `post_slack_reply(channel_id: str, thread_ts: str, message_blocks: list[dict]) → SlackDeliveryResult`

Posts the formatted split output as a threaded reply in the Slack channel
where the original L1 message was received.

**Auth:** Slack Bot Token retrieved from Secrets Manager at path
`ciam-agent/slack`. Scope: `chat:write`. The token is never logged or
surfaced in any payload or error message.

**Formatting:** The `message_blocks` parameter is a Slack Block Kit payload
constructed by the agent. Required block structure:

```
[Header block]         — "CIAM Agent Diagnosis — <intent>"
[Divider]
[Section block]        — "📊 RAW DATA" — verbatim field values, attributed
[Divider]
[Section block]        — "🤖 AI DIAGNOSIS" — root cause, confidence, actions
[Divider]
[Actions block]        — (SIMPLE_FIX only) ✅ Approve Fix | ❌ Escalate Instead
[Context block]        — run_id, timestamp, model_used, total_latency_ms
```

The Actions block is **omitted entirely** when `complexity == "ESCALATE_TO_L2"`.
Interactive button payloads carry the `run_id` and
`fix_classification.recommended_actions` in their `value` field for the future
remediation agent to act on when approved.

**Returns:** a `SlackDeliveryResult` with `ok` (boolean), `ts` (Slack message
timestamp of the posted reply), and `error` (string or null).

#### Tool 2 — `post_jira_internal_note(ticket_key: str, note_body: str) → JiraDeliveryResult`

Posts the split output as an internal note (not visible to customers) on the
specified TQI Jira ticket.

**Auth:** Jira API Token retrieved from Secrets Manager at path
`ciam-agent/jira`. **Jira REST API call:**
`POST /rest/api/3/issue/{ticket_key}/comment` with request body:
```json
{
  "body": { "type": "doc", "version": 1, "content": [...] },
  "visibility": { "type": "role", "value": "Service Desk Team" }
}
```
The `visibility` field ensures the note is internal and not exposed to the
customer reporter.

**Returns:** a `JiraDeliveryResult` with `ok` (boolean), `comment_id` (Jira
comment ID of the posted note), and `error` (string or null).

#### Tool 3 — `add_jira_labels(ticket_key: str, labels: list[str]) → JiraDeliveryResult`

Adds classification labels to the TQI Jira ticket without overwriting existing
labels.

**Auth:** Same Jira API Token as Tool 2. **Jira REST API call:**
`PUT /rest/api/3/issue/{ticket_key}` with body:
```json
{ "update": { "labels": [{ "add": "<label>" }, ...] } }
```
Using the `update.labels` field with `add` operations preserves existing labels.

**Labels applied (normative):**

| Condition | Labels added |
| :--- | :--- |
| Always (when `source == "jira"`) | `"ciam-agent-diagnosed"` |
| `complexity == "SIMPLE_FIX"` | `"ciam-agent-fixable"` |
| `complexity == "ESCALATE_TO_L2"` | `"ciam-agent-escalate"` |

**Returns:** a `JiraDeliveryResult` with `ok` (boolean) and `error`
(string or null).

## 5. Explicit Denies (Phase 1 invariants)

The CDK IAM role MUST attach an explicit `Deny` statement covering the
following actions with `Resource: "*"`. These denies are **gating posture
invariants** — CI fails the PR if they are missing or weakened.

| Denied action | Reason |
| :--- | :--- |
| `dynamodb:*` (all actions) | Account data is read by Agent 2; this agent must never touch DynamoDB. |
| `bedrock:Retrieve`, `bedrock:RetrieveAndGenerate` | KB retrieval is owned by Agent 4; this agent receives the KB results as input. |
| `bedrock:InvokeModel` on any ARN outside `claude-sonnet-4-5-*` | Scoped to Sonnet 4.5 only; no Haiku, no other model. |
| `secretsmanager:GetSecretValue` on any path outside `ciam-agent/slack-*` and `ciam-agent/jira-*` | Scoped to output-channel credentials only; no access to Auth0 or other secrets. |
| `s3:GetObject` (any bucket) | This agent writes the audit log; it never reads from S3. |
| `s3:PutObject` on any bucket outside `governor-audit-logs-*` | Audit writes scoped to the audit bucket only. |
| `sns:Publish` | The orchestrator, not this agent, owns alert fanout. |
| `sts:AssumeRole` | No cross-account or cross-service role assumption. |
| `iam:*` | No IAM reads or writes. |
| Auth0 Management API (any HTTPS call to `nskp.auth0.com`) | All Auth0 reads are delegated to Agent 3. |
| Slack `chat.postMessage` on channels outside the original `channel_id` | Output is scoped to the originating thread only. |
| Jira REST API methods beyond `POST /comment` and `PUT /issue/{key}` | No ticket creation, deletion, status transition, or assignee changes. |

Defense in depth: the code-layer action-group (`core/agentcore/action_group.py`)
MUST contain an explicit allow-list of exactly three permitted tool names —
`post_slack_reply`, `post_jira_internal_note`, and `add_jira_labels`. Any
invocation of a tool name outside this list raises `PostureViolationError`
*before* any network call is issued, emits a `posture-violation` finding
(CRITICAL), and aborts the invocation.

## 6. Behavior

An invocation proceeds in the following deterministic steps:

1. **Validate inputs.** Confirm that `account_payload`, `auth0_payload`,
   `kb_payload`, `source`, and `source_metadata` are all present in the
   orchestrator call. A missing payload object (not a payload with an error
   field) returns `error: "missing_upstream_payload"` immediately. Set
   availability flags: `db_unavailable`, `auth0_unavailable`,
   `kb_unavailable` based on non-null `error` fields in each payload.

2. **Total-failure check.** If all three sub-agent payloads have non-null
   `error` fields, return a `ResponsePayload` with `error:
   "all_data_sources_unavailable"`, deliver a minimal error message via the
   appropriate output tool(s), and skip steps 3–8.

3. **Correlate data (model inference).** Invoke `bedrock:InvokeModel`
   (`claude-sonnet-4-5-*`) with the synthesis system prompt (versioned at
   `prompts/ciam-response-generator/v1.md`). The prompt instructs the model
   to apply the synthesis rules in §6.3 and produce a structured
   `SynthesisResult` JSON object. The model receives the full upstream
   payloads as context but is explicitly prohibited from adding information
   not present in them.

4. **Set confidence level.** The model sets confidence in `SynthesisResult`
   per these rules (the prompt enforces them; the code validates them):
   - `HIGH`: all three sub-agent payloads are present with no errors, data
     across sources is consistent, and the birthright mismatch (if any) is
     unambiguous.
   - `MEDIUM`: one sub-agent payload has an error or one field is ambiguous
     (e.g., `data_may_be_stale`, multiple accounts found), but the remaining
     data supports a plausible diagnosis.
   - `LOW`: two or more sub-agent payloads have errors, or data conflicts
     between sources (e.g., DynamoDB reports `Customer` but Auth0 birthright
     is consistent with `Former Customer`), or the root cause is genuinely
     indeterminate.

5. **Apply confidence override.** After the model sets complexity and
   confidence, the code layer applies this deterministic override: if
   `fix_classification.complexity == "SIMPLE_FIX"` **and**
   `confidence == "LOW"` → override complexity to `"ESCALATE_TO_L2"` with
   `override_reason: "low_confidence_prevents_simple_fix"`. This override is
   recorded in `§ METADATA` and is **not** subject to model discretion.

6. **Assemble split output.** Construct the three-section `ResponseBody`
   (schema in §7.2) from the `SynthesisResult`. The § RAW DATA section is
   assembled deterministically from sub-agent payload fields — the model does
   not generate this section; the code does, to prevent hallucination.
   `RawDataSection.auth0_data` and `RawDataSection.dynamodb_data` are each
   built by copying **only** the fields explicitly enumerated in their
   respective `RawAuth0Data` / `RawDynamoDbData` allow-lists (§7.1) — the
   assembly code MUST NOT serialize the full `Auth0UserRecord` or
   `AccountRecord` object, or any other unfiltered upstream structure, into
   this section, since both contain a `user_id` field (two distinct
   internal identifiers, one from Auth0 and one from the NetskopeID table)
   that would otherwise leak through by accident. See §6.3 rule 7 and AC-15.

7. **Deliver output.** Based on `source` and `source_metadata`:
   - `source == "slack"` → call Tool 1 (`post_slack_reply`). If
     `ticket_key` is present in `source_metadata` → also call Tool 2
     (`post_jira_internal_note`). Do NOT call Tool 3 (`add_jira_labels`)
     for Slack-sourced requests.
   - `source == "jira"` → call Tool 2 (`post_jira_internal_note`), then
     call Tool 3 (`add_jira_labels`). Do NOT call Tool 1
     (`post_slack_reply`).
   Delivery failures are non-fatal for the `ResponsePayload` return value
   but are surfaced in `delivery_errors` (see §7.1).

8. **Write audit log.** Write the complete `ResponsePayload` (including
   `SynthesisResult`, delivery results, and `§ METADATA`) as a single JSON
   object to `governor-audit-logs-*/<run_id>/ciam-response-generator.json`
   (`s3:PutObject`) and to the CloudWatch Logs stream
   `/ciam/response-generator/<run_id>`. Audit log write failure is
   non-fatal.

9. **Return payload.** Return the complete `ResponsePayload` to the
   orchestrator.

### 6.1 Tool Call Conditionality

| Condition | Tool 1 | Tool 2 | Tool 3 |
| :--- | :---: | :---: | :---: |
| `source == "slack"`, no `ticket_key` | ✓ | — | — |
| `source == "slack"`, `ticket_key` present | ✓ | ✓ | — |
| `source == "jira"` | — | ✓ | ✓ |

### 6.2 Output Routing Logic

The agent MUST route output to the **originating thread or ticket only**. The
Slack `channel_id` and `thread_ts` are taken from `source_metadata` as
supplied by the orchestrator; the agent must not resolve, discover, or infer
alternative destinations. If `thread_ts` is absent for a Slack source, the
reply is posted as a new message in the channel rather than a thread reply,
and a `routing_warning: "no_thread_ts"` is appended to `delivery_warnings`.

### 6.3 Synthesis Rules (Hallucination Prevention — normative)

These rules are encoded in the synthesis system prompt and enforced by
code-layer post-processing validation. Any `SynthesisResult` that violates
them is rejected and the invocation returns `error: "synthesis_rule_violation"`.

1. **No new information.** Every fact in `§ AI DIAGNOSIS` must trace to a
   field present in one of the three upstream payloads. The model must not
   infer, guess, or introduce external knowledge.
2. **No null guessing.** If a field is `null` or its sub-agent returned an
   error, the output MUST state `"[data unavailable]"` — never a plausible
   value.
3. **Source attribution.** Every fact in `§ RAW DATA` and every claim in
   `§ AI DIAGNOSIS` must be tagged with its source system
   (`"Auth0 shows…"`, `"DynamoDB shows…"`, `"Agent 4 evaluation shows…"`).
4. **Conflict surfacing.** If data conflicts between sources (e.g., DynamoDB
   `account_status: "Customer"` but Auth0 birthright is `["Community",
   "Academy"]` with no `"Support"`), the conflict MUST be stated explicitly
   in `§ AI DIAGNOSIS` and confidence MUST be set to `"LOW"` or `"MEDIUM"`.
5. **§ RAW DATA is code-assembled.** The § RAW DATA section is built by the
   code layer directly from sub-agent payload fields, not by the model, to
   guarantee no model-introduced drift between facts and recommendations.
6. **KB references are supporting evidence only.** Past tickets and Confluence
   docs from `knowledge_base_results` are cited as references, not as the
   primary basis for the diagnosis.
7. **No credential or internal-identifier exposure.** The full list of fields
   that must never appear in L1-visible output, and the fields that should
   appear instead, is normative and defined in §6.5 (Output Sanitization
   Rules) — not merely by prompt instruction, but enforced at the schema
   level via explicit allow-listed structures. See AC-15 for the
   corresponding gating test.

   **This rule applies to `response_body` only.** The audit log
   (`ResponsePayload` written to S3/CloudWatch in §6 step 8) is an internal
   record, not L1-visible output, and MAY retain the full upstream payloads
   — including both `user_id` values, `client_id`, the Auth0 tenant domain,
   and other internal identifiers — for traceability and incident
   investigation. The retention and access-control treatment of that PII is
   governed separately by OQ-4, not by this rule.

### 6.4 Root Cause Determination Logic

The model is instructed to evaluate the following signals in priority order
when determining root cause. This ordering is normative and versioned in the
system prompt:

| Priority | Signal | Likely root cause |
| :---: | :--- | :--- |
| 1 | `kb_payload.birthright_evaluation.explicit_block_detected == true` | Block keyword in entitlements overriding access. |
| 2 | `kb_payload.birthright_evaluation.birthright_correct_but_access_denied == true` | Gatekeeper Action bug or misconfiguration. |
| 3 | `auth0_payload.user_found == false` | User not provisioned in Auth0. |
| 4 | `account_payload.account_found == false` | User not in DynamoDB / Salesforce. |
| 5 | `kb_payload.birthright_evaluation.missing_keywords` non-empty AND `auth0_payload.sync_stale == true` | Birthright sync stale; missing keywords not yet populated. |
| 6 | `kb_payload.birthright_evaluation.missing_keywords` non-empty AND sync is current | Birthright misconfigured; add keywords to entitlements. |
| 7 | `kb_payload.birthright_evaluation.extra_keywords` non-empty | Over-provisioning; security review required. |
| 8 | `intent == "SSO_ERROR"` | Auth0 Connection or SAML federation issue. |
| 9 | None of the above | Indeterminate; escalate with full context. |

> **Note.** A prior revision included a signal referencing
> `account_payload.recent_changes` (an account-status change-history field).
> Agent 2's spec no longer exposes this field — there is no DynamoDB history
> table in Phase 1 (see Agent 2 spec §1, OQ-1) — so that signal has been
> removed from this table and the corresponding former AC-8 has been
> retired. If Agent 2 reintroduces a change-history feature in a later
> phase, a signal referencing it can be added back here as an additive
> change.

### 6.5 Output Sanitization Rules (normative)

The L1-facing output (`response_body` — the Split Output posted to Slack
and/or Jira) **MUST NOT** contain the following internal fields, regardless
of whether they are present in the upstream payloads supplied to this agent.
These fields remain available in the audit log (§6 step 8) for traceability,
since the audit log is an internal record, not L1-visible output (see rule 7
above):

| Field | Why hidden | Where it's retained instead |
| :--- | :--- | :--- |
| `user_id` (Auth0's `Auth0UserRecord.user_id`) | Internal Auth0 identifier. Reveals the connection type and internal username format — a federated `user_id` (e.g. `con_aB3xY9kLm2pQ\|saml\|oscar@earlywarning.com`) additionally leaks the connection ID, the auth protocol, and the IdP mapping. | CloudWatch logs + S3 audit bucket |
| `user_id` (NetskopeID table's `AccountRecord.user_id`) | Internal NetskopeID table identifier; a distinct value from Auth0's `user_id` but the same exposure risk. | CloudWatch logs + S3 audit bucket |
| `client_id` | M2M application identifier — internal infrastructure detail. | CloudWatch logs only |
| `client_secret` | M2M credential — never exposed under any circumstance. | Secrets Manager only; never logged anywhere, including the audit log |
| `access_token` | Auth0 Management API bearer token — never exposed under any circumstance. | In-memory only for the agent that holds it (Agent 3); never logged, including in this agent's audit log |
| Auth0 tenant domain (e.g. `nskp.auth0.com`) | Internal infrastructure detail; not needed for diagnosis. | CloudWatch logs only |
| DynamoDB table name (`NetskopeID`) | Internal infrastructure detail. | CloudWatch logs only |
| AWS account ID | Internal infrastructure detail. | CloudWatch logs only |
| IAM role ARN | Internal infrastructure detail. | CloudWatch logs only |
| Raw connection name when it is a federated connection ID (e.g. `con_aB3xY9kLm2pQ`) | Leaks the customer's specific federated connection identifier. Replaced with a friendly name — see below. | CloudWatch logs + S3 audit bucket (raw value retained there) |

The L1-facing output **SHOULD** contain (non-exhaustive — see the full
`RawAuth0Data` / `RawDynamoDbData` allow-lists in §7.1 for the complete set):

| Field | Why shown |
| :--- | :--- |
| `email` (from `extracted_email`, §3) | L1 identifies the user by email, not by internal `user_id`. This is sufficient for L1's diagnostic needs in Phase 1. |
| `connection` | Shown as a **friendly name**, not the raw connection string — see the mapping below. L1 needs to know the connection *category*, not its raw identifier. |
| `birthright`, `entitlements` | Core diagnostic data. |
| `last_sync`, `last_daily_sync`, `sync_stale`, `birthright_sync_stale` | Helps L1 understand whether sync is current or stale. |
| `account_status`, `customer_status` | Core diagnostic data. |
| `last_login`, `failed_logins_last_7_days`, `last_failed_login_reason` | Helps L1 see recent login activity and failures. |

**Connection friendly-name mapping (normative).** Since the raw `connection`
string is suppressed when it would be a federated connection ID, the agent
maps it to a friendly name before inclusion in `response_body`:

```python
def get_friendly_connection_name(connection: str) -> str:
    """
    Convert internal Auth0 connection names to L1-friendly names.
    Prevents leaking internal connection IDs (e.g. federated connection
    IDs like "con_aB3xY9kLm2pQ") while still telling L1 which connection
    *category* the user authenticates through.
    """
    if connection == "NetskopeID":
        return "NetskopeID (Database)"
    elif connection == "Netskope-Partners":
        return "Legacy Partner (Database)"
    elif connection == "Netskope":
        return "Netskope Internal (Federated SSO)"
    else:
        # Federated connections have random IDs (e.g. "con_aB3xY9kLm2pQ").
        # The raw ID is never exposed to L1 — only the category.
        return "Customer Federated SSO"
```

This mirrors the connection-priority resolution already performed by Agent 3
(`connection_priority` 1/2/3 — see Agent 3 spec §6.3): the friendly name is a
presentation-layer transform applied on top of Agent 3's already-resolved
`connection` and `connection_priority` fields, not a re-derivation of
connection priority logic. `RawAuth0Data.connection` (§7.1) stores the
**friendly name**, not the raw connection string — the raw string is never
copied into `response_body` and remains available only in the audit log.



## 7. Outputs

### 7.1 Response Payload Schema

The agent returns one `ResponsePayload` object to the orchestrator and writes
it in full to the audit log.

```python
class ResponsePayload(BaseModel):
    schema_version:  Literal["1.0"]
    spec_id:         Literal["SPEC-CIAM-0005"]
    agent:           Literal["ciam-response-generator"]
    run_id:          str                        # uuid4, from AgentCore run header
    generated_at:    datetime                   # UTC, isoformat

    # --- Synthesis result ---
    synthesis:       SynthesisResult

    # --- Formatted output sections ---
    response_body:   ResponseBody               # the split output delivered to L1

    # --- Delivery results ---
    slack_delivery:  SlackDeliveryResult | None  # null when not attempted
    jira_note:       JiraDeliveryResult  | None  # null when not attempted
    jira_labels:     JiraDeliveryResult  | None  # null when not attempted
    delivery_errors: list[str]                   # non-fatal delivery failures
    delivery_warnings: list[str]                 # e.g. "no_thread_ts"

    # --- Audit metadata ---
    metadata:        ResponseMetadata

    # --- Top-level error ---
    error:           str | None                 # null on full success


class SynthesisResult(BaseModel):
    root_cause:          str                    # one-sentence summary
    root_cause_detail:   str                    # full explanation (2–5 sentences)
    confidence:          Literal["HIGH", "MEDIUM", "LOW"]
    confidence_reason:   str
    complexity:          Literal["SIMPLE_FIX", "ESCALATE_TO_L2"]
    complexity_overridden: bool                 # true if confidence override applied
    override_reason:     str | None
    db_unavailable:      bool
    auth0_unavailable:   bool
    kb_unavailable:      bool


class ResponseBody(BaseModel):
    raw_data_section:    RawDataSection         # code-assembled; model does not touch
    ai_diagnosis_section: AIDiagnosisSection    # model-generated; synthesis-rule validated
    metadata_section:    MetadataSection


class RawDataSection(BaseModel):
    auth0_data:          RawAuth0Data | None     # allow-listed fields only — see note below; null if auth0_payload errored
    dynamodb_data:       RawDynamoDbData | None  # allow-listed fields only — see note below; null if account_payload errored
    birthright_evaluation: dict[str, Any]        # verbatim fields from KnowledgeBasePayload
    data_availability:   dict[str, bool]         # {auth0, dynamodb, knowledge_base}: available?


class RawDynamoDbData(BaseModel):
    """
    Explicit allow-list of `AccountPayload` / `AccountRecord` fields
    permitted in L1-visible output. `AccountRecord.user_id` (the NetskopeID
    table's own internal identifier — a separate field from Auth0's
    `user_id`) is deliberately excluded for the same reason as the Auth0
    allow-list above: there is no field for it to occupy here, so it cannot
    leak through this section. See §6.3 rule 7 and AC-15.
    """
    account_name:          str | None
    account_status:        str | None
    customer_status:        str | None
    account_type:           str | None
    primary_partner_type:   str | None
    account_is_deleted:     bool
    contact_full_name:      str | None
    contact_title:          str | None
    active_tenant_count:    int
    company_name:           str | None
    country_name:           str | None
    job_title:              str | None
    last_login:             datetime | None
    last_sync:              datetime | None
    last_daily_sync:        datetime | None
    data_may_be_stale:      bool                # derived from AccountPayload.data_warnings
    birthright_sync_stale:  bool                # derived from AccountPayload.data_warnings
    multiple_accounts_found: bool               # derived from len(account_payload.accounts) > 1
    # Deliberately NOT included: user_id (NetskopeID table identifier),
    # email / contact_email (surfaced separately via extracted_email in
    # MetadataSection, not duplicated here), fed_og_id, raw birthright /
    # entitlements / permissions blobs (those are Agent 4's concern and are
    # surfaced via birthright_evaluation, not duplicated here).


class RawAuth0Data(BaseModel):
    """
    Explicit allow-list of Auth0 fields permitted in L1-visible output.
    Deliberately excludes `user_id` (and any other internal identifier) —
    there is no field for it to occupy, so it cannot be copied through by
    accident even if the code that assembles this section is modified later.
    See §6.3 rule 7 and AC-15.
    """
    connection:           str                    # FRIENDLY NAME, not the raw connection string — see §6.5 get_friendly_connection_name()
    connection_priority:  int                    # from Auth0UserRecord
    created_at:           datetime                # from Auth0UserRecord
    last_login:           datetime | None         # from Auth0UserRecord
    logins_count:         int                     # from Auth0UserRecord
    birthright:           list[str]               # from Auth0UserRecord
    entitlements:         list[str]                # from Auth0UserRecord
    last_sync:            datetime | None          # from Auth0UserRecord
    last_daily_sync:      datetime | None          # from Auth0UserRecord
    sync_stale:           bool                     # from Auth0Payload (top level)
    sync_stale_reason:    str | None               # from Auth0Payload (top level)
    failed_logins_last_7_days: int                 # from Auth0Payload (top level)
    last_failed_login_reason:  str | None          # from Auth0Payload (top level)
    multiple_users_found: bool                     # derived from len(auth0_payload.users) > 1
    # Deliberately NOT included: user_id, email (surfaced separately via
    # extracted_email in MetadataSection, not duplicated here), raw Auth0
    # API tokens, internal endpoint URLs, or the `selected` flag's
    # underlying connection-resolution internals beyond what's listed above.


class AIDiagnosisSection(BaseModel):
    root_cause:          str
    confidence:          Literal["HIGH", "MEDIUM", "LOW"]
    confidence_justification: str
    classification:      Literal["SIMPLE_FIX ✅", "ESCALATE_TO_L2 📤"]
    recommended_actions: list[RecommendedAction]
    kb_references:       list[str]              # titles of relevant KB docs/tickets
    escalation_summary:  str | None             # pre-built L2 summary; non-null when ESCALATE


class RecommendedAction(BaseModel):
    priority:  Literal["IMMEDIATE", "ESCALATE", "INVESTIGATE", "NOTIFY"]
    action:    str                              # imperative sentence


class MetadataSection(BaseModel):
    run_id:          str
    generated_at:    datetime
    agent_version:   str                        # from package version
    model_used:      Literal["claude-sonnet-4-5"]
    source:          Literal["slack", "jira"]
    source_metadata: dict[str, Any]
    total_latency_ms: int                       # pipeline_start_at → generated_at


class ResponseMetadata(BaseModel):
    pipeline_start_at: datetime
    total_latency_ms:  int
    model_used:        Literal["claude-sonnet-4-5"]
    agent_version:     str
    synthesis_tokens:  int                      # Bedrock InvokeModel token count
    audit_s3_key:      str | None               # S3 key of the written audit object
    audit_cw_stream:   str | None               # CloudWatch stream name


class SlackDeliveryResult(BaseModel):
    ok:    bool
    ts:    str | None                           # Slack message timestamp
    error: str | None


class JiraDeliveryResult(BaseModel):
    ok:         bool
    comment_id: str | None
    error:      str | None
```

### 7.2 Posture Violation Finding

If the agent's code attempts any denied action, it MUST emit a
`PostureViolationFinding` conforming to `core/findings/schema.py` and abort
the invocation. No `ResponsePayload` is returned in this case.

```python
class PostureViolationFinding(BaseModel):
    schema_version: Literal["1.0"]
    spec_id:        Literal["SPEC-CIAM-0005"]
    agent:          Literal["ciam-response-generator"]
    run_id:         str
    detected_at:    datetime
    category:       Literal["posture-violation"]
    severity:       Literal["CRITICAL"]
    evidence:       dict[str, Any]   # {"attempted_action": "<tool_or_api>"}
                                     # credentials NEVER included
```

## 8. Failure Handling

- **One sub-agent payload unavailable** (non-null `error` field). Set the
  corresponding `*_unavailable` flag to `true`. Proceed with partial data.
  The `§ AI DIAGNOSIS` section MUST state which source is unavailable and note
  that the diagnosis may be incomplete. Confidence is capped at `"MEDIUM"`.
- **Two sub-agent payloads unavailable.** Proceed with remaining data.
  Confidence is capped at `"LOW"`. If complexity evaluates to `"SIMPLE_FIX"`,
  the confidence override in §6 step 5 forces it to `"ESCALATE_TO_L2"`.
- **All three sub-agent payloads unavailable.** Return `ResponsePayload` with
  `error: "all_data_sources_unavailable"`. Deliver a minimal fixed error
  message via the applicable output tool(s): `"Unable to diagnose — all data
  sources unavailable. Please try again or escalate manually."` Do not invoke
  `bedrock:InvokeModel`.
- **Missing upstream payload object** (payload key absent from orchestrator
  call, not just errored). Return `error: "missing_upstream_payload"` without
  invoking any tool. This is a pipeline wiring defect, not a runtime failure.
- **Synthesis rule violation** (model output fails code-layer validation in
  §6.3). Return `error: "synthesis_rule_violation"` with the violated rule
  identifier. Do not deliver partial output to Slack or Jira.
- **Model inference timeout / error.** SDK timeout set to 30 s (Sonnet 4.5
  requires more time than Haiku). On timeout or error after one retry, return
  `error: "model_inference_error"`. Do not deliver output.
- **Slack delivery failure** (`post_slack_reply` returns `ok: false`).
  Non-fatal for the `ResponsePayload`. Record the error in `delivery_errors`.
  Still attempt `post_jira_internal_note` if `ticket_key` is present. Still
  write the audit log.
- **Jira delivery failure** (`post_jira_internal_note` or `add_jira_labels`
  returns `ok: false`). Non-fatal for the `ResponsePayload`. Record in
  `delivery_errors`. Still write the audit log.
- **Audit log write failure** (S3 or CloudWatch). Non-fatal. Record in
  `ResponsePayload.metadata.audit_s3_key: null` or
  `audit_cw_stream: null`. Do not abort the invocation.
- **Posture violation (tripwire).** Any code path that attempts a denied action
  raises `PostureViolationError`, emits a `posture-violation` finding
  (CRITICAL), and aborts the invocation with no `ResponsePayload` returned.
  This is a release-blocker defect.

## 9. Acceptance Criteria (Given/When/Then)

Each AC maps 1:1 to an eval case at
`evals/ciam-response-generator/cases/ac-N.yaml`. ACs marked **GATING** fail
the PR in CI if they regress.

### AC-1 — SIMPLE_FIX case produces correct split output with Slack buttons

- **Given** upstream payloads where `account_status: "Customer"`,
  `user_found: true`, `missing_keywords: ["Support"]`,
  `complexity: "SIMPLE_FIX"`, `confidence: "HIGH"`, and
  `source: "slack"`,
- **When** the agent runs,
- **Then** the `ResponsePayload` has `synthesis.complexity: "SIMPLE_FIX"`,
  `synthesis.confidence: "HIGH"`, `synthesis.complexity_overridden: false`,
  the `§ RAW DATA` section contains exact verbatim field values from all three
  upstream payloads, and the Slack Block Kit payload contains an Actions block
  with `✅ Approve Fix` and `❌ Escalate Instead` buttons.

### AC-2 — ESCALATE_TO_L2 case produces escalation summary and no Slack buttons

- **Given** upstream payloads where `explicit_block_detected: true` and
  `complexity: "ESCALATE_TO_L2"`, and `source: "slack"`,
- **When** the agent runs,
- **Then** `synthesis.complexity: "ESCALATE_TO_L2"`,
  `ai_diagnosis_section.escalation_summary` is non-null and contains a
  pre-built L2 summary, the Slack Block Kit payload does **not** contain an
  Actions block, and `ai_diagnosis_section.recommended_actions` contains at
  least one action with `priority: "ESCALATE"`.

### AC-3 — Jira source posts internal note and applies labels

- **Given** upstream payloads with `complexity: "SIMPLE_FIX"` and
  `source: "jira"` with `ticket_key: "TQI-9999"`,
- **When** the agent runs,
- **Then** Tool 2 (`post_jira_internal_note`) is called with
  `ticket_key: "TQI-9999"`, Tool 3 (`add_jira_labels`) is called with labels
  `["ciam-agent-diagnosed", "ciam-agent-fixable"]`, Tool 1
  (`post_slack_reply`) is **not** called, and `jira_note.ok: true` and
  `jira_labels.ok: true`.

### AC-4 — Slack source with ticket_key posts to both Slack and Jira

- **Given** upstream payloads with `source: "slack"` and
  `source_metadata.ticket_key: "TQI-8888"`,
- **When** the agent runs,
- **Then** Tool 1 (`post_slack_reply`) is called, Tool 2
  (`post_jira_internal_note`) is called with `ticket_key: "TQI-8888"`, Tool 3
  (`add_jira_labels`) is **not** called, and both delivery results have
  `ok: true`.

### AC-5 — Low confidence overrides SIMPLE_FIX to ESCALATE_TO_L2

- **Given** upstream payloads where Agent 4 evaluates `complexity:
  "SIMPLE_FIX"` but the model sets `confidence: "LOW"` due to conflicting
  signals between DynamoDB and Auth0,
- **When** the agent runs,
- **Then** `synthesis.complexity: "ESCALATE_TO_L2"`,
  `synthesis.complexity_overridden: true`,
  `synthesis.override_reason: "low_confidence_prevents_simple_fix"`, and no
  `✅ Approve Fix` button appears in the Slack output.

### AC-6 — Auth0 payload unavailable produces partial diagnosis with warning

- **Given** an `auth0_payload` with a non-null `error` field (e.g., Auth0
  timeout) and valid `account_payload` and `kb_payload`,
- **When** the agent runs,
- **Then** `synthesis.auth0_unavailable: true`,
  `synthesis.confidence` is `"MEDIUM"` or `"LOW"` (never `"HIGH"`),
  the `§ AI DIAGNOSIS` section states that Auth0 data is unavailable, and
  `error: null` (the invocation succeeds in partial mode).

### AC-7 — All sub-agents unavailable returns error and delivers minimal message

- **Given** all three upstream payloads with non-null `error` fields,
- **When** the agent runs,
- **Then** `error: "all_data_sources_unavailable"`, the Slack or Jira output
  contains the fixed error message `"Unable to diagnose — all data sources
  unavailable. Please try again or escalate manually."`, `bedrock:InvokeModel`
  is **not** called, and no synthesis or delivery of a split output is
  attempted.

### AC-8 — RETIRED

This AC previously tested `account_payload.recent_changes` surfacing in root
cause. Agent 2 no longer exposes this field (no DynamoDB history table in
Phase 1 — see §6.4 note and Agent 2 spec §1, OQ-1). Retired rather than
renumbered, so existing references to AC-9 through AC-15 and their eval case
files remain stable. If Agent 2 reintroduces account-change history in a
later phase, a new AC can be added at the end of this section rather than
reusing this number.

### AC-9 — Synthesis rule violation rejected; no partial output delivered

- **Given** a model response that introduces a field value not present in any
  upstream payload (simulated by eval fixture returning fabricated text),
- **When** the code-layer synthesis-rule validator runs,
- **Then** `error: "synthesis_rule_violation"`, no Slack or Jira delivery is
  attempted, and the audit log records the violated rule identifier.

### AC-10 — Agent attempts `dynamodb:Query` (GATING — posture invariant)

- **Given** a malformed tool call or code path that attempts a DynamoDB read
  from within this agent,
- **When** the agent processes the invocation,
- **Then** `PostureViolationError` is raised *before* any AWS SDK call is
  made, no `ResponsePayload` is returned, and a `posture-violation` (CRITICAL)
  finding is emitted. **Gating in CI.**

### AC-11 — Agent attempts `bedrock:RetrieveAndGenerate` (GATING — posture invariant)

- **Given** a malformed tool call or code path that attempts a Bedrock KB
  retrieval call from within this agent,
- **When** the agent processes the invocation,
- **Then** `PostureViolationError` is raised before any AWS SDK call is made,
  no `ResponsePayload` is returned, and a `posture-violation` (CRITICAL)
  finding is emitted. **Gating in CI.**

### AC-12 — Schema conformance (GATING — schema invariant)

- **Given** any invocation that produces a `ResponsePayload`,
- **When** the payload is validated against `ResponsePayload` (Pydantic strict
  mode),
- **Then** it passes validation without error; any failure fails the run and
  the CI gate. **Gating in CI.**

### AC-13 — Delivery failure is non-fatal; audit log still written

- **Given** a simulated Slack API `chat.postMessage` failure (returns
  `ok: false`),
- **When** the agent runs,
- **Then** `slack_delivery.ok: false`, `delivery_errors` is non-empty,
  `error: null` (invocation does not fail), and the audit log is written to S3
  with `audit_s3_key` non-null.

### AC-14 — § RAW DATA section is code-assembled, not model-generated

- **Given** any successful invocation,
- **When** the `raw_data_section` fields are compared against the
  corresponding upstream payload fields permitted by the `RawAuth0Data` /
  `dynamodb_data` / `birthright_evaluation` allow-lists (§7.1),
- **Then** every included value matches its upstream source field exactly
  (byte-for-byte for strings and numbers) with no model-introduced rewording
  or reformatting.

### AC-15 — Internal identifiers and credentials never present in L1-visible output (GATING — posture invariant)

- **Given** any successful or partial invocation where the upstream payloads
  contain: `auth0_payload.users[*].user_id` populated (e.g.
  `"NetskopeID|oscar.armbruster"`, or a federated-style value such as
  `"con_aB3xY9kLm2pQ|saml|oscar@earlywarning.com"`),
  `account_payload.accounts[*].user_id` populated with a distinct NetskopeID
  table identifier, and the agent's own runtime configuration containing a
  `client_id`, a (mocked) `access_token`, the Auth0 tenant domain
  (`nskp.auth0.com`), the `NetskopeID` table name, an AWS account ID, and an
  IAM role ARN,
- **When** the complete `response_body` (i.e. `raw_data_section`,
  `ai_diagnosis_section`, and `metadata_section` — the full L1-visible
  output delivered to Slack and/or Jira) is serialized and searched as text,
- **Then** none of the following appear anywhere in `response_body`: either
  `user_id` value, any string matching a known federated `user_id` pattern
  (e.g. containing `"con_"` or `"|saml|"`), `client_id`, `client_secret`,
  `access_token`, the Auth0 tenant domain string, the literal DynamoDB table
  name, the AWS account ID, or any IAM role ARN. `RawAuth0Data` and
  `RawDynamoDbData` (§7.1) have no field capable of holding any of these.
  The `connection` field present in `response_body` is the **friendly
  name** produced by `get_friendly_connection_name()` (§6.5), never the raw
  connection string. The model-generated `ai_diagnosis_section` text is
  checked the same way (string search against every value above in the test
  fixture) since the model receives the full upstream payloads as inference
  context and could otherwise restate a sensitive value verbatim. This check
  does **not** apply to the audit log written in §6 step 8, which is
  permitted to retain all of the above per §6.5 and OQ-4. **Gating in CI.**

## 10. Eval Mapping Table

| AC | Eval case file | Type | Gating |
| :--- | :--- | :--- | :--- |
| AC-1 | `evals/ciam-response-generator/cases/ac-1.yaml` | structured-assertion | no |
| AC-2 | `evals/ciam-response-generator/cases/ac-2.yaml` | structured-assertion | no |
| AC-3 | `evals/ciam-response-generator/cases/ac-3.yaml` | structured-assertion | no |
| AC-4 | `evals/ciam-response-generator/cases/ac-4.yaml` | structured-assertion | no |
| AC-5 | `evals/ciam-response-generator/cases/ac-5.yaml` | structured-assertion | no |
| AC-6 | `evals/ciam-response-generator/cases/ac-6.yaml` | failure-mode | no |
| AC-7 | `evals/ciam-response-generator/cases/ac-7.yaml` | failure-mode | no |
| AC-8 | _retired — see §9 AC-8 note_ | n/a | no |
| AC-9 | `evals/ciam-response-generator/cases/ac-9.yaml` | synthesis-invariant | no |
| AC-10 | `evals/ciam-response-generator/cases/ac-10.yaml` | posture-invariant | **yes** |
| AC-11 | `evals/ciam-response-generator/cases/ac-11.yaml` | posture-invariant | **yes** |
| AC-12 | `evals/ciam-response-generator/cases/ac-12.yaml` | schema-invariant | **yes** |
| AC-13 | `evals/ciam-response-generator/cases/ac-13.yaml` | failure-mode | no |
| AC-14 | `evals/ciam-response-generator/cases/ac-14.yaml` | synthesis-invariant | no |
| AC-15 | `evals/ciam-response-generator/cases/ac-15.yaml` | posture-invariant | **yes** |

## 11. Open Questions

- **OQ-1.** Interactive button callback handling: the `✅ Approve Fix` and
  `❌ Escalate Instead` Slack buttons carry `run_id` and recommended actions
  in their `value` payloads, but the handler that receives the button click
  and routes to a future remediation agent is out of scope for Phase 1.
  Confirm the callback URL and handler ownership before the Slack app manifest
  is finalised, to avoid publishing interactive components with no listener.
- **OQ-2.** Jira internal note visibility: Tool 2 uses `"role": "Service Desk
  Team"` as the visibility constraint. Confirm this is the correct Jira role
  name for the `TQI` project's internal note visibility setting in the
  Netskope instance, as the role name is case- and project-sensitive.
- **OQ-3.** Synthesis model version pin: this spec pins `claude-sonnet-4-5`.
  Confirm whether the IAM resource condition should be pinned to a specific
  model version ARN (e.g., `claude-sonnet-4-5-20250101`) or to the
  `claude-sonnet-4-5-*` prefix to allow minor version updates without a CDK
  deployment.
- **OQ-4.** Audit log retention: the spec writes the full `ResponsePayload`
  (including all upstream payloads) to S3. The upstream payloads contain PII
  (`email`, `user_id`, `ip` from login history). Confirm the S3 bucket
  lifecycle policy and data retention period for GDPR / SOC 2 compliance
  before the audit bucket CDK stack is deployed.
- **OQ-5.** Confidence scoring calibration: the confidence rules in §6 step 4
  are defined qualitatively (`"data across sources is consistent"`). Before
  Phase 1 launch, define quantitative thresholds (e.g., `HIGH` requires all
  three payloads present with zero `data_warnings`, `MEDIUM` allows at most
  one warning or one missing payload) and encode them in the system prompt
  and the code-layer validator to make AC-5 reliably assertable in CI.
