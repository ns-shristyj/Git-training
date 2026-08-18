# Resolved Ticket Patterns

> **Sourced from real CIAM L1 Common Issues & Release Notes** (Netskope
> Confluence, ISI space, exported 2026-07-28). Documents 8 confirmed
> L1-resolvable issue patterns (from `ciam-l1-common-issues.md`) and 6
> historical platform bugs (from `migration-known-issues.md`), all with
> real root causes and fixes. This replaces the earlier template-only
> version.

## Purpose

This is the basis for Agent 4's `similar_past_tickets` / pattern-matching
output — when a ticket's symptom matches an entry here, Agent 4 can
confidently recommend the documented fix without escalation.

## Real L1-Resolvable Patterns (8 Total)

### Pattern 1: Federated User Gatekeeper Failure
**Symptom:** Federated internal user gets "Cannot read properties of
undefined (reading 'includes')" in Gatekeeper logs.
**Root cause:** `set_federated_user_metadata` missing the `entitlements`
array initialization — Gatekeeper's `entitlements.includes()` check fails.
**Fix:** Manually add `"entitlements": []` to user's Auth0 `app_metadata`.

### Pattern 2: App_Metadata Roles Field Corrupted
**Symptom:** Failed action log shows `NetskopeID-Sync-2` and
`"...roles?.includes is not a function"`.
**Root cause:** Unknown actor overwrites `roles` field with an object
(entire `app_metadata`) instead of an array; **investigation ongoing**.
**Fix:** Reset `roles` to `[]` in `app_metadata` — values repopulate on
next sync. If recurs, escalate to L2.

### Pattern 3: Partner Auth0 ID Missing in IMPartner
**Symptom:** Channel Operations reports Partner Portal user missing Auth0
ID in IMPartner, or ID doesn't match user's real Auth0 `user_id`.
**Root cause:** `send_id` / `sendId` flag missing or false in user's
`app_metadata` — IMPartner sync function silently skips ID send.
**Fix:** Add `"send_id": true` to `app_metadata`; ID syncs on next
Partner Portal login.

### Pattern 4: Community Access Denied Despite Keyword
**Symptom:** User sees "Access Denied: Netskope Community" even though
`Community` keyword is present in `app_metadata`.
**Root cause:** `pending_community_user: true` flag is set — blocks access
regardless of birthright/entitlements keyword presence. Root cause of why
flag is set: Community sign-up form validation error (rare).
**Fix:** Requires NetskopeID DynamoDB access — escalate via CIAM Ticket
Escalation Process (TQI project). Cannot be fixed via Auth0 Admin alone.

### Pattern 5: Profile/Username/Email Mismatch (Support Login)
**Symptom:** User can't log into Support ("Invalid Email/Password", migration
loop) OR sees display-name mismatch in other portals.
**Root cause:** Salesforce is authoritative source; Auth0 `user_metadata`
populated at creation time and does NOT auto-refresh. Legacy Support flows
query by Username field, which may not be the real email. (~178 users
affected — see Project Starling Phase 2 workaround).
**Fix:** (1) Confirm Salesforce is correct first. (2) Update Auth0
`user_metadata` to match. (3) Force NetskopeID sync (clear `last_sync` /
`last_daily_sync` to `""`). (4) User must log in twice (first login persists
values, second propagates to downstream apps like SkillJar).
**Edge case:** For Support-specific username mismatch, the custom
NetskopeID Login script workaround (Project Starling Phase 2) accepts
username as login identifier and handles Salesforce SAML attribute mapping —
check this first if ~178-user population matches.

### Pattern 6: SSO Error Screen at Support Portal
**Symptom:** Auth0 login succeeds, but user redirected to generic "Single
Sign-On Error" instead of Support portal.
**Root cause — two most common:**
- Salesforce User object does NOT exist for the user (no JIT provisioning
  for Support).
- Salesforce User object IS deactivated (Auth0 doesn't know; assumes login
  is valid, redirect fails).
**Fix:** (Requires Salesforce access) (1) Search Salesforce by email for
matching Contact. (2) Check if Contact's Community/User status is Active.
(3a) If active but error persists → escalate (L2 investigation). (3b) If
NOT active → tell reporter account is disabled in Salesforce; ask them to
raise Salesforce ticket. (3c) If no match or multiple → escalate (ambiguous).

### Pattern 7: Partner Portal User Created But Missing in Auth0 UI
**Symptom:** Channel Operations confirms user exists in IMPartner and
Salesforce, but Auth0 User Management can't find them.
**Root cause — two possibilities:**
- Indexing delay (user created in DynamoDB first, indexed to Auth0 later).
- IMPartner "Create User in Auth0" workflow failed (rare).
**Fix:** (1) Check Auth0 logs for signup event matching user's email AND
"ImPartner User Management". (2a) If found → user exists in DynamoDB
already; have them do password reset via Partner Portal (no wait needed).
(2b) If not found → escalate (workflow failure).

### Pattern 8: Name Field Corrections
**Symptom:** User's given/family/full name is wrong (pulled from Salesforce
Contact or legacy account at migration time).
**Root cause:** Source data was already incorrect; hasn't been corrected
since.
**Fix — two options:**
- Self-service: user logs into Identity Dashboard and updates their own name
  (external guide available).
- Admin: Auth0 Admin manually edits user's `user_metadata` (`given_name`,
  `family_name`, `name`).

## Historical Platform Bugs (6 Already Fixed — Reference for Pattern Recognition)

| Bug | Symptom | Fix | Version |
| :--- | :--- | :--- | :--- |
| Stale Prime-level access retention | Demoted user kept Prime access (race condition) | Access recomputed as single decision per login | v2.0.0 |
| Access wiped on transient SFDC failure | Temporary Salesforce lookup error → access overwritten to empty | Access left untouched until lookup succeeds | v2.0.0 |
| Hourly sync over-triggering | Sync check referenced wrong field for native users | Fixed to reference correct field | v2.0.0 |
| Academy lookups wrong record | Federated users matched against wrong NetskopeID record | Fixed matching logic + removed duplicate assignment | v2.0.0 |
| Entitlement drift after Auth0 sync | Manual updates written only to Auth0, then overwritten by sync | Coordinated write to both systems | v2.5.0 (GIS-33767) |
| Name updates not reflected | Name change in Dashboard didn't propagate to Auth0 | Added database field to ensure consistency | v2.7.1 (GIS-3788) |

## Pattern Metadata Convention

Agent 4's `query_knowledge_base()` uses the prefix `"tqi-"` to detect
ticket-pattern documents. When real Jira TQI exports are ingested, confirm
this convention matches the actual naming scheme and update the
`is_ticket` detection logic in `agent.py` if needed.

## Open Questions

1. Confirm the exact metadata/naming convention for real TQI tickets once
   they are exported and uploaded to the Knowledge Base.
2. Are there additional L1-resolvable patterns not yet documented in
   `ciam-l1-common-issues.md` that should be added here?
3. For the 5 currently-open known issues in `migration-known-issues.md`,
   monitor for fixes in releases after v2.9.1 (the latest in this export)
   and update the "Historical" section once they are resolved.
