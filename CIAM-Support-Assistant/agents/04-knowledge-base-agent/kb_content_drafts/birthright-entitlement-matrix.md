# Birthright Entitlement Matrix

> **DRAFT — needs review against the real Birthright & Entitlements
> Guide or sync function source code (spec OQ-6/OQ-7) before this
> replaces the placeholder in production.** This draft is built from
> `derive_persona()` in `agent.py` plus everything observed this session
> (Agent 1's 7 recognized portals, Agent 2's account schema, Agent 3's
> Auth0 birthright/entitlements fields). Treat every row as a hypothesis
> to confirm, not a fact.

## Purpose

This is the source of truth Agent 4's Tool 1 (`evaluate_birthright`)
uses to compute what a user **should** have, before comparing it to
what they **actually** have. Every row below maps directly to a branch
in `derive_persona()`.

## Persona → Expected Birthright Table

| `account_status` (from Agent 2) | `active_tenant_count` | Persona | Expected `birthright` keywords |
| :--- | :---: | :--- | :--- |
| `Customer` | any | Customer | `Support`, `Community`, `Academy`, `Notification`, `Dashboard` |
| `Prospect - Net New` | `>= 1` | Prospect with Tenant | `Support`, `Community`, `Academy`, `Notification`, `Dashboard` |
| `Prospect - Net New` | `0` | Prospect without Tenant | `Community`, `Academy`, `Dashboard` |
| `Partner` | any | Partner | `Partner`, `Community`, `Academy`, `Dashboard` |
| `Former Customer` | any | Former Customer | `Community`, `Academy`, `Dashboard` |
| anything else / `null` | any | UNKNOWN | *(none — escalate to L2)* |

**Known gap (spec OQ-9):** Agent 1 also recognizes a `Prime` portal
(Prime Okta Tenant / Prime Partner Okta), but no persona in this table
currently expects it. If a persona for Prime-tenant users exists, add
it here.

## Known Portal Keywords (Vocabulary)

`Support`, `Community`, `Academy`, `Notification`, `Dashboard`,
`Partner` — six confirmed values (per Agent 1's routing + Agent 4's
`KNOWN_PORTAL_KEYWORDS`). `Prime` is a known 7th portal not yet wired
into this matrix (see above).

## How This Interacts With `entitlements`

A user's **actual access** is the union of their `birthright` array
(auto-computed by NetskopeID-Sync) and their `entitlements` array
(manually-added overrides). If a user is missing a birthright keyword
but has it in `entitlements` instead, Agent 4 treats this as
`entitlements_compensate: true` and does **not** flag a gap — this is
by design, since `entitlements` is the legitimate manual-override
channel.

## Block Keywords

A string like `block_Support` in `entitlements` overrides any grant —
the user is treated as **not** having that portal regardless of what
`birthright` says. This always forces `ESCALATE_TO_L2` (security-
sensitive, requires human review of who added the block and why).

## Open Questions to Resolve With the Real Guide

1. Is the persona list above exhaustive, or are there more account
   statuses in real Salesforce data (e.g. regional variants, OEM
   partners, trial-to-paid transitions)?
2. Does `active_tenant_count` matter for personas other than Prospect?
3. Should `Prime` be added, and to which persona(s)?
4. Are there additional portal keywords beyond the 6-7 identified here?
