# Salesforce → DynamoDB Field Mapping

> **Corrected title/scope.** There is no direct "Salesforce → Auth0"
> field sync — Salesforce data flows into the **NetskopeID DynamoDB
> table** (queried by Agent 2), and *separately*, NetskopeID-Sync
> pulls from Salesforce into Auth0 `app_metadata` for
> birthright/entitlements specifically (see
> `birthright-entitlement-matrix.md`). This document covers the
> DynamoDB side, using Agent 2's already-implemented real schema
> (`agents/02-database-agent/agent.py`) as the reference — not a guess.

## Purpose

Maps which Salesforce field feeds which DynamoDB field on the
NetskopeID table, so a suspected data-freshness or account-lookup issue
can be traced to the correct field.

## Real DynamoDB Schema (`AccountRecord`, from Agent 2's `agent.py`)

| DynamoDB field | Type | Notes |
| :--- | :--- | :--- |
| `user_id` | string | Primary key |
| `email` | string | Queried via `EmailIndex` GSI (case-insensitive lookup) |
| `account_name` | string | Salesforce Account name |
| `account_status` | string | Salesforce `Account_Status__c` — **see correction below** |
| `customer_status` | string | Salesforce customer status field |
| `active_tenant_count` | int | Number of active tenants for the account |
| `tenant_url` | string, optional | Per-account tenant identifier/URL |
| `sf_user_exists` | bool | Whether a matching Salesforce User object exists |
| `sf_user_active` | bool | Whether that Salesforce User object is active |

## ⚠️ Known Discrepancy — `account_status` Valid Values

Agent 2's code currently types `account_status` as:
```python
AccountStatusType = Literal["Customer", "Prospect - Net New", "Prospect - Churned", "Partner", "Former Customer"]
```

**Verified against the live `NetskopeID` DynamoDB table** (29-item
synthetic dataset, scanned directly): the actual stored `account_status`
values in use today are `Customer`, `Former Customer`, `Partner`, and
`Prospect - Net New` — matching Agent 2's current (provisional) type
exactly, since that's the vocabulary the synthetic dataset was built
against.

This is the **same provisional value set** Agent 4's persona table
originally had before being corrected against the real Birthright &
Entitlements Guide (see `birthright-entitlement-matrix.md`). The real
confirmed `Account_Status__c` values, per that same Confluence export,
are actually:

`Customer`, `Partner`, `Prospect - New New`, `Prospect - Existing`,
`Pending Partner`, `Churn`, `Quarantine`, `Out of Business`

**So there are now three, not two, mutually inconsistent vocabularies
for `account_status` in this project:**

1. Agent 2's `AccountStatusType` + the live synthetic DynamoDB dataset
   (`Prospect - Net New`, `Former Customer`, ...)
2. Agent 4's `derive_persona()` (now fixed to the real vocabulary:
   `Prospect` substring match, `Churn`, ...)
3. The real Salesforce `Account_Status__c` picklist (per the Birthright
   Guide, presumably the actual source of truth)

**This document does not modify Agent 2 or the DynamoDB table** —
flagging this purely as a cross-agent finding. Practical implication:
Agent 4 now expects real-vocabulary `account_status` values from Agent
2, but Agent 2's current synthetic test data still uses the old
vocabulary — so end-to-end orchestrator tests today will hit Agent 4's
`UNKNOWN` persona branch for every synthetic test account, since
`"Prospect - Net New"` no longer matches Agent 4's `"prospect"`
substring check... actually it does match (substring "prospect" is
present in "Prospect - Net New" case-insensitively), so `Prospect -
Net New` and `Customer` accounts still resolve correctly by
coincidence. **`Former Customer` does NOT match any of Agent 4's real
branches** and will resolve to `UNKNOWN` — worth knowing if an
end-to-end test using a `Former Customer` synthetic account produces
an unexpected escalation.

## `customer_status` Field

Real values seen in source screenshots: `Customer`, `Active`. Agent
2's own type (`CustomerStatusType = Literal["Active", "Churned",
"Inactive"]`) may also be worth reconciling against real Salesforce
picklist values, but — again — that's Agent 2's schema to fix, not
something changed here.

## Confirmed: Persona → Account Requirement (Registration Eligibility)

Separately from the birthright *calculation*, the real Academy/
Community/Partner Portal **registration** SOPs confirm a Salesforce
Contact must be associated to an Account with one of these
`Account_Status__c` values to be eligible for self-service
registration at all: `Customer`, `Partner`, `Prospect - New New`,
`Prospect - Existing`. A Contact with no associated Account at all is
classified as "Individual" under birthright policy (**confirmed
directly in the real docs** — this validates the "Individual" persona
fix already made in `agent.py`'s `derive_persona()`).

## Open Questions

1. Confirm the real Salesforce field names (e.g. is it literally
   `Account_Status__c`, `Customer_Status__c`?) feeding each DynamoDB
   column — this doc has the DynamoDB side confirmed via Agent 2's real
   code, but the upstream Salesforce field API names are not yet
   independently confirmed beyond `Account_Status__c` itself (named
   explicitly in the Birthright Guide).
2. Whether/when Agent 2's `AccountStatusType` and `CustomerStatusType`
   should be updated to match the real values above (out of scope for
   this document — Agent 2 is intentionally untouched here).
