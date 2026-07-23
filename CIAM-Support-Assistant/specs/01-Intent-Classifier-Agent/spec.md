---
spec_id: SPEC-CIAM-0001
capability: ciam-intent-classifier
status: Draft
owner: Shristy Jaiswal
reviewers: [Peer]
approver: Ritwik Mandal
prd: https://confluence.netskope.example/display/GIS/ciam-intent-classifier-prd  # placeholder — link to docs/confluence/ciam-intent-classifier/prd.md until Phase 0 lands
jira_epic: GIS-EPIC-CIAM  # placeholder — see docs/jira/ciam-intent-classifier-epic.md until Phase 0 lands
version: 0.4.0
created: 2026-06-23
last_updated: 2026-07-23
---

# spec.md — CIAM Intent Classifier Agent (Agent 1)

> This is the **executable contract**. Code, evals, and PR review trace back to
> this file. Acceptance criteria map 1:1 to eval cases under
> `evals/ciam-intent-classifier/cases/`. Posture/zero-external-access invariants
> (AC-7, AC-8, AC-9) are **gating in CI**: a regression fails the PR.

## 1. Summary

The CIAM Intent Classifier is the **orchestration entry point** of the CIAM
Support Assistant pipeline. It is a Layer 0 stateless AgentCore agent invoked
automatically whenever a new ticket is created in the **Jira TQI project** for
a CIAM-related issue. It receives the ticket's text content, classifies the
issue into one of eight canonical intent categories, extracts the user email
address and optional portal hint, determines which downstream sub-agents
(Agents 2–4) need to be invoked, and returns a single structured JSON routing
envelope to the orchestrator. The agent performs **no external system calls**
— no Auth0, no DynamoDB, no Salesforce, no Jira writes. Its only output is the
JSON routing envelope; all diagnosis and data retrieval is delegated to
downstream agents.

> **Single entry point (Phase 1).** Jira TQI ticket creation is the **only**
> trigger for this agent in Phase 1. There is no Slack entry point. If a
> Slack-based trigger (e.g. `#ciam-support` mentions) is introduced in a later
> phase, it requires a spec revision — see §3.1 and OQ-7.

> **Downstream contract.** `auto_escalate` and `escalation_reason` are not
> decorative fields — they are this agent's mechanism for halting the
> pipeline before any sub-agent runs. The orchestrator (and, transitively,
> Agent 5 / the L2 escalation path) **MUST** treat `auto_escalate: true` as a
> hard stop: skip invoking Agents 2–4 regardless of their individual
> `invoke_agent_*` flags (which are always `false` when `auto_escalate` is
> `true`, per §6 step 8), and instead route the ticket to L2 using
> `escalation_reason` as the displayed cause. This consumer obligation is
> binding on whichever spec defines the orchestrator/Agent 5 behavior, even
> though that spec does not yet exist — see OQ-6.

## 2. Goals / Non-Goals

### Goals

- Trigger automatically on **Jira TQI ticket creation** for CIAM-related
  issues, via the Jira webhook entry point.
- Classify the ticket into exactly **one** of the eight intent categories
  defined in §6.
- Extract the **user email address** from the ticket text (primary entity for
  all downstream lookups).
- Extract the **portal hint** when a specific Netskope portal is mentioned
  (Support, Community, Academy, Partner, Notification, Dashboard, Prime).
- Produce a deterministic, **Pydantic-validated JSON routing envelope** that
  specifies which sub-agents to invoke and whether to auto-escalate to L2.
- Auto-escalate (route to L2, invoke zero sub-agents) when no email is found,
  confidence is below threshold, or intent is `UNKNOWN` or `PASSWORD_RESET`.
- Emit a `posture-violation` finding (CRITICAL) and halt if the agent's own
  code attempts any external API call outside the allow-list (defense-in-depth
  tripwire).
- Produce byte-stable output for identical inputs (deterministic classification).

### Non-goals

