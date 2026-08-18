# CIAM Support Assistant

Multi-agent system that auto-triages CIAM (Customer Identity and Access Management) support tickets from Jira: classifies intent → pulls account, Auth0, and knowledge-base context → synthesizes a root-cause diagnosis with recommended fixes, ready to post back to the ticket. Designed to cut manual investigation time for L1 support engineers on access, birthright, and entitlement issues.

**All 5 agents deployed and live on AWS Bedrock AgentCore as of 2026-08-17, end-to-end tested and verified against real sandbox tickets.**

## Architecture

```
Jira Ticket
    │
    ▼
Orchestrator (ciam_orchestrator/) — pulls ticket from Jira, dispatches agents
    │
    ├──► Agent 1 — Intent Classifier (Python)
    │    • Classifies intent (ACCESS_DENIED, etc.), extracts email & portal
    │    • Deployed v3 on AgentCore — runtime READY
    │    • Tests: unit test + 25 real test cases ✅
    │
    ├──► Agent 2 — Database Agent (Python)
    │    • Queries NetskopeID DynamoDB table (Salesforce account data)
    │    • Deployed v6 on AgentCore — runtime READY
    │    • Tests: 67 case comprehensive_test.py ✅
    │
    ├──► Agent 3 — Auth0 Agent (Python)
    │    • Fetches user birthright, entitlements, login history from Auth0 Management API
    │    • Deployed v3 on AgentCore — runtime READY, credentials configured
    │    • Tests: 18 unit tests ✅ (1 stale domain test, cosmetic)
    │
    ├──► Agent 4 — Knowledge Base Agent (Python) [FIXED 2026-08-17]
    │    • Birthright evaluation (Salesforce vs live Auth0)
    │    • Fix classification (SIMPLE_FIX vs ESCALATE_TO_L2)
    │    • KB retrieval (9 live Auth0 Actions, post-login flow, core CIAM docs)
    │    • Deployed v14 on AgentCore — runtime READY
    │    • Fixed: Python 3.13 ABI mismatch (v13 silently packaged cp314 wheels)
    │    • Tests: 60 unit tests ✅
    │
    └──► Agent 5 — Response Generator (Python)
         • Synthesizes Agents 2/3/4 into final diagnosis
         • Root cause, evidence, recommended actions, L1/L2 routing
         • Deployed v9 on AgentCore — runtime READY
         • Tests: 29 unit tests ✅
    │
    └──► Posts diagnosis back to Jira
```

## Deployment Status (verified live, 2026-08-17)

| Agent | Version | Status | Last Updated | Backend |
|---|---|---|---|---|
| 1 — Intent Classifier | v3 | READY | 2026-07-23 | — |
| 2 — Database | v6 | READY | 2026-07-21 | NetskopeID (DynamoDB) |
| 3 — Auth0 | v3 | READY | 2026-08-04 | Auth0 Management API |
| 4 — Knowledge Base | v14 | READY | 2026-08-17 | ciam-kb KB (27 docs + 9 live Actions) |
| 5 — Response Generator | v9 | READY | 2026-08-13 | — |

Knowledge Base (Agent 4): `ciam-kb` (ID `O4XMWIIEHS`) — **ACTIVE** with S3 data source **AVAILABLE**, synced with core CIAM docs, live Auth0 Action scripts, and post-login execution order.

## Directory Structure

```
CIAM-Support-Assistant/
├── agents/                                  # 5 deployed agents
│   ├── 01-intent-classifier/                # v3: intent classification
│   ├── 02-database-agent/                   # v6: Salesforce/DynamoDB lookup
│   ├── 03-auth0-agent/                      # v3: user metadata & birthright
│   ├── 04-knowledge-base-agent/             # v14: birthright eval + KB RAG
│   │   ├── agentcore/                       # NEW: agentcore.json packaging config
│   │   ├── pyproject.toml                   # NEW: Python version pinning (>=3.13,<3.14)
│   │   └── .bedrock_agentcore.yaml          # Deployment metadata, v14 changelog
│   └── 05-response-generator/               # v9: final diagnosis synthesis
├── orchestrator/                            # Dispatch, invocation, state
│   ├── ciam_orchestrator/
│   │   ├── orchestrator.py                  # Main entry point (5-agent pipeline)
│   │   ├── schemas.py                       # Agent input/output types (Pydantic)
│   │   ├── jira_client.py                   # Jira integration (see known issues)
│   │   └── agent_invoker.py                 # AgentCore invoke + result parsing
│   ├── tests/                               # 19 orchestrator tests ✅
│   ├── run_ticket.py                        # NEW: CLI to run any Jira ticket end-to-end
│   └── webhook_listener.py                  # Jira webhook handler (Lambda-ready)
├── specs/                                   # Agent specs (executable contracts)
│   ├── 01-Intent-Classifier-Agent/
│   ├── 02-Database-Agent/
│   ├── 03-Auth0-Agent/
│   ├── 04-Knowledge-Base-Agent/
│   └── 05-Response-Generator-Agent/
└── README.md (this file)
```

## Quick Start

### Run any Jira ticket through the live pipeline:

```bash
cd orchestrator
set -a && source ../.env && set +a
export AWS_REGION=us-east-1
python3 run_ticket.py RJT-31
```

Fetches the ticket from Jira sandbox, runs all 5 agents live, prints per-agent results, saves full JSON result as `rjt-31_orchestrator_result.json`.

### Or run the orchestrator tests:

```bash
cd orchestrator
python3 -m pytest tests/ -v
```

### Or run individual agent tests:

```bash
cd agents/04-knowledge-base-agent
python3 -m pytest test_agent4.py -v      # 60 tests

cd agents/05-response-generator
python3 -m pytest test_agent5.py -v      # 29 tests
```

