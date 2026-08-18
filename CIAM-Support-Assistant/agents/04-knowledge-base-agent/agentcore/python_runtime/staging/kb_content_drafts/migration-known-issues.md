# Migration & Platform Known Issues

> **Sourced from real Unified Login / Identity Dashboard release notes**
> (Netskope Confluence, ISI space, versions v1.4.0 through v2.8.1,
> exported 2026-07-28). Replaces the earlier empty template — this is
> real, dated, versioned known-issue data, not a guess. Note the scope
> is broader than just "the Nov 1 migration" — it's the ongoing
> known-issues/fixes history of the whole Unified Login platform, which
> is more useful for Agent 4's KB retrieval anyway (a support ticket
> rarely cares whether a bug is migration-era or just a later platform
> bug).

## Currently Open Known Issues (as of v2.8.1)

### Partner Portal registrations not allowed via Auth0 sign-up (v1.4.0+)

Users are confused by a Sign-Up link shown on the Partner Portal login
screen, but Partner Portal registrations are **not** actually allowed
through that Auth0 form (registration requires the separate Partner
Registration flow — see `Netskope Partner Portal: Registration
Process`). Planned fix (redirect users to the correct registration
page) has no confirmed release date as of this export.

### Federated users cannot log into the Identity Dashboard (v1.5.0+)

Even with the `Dashboard` keyword present in birthright or
entitlements, federated (non-`NetskopeID` connection) users cannot log
into the Netskope Identity Dashboard. No fix confirmed as of this
export — cross-reference with `Support Portal Access Tile` UX changes
in later releases, which suggest this area is under active work.

### New federated users need manual Salesforce account creation (v2.0.0+)

No SAML Just-In-Time (JIT) provisioning exists yet for federated users
— new federated users still require a manually-created Salesforce
account. A SAML JIT Provisioning APEX Class is the planned long-term
fix; not confirmed shipped as of this export.

### Duplicate accounts visible to Organization Admins (v2.0.0+)

Org admins using federated services may see **duplicate** accounts in
the Identity Dashboard's Manage Users section — old pre-federation
NetskopeID (username/password) accounts remain listed alongside the
newer federated accounts for the same person.

### Orphaned DynamoDB records on federated connection deletion (v2.0.0+)

Deleting a federated SSO connection does **not** trigger the
`Federated-User-Deletion-Sync` action, so federated users created under
that connection remain in the `NetskopeID` DynamoDB table indefinitely.
**Documented workaround:** before deleting a federated connection, take
note of all federated users under it so the corresponding records can
be manually purged afterward.

## Historical Bugs — Already Fixed (Useful Context for "Is this a known pattern?")

These are **resolved**, but valuable for Agent 4/5 to recognize "this
matches a bug that was already fixed in version X" when a ticket
describes a symptom that matches:

| Version | Bug | Symptom | Fix |
| :--- | :--- | :--- | :--- |
| v2.0.0 | Stale Prime-level access retention | A demoted user could incorrectly **keep** Prime-level access because sequential permission updates were each computed from outdated data (race condition) | Access is now recomputed as a single, up-to-date decision on every login |
| v2.0.0 | Access wiped on transient Salesforce lookup failure | A temporary Salesforce lookup failure could **overwrite** a user's existing access data with empty values, downgrading their access for no real reason | Access data is now left untouched until a lookup completes successfully |
| v2.0.0 | Hourly sync over-triggering for native users | The hourly sync check for native `NetskopeID` users referenced the wrong tracking field, causing sync to run more often than intended | Fixed to reference the correct field |
| v2.0.0 | Academy lookups matched wrong record for federated users | Netskope Academy attribute lookups only matched **native** `NetskopeID` users correctly; federated users could be matched against the wrong `NetskopeID` table record entirely | Fixed matching logic; also removed a duplicate attribute assignment |
| v2.5.0 | Entitlement drift after Auth0 script sync (GIS-33767) | User entitlement/permission changes were written only to the Auth0 database; a subsequent Auth0 script-based sync could **silently overwrite** those changes, causing drift and unexpected reversions | Updates now perform a coordinated write to both the Identity Dashboard database and Auth0 |
| v2.7.1 | Name updates not reflected in Auth0 (GIS-3788) | When a user's name was updated in the Identity Dashboard, the change wasn't always correctly propagated to Auth0 | An additional database field now ensures name-update consistency between both systems |

## Deferred / In-Progress Items

- **GIS-3777 (Support Portal Access Tile warning removed)** — first
  announced in v2.6.0, then **deferred to the v2.7.0 release** per this
  export's own tracking, and finally confirmed shipped in v2.7.1. Shows
  this kind of feature can slip a release or two — worth checking the
  *latest* release notes rather than assuming the first-announced
  version if a ticket references this specific behavior.
- **Identity Dashboard self-service federation configuration
  (GIS-3789) — genuinely unstable, not just "pending."** This feature
  has cycled through **added → reverted → reapplied → reverted again**
  across four consecutive releases: added in v2.8.0, reverted in
  v2.8.1, reapplied in v2.9.0, reverted *again* in v2.9.1 (the latest
  release in this export). If a ticket references self-service
  federation setup, **check the org's exact platform version before
  assuming the feature is even present** — its availability has
  flip-flopped repeatedly and the team's own FAQ describes it as
  something they'll "reintroduce once outstanding items are resolved,"
  with no committed date.

## Open Questions

1. Confirm whether any of the "currently open" issues above have since
   been fixed in a release newer than v2.9.1 (this export's latest).
2. Is there a dedicated migration retro/postmortem document separate
   from these release notes, with more specifically Nov-1-migration-era
   content (as opposed to the ongoing platform release history covered
   here)?
