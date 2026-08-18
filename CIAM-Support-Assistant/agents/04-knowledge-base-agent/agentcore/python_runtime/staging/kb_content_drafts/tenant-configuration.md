# Tenant Configuration & Pre-Migration GO/No-GO Checklist

> **Sourced from the real CIAM GO/No GO Checklist** (Netskope Confluence, ISI space,
> exported 2026-07-28). This replaces the earlier draft that speculated about
> tenant models — it is a real, dated, pre-migration validation checklist covering
> business readiness, Auth0/DynamoDB infrastructure, and per-portal setup
> confirmations. It is useful both for initial tenant setup verification and as a
> historical record of what was validated before the Nov 1 migration.

## Purpose

This document covers the operational and technical readiness checklist that must
be completed before a tenant can proceed with the CIAM migration. It serves both
as a setup validation guide (for new tenants) and as a troubleshooting reference
(if a portal behaves unexpectedly post-migration, check whether its setup item
was marked complete in the original checklist).

---

## Business Readiness Checklist

- [ ] CIAM Nov 1 Change Approval
- [x] CIAM Internal communications and FAQ
- [ ] CIAM Communications for Customers
- [x] Final Support Email Communications
- [x] Community Blog Post
- [ ] Update support.netskope.com banner
- [ ] Community Only Users Email Communications
- [ ] Academy Only Users Email Communications
- [x] CIAM Partner Communications
- [x] CSG Training
  - [x] US Timezone Training
  - [x] IST Timezone Training
- [x] CSG to CIAM Team support document (CIAM Support - Getting Support)
- [x] CSG to CIAM Team Slack Channel

## Auth0, DynamoDB, and Infrastructure Checklist

- [x] NetskopeID DynamoDB Table created in us-east-2
  - [x] Replica created within us-east-1
  - [ ] Replica created within us-west-2
- [x] Auth0DynamoDBAccessServiceAccount created within production AWS account
  - [x] Service account credentials obtained
- [x] Error detection and alerting for failed DynamoDB CRUD operations, backup, replica operations
- [x] DynamoDB table write/read metrics enabled
- [x] Alerting on DynamoDB rate limiting
- [x] Create Netskope Support app in Auth0
  - [x] Configure as a SAML connection
- [x] Create Netskope Client Academy app in Auth0
  - [x] Configure as a SAML connection
- [x] Create Netskope Notification Portal app in Auth0
  - [ ] Configure as a OIDC connection
- [x] Error detection and alerting for failed delete/create operations and Action executions
- [x] Alerting for mass authentication failures
- [x] Alerting on Auth0 Management & Authentication API rate limiting
- [x] Create federation group in Okta: prod-cust-nsid-supportportal-user-grn
  - [x] Assign it access to Netskope ID application

## Netskope Support Portal Setup Checklist

- [x] SSO Setup within Production Salesforce
  - [x] SP SAML Metadata shared
- [x] Community ID obtained
- [x] Organization ID obtained
- [x] External Client Application within Prod. Salesforce
  - [x] Consumer Credentials shared
- [x] SearchUnify received SSO login link template
- [x] CIAM - Create Auth0 User Flow within Prod. Salesforce
- [x] Successful migration test with fake account
- [x] Successful user creation via new Flow
- [ ] Find workaround for error email being sent out
- [ ] Permission Set for internal user access to support portal
  - [ ] Assigned to all users who currently have access

## Netskope Client Academy Portal Setup Checklist

- [x] SSO Setup within Client Academy
  - [x] Set custom logout URL (add to allowed logout URLs in Auth0)
- [x] Retrieve API key for Client Academy
  - [x] Apply key to scripts and Actions
- [x] Successful migration test with fake user
- [ ] Disable Portal Local Login Page within SAML Settings

## Netskope Community Setup Checklist

- [ ] Disable Username & Password authentication
- [ ] Rename the Partner login button to Netskope Unified Login
- [x] Retrieve API key for Community
  - [x] Apply key to scripts and Actions
- [x] Successful migration test with fake user

## Netskope Notification Portal Setup Checklist

- [ ] OIDC connection setup within Notification Portal
- [ ] Successful migration test with fake user

---

## Post-Migration User Management SOPs

### MFA Enrollment (User Self-Service)

**Recommended authenticator apps:**
- Microsoft Authenticator
- Google Authenticator
- Authy (by Twilio)

**Path:** Auth0 Teams (Netskope app in Okta) → select `nskp` tenant → User
Management → Users → target user → scroll to Multi-Factor Authentication
section → "Keep Your Account Safe" → select Google Authenticator or Security
Key → scan QR code → enter one-time code.

### MFA Reset

**Purpose:** Reset a user's MFA enrollments if they lose access to their
authenticator app or security key.

1. Log into Auth0 Teams (Netskope app in Okta)
2. Select the `nskp` tenant
3. Navigate to User Management → Users
4. Find the target user (must be on NetskopeID connection)
5. Scroll to Multi-Factor Authentication section
6. Click "Reset MFA" link
7. Confirm with "Yes, Reset It"

**Critical:** If the user doesn't log in within **90 days** AND still hasn't
accepted the migration acknowledgement, their account is **deleted**. This SOP
is time-sensitive.

### Disabling Support Portal Access via Entitlement Block

**Purpose:** When a Salesforce/Netskope Support user is suspended/disabled,
disable Support portal access without deleting them.

1. Log into Auth0 Teams (Netskope app in Okta)
2. Select the `nskp` tenant
3. Navigate to User Management → Users
4. Find the target user (must be on NetskopeID connection)
5. Scroll to Metadata section, find "App Metadata (app_metadata)" box
6. Within the `entitlements` array, add the string `"Block-Supp"`
7. Save

**Critical:** Blocking affects **all** Auth0-authenticated apps (Support,
Academy, Community, Partner Portal, Prime Okta Tenant) — it is a full-account
lockout, not a single-resource block.

### Deleting Auth0 Users

**WARNING:** Deleting a user from Auth0 **permanently removes them from the
NetskopeID/Netskope Unified Login database**. They will no longer access any
onboarded applications, but their local accounts in each app (e.g. SkillJar,
Community local account) will **not** be deleted.

**During migration period (October 5 – TBD):** Deleted users may be able to
recreate their account if found within Community and Academy. **Blocking is
recommended instead** to prevent login while allowing eventual planned deletion
after migration is complete.

To delete:
1. Log into Auth0 Teams (Netskope app in Okta)
2. Select the `nskp` tenant
3. Navigate to User Management → Users
4. Find the target user (must be on NetskopeID connection)
5. Click "Actions" → "Delete"
6. Confirm deletion

---

## Known Configuration Gaps

1. **Partner Portal DynamoDB Replica (us-west-2)** — not yet created as of this
   export; may be completed in a follow-up phase.
2. **Notification Portal OIDC setup** — listed as incomplete on the checklist;
   clarify whether intentionally deferred or requires follow-up.
3. **Support Portal error email workaround** — one checklist item ("Find
   workaround for error email being sent out") was flagged with no resolution
   noted; worth confirming whether resolved post-migration.

## Open Questions

1. What is the current status of incomplete checklist items? (May have been
   completed after the export date.)
2. Is there a separate acceptance/sign-off process per section, or is the
   entire checklist reviewed as one gate before cutover?
3. For ongoing tenant onboarding (new customers post-Nov 1), which items are
   still relevant versus one-time migration setup only?
