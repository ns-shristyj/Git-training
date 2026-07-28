# Auth0 `app_metadata` Fields & Common SOPs

> **Sourced from the real Confluence export** (Netskope ISI space,
> 2026-07-28) — specifically the "Assigning Organization Admin", "Force
> Password Reset", "Block & Unblock Users", "Helping a User That
> Declined Migration Acknowledgment", and "Force A NetskopeID Sync -
> Update Birthright & Community Provisioning" pages. This replaces the
> earlier hypothetical "9-step login flow" draft, which was not derived
> from a real source — that draft's step numbering/names are NOT
> confirmed anywhere in the real docs and should be discarded rather
> than reconciled.

## Confirmed Real `app_metadata` Fields

| Field | Type | Purpose |
| :--- | :--- | :--- |
| `birthright` | array of strings | Auto-set by NetskopeID-Sync hourly. Do not modify manually — see `birthright-entitlement-matrix.md`. |
| `entitlements` | array of strings | Manually assigned overrides + block keywords. |
| `permissions` | array of strings | e.g. `["o-admin"]` for Organization Admin (Identity Dashboard). Manually assigned. |
| `send_id` / `sendId` | boolean | Controls whether the user's Auth0 `user_id` gets pushed to IMPartner on Partner Portal login (new/old schema names for the same flag). |
| `last_sync` | epoch timestamp | Last NetskopeID-Sync run. Clearing to `""` forces a resync on next login. |
| `last_daily_sync` | epoch timestamp | Last daily sync run. Same clear-to-force-resync behavior. |
| `pending_community_user` | boolean | `true` blocks Community access even if `Community` keyword is present — see common issue #4 in `ciam-l1-common-issues.md`. |
| `pending_support_user` | boolean | Analogous flag observed for Support provisioning (seen in real `app_metadata` example; exact gating behavior not yet documented as thoroughly as `pending_community_user`). |
| `privacy_policy` | boolean | Privacy policy acceptance status. |
| `nskp-prime` (under `permissions` or similar) | — | Seen in one real example tied to a `federated: true` user — exact semantics not fully confirmed, likely related to Prime tenant assignment. |

## Confirmed Real SOPs (Not Hypothetical)

### Assigning Organization Admin (`o-admin`)

Two distinct paths depending on user type:

- **Partner users** (connection ≠ `Netskope-Partners`... actually the
  reverse — see note below): via the **ImPartner Admin Console**
  (`https://prod.impartner.live/`) → Users → find user → Edit →
  Delegated Administration Privileges → enable **Member
  Administrator** → Update. Takes effect on the user's next successful
  login to Partner Portal or the Identity Dashboard.
- **Non-Partner users**: directly in Auth0 → User Management → Users →
  find user (must NOT be on the `Netskope-Partners` connection) → edit
  `app_metadata.permissions` array to include `"o-admin"` → Save.

> Note: step 5 of the real SOP says "make sure the user is not within
> the Netskope-Partners connection; any other connection is fine" for
> **both** paths' user-lookup step — the Partner-specific path is
> selected based on whether the user is found in ImPartner at all, not
> strictly by Auth0 connection name. Worth clarifying with the CIAM
> platform team if this seems ambiguous in practice.

### Force Password Reset

Auth0 → User Management → Users → find user (must be on **NetskopeID**
connection) → `•••` → **Change Password** → set a new password
(1Password generator recommended) → tell the user to use "Forgot
Password" on next login to claim it themselves.

### Block & Unblock Users

Auth0 → User Management → Users → find user (must be on **NetskopeID**
connection) → **Actions** → **Block** or **Unblock**.

> **Blocking affects ALL Auth0-authenticated apps for that user** —
> Partner Portal, Partner Academy, Netskope Prime Okta Tenant, **and**
> the partner login path for Netskope Community. This is broader than
> just one portal — treat as a full-account lockout, not a
> single-resource block.

### Helping a User That Declined Migration Acknowledgment

If a user accidentally declines the Migration Acknowledgement form,
they get blocked. Fix: Auth0 → find user (**NetskopeID** connection) →
Actions → **Unblock**. They'll then see the acknowledgement form again
on next login attempt.

> **Time-sensitive:** if the user doesn't log in within **90 days**
> AND still hasn't accepted the migration acknowledgement, their
> account is **deleted**. Don't let this SOP sit unresolved.

### Force A NetskopeID Sync (Birthright & Community Provisioning Refresh)

Also pulls fresh Salesforce Contact/Account assignment data, not just
birthright. Auth0 → find user (**NetskopeID** connection) →
`app_metadata` → clear both `last_sync` and `last_daily_sync` to an
empty string `""` → Save. **Changes are visible after the user's next
login** — this doesn't take effect immediately/server-side, the user
must actually log in again to trigger the refresh.

## Open Questions

1. Real end-to-end login pipeline step names/order (the earlier "9-step
   flow" draft was never confirmed against a real source — needs an
   actual Auth0 Action/Rule/Flow script export, or a platform-team
   walkthrough, not just SOP pages like these).
2. Exact semantics of `pending_support_user` and the `nskp-prime` value
   seen under one federated user's `app_metadata` — neither is
   documented as thoroughly in the source as `pending_community_user`.
3. Minor date inconsistency in the source itself: the Birthright Guide
   states C-Academy/P-Academy sunset as `11/17/2025`, while the Assign
   & Revoke Entitlement page states `09/25` for the same two legacy
   keywords. Likely the same event described with different precision,
   but worth a one-line confirmation with whoever owns the doc.
