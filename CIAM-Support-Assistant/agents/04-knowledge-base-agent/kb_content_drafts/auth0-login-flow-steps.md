# Auth0 Login Flow Steps

> **DRAFT — needs verification against the real Auth0 Action/Rule/Flow
> scripts for the `nskp` tenant (spec OQ-8).** This draft reconstructs
> the flow from what was described earlier in this project and from
> Agent 3's Auth0Payload schema (`birthright`, `entitlements`,
> `last_sync`, `last_daily_sync` fields). Step names, order, and field
> mappings below are **unverified** until the real scripts are supplied.

## Purpose

Documents the ordered pipeline a user's login/provisioning request
passes through in Auth0, so a failure can be traced to a specific step
rather than left as a generic "access denied." This is the reference
Tool 4 (`identify_failing_workflow`, currently a placeholder — see spec
OQ-8) will eventually be implemented against.

## The Pipeline (Draft Order)

| # | Step | What It Checks | Failure Category (if broken) |
| :---: | :--- | :--- | :--- |
| 1 | Email Verification | `email_verified` flag | `ACCESS_DENIED` |
| 2 | Registration Forms | Required profile fields completed | `ACCOUNT_LOCKOUT` |
| 3 | Migration Acknowledgement | User has acknowledged the Nov 1 CIAM migration notice | `ACCOUNT_LOCKOUT` |
| 4 | Privacy Policy Acceptance | `privacy_policy_accepted_at` is non-null | `ACCOUNT_LOCKOUT` |
| 5 | NetskopeID-Sync-1 (Salesforce → Auth0) | Populates `app_metadata.birthright` and `app_metadata.entitlements` from Salesforce account data | `ENTITLEMENT_MISSING` |
| 6 | NetskopeID-Sync-2 (DynamoDB → Auth0) | Populates `app_metadata.tenant_id`; resolves `pending_community_user` | `SYNC_STALE` |
| 7 | RBAC Consolidated | Assigns `app_metadata.roles` based on birthright + entitlements | `BIRTHRIGHT_MISMATCH` |
| 8 | Gatekeeper | Final portal-access decision — checks `birthright` ∪ `entitlements` against the requested portal's required keyword (see `portal-access-requirements.md`) | `SSO_FAILURE` |
| 9 | MFA Consolidated | Enforces MFA enrollment if required for the persona | `ACCOUNT_LOCKOUT` |

## Fields Referenced (Cross-check Against Agent 3's Schema)

| Field | Populated By Step | Agent 3's `Auth0UserRecord` equivalent |
| :--- | :--- | :--- |
| `app_metadata.birthright` | Step 5 (Sync-1) | `birthright` |
| `app_metadata.entitlements` | Step 5 (Sync-1) | `entitlements` |
| `app_metadata.last_sync` | Step 5 (Sync-1) | `last_sync` |
| `app_metadata.last_daily_sync` | Step 6 (Sync-2) | `last_daily_sync` |

## Diagnostic Signals Already Computed by Agent 3

- `sync_stale` (true if `last_sync` > 7 days ago, or never ran) — points
  at Step 5/6 as the likely broken step.
- `sync_never_ran` — same, but stronger signal (user's account may be
  brand new or Sync-1 never fired at all).
- `failed_logins_last_7_days` + `last_failed_login_reason` — the actual
  Auth0 log description often names which step failed (e.g. "Access
  Denied: missing 'Support' in birthright" implicates Step 8, Gatekeeper).

## Open Questions to Resolve With the Real Scripts

1. Is this 9-step order and naming accurate, or does the real Auth0
   tenant have a different/additional set of Actions?
2. Are the failure-category mappings (right column) correct, or does a
   single step actually map to multiple intents depending on context?
3. What does the real `pending_community_user` flag actually gate, and
   which step sets/clears it?