- Diagnosing the root cause of an access issue (delegated to Agents 2–4).
- Querying Auth0, DynamoDB, Salesforce, Bedrock KB, or any external system.
- Writing to Jira (creating/updating tickets, posting comments) or any
  persistence store.
- MFA resets, password resets, or any write-side action on behalf of a user.
- Multi-turn conversation handling — each invocation is a single-shot
  classification of one Jira ticket.
- Account creation or entitlement provisioning (detect intent only; action
  deferred to L2 or a future remediation spec).
- Any Slack-based entry point (deferred — see §3.1 and OQ-7).

## 3. Inputs

| Input | Source | Notes |
| :--- | :--- | :--- |
| Jira webhook payload | Jira TQI project webhook (`issue_created`) | The `issue.fields.description`, `issue.fields.summary`, and `issue.key` fields from the Jira issue-created webhook. |
| Run ID | AgentCore run header | Propagated to the routing envelope and any posture-violation findings for traceability. |

The agent is **fully stateless** — it holds no memory between invocations and
reads no external configuration at runtime beyond what is supplied in the
input payload.

### 3.1 Entry Point (normative)

Phase 1 has exactly **one** entry point: the **Jira TQI project webhook**,
firing on `issue_created` events for tickets filed against CIAM-related
issues. The Jira entry-point adapter (the Lambda/handler that receives this
webhook) invokes the classifier directly — there is no `source` field to
branch on, since Jira is the only caller. The classifier MUST NOT assume any
other invocation path exists in Phase 1.

This is a deliberate simplification from the original design (which also
considered a Slack `app_mention` entry point). Slack support is explicitly
out of scope for Phase 1 — see Non-goals and OQ-7. If Slack is added in a
later phase, this spec will need a new `source` discriminator field and the
corresponding routing/schema changes reintroduced; that is **not** assumed
or pre-built here.

## 4. Permitted Tools / Authorization Boundary

The Intent Classifier has **zero permitted external API calls** beyond the
single Bedrock model invocation. It operates entirely on the text supplied in
the invocation payload. The `ALLOWED_ACTIONS` allow-list, defined directly in
`agent.py` (there is no separate action-group module), contains **exactly
one** entry — `bedrock:InvokeModel` — checked via an `assert_posture(action)`
tripwire before every SDK call. Any attempt to call an action outside this set
raises `PostureViolationError` before the call is issued.

| Tool | Permitted | Notes |
| :--- | :--- | :--- |
| Auth0 Management API | **NO** | Owned by Agent 3. |
| DynamoDB (any table) | **NO** | Owned by Agent 2. |
| Salesforce API | **NO** | Owned by Agent 2 via DynamoDB replica. |
| Bedrock Knowledge Base | **NO** | Owned by Agent 4. |
| SNS `Publish` | **NO** | Only the orchestrator publishes alerts. |
| Jira REST API (writes) | **NO** | No ticket mutation in Phase 1. |
| S3 (any bucket) | **NO** | No state persistence for this agent. |
| Bedrock `InvokeModel` | **YES** | Scoped to `claude-haiku-*` model ID only, for the classification inference call. |

Any tool implementation that calls an API not in this table is a **defect and a
release blocker** (see §5).

## 5. Explicit Denies (Phase 1 invariants)

The agent's code-layer `ALLOWED_ACTIONS` allow-list (in `agent.py`) MUST
contain only `bedrock:InvokeModel`. Because this agent has no IAM execution
role with AWS service permissions beyond model invocation, the deny surface
for every other action is enforced entirely in code rather than via an IAM
policy. These invariants are **gating posture invariants** — CI fails the PR
if they are missing or weakened.

| Denied capability | Reason |
| :--- | :--- |
| Any Auth0 API call | Classification requires no live identity data. |
| Any DynamoDB read or write | No account data needed at classification time. |
| Any S3 read or write | Agent is stateless; no baseline or audit bucket access. |
| Any SNS `Publish` | The orchestrator, not this agent, owns alert fanout. |
| Any Jira REST write (`PUT`, `POST`, `DELETE`) | No ticket mutation in Phase 1. |
| Any Bedrock Knowledge Base (`Retrieve`, `RetrieveAndGenerate`) | RAG is owned by Agent 4. |
| Any `sts:AssumeRole` | No cross-account or cross-service role assumption. |
| Any network egress outside `bedrock:InvokeModel` | Classification is a self-contained inference task. |

