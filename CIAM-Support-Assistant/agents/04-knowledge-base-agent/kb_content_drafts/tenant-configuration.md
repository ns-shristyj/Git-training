# Tenant Configuration Guide

> **DRAFT — needs verification against the real tenant provisioning
> model.** This draft describes what's inferable from Agent 2's schema
> (`active_tenant_count`, `tenant_url`) and how that field is already
> used in Agent 4's persona logic — but the underlying tenant model
> itself (what a "tenant" is, how it's assigned) is not documented
> anywhere in this project yet.

## Purpose

Explains the tenant → organization → portal-access relationship, since
`active_tenant_count` is already a load-bearing input to Agent 4's
persona determination (it's what distinguishes "Prospect with Tenant"
from "Prospect without Tenant" in the current birthright matrix), but
nothing in this project currently documents what a tenant actually
*is* or how that count gets computed upstream.

## What's Already Known (From Existing Schemas)

- Agent 2's `AccountPayload.accounts[].tenant_url` — a per-account
  tenant identifier/URL (e.g. `global-employee.netskope.com`, seen in
  real test data this session).
- Agent 2's `AccountPayload.accounts[].active_tenant_count` — an
  integer count of active tenants for the account.
- Agent 3's `app_metadata.tenant_id` (referenced in the draft Auth0
  login flow, Step 6/NetskopeID-Sync-2) — the tenant assignment that
  gets synced into Auth0.

## Draft Model (Unverified)

A single Salesforce **account** can apparently have zero, one, or more
than one **active tenant**. This matters specifically for the
"Prospect - Net New" persona: a prospect with `active_tenant_count >=
1` gets the full portal set (same as a Customer), while a prospect with
`active_tenant_count: 0` gets a reduced set (Community/Academy/
Dashboard only — no Support/Notification, presumably because there's
no live tenant to get support *for* yet).

## Open Questions to Resolve

1. What exactly is a "tenant" in this system — is it 1:1 with a
   Netskope cloud instance/deployment per customer?
2. How is `active_tenant_count` actually computed — is it purely from
   Salesforce, or does it also depend on Auth0/DynamoDB tenant
   provisioning state?
3. Are there known multi-tenant edge cases (e.g. a user who should have
   access to two tenants but only has one currently assigned; a tenant
   merged or renamed as part of the Nov 1 migration)?
4. Does `active_tenant_count` matter for any persona besides "Prospect
   - Net New," or only that one (current code only branches on it for
   that one account_status)?
