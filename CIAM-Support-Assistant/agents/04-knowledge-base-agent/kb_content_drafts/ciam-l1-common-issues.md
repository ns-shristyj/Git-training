# CIAM L1 Common Issues & Fixes

> **DRAFT — needs review against real L1 support playbooks/ticket
> volume.** This draft is built from the test scenarios exercised
> against Agents 1–4 this session (real, but a small sample — not
> necessarily representative of true issue frequency). Replace with
> actual frequency-ranked data once available.

## Purpose

A "greatest hits" reference of recurring L1 issues, so Agent 4/5 can
recognize a known pattern instead of treating every ticket as novel.
Also doubles as a validation set: if a real common issue doesn't map
cleanly to `SIMPLE_FIX` / `ESCALATE_TO_L2` / `NO_GAP`, that's a sign
Tool 3's decision tree (`classify_fix_complexity`) is missing a case.

## Issue Patterns Observed This Session

### 1. Missing single portal entitlement (Customer)

- **Symptom:** Customer user reports "Access Denied" on one specific
  portal (e.g. Support), all other portals work fine.
- **Root cause:** `birthright` array is missing the one keyword; no
  compensating `entitlements` override.
- **Agent 4 classification:** `SIMPLE_FIX` — add the missing keyword to
  `entitlements`.
- **Confidence:** HIGH (this is the cleanest, most common case).

### 2. Zero access configured (`no_access_configured`)

- **Symptom:** Both `birthright` and `entitlements` are empty arrays —
  user has no portal access at all.
- **Root cause:** Either the user was never synced, or the account is
  brand new and Sync-1 hasn't run yet.
- **Agent 4 classification:** `SIMPLE_FIX` if `user_found_in_auth0:
  true` and account status supports it — add the *entire* expected
  birthright set as entitlements. Check `sync_never_ran` first; if
  true, consider triggering a re-sync instead of manual entitlement
  addition.

### 3. User not found in Auth0

- **Symptom:** Agent 3 returns `user_found: false` for a known/expected
  email.
- **Root cause:** Provisioning gap — user exists in Salesforce/DynamoDB
  but was never created in Auth0.
- **Agent 4 classification:** `ESCALATE_TO_L2` — this is not an
  entitlement fix, it's a missing-account problem. Recommended action:
  follow the "User Creation in Auth0" SOP (see cross-reference in
  `sfdc-to-auth0-field-mapping.md`).

### 4. Birthright correct, but access still denied

- **Symptom:** All expected keywords are present in `birthright`/
  `entitlements` (Agent 4's `match: true`), yet the user still reports
  `ACCESS_DENIED`.
- **Root cause:** Likely a Gatekeeper Action bug or Auth0 configuration
  issue — the data says access should work, but the enforcement layer
  disagrees.
- **Agent 4 classification:** `ESCALATE_TO_L2` (flagged as
  `birthright_correct_but_access_denied: true`) — this is an
  engineering/config issue, not a support-fixable entitlement gap.

### 5. Explicit block keyword present

- **Symptom:** User has the right birthright keyword but is still
  denied; `entitlements` contains a `block_<Keyword>` entry.
- **Root cause:** Someone manually blocked this user's access to a
  specific portal — could be intentional (policy enforcement) or a
  stale/forgotten block.
- **Agent 4 classification:** `ESCALATE_TO_L2` (always) — never
  auto-remove a block keyword; requires human judgment on whether the
  block is still valid.

### 6. Migration-related access confusion (Nov 1 CIAM migration)

- **Symptom:** Ticket mentions the migration explicitly, or timing
  correlates (user worked fine before Nov 1, broke after).
- **Root cause:** See `migration-known-issues.md` for specific known
  gaps.
- **Agent 4 classification:** Varies — depends on the specific gap, but
  KB retrieval should surface `migration-known-issues.md` automatically
  (already proven working: a test ticket mentioning "Nov 1 migration"
  correctly surfaced that document at a 0.35 relevance score even
  before real content was added).

### 7. Correct account, wrong tenant / community-portal-specific access issues

- **Symptom:** User confirms correct birthright in Auth0 (per manual
  check) but portal-specific access still fails — most commonly
  reported for the Community portal specifically.
- **Root cause:** Unclear without further data — possibly tenant
  routing, possibly a portal-specific Gatekeeper quirk. This pattern
  showed up in real (sanitized) ticket testing this session where the
  account existed in Auth0 with correct birthright but was not found in
  the CIAM DynamoDB table — i.e., a **cross-system** inconsistency
  (Auth0 says one thing, DynamoDB says another) rather than a single-
  system gap.
- **Agent 4 classification:** `ESCALATE_TO_L2` — cross-system data
  inconsistencies are not currently auto-resolvable by this agent.

## Open Questions to Resolve

1. What is the *actual* frequency ranking of these issues in real
   ticket volume? (This draft has no frequency data — just a list of
   patterns observed in testing.)
2. Are there common issue patterns not covered above (e.g. MFA
   enrollment failures, SSO/federation-specific issues)?