Defense in depth: in addition to the code-layer deny list, the agent's
invocation runtime MUST be deployed with an IAM execution role that has
**only** `bedrock:InvokeModel` (scoped to `claude-haiku-*` ARN). Any attempt
to call a denied capability raises `PostureViolationError`, emits a
`posture-violation` finding (CRITICAL), and aborts the invocation so the
Oversight Agent can surface it.

## 6. Behavior

An invocation proceeds in the following deterministic steps:

1. **Validate input.** Confirm the payload contains a non-empty `text` field
   (the concatenation of `issue.fields.summary` and `issue.fields.description`
   — see OQ-5) and a non-null `issue.key`. If either is missing or malformed,
   return a routing envelope with `intent: "UNKNOWN"`, `auto_escalate: true`,
   `escalation_reason: "malformed_input"`, and `confidence: 0.0` without
   invoking the model.

2. **Extract ticket key.** Extract `issue.key` from the payload and set
   `ticket_key` in the routing envelope (e.g. `"TQI-4321"`).

3. **Classify intent.** Invoke `bedrock:InvokeModel` (`claude-haiku-*`) with
   the classification system prompt (versioned at
   `prompts/ciam-intent-classifier/v1.md`). The prompt instructs the model to
   return a JSON object with `intent`, `confidence` (float 0–1), and
   `extracted_email` (string or `null`), and `extracted_portal` (string or
   `null`). The model MUST NOT be given any tool access at this step — it
   performs text analysis only.

4. **Validate classification output.** Parse and validate the model's JSON
   response against `ClassificationResult` (Pydantic). On parse failure, set
   `intent: "UNKNOWN"`, `confidence: 0.0`, `auto_escalate: true`,
   `escalation_reason: "model_parse_error"`.

5. **Apply email extraction rules.** The final `extracted_email` is resolved
   via a two-stage fallback: prefer the model's own extraction; if the model
   returns `null`, fall back to the first email found by a deterministic regex
   pass over the raw text (see OQ-2 — this fallback is implemented, not
   pending).
   - If the **final** `extracted_email` (after the fallback) is still `null`
     → override `intent` to `"UNKNOWN"`, set `auto_escalate: true`,
     `escalation_reason: "no_email_found"`.
   - If multiple emails are present in the raw text (regardless of which one
     the model or fallback selected) → log a `routing_warning:
     "multiple_emails_found"` in the envelope.

6. **Apply confidence threshold.** If `confidence < 0.7` (and `intent` is not
   already overridden) → set `auto_escalate: true`,
   `escalation_reason: "low_confidence"`.

7. **Apply password-reset/unknown escalation rules.** If `intent` is
   `"PASSWORD_RESET"` or `"UNKNOWN"` → set `auto_escalate: true`. These
   intents always escalate regardless of confidence score.

8. **Resolve routing flags.** Using the routing table in §6.1, populate
   `invoke_agent_2` (Database), `invoke_agent_3` (Auth0), and `invoke_agent_4`
   (Knowledge Base) as booleans. If `auto_escalate: true`, all three flags are
   `false`.

9. **Return routing envelope.** Emit the complete `RoutingEnvelope` JSON
   (schema in §7) to the orchestrator. No writes to any external system occur.

### 6.1 Intent Routing Table