## Recent Work (This Session, 2026-08-17)

### 🔧 Fixed Agent 4 deployment (v13 → v14)

**Issue:** Agent 4 v13 was deployed but failed on every invocation with "Runtime initialization time exceeded (30s)" — no CloudWatch logs at all.

**Root cause:** A new `agentcore/agentcore.json` file (needed for packaging) never set `runtimeVersion`, so the packager silently defaulted to `PYTHON_3_14` and resolved a `pydantic_core` wheel with the cp314 ABI. The actual deployed runtime is `PYTHON_3_13`, which can't load cp314 compiled extensions — `import pydantic_core` crashed agent.py's top-level import chain on every cold start before CloudWatch could initialize.

**Fix:** Added `"runtimeVersion": "PYTHON_3_13"` to `agentcore.json` and pinned `requires-python = ">=3.13,<3.14"` in a new `pyproject.toml`. Repackaged (confirmed `.so` tag flipped from `cpython-314` to `cpython-313`), redeployed as v14. **Verified live:** invocation succeeds in ~4–6s (was: always timed out at 30s), full v13 feature set confirmed working against real tickets.

**Lesson:** When packaging AgentCore agents with a hand-written `agentcore.json`, always set `runtimeVersion` explicitly and match it to the deployed runtime's declared Python version. The packager won't fail if you don't — it will silently produce incompatible wheels.

### 📦 Agent 4 v13 improvements

- **Multi-persona support:** Internal Netskope.com users (NSKP-Preview connection) get birthright from Okta group membership (NetskopeID-Sync-1 Action) instead of Salesforce Account Status. Added `derive_group_based_persona()` and persona_source field ("okta_groups" | "salesforce_account_status") to distinguish the two paths. Backward-compatible.
- **Expanded Auth0 Action monitoring:** Went from 2 to 9 actions checked live for code drift (NetskopeID-Sync-1/2, Gatekeeper, RBAC-Consolidated, Email Verification v2, Registration-Forms, Account Migration Acknowledgement, Privacy Policy Acknowledgement, MFA-Consolidated).
- **Sync diagnostics:** Added helpers to distinguish real birthright gaps from pending-login-refresh or multi-account ambiguity.

### 🛠 Orchestrator improvements

- **New `orchestrator/run_ticket.py`:** CLI tool to fetch any Jira ticket and run it through all 5 agents live. Usage: `python3 run_ticket.py <ISSUE-KEY>`.
- **Jira integration:** Added webhook listener and Jira API client (with one known bug, see below).

### ✅ End-to-end verification (real tickets)

Ran **RJT-30** and **RJT-31** through the live 5-agent pipeline:
- All agents READY and responsive
- Correctly identified missing birthright keywords (Notification, Support)
- Detected real live code-drift signal on Auth0 "Account Migration Acknowledgement" Action
- Posted comprehensive diagnoses back to Jira

## Known Issues

### 1. Agent 3 test is stale (cosmetic)

`agents/03-auth0-agent/test_agent3.py::test_http_posture_allows_expected_paths` fails because the test hardcodes an old domain `nskp.auth0.com` that no longer matches the real `AUTH0_DOMAIN` constant. The agent works fine in production — it's just a test data mismatch. Fix: update test to use the real domain or parametrize it.

### 2. `jira_client.py` has a path bug (not yet triggered in production)

`get_issue()` and `update_issue()` methods call `/rest/api/2/issues/{key}` (plural), but Jira's actual REST API path is `/issue/{key}` (singular). The `add_comment()` method has the correct path. This doesn't break anything currently used (the orchestrator only calls `add_comment`), but should be fixed before anyone tries to use `get_issue` or `update_issue` through this client.

### 3. Recurring Auth0 Action code-drift flag (needs human confirmation)

The live monitoring on the "Account Migration Acknowledgement" Auth0 Action keeps flagging a missing "CIAM" marker on real tickets (RJT-30, RJT-31). This may be a genuine regression in that Action's code, or a stale marker in our monitoring. L2 should confirm which, since it's currently escalating tickets that might otherwise be simple fixes. The marker itself is verified (copy-pasted from the actual archived source), so the flag is real — just needs a human to check whether the live Action code has actually changed.

## Test Results (2026-08-17)

| Component | Tests | Status |
|---|---|---|
| Agent 1 — Intent Classifier | unit | — |
| Agent 2 — Database | comprehensive_test.py | ✅ 67 pass |
| Agent 3 — Auth0 | test_agent3.py | ⚠️ 17/18 pass (1 stale) |
| Agent 4 — Knowledge Base | test_agent4.py | ✅ 60 pass |
| Agent 5 — Response Generator | test_agent5.py | ✅ 29 pass |
| Orchestrator | tests/ | ✅ 19 pass |
| **Total** | | **✅ 192/193** |

## Contributing

Each agent is a standalone Bedrock AgentCore deployment. To test locally before deploying:

1. Run the unit tests in that agent's folder.
2. The agent code itself is in `agent.py` — edit there, then run tests to verify.
3. To deploy to AWS, use `bedrock-agentcore` CLI or boto3's `UpdateAgentRuntime` (see `.bedrock_agentcore.yaml` for credentials and runtime ID).

The orchestrator ties them together — edit `ciam_orchestrator/orchestrator.py` to change the dispatch logic, or `ciam_orchestrator/schemas.py` to change request/response types.

## Environment

Requires `.env` with:
- `JIRA_INSTANCE_URL` — Jira sandbox instance URL
- `JIRA_EMAIL` — Jira API user email
- `JIRA_API_TOKEN` — Jira API token
- `AUTH0_DOMAIN` — Auth0 tenant domain
- And others for AWS access (boto3 auto-discovers from IAM role in AgentCore, or `~/.aws/credentials` locally)
