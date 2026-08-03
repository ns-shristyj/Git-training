"""
Agent 4 integration test using realistic Jira ticket format
Tests end-to-end flow: Jira ticket → Agent 4 analysis → KB results
"""

import json
from conftest import _install_stub
_install_stub()

from agent import evaluate_ciam_case

# ============================================================================
# JIRA TICKET FORMAT - CIAM-4521
# ============================================================================
JIRA_TICKET = {
    "key": "CIAM-4521",
    "summary": "User unable to access Support Portal",
    "description": """
User vshah@netskope.com reports ACCESS_DENIED error when attempting to access
Support Portal. User can access Community and Academy portals without issue.

Recent login attempt timestamp: 2026-07-29 14:32:15 UTC
User connection: NSKP-Preview (federated)
Account status: Customer (2 active tenants)

Error message from portal: "Insufficient permissions. Required keyword: Support"
""",
    "reporter": "support-l1@netskope.com",
    "assignee": "ciam-l1-agent",
    "priority": "HIGH",
    "status": "IN_PROGRESS",
    "created": "2026-07-29T14:35:00Z",
    "environment": "Production",
    "labels": ["access-denied", "portal-access", "birthright"],
}

print("=" * 80)
print("JIRA TICKET → AGENT 4 ANALYSIS")
print("=" * 80)
print()
print(f"Ticket: {JIRA_TICKET['key']}")
print(f"Summary: {JIRA_TICKET['summary']}")
print(f"Priority: {JIRA_TICKET['priority']}")
print(f"Reporter: {JIRA_TICKET['reporter']}")
print()

# ============================================================================
# EXTRACT DATA FROM JIRA TICKET → AGENT 4 PAYLOAD
# ============================================================================
print("Step 1: Parse Jira Ticket and Extract CIAM Data")
print("-" * 80)

# This is how the orchestrator would map Jira data to Agent 4 input
agent4_payload = {
    "account_status": "Customer",  # Extracted from description
    "active_tenant_count": 2,      # Extracted from description
    "actual_birthright": [         # From Auth0 (Agent 3 output)
        "Community",
        "Academy",
        "Notification",
        "Dashboard"
    ],
    "entitlements": [],            # No compensating entitlements
    "user_found_in_auth0": True,   # User found (vshah@netskope.com)
    "intent": "ACCESS_DENIED",     # From error message
    "last_sync": None,             # Sync metadata from Agent 3
    "top_k": 5,                    # Retrieve 5 KB docs
    "raw_input": JIRA_TICKET["description"],  # Full ticket context
}

print(f"✅ Extracted from Jira ticket {JIRA_TICKET['key']}:")
print(f"   Account Status: {agent4_payload['account_status']}")
print(f"   Active Tenants: {agent4_payload['active_tenant_count']}")
print(f"   Actual Birthright: {agent4_payload['actual_birthright']}")
print(f"   User Found in Auth0: {agent4_payload['user_found_in_auth0']}")
print(f"   Intent: {agent4_payload['intent']}")
print()

# ============================================================================
# INVOKE AGENT 4
# ============================================================================
print("Step 2: Invoke Agent 4 (Knowledge Base Agent)")
print("-" * 80)

try:
    result = evaluate_ciam_case(agent4_payload)

    # Extract key results
    be = result.get("birthright_evaluation", {})
    fc = result.get("fix_classification", {})
    kb = result.get("knowledge_base_results", {})
    wf = result.get("workflow_identification", {})

    print(f"✅ Agent 4 Analysis Complete (Run ID: {result['run_id']})")
    print()

    # ========================================================================
    # TOOL 1: BIRTHRIGHT EVALUATION
    # ========================================================================
    print("Step 3a: Tool 1 - Birthright Evaluation")
    print("-" * 80)
    print(f"Persona: {be.get('persona')}")
    print(f"Expected Birthright: {be.get('expected_birthright')}")
    print(f"Actual Birthright: {be.get('actual_birthright')}")
    print(f"Match: {be.get('match')}")
    print(f"Missing Keywords: {be.get('missing_keywords')}")
    print(f"Extra Keywords: {be.get('extra_keywords')}")
    print(f"Sync Metadata:")
    print(f"  - Never Ran: {be.get('sync_never_ran')}")
    print(f"  - Stale: {be.get('sync_stale')}")
    print()

    # ========================================================================
    # TOOL 3: FIX COMPLEXITY CLASSIFICATION
    # ========================================================================
    print("Step 3b: Tool 3 - Fix Complexity Classification")
    print("-" * 80)
    print(f"Complexity Level: {fc.get('complexity')}")
    print(f"Confidence: {fc.get('confidence')}")
    print(f"Reason: {fc.get('reason')}")
    print(f"Recommended Actions:")
    for i, action in enumerate(fc.get('recommended_actions', []), 1):
        print(f"  {i}. {action}")
    print()

    # ========================================================================
    # TOOL 2: KNOWLEDGE BASE QUERIES
    # ========================================================================
    print("Step 3c: Tool 2 - Knowledge Base Query Results")
    print("-" * 80)
    relevant_docs = kb.get('relevant_docs', [])
    past_tickets = kb.get('similar_past_tickets', [])

    if relevant_docs:
        print(f"✅ Found {len(relevant_docs)} relevant documents:")
        for i, doc in enumerate(relevant_docs, 1):
            print(f"\n  [{i}] {doc.get('title')}")
            print(f"      Score: {doc.get('relevance_score', 'N/A'):.2f}")
            print(f"      URL: {doc.get('url')}")
            excerpt = doc.get('excerpt', '')
            preview = excerpt[:150] + "..." if len(excerpt) > 150 else excerpt
            print(f"      Preview: {preview}")
    else:
        print(f"⚠️  No relevant documents found")

    if past_tickets:
        print(f"\n✅ Found {len(past_tickets)} similar past tickets:")
        for ticket in past_tickets:
            print(f"  - {ticket}")
    else:
        print(f"\n⚠️  No similar past tickets found")
    print()

    # ========================================================================
    # TOOL 4: WORKFLOW IDENTIFICATION (STUB)
    # ========================================================================
    print("Step 3d: Tool 4 - Workflow Identification")
    print("-" * 80)
    print(f"Status: {wf.get('note', 'N/A')}")
    print()

    # ========================================================================
    # FINAL RECOMMENDATION
    # ========================================================================
    print("=" * 80)
    print("FINAL RECOMMENDATION FOR JIRA TICKET")
    print("=" * 80)
    print()
    print(f"Ticket: {JIRA_TICKET['key']}")
    print(f"Issue: {JIRA_TICKET['summary']}")
    print()
    print(f"Diagnosis:")
    print(f"  Root Cause: User missing '{be.get('missing_keywords')[0]}' in birthright")
    print(f"  Persona: {be.get('persona')}")
    print(f"  Fix Type: {fc.get('complexity')}")
    print()
    print(f"Recommended L1 Resolution:")
    for action in fc.get('recommended_actions', []):
        print(f"  • {action}")
    print()
    print(f"Knowledge Base Reference:")
    if relevant_docs:
        print(f"  See: {relevant_docs[0].get('title')}")
        print(f"  URL: {relevant_docs[0].get('url')}")
    print()
    print(f"Next Steps:")
    print(f"  1. Apply recommended fix")
    print(f"  2. Verify user regains access to Support Portal")
    print(f"  3. Monitor next sync to confirm birthright recalculation")
    print(f"  4. Close ticket with resolution documented")
    print()
    print("=" * 80)

except Exception as e:
    print(f"❌ Agent 4 invocation failed:")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    import traceback
    traceback.print_exc()