| Intent | Description | `invoke_agent_2` | `invoke_agent_3` | `invoke_agent_4` | `auto_escalate` |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `ACCESS_DENIED` | User cannot access a Netskope portal. | ✓ | ✓ | ✓ | — |
| `SSO_ERROR` | SSO error, redirect loop, or SAML failure. | — | ✓ | — | — |
| `ACCOUNT_NOT_FOUND` | User does not exist in Auth0 or Salesforce. | ✓ | ✓ | — | — |
| `PASSWORD_RESET` | Password reset requested, or reset token/link invalid. | — | — | — | **always** |
| `ACCOUNT_CREATION` | Request to create a new portal account. | ✓ | ✓ | — | — |
| `BIRTHRIGHT_INQUIRY` | Question about what access a user should have. | ✓ | ✓ | ✓ | — |
| `SYNC_ISSUE` | Birthright sync not run or stale entitlements. | ✓ | ✓ | ✓ | — |
| `UNKNOWN` | Cannot classify or insufficient context. | — | — | — | **always** |

### 6.2 Portal Extraction

When the ticket text contains one of the following portal names
(case-insensitive), the classifier populates `extracted_portal` with the
canonical value:

| Keyword(s) in message | Canonical `extracted_portal` value |
| :--- | :--- |
| "support portal", "support access", bare "support" | `"Support"` |
| "community" | `"Community"` |
| "academy", "learning" | `"Academy"` |
| "partner portal", "partner access", bare "partner" | `"Partner"` |
| "notification", "notification center" | `"Notification"` |
| "dashboard" | `"Dashboard"` |
| "prime", "prime okta", "prime tenant", "prime partner okta" | `"Prime"` |

> Matching on the bare substrings "support" and "partner" (not just the
> multi-word phrases) is intentional per `PORTAL_KEYWORD_TABLE` in `agent.py`
> — it maximizes recall on short/informal tickets, at the cost of also
> matching incidental uses of those words (see OQ-3 for whether this should be
> narrowed).

If no portal keyword is found, `extracted_portal` is `null`. If multiple portals
are mentioned, capture only the **first** match and log
`routing_warning: "multiple_portals_found"`.

> **Note on "Partner" vs. "Prime."** These are distinct portal contexts in
> Phase 1 and MUST NOT be conflated: `"Partner"` matches generic partner-portal
> language, while `"Prime"` specifically matches references to the **Prime
> Okta Tenant** / **Prime Partner Okta** identity provider context. A ticket
> mentioning both keyword groups captures whichever appears first in the text,
> per the multiple-portal rule above.

### 6.3 Determinism

For identical ticket text inputs the routing envelope is **byte-stable**
except for the fields `run_id` and `classified_at`. This is verified in
eval AC-9.

## 7. Outputs

### 7.1 Routing Envelope Schema

The agent returns exactly one `RoutingEnvelope` object to the orchestrator.
The shape is:

```python
class RoutingEnvelope(BaseModel):
    schema_version: Literal["1.0"]
    spec_id: Literal["SPEC-CIAM-0001"]
    agent: Literal["ciam-intent-classifier"]
    run_id: str                          # uuid4, from AgentCore run header
    classified_at: datetime              # UTC, isoformat
    source: Literal["jira"]              # fixed to "jira" — sole Phase 1 entry point
    ticket_key: str                      # e.g. "TQI-4321"; always present (Jira-only)
    raw_text_length: int                 # character count of input text (no PII)
    intent: Literal[
        "ACCESS_DENIED",
        "SSO_ERROR",
        "ACCOUNT_NOT_FOUND",
        "PASSWORD_RESET",
        "ACCOUNT_CREATION",
        "BIRTHRIGHT_INQUIRY",
        "SYNC_ISSUE",
        "UNKNOWN",
    ]
    confidence: float                    # 0.0–1.0; 0.0 on parse/input error
    extracted_email: str | None          # first email found; null if none
    extracted_portal: str | None         # canonical portal name or null — one of
                                          # "Support","Community","Academy","Partner",
                                          # "Notification","Dashboard","Prime" (see §6.2)
    invoke_agent_2: bool                 # Database Agent
    invoke_agent_3: bool                 # Auth0 Agent
    invoke_agent_4: bool                 # Knowledge Base Agent
    auto_escalate: bool                  # true → route to L2, no sub-agents invoked
    escalation_reason: str | None        # populated when auto_escalate is true
    routing_warnings: list[str]          # non-fatal warnings (e.g. multiple emails)
```

