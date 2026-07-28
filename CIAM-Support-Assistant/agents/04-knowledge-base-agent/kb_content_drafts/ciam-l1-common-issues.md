# CIAM L1 Support — Common Issues & Fixes

> **Sourced from the real "[CIAM L1 Support] Common Issues & Fixes"**
> Confluence page (Netskope ISI space, exported 2026-07-28). Replaces
> the earlier fully-hypothetical draft. Employee names appearing in the
> original doc's screenshots have been genericized here; real TQI
> ticket references are kept since they're already tracked in Jira and
> don't contain new PII beyond what's in the ticket system itself.

## Purpose

Real, confirmed recurring issues for the Netskope Unified
Login/NetskopeID service, with root cause and fix for each — this is
the actual basis for Agent 4's `similar_past_tickets` / common-pattern
matching, not a hypothetical list.

---

### 1. Internal/Federated user failing Gatekeeper action

**Symptom:** A federated (internal) user gets an error/access denied
logging into partner resources via the Okta federated connection.
Gatekeeper's failed-action log shows: `"Cannot read properties of
undefined (reading 'includes')"`.

**Root cause:** Only affects new internal users assigned to the
`prod-cust-nsid-partnerportal-prime-user-grn` Okta group. The
`set_federated_user_metadata` function inside NetskopeID-Sync-1 has a
missing line that's supposed to add the `entitlements` array — so
Gatekeeper's `entitlements.includes()` check fails because
`entitlements` doesn't exist at all on the user's `app_metadata`. A
TCR (ticket/change request) has been filed for this.

**Fix:** Add an empty `entitlements` array to the affected user's
`app_metadata` (Auth0 → User Management → Users → target user →
`app_metadata`), e.g. `"entitlements": []`.

---

### 2. User's `app_metadata.roles` field is not an array

**Symptom:** Failed action log shows `NetskopeID-Sync-2` and
`"...roles?.includes is not a function"`.

