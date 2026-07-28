# Portal Access Requirements

> **DRAFT — needs verification against the real Gatekeeper Action logic
> (spec §4.1 Tool 1, OQ-9).** This draft is the inverse view of
> `birthright-entitlement-matrix.md` — that doc answers "what should
> this persona have," this answers "what does this specific portal
> actually check for." The two should agree; any mismatch found during
> review is itself a finding worth raising.

## Purpose

Documents, per portal, the exact keyword(s) — and any additional RBAC
role — required for access. Directly validates the
`KNOWN_PORTAL_KEYWORDS` constant hardcoded in `agent.py`.

## Portal → Required Access Table

| Portal | Required `birthright`/`entitlements` keyword | Additional RBAC role required? | Notes |
| :--- | :--- | :--- | :--- |
| Support | `Support` | Unconfirmed | Netskope Support Portal |
| Community | `Community` | Unconfirmed | Cloud Security & Cybersecurity Forum |
| Academy | `Academy` | Unconfirmed | Training/learning portal |
| Partner | `Partner` | Unconfirmed | Partner-facing portal — distinct from the `Netskope-Partners` Auth0 *connection* (Agent 3), which is a legacy identity source, not a portal permission |
| Notification | `Notification` | Unconfirmed | Notification Center |
| Dashboard | `Dashboard` | Unconfirmed | — |
| Prime | Unconfirmed — not in Agent 4's current `KNOWN_PORTAL_KEYWORDS` (spec OQ-9) | Unconfirmed | Prime Okta Tenant / Prime Partner Okta context — distinct from the generic `Partner` portal per Agent 1's spec explicit note (§6.2) |

## Gatekeeper Union Logic (Confirmed From Code)

The Gatekeeper Action grants access if the required keyword is present
in **either** the `birthright` array or the `entitlements` array (OR
logic, not AND) — Agent 4's Tool 1 mirrors this with
`effective_access = birthright ∪ entitlements`.

## Block Keyword Override (Confirmed From Code)

A keyword like `block_Support` in `entitlements` overrides any grant
from `birthright`, even if `Support` is present there — the user is
treated as blocked from that portal. This is a manual, security-
sensitive override; Agent 4 always escalates when detected rather than
attempting auto-remediation.

## Open Questions to Resolve

1. Does any portal require **more than one** keyword (AND logic), or a
   specific RBAC role in addition to the birthright/entitlements
   keyword? (All "Additional RBAC role required?" cells above are
   currently unconfirmed guesses.)
2. Is the 6-portal + Prime list (7 total) exhaustive, or are there
   other portals not yet surfaced anywhere in this project's specs?
3. Confirm the exact distinction between `Partner` (portal keyword) and
   `Netskope-Partners` (Auth0 connection name) doesn't confuse anyone
   reading tickets — these are unrelated concepts that happen to share
   a word.
