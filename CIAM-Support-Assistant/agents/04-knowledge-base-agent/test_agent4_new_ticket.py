"""
Agent 4 - New Jira Ticket Test (queries the LIVE deployed AgentCore agent)

Simulates a fresh support ticket arriving at Agent 4, as if it had already
passed through Agent 1 (intent), Agent 2 (database), and Agent 3 (Auth0) --
this is the exact combined payload shape those agents would hand off.

Run from your terminal:
    cd agents/04-knowledge-base-agent
    python3 test_agent4_new_ticket.py
"""

import ast
import base64
import json
import os
import re
import subprocess
import tempfile

AGENT_RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamKnowledgeBaseAgent-VdVt7x7TZ1"
REGION = "us-east-1"


def invoke_live_agent(payload: dict, session_id: str) -> dict:
    """Calls the real deployed AgentCore runtime via AWS CLI and returns the parsed response."""
    encoded_payload = base64.b64encode(json.dumps(payload).encode()).decode()
    out_file = os.path.join(tempfile.gettempdir(), "agent4_new_ticket_response.json")
    padded_session_id = session_id.ljust(33, "0")

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

    sanitized = re.sub(r"datetime\.datetime\([^)]*\)", "None", raw)
    return ast.literal_eval(sanitized)


# ============================================================================
# JIRA TICKET INPUT
# ============================================================================
JIRA_TICKET = {
    "key": "CIAM-4602",
    "summary": "Partner user cannot access Partner Portal",
    "description": (
        "Partner contact jsmith@partnerco.com reports being unable to reach the "
        "Partner Portal despite having an active Auth0 account and a working "
        "login. They can access Community and Support without issue."
    ),
    "reporter": "support-l1@netskope.com",
    "priority": "MEDIUM",
}

print("=" * 80)
print("JIRA TICKET -> AGENT 4 (LIVE AgentCore v7)")
print("=" * 80)
print()
print(f"Ticket: {JIRA_TICKET['key']} - {JIRA_TICKET['summary']}")
print(f"Priority: {JIRA_TICKET['priority']}")
print(f"Description: {JIRA_TICKET['description']}")
print()

# ============================================================================
# Combined payload -- shaped exactly as the orchestrator would build it from
# Agent 1 (intent), Agent 2 (account_status/active_tenant_count), and
# Agent 3 (actual_birthright/entitlements/user_found_in_auth0/last_sync)
# ============================================================================
print("Step 1: Payload assembled from Agents 1/2/3 outputs")
print("-" * 80)

payload = {
    "account_status": "Partner",              # from Agent 2
    "active_tenant_count": 0,                 # from Agent 2 -- partners don't hold tenants
    "actual_birthright": ["Community", "Support"],  # from Agent 3
    "entitlements": [],                       # from Agent 3
    "user_found_in_auth0": True,              # from Agent 3
    "intent": "ACCESS_DENIED",                # from Agent 1
    "last_sync": "2026-08-03T09:00:00Z",      # from Agent 3
    "top_k": 3,
    "raw_input": JIRA_TICKET["description"],
}

print(json.dumps(payload, indent=2))
print()

# ============================================================================
# Invoke the LIVE deployed Agent 4
# ============================================================================
print("Step 2: Invoking live Agent 4 (AgentCore runtime)")
print("-" * 80)

result = invoke_live_agent(payload, "test-ciam-4602-partner-portal")

be = result["birthright_evaluation"]
fc = result["fix_classification"]
wf = result["workflow_identification"]
kb = result["knowledge_base_results"]

print(f"Run ID: {result['run_id']}")
print()

print("Tool 1 - Birthright Evaluation:")
print(f"  Persona: {be['persona']}")
print(f"  Expected: {be['expected_birthright']}")
print(f"  Actual:   {be['actual_birthright']}")
print(f"  Missing:  {be['missing_keywords']}")
print(f"  Extra:    {be['extra_keywords']}")
print()

print("Tool 3 - Fix Classification:")
print(f"  Complexity: {fc['complexity']} ({fc['confidence']} confidence)")
print(f"  Reason: {fc['reason']}")
print(f"  Recommended Actions:")
for i, action in enumerate(fc["recommended_actions"], 1):
    print(f"    {i}. {action}")
print()

print("Tool 4 - Workflow Identification:")
print(f"  Root-cause workflow: {wf.get('workflow_name')}")
print(f"  Enforcement workflow: {wf.get('enforcement_workflow_name')}")
print(f"  Note: {wf['note']}")
print()

print("Tool 2 - Knowledge Base Matches:")
for i, doc in enumerate(kb["relevant_docs"], 1):
    print(f"  [{i}] {doc['title']} (score {doc['relevance_score']:.2f})")
    print(f"      {doc['excerpt'][:150]}...")
print()

print("=" * 80)
print(f"SUMMARY FOR {JIRA_TICKET['key']}")
print("=" * 80)
print(f"Root cause: user missing {be['missing_keywords']} in birthright")
print(f"Fix type: {fc['complexity']}")
print(f"Responsible workflow: {wf.get('workflow_name')} (enforced by {wf.get('enforcement_workflow_name')})")
print("=" * 80)
