# Portal Access Requirements

> **Sourced from the real Birthright & Entitlements Guide** (Netskope
> Confluence, ISI space, exported 2026-07-28). This is the **inverse
> view** of `birthright-entitlement-matrix.md` — that doc answers "what
> should this persona have?", this answers "what does each portal
> actually check for?" and "which personas should see each portal in
> their nav bar?"

## Purpose

Documents, per portal, the access requirement — which keyword(s) in the
`birthright` or `entitlements` array grant access. Validates the
`KNOWN_PORTAL_KEYWORDS` constant in `agent.py` and supports Agent 4's
Tool 1 (`evaluate_birthright`) comparisons.

## Portal → Access Persona Matrix

**The inverse of the birthright table:** shows, for each portal, which
personas have it in their expected keyword set.

| Portal | Access Granted To Personas | Required Keyword |
| :--- | :--- | :--- |
| **Support** | Prospect (w/ Tenant), Customer, Pending Partner (w/ Tenant), Partner (all types), Churn (w/ Tenant) | `Support` |
| **Community** | All personas except Churn (without Tenant) and QOB; explicitly includes: Individual, Prospect, Prospect (w/ Tenant), Customer, Pending Partner, Pending Partner (w/ Tenant), Partner (all), Churn (w/ Tenant) | `Community` |
| **Academy** | Prospect, Prospect (w/ Tenant), Customer, Pending Partner, Pending Partner (w/ Tenant), Partner (all), Churn (w/ Tenant) — excludes Individual and QOB | `Academy` |
| **Notification** | Prospect (w/ Tenant), Customer, Pending Partner (w/ Tenant), Partner (all types), Churn (w/ Tenant) — same set as Support | `Notification` |
| **Partner** | Partner (all types only) — Customers, Prospects, and Pending Partners do **not** receive this keyword even with tenants | `Partner` |
| **Dashboard** | All personas except none — Dashboard access is **universal**: Individual, Prospect, QOB, Customer, Pending Partner, Partner (all), Churn (all). | `Dashboard` |
| **Prime** | Partner (types only) — specifically, only the subset of Partners marked as "Prime partners" (detection method not yet confirmed) | `Prime` |
| **C-Academy** | Same set as Academy, but sunset 2025-11-17 — Legacy keyword, still assignable but being phased out. | `C-Academy` |
| **P-Academy** | Same set as Academy, but sunset 2025-11-17 — Legacy keyword, still assignable but being phased out. | `P-Academy` |

## Access Control Logic (From Gatekeeper & Agent 4)

1. **Union grant:** Gatekeeper checks `(birthright ∪ entitlements)` — a
   keyword in **either** array grants access (OR logic).
2. **Block override:** A block keyword (e.g., `Block-Supp`) in
   `entitlements` **overrides any grant** from `birthright` — this is
   the security-sensitive manual override path.
3. **Birthright only:** Most access is via birthright (auto-set by
   NetskopeID-Sync hourly, derived from Salesforce Account_Status__c).
4. **Entitlements override/extend:** Manually assigned by Auth0 admins;
   used for ad-hoc access grants, block keywords, or corrections when
   birthright sync is stale.

## Known Gaps

1. **Prime partner detection:** The source table flags that Partners
   additionally get `Prime`, but the exact field used to identify a
   "Prime partner" is not yet confirmed (noted as OQ-11 in spec).
2. **Dashboard universality:** Dashboard appears to grant to all personas
   in the real table — this is broader than typical portal access (no
   restrictions), worth confirming is intentional and not a doc error.
3. **Legacy academy keywords:** C-Academy and P-Academy are being sunset
   2025-11-17; users assigned these keywords after that date will lose
   access. Confirm rundown plan.

## Open Questions

1. Is Dashboard access truly universal (all personas including Individual
   and QOB), or is the source table incomplete?
2. What is the exact field/logic for detecting "Prime partners" to assign
   the `Prime` keyword?
3. Are there any other portals not listed here (beyond the 9 documented)?