**Root cause:** Something is overwriting the `roles` field with an
**object** (a copy of the user's entire `app_metadata`) instead of
leaving it as an array. Root cause of *why* this happens is still
**under investigation** as of this export.

**Fix:** Reset `roles` to an empty array (`"roles": []`) in the user's
`app_metadata` — values repopulate automatically on next sync. If it
recurs, escalate via the CIAM Ticket Escalation Process.

---

### 3. Partner missing Auth0 ID within IMPartner (or stale Auth0 ID)

**Symptom:** Channel Operations (Netskope Partners team) reports a
Partner Portal user has no Auth0 ID value in IMPartner after first
login, or the Auth0 ID value there doesn't match the user's real Auth0
`user_id`. **Does not block the user from logging in.**

**Root cause:** `NetskopeID-Sync-2`'s `update_auth0id_within_impartner()`
function only sends the Auth0 `user_id` to IMPartner during Partner
Portal login **if** the `send_id` (new schema) or `sendId` (old schema)
boolean is `true` in the user's `app_metadata`. If that field is
missing entirely, the function silently returns early and never sends
the ID.

**Fix:** Add `"send_id": true` to the user's `app_metadata`. The ID
gets sent/updated on the user's next Partner Portal login. If it still
doesn't update, escalate via CIAM Ticket Escalation Process.

---

### 4. User's Community access denied despite having "Community" in birthright/entitlements

**Symptom:** User sees "Access Denied: Netskope Community" even though
their `app_metadata` already contains the `Community` keyword. They
also have a `pending_community_user: true` key set.

**Root cause:** Strict input validation on the Community sign-up form
sometimes silently replaces an invalid field value with a blank string
instead of rejecting the submission outright. That missing field then
blocks full Community account creation — so even though the keyword is
present, the underlying Community account was never actually finished
provisioning.

**Fix:** Requires **NetskopeID DynamoDB access** (not just Auth0).
Find the affected user in the `nskp` Auth0 tenant, copy their profile
URL, and escalate via the CIAM Ticket Escalation Process — this is not
an Auth0-Admin-resolvable issue alone.

---

### 5. Profile / Username / Email mismatch between Salesforce and Auth0

**Symptom:** A user logging into any CIAM-enabled app (Support,
Academy, Community, Partner Portal, SkillJar) either sees a display
name/profile mismatch vs. Salesforce, or Support login fails outright
("Invalid Email/Password", migration loop).

**Root cause:** Salesforce is the **canonical source of truth**, but
Auth0's `user_metadata` (`email`, `given_name`, `family_name`, `name`)
is populated from Salesforce at creation time and does **not**
auto-refresh if Salesforce is updated later. Additionally, some legacy
Support login flows query Salesforce **by Username**, and in some
older/legacy cases the Salesforce `Username` field isn't the user's
real login email at all — causing lookup failures even with correct
credentials.

**Fix:**
1. Confirm Salesforce is correct first (fix there if wrong — it's the
   canonical source).
2. Check the user's actual Auth0 `given_name`/`family_name` for
   mismatches.
3. Update Auth0 `user_metadata` to mirror Salesforce exactly, then run
   a **forced identity refresh** (see the "Force A NetskopeID Sync"
   procedure).
4. Have the user **log in twice**: first login+logout persists the
   refreshed values; the second login propagates them to downstream
   apps (e.g. SkillJar) so display name/profile details actually
   update.

A documented edge-case workaround exists for Support users with a
username mismatch specifically ("Project Starling: Phase 2") — check
that first if this is a Support-specific case.

---

### 6. SSO error screen when logging into the Support portal

**Symptom:** User has birthright access to Support, authenticates
successfully in Auth0, but is redirected to a generic "Single Sign-On
Error" page instead of reaching the Support portal. **Auth0 itself
shows this as a successful login** — the failure happens downstream,
in the Salesforce/Support-portal redirect, which makes it easy to
mis-diagnose as an Auth0 problem.

**Root cause — two most common:**
1. The user's Netskope Support account (Salesforce User object)
   doesn't exist yet — there's no just-in-time (JIT) provisioning for
   Support/Salesforce, so having the `Support` birthright keyword alone
   doesn't guarantee an account exists at login time.
2. The user's Salesforce User object was **deactivated**, but Auth0
   has no visibility into that — so Auth0 still lets the (now invalid)
   login proceed, and the failure surfaces only at the Salesforce
   redirect step.

**Fix (requires Salesforce access):**
1. Confirm the user exists in Salesforce (search by email, check for
   matching Contact with a "Customer Community User" value).
2. If exactly one match → check whether that Contact's Community/User
   status is Active.
3. If the user **is** active but still sees the error → escalate via
   CIAM Ticket Escalation Process (deeper investigation needed).
4. If the user is **not** active → tell the reporter the account is
   disabled in Salesforce, ask them to raise a Salesforce-side ticket.
5. If there are multiple matching Contacts, or none at all → escalate;
   don't guess which account is authoritative.

---

### 7. Partner Portal user created but missing within Auth0

**Symptom:** Channel Operations reports a new user exists in Partner
Portal (IMPartner) and Salesforce (as a Contact), but can't be found in
Auth0's User Management.

**Root cause — two possibilities:**
1. **Indexing delay** — the user is created in the DynamoDB database
   first, then indexed into Auth0 afterward; under load this can take
   a noticeable amount of time before showing up in the Auth0 Users UI.
2. IMPartner's "Create User in Auth0" workflow failed or errored out
   (rare).

**Fix:**
1. Check Auth0 logs (Monitoring → Logs) for a signup event matching
   `"ImPartner User Management" AND "<user's email>"`.
2. If found → the user **was** successfully created in DynamoDB even
   if not yet visible in the Auth0 UI. Have them do a password reset
   via the Partner Portal login page (they'll receive a reset email
   from `id@netskope.com` and can set credentials immediately — no need
   to wait for Auth0 UI visibility).
3. If no signup event is found, or the signup event itself failed →
   escalate via CIAM Ticket Escalation Process.

---

### 8. Given Name / Family Name / Full Name correction

**Symptom:** A user's name is wrong in the system (pulled incorrectly
from Salesforce Contact or a pre-existing legacy Netskope-Partners
account during migration/registration).

**Root cause:** Values pulled from Salesforce or old legacy user
accounts at migration time were themselves already incorrect and
haven't been corrected since.

**Fix — two options:**
1. **Self-service**: have the user log into the Netskope Identity
   Dashboard and update their own name (a friendly external guide for
   this exists and can be shared directly with users).
2. **Admin correction**: an Auth0 Admin manually edits the user's
   `user_metadata` (`given_name`, `family_name`, `name`) directly, then
   saves.

---

## Escalation Path (All Issues)

Most fixes above that require Salesforce or DynamoDB access, or that
don't resolve after the documented fix, should be escalated via the
**CIAM Ticket Escalation Process** (Jira project `TQI`, auto-created via
Jira Service Management from monitoring alerts or user-reported
issues — see the CIAM Support Overview doc for the full P1–P4 SLA
table and escalation flow).
