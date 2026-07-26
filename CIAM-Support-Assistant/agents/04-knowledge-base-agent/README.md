# Agent 4 — CIAM Knowledge Base Agent

Implements SPEC-CIAM-0004. Applies the Birthright & Entitlements Guide as
pure local logic (no LLM for the evaluation itself), then queries a Bedrock
Knowledge Base for supporting docs/tickets. Non-goal: fetching data itself
(Agent 2/3 already did that) or generating the final L1 response (Agent 5).

## Status

| Item | Status |
|---|---|
| Tool 1 `evaluate_birthright` | ✅ Implemented |
| Tool 3 `classify_fix_complexity` | ✅ Implemented |
| Tool 4 `identify_failing_workflow` | ⚠️ **Placeholder only** — always returns a stub; needs real Auth0 Action/Rule/Flow scripts (see spec OQ-8) |
| Tool 2 `query_knowledge_base` | ✅ Implemented, but points at `KNOWLEDGE_BASE_ID = "PLACEHOLDER_KB_ID"` — no real KB exists yet |
| Unit tests | ✅ 16/16 passing, mapped to spec §9 acceptance criteria (AC-1–AC-15) |
| Deployed to AgentCore | ❌ Not yet |
| Wired into orchestrator | ❌ Not yet |

## ⚠️ Known Provisional Data

The persona/expected-birthright table in `derive_persona()` is **provisional**
per spec §1 — it has not been verified against the real Birthright &
Entitlements Guide or the actual sync function source code. See spec OQ-6
and OQ-7. Do not treat its output as authoritative until reconciled against
one of those sources.

## What's needed before this can go live

1. **Real Birthright & Entitlements Guide** (or the sync function source
   code) to replace the provisional persona table (OQ-6/OQ-7).
2. **A provisioned Bedrock Knowledge Base** — S3 bucket with the 8 markdown
   docs (birthright matrix, login-flow steps, portal matrix, common issues,
   SFDC field mapping, tenant config, migration issues, resolved-ticket
   patterns), OpenSearch Serverless vector store, Titan embeddings. Set the
   real `KNOWLEDGE_BASE_ID` in `agent.py` once provisioned.
3. **Real Auth0 Action/Rule/Flow scripts** for the `nskp` tenant, to
   implement Tool 4 for real (currently a stub — see OQ-8).
4. **IAM execution role** — `bedrock:Retrieve` / `bedrock:RetrieveAndGenerate`
   scoped to the CIAM KB ARN, `bedrock:InvokeModel` scoped to `claude-haiku-*`.
   No DynamoDB, no Secrets Manager, no S3 (Bedrock reads the KB, not this
   agent directly).
5. Deploy to AgentCore (same pattern as Agents 1-3).
6. Wire into orchestrator's `AGENT_REGISTRY["agent_4"]`.

## Running the tests

```bash
cd agents/04-knowledge-base-agent
pip install -r requirements.txt pytest
python -m pytest test_agent4.py -v
```

`conftest.py` stubs `bedrock_agentcore.BedrockAgentCoreApp` for local testing,
same pattern as Agents 2/3.
