# Agent 4 Knowledge Base — Content Requirements

This document enumerates exactly what real content is needed to replace
the 8 placeholder stub files currently in
`s3://ciam-agent4-kb-docs-786063285476-us-east-1/docs/`, why each one is
needed, and precisely how Agent 4 uses it. Nothing here is optional —
each document maps to a specific line of code, tool, or test case in
`agent.py` / `SPEC-CIAM-0004`. Where a document is a hard blocker for
correct (not just running) behavior, it is marked **BLOCKING**.

---

## 1. `birthright-entitlement-matrix.md` — **BLOCKING**

### What exactly is needed

- The full, authoritative list of **user personas/types** recognized by
  the CIAM system (e.g. Customer, Partner, Former Customer, Prospect
  with/without tenant, Internal/Netskope employee, Contractor, Trial
  User — confirm the *exact* set; this list itself is unverified).
- For **each persona**, the exact list of `birthright` keywords they are
  entitled to (e.g. `Support`, `Community`, `Academy`, `Notification`,
  `Dashboard` — confirm this is the complete keyword vocabulary, or if
  there are others).
- The **decision rule** that maps a persona to that keyword list — is it
  purely `account_status` + `active_tenant_count`, or are there other
  inputs (contact type, region, product tier)?
- Whether the rule is a flat lookup table or has conditional branches
  (e.g. "Prospect with 0 tenants gets X, but Prospect with 1+ tenants
  gets Y").
- The **real list of `account_status` values** that exist in production
  Salesforce/DynamoDB data (the current provisional table already had
  one wrong value — `"Prospect - Churned"` — that doesn't actually
  exist; there could be others wrong or missing).

### Why it's needed

This is the **single most important document in the entire KB**, because
it isn't just a reference document — it directly determines whether
`derive_persona()` in `agent.py` (lines ~166–178) produces correct
output. Right now that function's persona table is explicitly marked
**provisional** in `SPEC-CIAM-0004` §1 and OQ-6/OQ-7, meaning every
`SIMPLE_FIX` vs. `ESCALATE_TO_L2` decision Agent 4 makes today rests on
an unverified guess. Every other tool in Agent 4 (Tool 3's fix
classification, the KB query construction) is downstream of this.

### How Agent 4 uses it

- `evaluate_birthright()` (Tool 1) computes `expected_birthright` from
  `derive_persona()` — this doc's content should be the literal source
  the persona table is verified against.
- The KB copy of this document also gets **retrieved live** — if an L1
  engineer or Agent 5 wants to double-check *why* a persona has a given
  expected birthright, `query_knowledge_base()` will surface this doc
  when queries mention persona names or missing keywords.

### Source

The real **Birthright & Entitlements Guide** (per spec OQ-6) — export as
`.docx` or paste as text, or better, the actual **sync function source
code** that computes birthright in production (per spec OQ-7; code
outranks documentation if they disagree, since code is what actually
runs).

---

## 2. `auth0-login-flow-steps.md`

### What exactly is needed

- The complete, ordered list of steps a user's login/provisioning
  request passes through in Auth0 (the "9-step flow" referenced earlier
  in this project — e.g. Email Verification, Registration Forms,
  Migration Acknowledgement, Privacy Policy, NetskopeID-Sync-1,
  NetskopeID-Sync-2, RBAC Consolidated, Gatekeeper, MFA Consolidated —
  **confirm this exact list and order**, since it was drafted from
  memory, not a verified source).
- For each step: what field(s) it reads/writes, what a "pass" looks
  like, what a "fail" looks like, and what the resulting user-facing
  error message is (if any).
- Which steps are **relevant to which intents** (e.g. does a
  `SYNC_ISSUE` ticket only ever fail at Sync-1/Sync-2, or can it fail
  anywhere?).

### Why it's needed

Right now, Agent 4 can tell you *what's* wrong (a missing keyword, an
over-provisioned keyword, a block flag) but not *where in the pipeline*
it went wrong. This doc is what would let a future version of Tool 4
(`identify_failing_workflow`, currently a placeholder — see item 8 below
and spec OQ-8) actually map a gap to a specific broken step, instead of
just returning a stub. It's also directly useful to an L1 engineer
reading Agent 5's synthesized response, since "Sync-2 failed" is more
actionable than "there's a gap."

### How Agent 4 uses it

- Retrieved by `query_knowledge_base()` whenever the query references a
  sync/flow-related term.
- Once Tool 4 is implemented for real (blocked on item 8 below), this
  doc becomes the reference table the workflow-mapping logic is built
  against.

### Source

Whoever owns the Auth0 tenant configuration/Actions pipeline — likely
the same person who can supply the raw Auth0 Action/Rule/Flow scripts
(see item 8).

