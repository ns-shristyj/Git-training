# Auth0 Post-Login Flow: Execution Order

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com) --
> GET /api/v2/actions/triggers/post-login/bindings, fetched via the
> workflow-reader M2M app. This is the real, current binding order for
> the `post-login` trigger -- Actions execute top to bottom on every login.

## post-login (in execution order)

1. **Email Verification v2** -- enforces/prompts email verification if the user isn't yet verified.
2. **Registration-Forms** -- retrieves the user's profile from the NetskopeID table and drives onboarding forms.
3. **Account Migration Acknowledgement** -- one-time acknowledgement for legacy-migrated users.
4. **Privacy Policy Acknowledgement** -- requires acceptance of the current privacy policy.
5. **NetskopeID-Sync-1** -- bootstraps app_metadata, initializing an empty birthright array if missing.
6. **NetskopeID-Sync-2** -- **the birthright engine**. Computes the user's birthright access array from Salesforce Account Status and Tenant Requests, writes it (+ last_sync) to app_metadata.
7. **RBAC - Consolidated** -- grants portal-specific roles based on the birthright/entitlement keywords set by step 6.
8. **Gatekeeper** -- **the enforcement point**. Checks the (now-finalized) birthright/entitlements against the portal being accessed; denies login if the required keyword is absent or a Block-<Portal> keyword is present.
9. **MFA - Consolidated** -- enforces/skips multi-factor authentication (runs last, after access has already been decided).

### Why the order matters for diagnosis

A missing-portal-access ticket (e.g. "Support" missing) traces to step 6
(NetskopeID-Sync-2) miscalculating or not yet syncing birthright -- and is
*visibly enforced* at step 8 (Gatekeeper), which is what actually produces
the "insufficient permissions" error the user sees. Steps 1-4 run first
and can short-circuit the flow (e.g. unverified email) before birthright
is ever evaluated -- worth ruling out first if the user never even reaches
a portal-specific denial.

## pre-user-registration (in execution order)

1. **Provisioner** -- validates/sanitizes the submitted email before allowing self-service sign-up to proceed.

## custom-phone-provider

1. **Custom Phone Provider** -- sends OTP codes via AWS End User Messaging Notify instead of Auth0's default SMS provider.

## Other triggers checked with no bound actions

`credentials-exchange`, `send-phone-message`, `custom-email-provider`,
`password-reset-post-challenge` currently have no bindings, despite a
"Custom Email Provider" Action existing in the Actions list -- it may be
unbound/disabled, or bound to a trigger not checked here.
