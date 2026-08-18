# Agent 4 — CIAM Knowledge Base Agent

Implements SPEC-CIAM-0004. Applies the Birthright & Entitlements Guide as
pure local logic (no LLM for the evaluation itself), then queries a Bedrock
Knowledge Base for supporting docs/tickets. Non-goal: fetching data itself
(Agent 2/3 already did that) or generating the final L1 response (Agent 5).

## Status (2026-08-18)

| Item | Status | Details |
|---|---|---|
| Tool 1 `evaluate_birthright` | ✅ Complete | Salesforce vs Auth0 birthright comparison, multi-persona support, edge cases |
| Tool 3 `classify_fix_complexity` | ✅ Complete | SIMPLE_FIX vs ESCALATE_TO_L2 classification |
| Tool 4 `identify_failing_workflow` | ✅ Enhanced | 9 live Auth0 Actions monitored for code drift (was placeholder, now live) |
| Tool 2 `query_knowledge_base` | ✅ Live | Bedrock KB `O4XMWIIEHS` (ciam-kb), 27 docs, S3 data source synced |
| Unit tests | ✅ 60/60 passing | Complete spec coverage + edge cases, K8 integration tests |
| Deployed to AgentCore | ✅ **LIVE (v14)** | Runtime: `arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamKnowledgeBaseAgent-VdVt7x7TZ1` |
| **Fixed:** Python 3.13 ABI | ✅ **v13→v14** | Added agentcore.json runtimeVersion + pyproject.toml (was silently packing cp314 wheels) |
| Wired into orchestrator | ✅ **INTEGRATED** | `AGENT_REGISTRY["agent_4"]` configured, routing_flag: `invoke_agent_4`, ENABLE_AGENT_4=true (verified on RJT-30, RJT-31) |
| End-to-end verification | ✅ VERIFIED | 4–6s invocation (was 30s timeout before ABI fix), live Auth0 Action drift detection working |

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

## Deployment Status (Live ✅)

**Already done:**
1. ✅ Birthright evaluation logic complete (Salesforce vs Auth0 birthright, multi-persona)
2. ✅ Fix classification implemented and tested
3. ✅ 9 live Auth0 Actions monitored for code drift (NetskopeID-Sync-1/2, Gatekeeper, RBAC-Consolidated, Email Verification v2, Registration-Forms, Account Migration Acknowledgement, Privacy Policy Acknowledgement, MFA-Consolidated)
4. ✅ KB document content in S3 (27 docs synced from CIAM docs)
5. ✅ Deployed to Bedrock AgentCore (v14, live runtime)
6. ✅ Python 3.13 ABI fix (v13→v14: agentcore.json runtimeVersion + pyproject.toml)
7. ✅ Wired into AGENT_REGISTRY with routing_flag: `invoke_agent_4`
8. ✅ End-to-end tested on real tickets (RJT-30, RJT-31)

**Future improvements (not blocking):**
- Expand KB with additional CIAM scenarios
- Monitor for new Auth0 Actions to track
- Provisional birthright/persona table verified against official source (currently working well in practice)

## Running the tests

```bash
cd agents/04-knowledge-base-agent
pip install -r requirements.txt pytest
python -m pytest test_agent4.py -v
```

`conftest.py` stubs `bedrock_agentcore.BedrockAgentCoreApp` for local testing,
same pattern as Agents 2/3. Tool 2's tests mock `requests.post` (not a
boto3 client) to match the raw-HTTP implementation described above.