`source` is fixed to the literal `"jira"` in Phase 1 — it is retained as a
field (rather than removed) so a future Slack entry point can be added as an
additive schema change instead of a breaking one, per OQ-7.

### 7.2 Posture Violation Finding

If the agent's own code attempts a denied external call, it MUST also emit a
`PostureViolationFinding` conforming to `core/findings/schema.py`:

```python
class PostureViolationFinding(BaseModel):
    schema_version: Literal["1.0"]
    spec_id: Literal["SPEC-CIAM-0001"]
    agent: Literal["ciam-intent-classifier"]
    run_id: str
    detected_at: datetime
    category: Literal["posture-violation"]
    severity: Literal["CRITICAL"]
    evidence: dict[str, Any]             # {"attempted_call": "<api_name>"}
```

The `RoutingEnvelope` is **not** returned on a posture violation — the
invocation aborts after emitting the finding.

## 8. Failure Handling

- **Model inference timeout / error.** If `bedrock:InvokeModel` returns an
  error or times out (max 10 s), set `intent: "UNKNOWN"`, `confidence: 0.0`,
  `auto_escalate: true`, `escalation_reason: "model_inference_error"`. The
  routing envelope is still returned; the invocation does not raise an
  unhandled exception.
- **Malformed model JSON response.** If the model's output cannot be parsed as
  valid `ClassificationResult` JSON, set `intent: "UNKNOWN"`, `confidence: 0.0`,
  `auto_escalate: true`, `escalation_reason: "model_parse_error"`.
- **No email in ticket.** Override intent to `"UNKNOWN"`, `auto_escalate:
  true`, `escalation_reason: "no_email_found"`, regardless of classified intent
  (see §6 step 5).
- **Low confidence (< 0.7).** Set `auto_escalate: true`,
  `escalation_reason: "low_confidence"`. The classified `intent` value is
  still recorded for observability but no sub-agents are invoked.
- **Posture violation (tripwire).** Any code path that attempts a denied
  external call raises `PostureViolationError`, emits a `posture-violation`
  finding (CRITICAL), and aborts the invocation with no `RoutingEnvelope`
  returned. This is a release-blocker defect.

## 9. Acceptance Criteria (Given/When/Then)

Each AC maps 1:1 to an eval case at `evals/ciam-intent-classifier/cases/ac-N.yaml`.
ACs marked **GATING** fail the PR in CI if they regress.

### AC-1 — ACCESS_DENIED intent classified and routed correctly

