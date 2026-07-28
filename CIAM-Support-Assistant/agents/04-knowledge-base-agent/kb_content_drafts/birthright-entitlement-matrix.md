# Birthright Entitlement Matrix

> **Sourced from the real Birthright & Entitlements Guide** (Netskope
> Confluence, ISI space, exported 2026-07-28). This replaces the earlier
> fully-guessed draft. `derive_persona()` in `agent.py` has been updated
> to match this table exactly. A few rows (Customer Partner / MSP
> Partner / Service Provider-Telco Partner / Prime-partner detection)
> are not yet fully wired into code — see "Known Gaps" below.

## Purpose

This is the source of truth Agent 4's Tool 1 (`evaluate_birthright`)
uses to compute what a user **should** have, before comparing it to
what they **actually** have.

## Keyword Index

User access is determined by two arrays in the user's Auth0
`app_metadata`: **birthright** (auto-set by NetskopeID-Sync — do not
modify manually, overwritten hourly) and **entitlements** (manually
assigned by Auth0 Admins with "Edit - Users" access; also used to
*block* access).

| Keyword | Resource |
| :--- | :--- |
| `Support` | Netskope Support Portal |
| `Academy` | Netskope Academy |
| `Community` | Netskope Community |
| `Notification` | Netskope Notification Portal |
| `Partner` | Netskope Partner Portal |
| `Prime` | Netskope Prime Okta Tenant |
| `Dashboard` | Netskope Identity Dashboard |
| `C-Academy` | Netskope Client Academy — **sunset 2025-11-17** |
| `P-Academy` | Netskope Partner Academy — **sunset 2025-11-17** |

## Block Keywords

Block keywords go in the **entitlements** array and override access
**even if the birthright array grants it**. Format is a hyphenated
abbreviation, e.g. `Block-Supp` — **not** `block_Support`.

| Blocking Keyword | Resource |
| :--- | :--- |
| `Block-Supp` | Support Portal |
| `Block-Acad` | Academy |
| `Block-Comm` | Community |
| `Block-Notif` | Notification Portal |
| `Block-Partner` | Partner Portal |
| `Block-Prime` | Prime Okta Tenant |
| `Block-Dash` | Identity Dashboard |
| `Block-CAcad` | Client Academy — not released, but still assignable |
| `Block-PAcad` | Partner Academy — not released, but still assignable |

## Persona → Expected Birthright Table

Birthright access is determined at signup/migration from the user's
Salesforce **Account_Status__c** field (plus a few other fields for the
more specific Partner sub-personas).

| Persona | `Account_Status__c` | Other Values | Birthright Access |
| :--- | :--- | :--- | :--- |
| Individual | No Account Found | N/A | `Community`, `Dashboard` |
| Prospect | Includes "Prospect" | N/A | `Community`, `Academy`, `Dashboard` |
| Prospect (w/ Tenant) | Includes "Prospect" | Active Tenant ≥ 1 | `Community`, `Academy`, `Support`, `Notification`, `Dashboard` |
| QOB | Includes "Quarantine" OR "Out of Business" | N/A | `Community`, `Dashboard` |
| Customer | Equals "Customer" | N/A | `Community`, `Academy`, `Support`, `Notification`, `Dashboard` |
| Pending Partner | Equals "Pending Partner" | N/A | `Community`, `Academy`, `Dashboard` |
| Pending Partner (w/ Tenant) | Equals "Pending Partner" | Active Tenant ≥ 1 | `Community`, `Academy`, `Support`, `Notification`, `Dashboard` |
| Partner | Equals "Partner" | N/A | `Support`, `Community`, `Academy`, `Partner`, `Notification`, `Dashboard`, (`Prime`)\* |
| Customer Partner | Equals "Partner" | Customer Status includes "Customer" AND "Partner" | same as Partner, (`Prime`)\* |
| MSP Partner | Equals "Partner" | Primary/Secondary/Tertiary Partner Type = "MSP" | same as Partner, (`Prime`)\* |
| Service Provider/Telco Partner | Equals "Partner" | Partner Type = "Service Provider/Telco" | same as Partner, (`Prime`)\* |
| Churn (w/ Tenant) | Equals "Churn" | Active Tenant ≥ 1 | `Community`, `Academy`, `Support`, `Notification`, `Dashboard` |
| Churn | Equals "Churn" | N/A | `Community`, `Dashboard` |

\* `Prime` only added for Prime partners specifically.

## Known Gaps (Not Yet Wired Into Code)

1. **Customer Partner / MSP Partner / Service Provider-Telco Partner**
   distinction: all four Partner-type personas above grant the **same**
   keyword set, so `derive_persona()` currently collapses them all to a
   single "Partner" branch — this is NOT a correctness gap for the
   birthright *output*, only a persona-*label* granularity gap. Wiring
   in the real `customer_status` and `partner_type` fields (not
   currently in Agent 2's `AccountPayload` schema) would only improve
   labeling precision, not the actual expected-keyword computation.
2. **`(Prime)` keyword for Prime partners**: the source table flags
   that Prime partners additionally get the `Prime` keyword, but how a
   "Prime partner" is identified (which field/value) is not yet
   confirmed — needs the CIAM platform team to clarify the exact
   detection field before this can be added to `derive_persona()`.
