"""
Live verification test for Agent 4 (Knowledge Base Agent) -- invokes the
ACTUAL deployed Bedrock AgentCore runtime (not a local import), to confirm:

  1. Tool 1 (birthright evaluation) + Tool 3 (fix complexity) work correctly
  2. Tool 2 (KB query) returns curated, code-free summaries for real Auth0
     Action docs -- no literal source code ever reaches the response
  3. Tool 4 (workflow identification) correctly attributes the root cause
     to the real Auth0 Action responsible (NetskopeID-Sync-2 / Gatekeeper)
  4. The post-login execution order doc is retrievable and ranks highly
     for flow-order questions

Run from your terminal (needs AWS credentials + network access this
sandbox doesn't reliably have for auth0.com / large S3 transfers):

    cd agents/04-knowledge-base-agent
    python3 test_agent4_live_verification.py
"""

import ast
import base64
import json
import re
import subprocess
import sys
import tempfile
import os
import time
import uuid

AGENT_RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamKnowledgeBaseAgent-VdVt7x7TZ1"
REGION = "us-east-1"


def invoke_live_agent(payload: dict, session_id: str) -> dict:
    """Calls the real deployed AgentCore runtime via AWS CLI and returns the parsed response."""
    encoded_payload = base64.b64encode(json.dumps(payload).encode()).decode()
    out_file = os.path.join(tempfile.gettempdir(), "agent4_live_verification_response.json")

    # AgentCore can pin a session ID to a persistent warm container (idle
    # timeout 900s) -- always append a fresh unique suffix so re-running
    # this script never risks silently hitting a container still running a
    # previously deployed version. Also satisfies the >= 33 char minimum.
    padded_session_id = f"{session_id}-{uuid.uuid4().hex}-{int(time.time())}"

    result = subprocess.run(
        [
            "aws", "bedrock-agentcore", "invoke-agent-runtime",
            "--agent-runtime-arn", AGENT_RUNTIME_ARN,
            "--runtime-session-id", padded_session_id,
            "--payload", encoded_payload,
            "--region", REGION,
            "--no-verify-ssl",
            out_file,
        ],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"invoke-agent-runtime failed: {result.stderr}")

    with open(out_file) as f:
        raw = json.load(f)

    # The response body is a Python-repr string with embedded
    # datetime.datetime(...) calls, which ast.literal_eval can't parse (it
    # only accepts literals, never a call) -- strip those calls out first
    # rather than eval()'ing the string.
    sanitized = re.sub(r"datetime\.datetime\([^)]*\)", "None", raw)
    return ast.literal_eval(sanitized)


print("=" * 80)
print("AGENT 4 -- LIVE DEPLOYED-AGENT VERIFICATION (AgentCore v7)")
print("=" * 80)

# ============================================================================
# TEST QUERY 1: Missing Support portal -- exercises Tools 1, 3, 4 + code-free KB
# ============================================================================
print("\n[QUERY 1] Missing Support Portal (CIAM-4521 scenario)")
print("-" * 80)

query_1 = {
    "account_status": "Customer",
    "active_tenant_count": 2,
    "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
    "entitlements": [],
    "user_found_in_auth0": True,
    "intent": "ACCESS_DENIED",
    "last_sync": None,
    "top_k": 3,
    "raw_input": "User vshah@netskope.com reports ACCESS_DENIED for Support Portal",
}
print(f"REQUEST: {json.dumps(query_1, indent=2)}")

result_1 = invoke_live_agent(query_1, "test-query-1-missing-support")

be = result_1["birthright_evaluation"]
fc = result_1["fix_classification"]
wf = result_1["workflow_identification"]
kb = result_1["knowledge_base_results"]

print(f"\nRESPONSE:")
print(f"  Missing keywords: {be['missing_keywords']}")
print(f"  Fix complexity: {fc['complexity']} ({fc['confidence']} confidence)")
print(f"  Workflow identified: {wf['workflow_name']} -> enforced by {wf['enforcement_workflow_name']}")
print(f"  KB top match: {kb['relevant_docs'][0]['title']} (score {kb['relevant_docs'][0]['relevance_score']:.2f})")

# Assertions -- fail loudly if the deployed agent regresses
assert be["missing_keywords"] == ["Support"], f"Expected missing Support, got {be['missing_keywords']}"
assert fc["complexity"] == "SIMPLE_FIX", f"Expected SIMPLE_FIX, got {fc['complexity']}"
assert wf["workflow_name"] == "NetskopeID-Sync-2", f"Expected NetskopeID-Sync-2, got {wf['workflow_name']}"
assert wf["enforcement_workflow_name"] == "Gatekeeper"
for doc in kb["relevant_docs"]:
    assert "const " not in doc["excerpt"], f"CODE LEAK in excerpt: {doc['excerpt'][:100]}"
    assert "setAppMetadata" not in doc["excerpt"], f"CODE LEAK in excerpt: {doc['excerpt'][:100]}"
print("  ✅ All assertions passed -- no code leak, correct diagnosis")

# ============================================================================
# TEST QUERY 2: Flow order question -- exercises the new flow-order KB doc
# ============================================================================
print("\n[QUERY 2] Post-Login Flow Order Question")
print("-" * 80)

query_2 = {
    "account_status": "Customer",
    "active_tenant_count": 1,
    "actual_birthright": ["Community", "Academy", "Support", "Notification", "Dashboard"],
    "entitlements": [],
    "user_found_in_auth0": True,
    "intent": "GENERAL_INQUIRY",
    "last_sync": None,
    "top_k": 5,
    "raw_input": "what order do the post-login actions run in and how is birthright calculated at login",
}
print(f"REQUEST raw_input: \"{query_2['raw_input']}\"")

result_2 = invoke_live_agent(query_2, "test-query-2-flow-order")
kb_2 = result_2["knowledge_base_results"]

print(f"\nRESPONSE (top 2 KB matches):")
for i, doc in enumerate(kb_2["relevant_docs"][:2], 1):
    print(f"  [{i}] {doc['title']} (score {doc['relevance_score']:.2f})")
    print(f"      {doc['excerpt'][:150]}...")

assert kb_2["relevant_docs"][0]["title"] == "auth0-post-login-flow-order.md", (
    f"Expected flow-order doc as top match, got {kb_2['relevant_docs'][0]['title']}"
)
assert kb_2["relevant_docs"][0]["relevance_score"] > 0.8, "Expected high relevance for direct flow-order question"
for doc in kb_2["relevant_docs"]:
    assert "function(" not in doc["excerpt"] and "exports." not in doc["excerpt"], (
        f"CODE LEAK in excerpt: {doc['excerpt'][:100]}"
    )
print("  ✅ All assertions passed -- flow-order doc ranks top, no code leak")

print("\n" + "=" * 80)
print("ALL LIVE VERIFICATION CHECKS PASSED")
print("=" * 80)