---

## 3. `portal-access-requirements.md`

### What exactly is needed

- For each portal (`Support`, `Community`, `Academy`, `Partner`,
  `Notification`, `Dashboard`, and any others not yet in this project's
  known list), the exact `birthright`/`entitlements` keyword(s) that
  grant access.
- Whether any portal requires **more than one** keyword (AND logic), or
  a specific **RBAC role** in addition to a birthright keyword.
- Any portal-specific caveats (e.g. "Partner portal additionally checks
  tenant type").

### Why it's needed

This is the **inverse view** of document #1 — #1 answers "what should
this persona have," this answers "what does this specific portal
actually check for." The two should agree, and any mismatch between
them is itself a finding worth surfacing. It also directly validates the
`KNOWN_PORTAL_KEYWORDS` frozenset hardcoded in `agent.py` (currently:
`Support, Community, Academy, Notification, Dashboard` — confirm this is
the complete and correct list; `Partner` is notably referenced elsewhere
in this project's specs but is **not** currently in that frozenset,
which may itself be a bug worth checking once this doc exists).

### How Agent 4 uses it

- Cross-referenced conceptually by Tool 1's `KNOWN_PORTAL_KEYWORDS`
  constant — if this doc reveals a missing or wrong keyword, the code
  constant needs updating to match.
- Retrieved live by `query_knowledge_base()` for portal-specific
  questions.

### Source

CIAM platform team / whoever owns the Gatekeeper Action's authorization
logic in Auth0.

---

## 4. `ciam-l1-common-issues.md`

### What exactly is needed

- A curated list of the **most frequently recurring** L1 support issues
  (pull from real ticket volume/frequency if available — not a
  hypothetical list).
- For each issue: symptom description, root cause, standard fix,
  and — critically — which of Agent 4's `fix_classification.complexity`
  values it should map to (`SIMPLE_FIX` / `ESCALATE_TO_L2` / `NO_GAP`),
  so this doc can also serve as a **validation set** for Tool 3's
  decision tree.

### Why it's needed

This is the "greatest hits" troubleshooting reference — it's what lets
Agent 4/5 recognize "oh, this is that common thing" instead of treating
every ticket as novel. It also doubles as a sanity check: if a real
common issue doesn't cleanly map to one of Tool 3's three complexity
values, that's a sign the decision tree in `classify_fix_complexity()`
(agent.py lines ~230–345) is missing a case.

### How Agent 4 uses it

- Retrieved by `query_knowledge_base()` and returned in
  `relevant_docs` whenever a query matches a known pattern.

### Source

Whoever maintains L1 support runbooks/playbooks — likely a
Confluence page or internal wiki already in informal use by the support
team; this project should not need to invent this content from scratch.

---

## 5. `sfdc-to-auth0-field-mapping.md`

### What exactly is needed

- A field-by-field table: Salesforce field name → Auth0 `app_metadata`
  (or `user_metadata`) field name it syncs to, plus the sync mechanism
  name (e.g. "NetskopeID-Sync-1") and direction (one-way vs. two-way).
- Which fields are **required** for birthright calculation vs. which are
  informational only.
- Known **lag/latency** characteristics of each sync (e.g. "runs hourly,"
  "runs on Salesforce record save").

### Why it's needed

When a ticket looks like a sync issue (e.g. "user's Salesforce record
says Active but Auth0 still shows old data"), this doc is what lets
Agent 4/5 pinpoint *which* field is stale and *which* sync job should
have propagated it. Without it, "sync issue" is a diagnosis with no
actionable next step.

### How Agent 4 uses it

- Retrieved by `query_knowledge_base()` for `SYNC_ISSUE` intent queries
  and any query mentioning `sync_stale` / `sync_never_ran` (both already
  computed by `derive_sync_flags()` in `agent.py`).

### Source

Whoever owns the NetskopeID-Sync Lambda/pipeline configuration.

---

## 6. `tenant-configuration.md`

### What exactly is needed

- The tenant → organization → portal-access mapping model (how does a
  user's tenant assignment affect which portals they can reach,
  independent of their persona/birthright?).
- Any known **multi-tenant edge cases** (e.g. a user who should have
  access to two tenants but only has one; a tenant that was
  merged/renamed post-migration).
- How `active_tenant_count` (already a required Agent 4 input — see
  `evaluate_birthright()` signature) is defined and computed upstream.

### Why it's needed

`active_tenant_count` is already load-bearing in Agent 4's persona logic
(it's what distinguishes "Prospect with Tenant" from "Prospect without
Tenant" in the current provisional table), but nothing in this project
yet documents *what a tenant actually is* in this system or how that
count is derived. This doc closes that gap and would also help diagnose
tenant-routing confusion tickets (user has correct entitlements but
wrong tenant assignment).

### How Agent 4 uses it

- Retrieved by `query_knowledge_base()` for tenant-routing or
  multi-tenant confusion queries.

### Source

CIAM platform team / whoever owns tenant provisioning.

---

## 7. `migration-known-issues.md`

### What exactly is needed

- A dated list of specific bugs/gaps introduced by the Nov 1 CIAM
  migration (referenced repeatedly in real tickets tested this
  session — e.g. `TQI-206591`, the `jfuller@winscap.com` Community
  portal case), each with: symptom, affected user segment (if known),
  root cause, remediation status (fixed / workaround / open).
- Whether there's a **cutoff date** after which migration-era issues are
  considered resolved (so this doc doesn't stay "relevant" forever).

### Why it's needed

We already proved this doc's value live — in the end-to-end orchestrator
test with `raw_input` mentioning "Nov 1 migration," Agent 4's KB query
correctly surfaced this document with a 0.35 relevance score. Real
content here would let Agent 4 immediately flag "this matches a known
migration bug" instead of treating it as a fresh, unexplained gap.

### How Agent 4 uses it

- Retrieved automatically by `query_knowledge_base()` whenever
  `raw_input` (the original ticket text) mentions migration-related
  terms — this is already working mechanically, just needs real content.

### Source

Whoever ran/owns the Nov 1 CIAM migration project — likely has a
retro/postmortem doc or a tracked list of migration-related Jira tickets
already.

---

## 8. `resolved-tickets-patterns.md` — **BLOCKING for `similar_past_tickets`**

### What exactly is needed

- A curated export of the **top ~50 resolved TQI tickets** (per the
  original Agent 4 design brief), each formatted consistently with:
  ticket key, one-line summary (PII removed), resolution/fix applied,
  and ideally a persona/intent tag.
- Confirmation of the **exact metadata field convention** to use so
  Agent 4's code can tell a ticket-doc apart from a SOP-doc. Currently
  `agent.py`'s `query_knowledge_base()` (see the `is_ticket` check) uses
  a heuristic — title starts with or contains `"tqi-"` — as a stand-in
  per spec OQ-3. **This needs to be confirmed or replaced** with
  whatever the real ingestion metadata convention will be once actual
  ticket exports are uploaded.

### Why it's needed

This is the entire basis for `similar_past_tickets` in Agent 4's output
schema — without it, that field will always be empty, no matter how
good the birthright logic is. It's also, per the original design intent
for this agent, one of the most valuable things Agent 4 can surface to
an L1 engineer: "someone already solved this exact problem, here's how."

### How Agent 4 uses it

- Directly populates `KnowledgeBaseResults.similar_past_tickets` in the
  agent's output schema (`agent.py`, `KBTicket` class).
- The classification heuristic (`is_ticket` check in
  `query_knowledge_base()`) needs to be revisited once this doc's real
  naming/metadata convention is known — flagged here so it isn't
  forgotten.

### Source

Exported from Jira (TQI project, `status: Done`, ideally last 90 days
per spec §4.1 Tool 2's "past resolved TQI tickets" ingestion path
description) — PII must be stripped per this project's established
practice (see the `jfuller@winscap.com` ticket sanitization done earlier
this session as the precedent).

---

## Summary Table

| # | Document | Blocking? | Feeds | Source Owner |
|---|---|:---:|---|---|
| 1 | `birthright-entitlement-matrix.md` | **Yes** | Tool 1 persona table | Birthright Guide owner / sync-code owner |
| 2 | `auth0-login-flow-steps.md` | No (Tool 4 already deferred) | Future Tool 4 | Auth0 tenant/Actions owner |
| 3 | `portal-access-requirements.md` | No | Validates `KNOWN_PORTAL_KEYWORDS` | Gatekeeper Action owner |
| 4 | `ciam-l1-common-issues.md` | No | KB retrieval + Tool 3 validation | L1 support playbook owner |
| 5 | `sfdc-to-auth0-field-mapping.md` | No | Sync-issue diagnosis | NetskopeID-Sync owner |
| 6 | `tenant-configuration.md` | No | `active_tenant_count` context | Tenant provisioning owner |
| 7 | `migration-known-issues.md` | No (already proven useful even empty-adjacent) | KB retrieval | Migration project owner |
| 8 | `resolved-tickets-patterns.md` | **Yes** (for `similar_past_tickets`) | `KBTicket` output | Jira/TQI export |

**Nothing on this list is currently satisfied** — all 8 S3 objects
contain only placeholder stub text. Items 1 and 8 are the two genuine
blockers for Agent 4 producing trustworthy, non-placeholder output;
the rest improve retrieval quality and coverage but don't block basic
correct operation.
