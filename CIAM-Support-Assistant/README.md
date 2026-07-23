# CIAM Support Assistant

Multi-agent system that auto-triages CIAM (Customer Identity and Access
Management) support tickets from the Jira TQI project, classifies intent,
looks up account/Auth0/knowledge-base data, and synthesizes a diagnosis for
L1 support engineers.

## Directory Structure

```
CIAM-Support-Assistant/
├── specs/                          # Executable contracts (spec.md per agent)
│   ├── 01-Intent-Classifier-Agent/
│   ├── 02-Database-Agent/
│   ├── 03-Auth0-Agent/
│   ├── 04-Knowledge-Base-Agent/
│   └── 05-Response-Generator-Agent/
├── agents/
│   ├── 01-intent-classifier/       # Agent 1 — deployed, Claude Haiku
│   └── 02-database-agent/          # Agent 2 — deployed, DynamoDB lookup
├── orchestrator/                   # Dispatches Agent 1 -> Agent 2/3/4
└── docs/                           # Slides, status updates, test summaries
```

## Architecture

```
Jira TQI Ticket
      │
      ▼
Orchestrator
      │
      ├──► Agent 1 (Intent Classifier, Claude Haiku)
      │       classifies intent, extracts email, returns RoutingEnvelope
      │
      │    confidence < 0.70 OR auto_escalate=true?
      │       │
      │       yes → escalate to human L2
      │       no  → dispatch per RoutingEnvelope flags:
      │
      ├──► Agent 2 (Database Agent) — DynamoDB account lookup      [deployed]
      ├──► Agent 3 (Auth0 Agent) — Auth0 user metadata/logs        [not built]
      ├──► Agent 4 (Knowledge Base Agent) — RAG over Confluence    [not built]
      │
      └──► Agent 5 (Response Synthesizer, Claude Sonnet) — diagnosis [not built]
```

## Current Status

| Component | Status |
|---|---|
| Agent 1 — Intent Classifier | ✅ Deployed to Bedrock AgentCore, 100% test accuracy on 25 real-ticket-derived cases |
| Agent 2 — Database Agent | ✅ Deployed, wired to real DynamoDB (`NetskopeID` table), 100% pass rate across 67 test cases |
| Orchestrator | ✅ Built, tested end-to-end with real Agent 1 + Agent 2 |
| Agent 3 — Auth0 Agent | ⏳ Not built |
| Agent 4 — Knowledge Base Agent | ⏳ Not built |
| Agent 5 — Response Synthesizer | ⏳ Not built |

See `orchestrator/README.md` for how to run/test the orchestrator locally.
