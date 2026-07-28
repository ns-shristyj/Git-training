# Resolved Ticket Patterns

> **DRAFT — this is NOT real resolved-ticket data.** No actual Jira TQI
> export was available in this session. What follows is a **template**
> plus the anonymized *test scenarios* used to validate Agents 1–4
> (synthetic/test ticket IDs, not real production Jira tickets — do not
> confuse these with genuine historical resolutions). Real content
> requires an actual export from Jira (TQI project, `status: Done`,
> PII stripped per this project's established practice).

## Purpose

This is the entire basis for Agent 4's `similar_past_tickets` output
field — without real entries here, that field will always be empty
regardless of how good the birthright logic is.

## Metadata Convention Needed (Blocking — See Spec OQ-3)

Agent 4's code (`query_knowledge_base()` in `agent.py`) currently uses a
**heuristic** to tell a ticket-doc apart from a SOP/guide-doc: it checks
whether the document title starts with or contains `"tqi-"`. This is a
placeholder guess, not a confirmed convention — **once real ticket
exports are formatted and uploaded, confirm the actual naming/metadata
convention and update the `is_ticket` check in `agent.py` to match.**

## Template (Format Each Real Ticket Should Follow)

```
### TQI-XXXXX
- Summary: <one-line summary, PII removed>
- Persona/intent: <e.g. Customer / ACCESS_DENIED>
- Resolution: <what fixed it>
```

## Anonymized Test Scenarios (Session Test Data — NOT Real Resolutions)

These are the synthetic scenarios used to validate the pipeline this
session. They are structurally realistic but were **not** drawn from
real resolved tickets, and their "resolutions" are what Agent 4 itself
computed during testing, not human-verified fixes:

- **Scenario:** Customer persona, missing `Support` keyword only, all
  other expected keywords present, user confirmed in Auth0.
  **Agent 4 result:** `SIMPLE_FIX` — add `Support` to entitlements.

- **Scenario:** Customer persona, zero `birthright` and zero
  `entitlements` (fresh/never-synced account), user confirmed in
  Auth0. **Agent 4 result:** `SIMPLE_FIX` — add the full expected set.

- **Scenario:** User not found in Auth0 at all, despite existing in
  Salesforce/DynamoDB. **Agent 4 result:** `ESCALATE_TO_L2` —
  provisioning gap, not an entitlement fix.

- **Scenario:** All expected keywords present (`match: true`), but
  intent was `ACCESS_DENIED` anyway. **Agent 4 result:**
  `ESCALATE_TO_L2` — flagged as `birthright_correct_but_access_denied`,
  likely a Gatekeeper Action bug, not a data gap.

- **Scenario:** Ticket mentioning a Community-portal access issue where
  the user was confirmed to exist correctly in Auth0 with proper
  birthright, but the same email could not be found in the CIAM
  DynamoDB account table. **Agent 4/Agent 2 result:** a genuine
  cross-system inconsistency (Auth0 says one thing, DynamoDB says
  another) — not resolvable by entitlement changes alone.

## Open Questions to Resolve

1. Get a real Jira TQI export (last ~90 days of `status: Done` tickets,
   per spec §4.1 Tool 2's ingestion description) — this is the actual
   blocker.
2. Confirm the metadata/naming convention so `is_ticket` detection in
   `agent.py` can be made accurate instead of a heuristic guess.