- **Given** a Jira TQI ticket containing a user email and language indicating
  the user cannot access the Support portal (e.g. "getting Access Denied on
  support portal"),
- **When** the agent runs,
- **Then** the routing envelope has `intent: "ACCESS_DENIED"`, `confidence >=
  0.7`, `extracted_email` matching the email in the ticket,
  `extracted_portal: "Support"`, `invoke_agent_2: true`, `invoke_agent_3:
  true`, `invoke_agent_4: true`, and `auto_escalate: false`.

### AC-2 — SSO_ERROR intent routes to Agent 3 only

- **Given** a Jira TQI ticket containing a user email and language indicating
  an SSO redirect loop (e.g. "SSO redirect loop, can't log in"),
- **When** the agent runs,
- **Then** the routing envelope has `intent: "SSO_ERROR"`, `invoke_agent_2:
  false`, `invoke_agent_3: true`, `invoke_agent_4: false`, and `auto_escalate:
  false`.

### AC-3 — PASSWORD_RESET auto-escalates with zero sub-agents invoked

- **Given** a Jira TQI ticket containing a user email and a request to reset
  a password (e.g. "user needs password reset"),
- **When** the agent runs,
- **Then** the routing envelope has `intent: "PASSWORD_RESET"`,
  `auto_escalate: true`, `invoke_agent_2: false`, `invoke_agent_3: false`,
  `invoke_agent_4: false`, and `escalation_reason` is non-null.

### AC-4 — No email found forces UNKNOWN and auto-escalation

- **Given** a Jira TQI ticket that describes an access issue but contains no
  email address,
- **When** the agent runs,
- **Then** the routing envelope has `intent: "UNKNOWN"`, `extracted_email:
  null`, `auto_escalate: true`, and `escalation_reason: "no_email_found"`,
  regardless of what intent the model would otherwise classify.

### AC-5 — Low confidence forces auto-escalation

- **Given** a ticket that yields a model `confidence` score below `0.7`,
- **When** the agent runs,
- **Then** the routing envelope has `auto_escalate: true`,
  `escalation_reason: "low_confidence"`, and all `invoke_agent_*` flags are
  `false`.

### AC-6 — Multiple emails: first used, warning logged

- **Given** a Jira TQI ticket containing two distinct email addresses,
- **When** the agent runs,
- **Then** `extracted_email` equals the **first** email found in the ticket
  text, `routing_warnings` contains `"multiple_emails_found"`, and the run
  does not error.

### AC-7 — Agent attempts Auth0 API call (GATING — posture invariant)

- **Given** a malformed prompt or tool shim that attempts to call the Auth0
  Management API from within the classifier,
- **When** the agent processes the invocation,
- **Then** `PostureViolationError` is raised *before* any HTTP call is made, no
  `RoutingEnvelope` is returned, and a `posture-violation` (CRITICAL) finding
  is emitted. **Gating in CI.**

### AC-8 — Agent attempts DynamoDB read (GATING — posture invariant)

- **Given** a malformed prompt or tool shim that attempts a DynamoDB `GetItem`
  call from within the classifier,
- **When** the agent processes the invocation,
- **Then** `PostureViolationError` is raised before any AWS API call is made,
  no `RoutingEnvelope` is returned, and a `posture-violation` (CRITICAL)
  finding is emitted. **Gating in CI.**

### AC-9 — Schema conformance (GATING — schema invariant)

- **Given** any invocation that produces a `RoutingEnvelope`,
- **When** the envelope is validated against `RoutingEnvelope` (Pydantic strict
  mode),
- **Then** it passes validation without error; any failure fails the run and the
  CI gate. **Gating in CI.**

### AC-10 — Jira ticket key always extracted

- **Given** a Jira TQI webhook payload with `issue.key: "TQI-4321"` and a
  ticket containing a user email,
- **When** the agent runs,
- **Then** the routing envelope has `ticket_key: "TQI-4321"` and
  `source: "jira"`.

### AC-11 — UNKNOWN intent auto-escalates

- **Given** a ticket containing a user email but content that does not match
  any of the seven named intent categories,
- **When** the agent runs,
- **Then** the routing envelope has `intent: "UNKNOWN"`, `auto_escalate: true`,
  and all `invoke_agent_*` flags are `false`.

### AC-12 — Determinism: identical input produces identical envelope

- **Given** the same ticket text and `issue.key` submitted in two separate
  invocations,
- **When** both runs complete,
- **Then** the two routing envelopes are byte-identical except for the `run_id`
  and `classified_at` fields. *(This is the false-non-determinism floor test.)*

### AC-13 — Prime portal keyword extracted correctly

- **Given** a Jira TQI ticket containing a user email and language referencing
  the Prime Okta Tenant or Prime Partner Okta (e.g. "user can't log into Prime
  Okta, getting access denied"),
- **When** the agent runs,
- **Then** the routing envelope has `extracted_portal: "Prime"`, distinct from
  `"Partner"`, and the intent/routing flags are determined per §6.1 as for any
  other `ACCESS_DENIED` message.

### AC-14 — Missing ticket text or issue.key forces malformed-input escalation

- **Given** a Jira webhook payload missing `issue.fields.description` and
  `issue.fields.summary`, or missing `issue.key`,
- **When** the agent runs,
- **Then** the routing envelope has `intent: "UNKNOWN"`, `confidence: 0.0`,
  `auto_escalate: true`, `escalation_reason: "malformed_input"`, and the
  model is never invoked.

## 10. Eval Mapping Table

| AC | Eval case file | Type | Gating |
| :--- | :--- | :--- | :--- |
| AC-1 | `evals/ciam-intent-classifier/cases/ac-1.yaml` | structured-assertion | no |
| AC-2 | `evals/ciam-intent-classifier/cases/ac-2.yaml` | structured-assertion | no |
| AC-3 | `evals/ciam-intent-classifier/cases/ac-3.yaml` | structured-assertion | no |
| AC-4 | `evals/ciam-intent-classifier/cases/ac-4.yaml` | structured-assertion | no |
| AC-5 | `evals/ciam-intent-classifier/cases/ac-5.yaml` | structured-assertion | no |
| AC-6 | `evals/ciam-intent-classifier/cases/ac-6.yaml` | structured-assertion | no |
| AC-7 | `evals/ciam-intent-classifier/cases/ac-7.yaml` | posture-invariant | **yes** |
| AC-8 | `evals/ciam-intent-classifier/cases/ac-8.yaml` | posture-invariant | **yes** |
| AC-9 | `evals/ciam-intent-classifier/cases/ac-9.yaml` | schema-invariant | **yes** |
| AC-10 | `evals/ciam-intent-classifier/cases/ac-10.yaml` | structured-assertion | no |
| AC-11 | `evals/ciam-intent-classifier/cases/ac-11.yaml` | structured-assertion | no |
| AC-12 | `evals/ciam-intent-classifier/cases/ac-12.yaml` | determinism-assertion | no |
| AC-13 | `evals/ciam-intent-classifier/cases/ac-13.yaml` | structured-assertion | no |
| AC-14 | `evals/ciam-intent-classifier/cases/ac-14.yaml` | structured-assertion | no |

## 11. Open Questions

- **OQ-1.** Confidence threshold: `0.7` is the Phase 1 default. Should this be
  tunable per-intent (e.g. a lower threshold for `ACCESS_DENIED` which is the
  most common case) or remain a single global value? Pending eval data from
  Phase 1 runs.
- **OQ-2 (resolved).** Email extraction strategy: the implementation prefers
  the model's own extraction, falling back to the first email found by a
  regex pass over the raw text only if the model returns `null` (see §6 step
  5). This is already implemented unconditionally in `agent.py`, not an open
  decision.
- **OQ-3.** Portal extraction: "Prime" (Prime Okta Tenant / Prime Partner Okta)
  has been added to the §6.2 keyword table. Is the list now exhaustive for
  Phase 1, or do additional portal aliases (e.g. "NSS", "Borderless WAN")
  still need to be included? Requires review by the CIAM product team.
- **OQ-4.** `ACCOUNT_CREATION` routing: Agent 2 + Agent 3 are invoked to check
  whether the account already exists, but no creation action is taken.
  Should a fifth `invoke_agent_5` flag (Response Generator) be set directly
  here, or does the orchestrator always fan out to Agent 5 regardless? Pending
  orchestrator design decision.
- **OQ-5.** Jira webhook text source: §6 step 1 assumes the classification
  text is `issue.fields.summary` concatenated with `issue.fields.description`.
  Confirm this is sufficient, or whether custom TQI fields also carry
  relevant context that should be concatenated in.
- **OQ-6.** `auto_escalate` consumption: this spec defines `auto_escalate` and
  `escalation_reason` as a hard-stop signal (see §1, "Downstream contract"),
  but no orchestrator or Agent 5 spec currently exists to specify *how* that
  signal is acted on (e.g. posting an L2-escalation comment on the Jira
  ticket, tagging severity). This must be closed when the
  Orchestrator/Response Generator spec is written, so the field does not
  remain set-but-unread in the running system.
- **OQ-7.** Slack entry point: out of scope for Phase 1 (see §3.1). If a
  later phase reintroduces a Slack `app_mention` trigger, this spec will need
  a `source` discriminator with `"jira" | "slack"` values, conditional
  `ticket_key` handling, and corresponding ACs — tracked here so it isn't
  silently reintroduced without a spec revision.
