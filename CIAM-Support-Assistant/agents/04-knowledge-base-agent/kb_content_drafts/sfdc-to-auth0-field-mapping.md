# Salesforce → Auth0 Field Mapping

> **DRAFT — needs verification against the real NetskopeID-Sync
> pipeline configuration.** This draft infers likely field mappings
> from Agent 2's DynamoDB schema and Agent 3's Auth0Payload schema
> (both already implemented and tested this session) — but the actual
> Salesforce field names and the exact sync mechanism are unconfirmed.

## Purpose

Maps which Salesforce field feeds which Auth0 `app_metadata` field, via
which sync job, so a suspected sync issue can be traced to the specific
upstream field and pipeline stage responsible.

## Known Fields (From Agent 2 + Agent 3's Already-Implemented Schemas)

| Salesforce-derived field (Agent 2's `AccountPayload`) | Auth0 field (Agent 3's `Auth0UserRecord`) | Sync mechanism | Direction |
| :--- | :--- | :--- | :--- |
| `account_status` | *(feeds birthright calculation, not a direct 1:1 Auth0 field)* | NetskopeID-Sync-1 | Salesforce → Auth0 (indirect, via persona logic) |
| `active_tenant_count` | *(feeds birthright calculation)* | NetskopeID-Sync-1 | Salesforce → Auth0 (indirect) |
| `customer_status` | Unconfirmed — no direct Auth0 field identified yet | Unconfirmed | Unconfirmed |
| `sf_user_exists` / `sf_user_active` | Related to Auth0 `user_found` / account existence | Provisioning check, not a per-field sync | N/A |
| — | `app_metadata.last_sync` | NetskopeID-Sync-1 (timestamp of last run) | N/A (metadata about the sync itself) |
| — | `app_metadata.last_daily_sync` | NetskopeID-Sync-2 (timestamp of last run) | N/A (metadata about the sync itself) |

## Required vs. Informational Fields

**Required for birthright calculation** (per `evaluate_birthright()`
in `agent.py`):
- `account_status`
- `active_tenant_count`

**Informational only** (used elsewhere, not in the birthright formula
itself):
- `customer_status`, `sf_user_exists`, `sf_user_active`,
  `tenant_url` (all from Agent 2's schema) — useful context for L1, not
  direct inputs to Tool 1.

## Sync Timing Characteristics

- `sync_stale` is flagged by Agent 3 if `last_sync` is more than 7 days
  old (hardcoded threshold in both Agent 3's and Agent 4's code —
  confirm this matches the actual sync job's real run frequency).
- `sync_never_ran` is flagged if `last_sync` is null/absent entirely.

## Open Questions to Resolve

1. What are the **actual Salesforce field API names** (e.g.
   `Account.Status__c` or similar) that feed `account_status` and
   `active_tenant_count`? This draft only has Agent 2's already-
   transformed output field names, not the raw Salesforce source.
2. What is `customer_status`'s real role — is it used anywhere in
   birthright/entitlement logic, or purely informational?
3. Confirm the real sync job frequency (currently assumed ~hourly for
   Sync-1, daily for Sync-2, based on field naming alone —
   `last_sync` vs. `last_daily_sync`).
4. Is there a Salesforce field for `Prime` tenant/portal eligibility
   that isn't yet reflected in Agent 2's schema at all?
