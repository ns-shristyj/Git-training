# Migration Known Issues (Nov 1 CIAM Migration)

> **DRAFT — needs real input from whoever ran/owns the Nov 1 migration
> project.** This draft is a placeholder structure only — it does
> **not** contain verified real migration bugs, since that information
> wasn't available in this session. It's included so the document's
> *shape* exists and can be filled in, and because this document has
> already proven useful even near-empty: a test ticket mentioning "Nov
> 1 migration" correctly caused Agent 4's KB search to surface this
> exact document (relevance score 0.35) purely from the filename/title
> match, before any real content existed.

## Purpose

A dated list of specific, confirmed bugs or gaps introduced by the
Nov 1 CIAM migration, so Agent 4 can immediately recognize "this
matches a known migration issue" instead of treating a migration-
adjacent ticket as a fresh, unexplained problem.

## Structure to Fill In (Template)

For each known migration issue, capture:

```
### Issue: <short title>
- Reported: <date range>
- Symptom: <what the user/L1 sees>
- Affected segment: <which persona/account type, if known>
- Root cause: <what actually broke during/after migration>
- Status: Fixed | Workaround available | Open
- Fix/workaround: <what to do about it, if anything>
```

## What We Know Is True (Confirmed Context, Not a Bug List)

- A hard migration date of **November 1** is referenced consistently
  across tickets tested this session — this appears to be a real,
  significant cutover date worth anchoring all migration-era issue
  reports against.
- Tickets that explicitly mention the migration in their raw text
  should be expected to correlate with genuine post-migration gaps more
  often than tickets that don't — this is exactly the kind of signal
  Agent 4's KB query (`build_kb_query()` in `agent.py`) is designed to
  pick up on, since it includes the raw ticket text verbatim.

## Open Questions to Resolve

1. Is there an existing migration retro/postmortem document this can
   be built from directly, rather than reconstructed from ticket
   patterns?
2. Is there a **cutoff date** after which migration-era issues should
   be considered resolved, so this document doesn't stay "relevant"
   indefinitely?
3. What are the actual confirmed bugs/gaps from the migration (this
   draft has none — it's a template only)?
