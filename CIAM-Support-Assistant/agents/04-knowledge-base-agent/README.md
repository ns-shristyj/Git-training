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
| Tool 2 `query_knowledge_base` | ✅ Implemented and working against a real, live Bedrock Knowledge Base (`O4XMWIIEHS`) |
| Unit tests | ✅ 16/16 passing, mapped to spec §9 acceptance criteria (AC-1–AC-15) |
| Deployed to AgentCore | ✅ `ciamKnowledgeBaseAgent-VdVt7x7TZ1` (v2), READY, tested live end-to-end |
| Wired into orchestrator | ⏳ Not yet — see next steps |

## ⚠️ Known Provisional Data

The persona/expected-birthright table in `derive_persona()` is **provisional**
per spec §1 — it has not been verified against the real Birthright &
Entitlements Guide or the actual sync function source code. See spec OQ-6
and OQ-7. Do not treat its output as authoritative until reconciled against
one of those sources.

## The Knowledge Base

- **Knowledge Base ID:** `O4XMWIIEHS` (`ciam-kb`)
- **Type:** Managed Knowledge Base (Bedrock's fully-managed vector store —
  see spec OQ-1). Provisioned via the AWS Console's "Quick create" flow
  after direct OpenSearch Serverless index creation was blocked by an
  account-level restriction outside this project's control.
- **Data source:** `s3://ciam-agent4-kb-docs-786063285476-us-east-1/docs/`
  — currently **8 placeholder markdown stubs only**. Real content (the
  actual Birthright & Entitlements Guide, SOPs, resolved TQI ticket
  exports, etc.) still needs to be authored and uploaded, then synced in
  the Bedrock console.
- **A real SDK gap was hit and worked around:** as of boto3 1.42.97 (the
  latest release), `client.retrieve()` does not yet support the
  `managedSearchConfiguration` parameter that Managed Knowledge Bases
  require (it only recognizes `vectorSearchConfiguration`, which the
  *service* then rejects for Managed KBs with a `ValidationException`).
  `query_knowledge_base()` in `agent.py` therefore issues a raw
  SigV4-signed HTTP request to the same API instead of using the boto3
  client method. **Once botocore adds support for
  `managedSearchConfiguration`, switch back to `client.retrieve()`** —
  the raw-HTTP path is a deliberate, commented workaround, not a
  permanent architectural choice.

## What's needed before this can go fully live

1. **Real Birthright & Entitlements Guide** (or the sync function source
   code) to replace the provisional persona table (OQ-6/OQ-7).
2. **Real KB document content** — replace the 8 placeholder stubs in S3
   with actual Confluence exports, SOPs, and resolved TQI ticket data,
   then re-sync the data source in the Bedrock console.
3. **Real Auth0 Action/Rule/Flow scripts** for the `nskp` tenant, to
   implement Tool 4 for real (currently a stub — see OQ-8).
4. Wire into orchestrator's `AGENT_REGISTRY["agent_4"]` (set
   `AGENT_4_ARN` and `ENABLE_AGENT_4=true`).

## Running the tests

```bash
cd agents/04-knowledge-base-agent
pip install -r requirements.txt pytest
python -m pytest test_agent4.py -v
```

`conftest.py` stubs `bedrock_agentcore.BedrockAgentCoreApp` for local testing,
same pattern as Agents 2/3. Tool 2's tests mock `requests.post` (not a
boto3 client) to match the raw-HTTP implementation described above.
