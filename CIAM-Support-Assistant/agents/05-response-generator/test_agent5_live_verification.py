"""
Live verification test for Agent 5 (Response Generator) -- invokes the
ACTUAL deployed Bedrock AgentCore runtime (not a local import).

This is the first real deployment of Agent 5 (2026-08-04). Prior commit
messages claimed it was already deployed and had 22/22 tests passing --
neither was true (see .bedrock_agentcore.yaml for the full story). This
test exists specifically to catch that class of failure again: it invokes
the live ARN, not agent.py imported locally, so a broken deployment can
never again hide behind a passing local test suite.

Run from your terminal:
    cd agents/05-response-generator
    python3 test_agent5_live_verification.py
"""

import ast
import base64
import json
import os
import re
import subprocess
import tempfile
import time
import uuid

AGENT_RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamResponseGenerator-75l4h0HADB"
REGION = "us-east-1"


def invoke_live_agent(payload: dict, session_id: str) -> str:
    """Calls the real deployed AgentCore runtime via AWS CLI and returns the raw response string."""
    encoded_payload = base64.b64encode(json.dumps(payload).encode()).decode()
    out_file = os.path.join(tempfile.gettempdir(), "agent5_live_verification_response.json")

    # Fresh session ID every call -- AgentCore can pin a session ID to a
    # persistent warm container, so reusing one risks talking to a
    # container still running a previously deployed version.
    unique_session_id = f"{session_id}-{uuid.uuid4().hex}-{int(time.time())}"

    result = subprocess.run(
        [
            "aws", "bedrock-agentcore", "invoke-agent-runtime",
            "--agent-runtime-arn", AGENT_RUNTIME_ARN,
            "--runtime-session-id", unique_session_id,
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
        return json.load(f)


print("=" * 80)
print("AGENT 5 -- LIVE DEPLOYED-AGENT VERIFICATION")
print("=" * 80)

payload = {
    "account_payload": {
        "agent": "ciam-database-agent",
        "account_found": True,
        "accounts": [{
            "account_name": "Netskope Customer",
            "account_status": "Customer",
            "customer_status": "ACTIVE",
            "active_tenant_count": 2,
            "tenant_url": "https://customer.netskope.com",
            "sf_user_exists": True,
            "sf_user_active": True,
        }],
        "data_freshness": {"last_synced_at": None, "age_hours": 2.0, "is_stale": False},
        "data_warnings": [],
        "error": None,
    },
    "auth0_payload": {
        "agent": "ciam-auth0-agent",
        "user_found": True,
        "users": [{
            "user_id": "samlp|NSKP-Preview|vshah@netskope.com",
            "email": "vshah@netskope.com",
            "connection": "NSKP-Preview",
            "created_at": "2025-10-28T18:36:53.509Z",
            "last_login": "2026-07-29T14:32:15.000Z",
            "logins_count": 42,
            "birthright": ["Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "last_sync": None,
        }],
        "failed_logins_last_7_days": 0,
        "last_failed_login_reason": None,
        "sync_stale": True,
        "auth0_warnings": [],
        "error": None,
    },
    "kb_payload": {
        "agent": "ciam-knowledge-base-agent",
        "birthright_evaluation": {
            "match": False,
            "persona": "Customer",
            "expected_birthright": ["Community", "Academy", "Support", "Notification", "Dashboard"],
            "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "missing_keywords": ["Support"],
            "extra_keywords": [],
            "explicit_block_detected": False,
            "block_keywords_found": [],
            "no_access_configured": False,
        },
        "fix_classification": {
            "complexity": "SIMPLE_FIX",
            "reason": "Missing entitlements can be safely added.",
            "recommended_actions": ["Add Support to entitlements via Auth0 Management API"],
            "confidence": "HIGH",
        },
        "knowledge_base_results": {
            "relevant_docs": [{
                "title": "portal-access-requirements.md",
                "excerpt": "Support portal requires Support keyword.",
                "relevance_score": 0.75,
            }],
            "similar_past_tickets": [],
        },
        "error": None,
    },
    "ticket_email": "vshah@netskope.com",
    "ticket_intent": "ACCESS_DENIED",
}

print("\nREQUEST: combined Agent 2/3/4 payload for a missing-Support-keyword scenario\n")

raw_response = invoke_live_agent(payload, "test-agent5-live-verify")

print("RAW RESPONSE:")
print(raw_response)
print()

# Hard assertions -- fail loudly if the deployed agent regresses
assert "error=None" in raw_response, f"Expected error=None, got a non-null error in: {raw_response[:300]}"
assert "primary_cause='Missing portal access: Support'" in raw_response
assert "escalation_level='L1_RESOLVABLE'" in raw_response
assert "jira_summary='Missing portal access: Support'" in raw_response

print("✅ All assertions passed:")
print("  - error is None (no synthesis failure)")
print("  - root cause correctly identifies missing Support portal access")
print("  - escalation level is L1_RESOLVABLE (matches Agent 4's SIMPLE_FIX classification)")
print("  - jira_summary is populated and correct")
print()
print("=" * 80)
print("AGENT 5 LIVE VERIFICATION PASSED")
print("=" * 80)
