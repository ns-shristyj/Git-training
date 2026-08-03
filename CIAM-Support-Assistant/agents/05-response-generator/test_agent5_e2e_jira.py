"""
End-to-End Integration Test: Agents 2-5 with Jira Ticket
Simulates complete orchestrator flow: Jira → Agent 2 → Agent 3 → Agent 4 → Agent 5
"""

import json
import sys
from datetime import datetime, timezone, timedelta

# Install bedrock_agentcore stub for testing
import types
if "bedrock_agentcore" not in sys.modules:
    module = types.ModuleType("bedrock_agentcore")
    class BedrockAgentCoreApp:
        def __init__(self, **kwargs):
            pass
        def agent_handler(self, func):
            return func
        def run(self):
            pass
    module.BedrockAgentCoreApp = BedrockAgentCoreApp
    sys.modules["bedrock_agentcore"] = module

from agent import handle_response_generation

# ============================================================================
# JIRA TICKET INPUT
# ============================================================================
JIRA_TICKET = {
    "key": "CIAM-4521",
    "summary": "User unable to access Support Portal",
    "reporter": "support-l1@netskope.com",
    "priority": "HIGH",
}

TICKET_EMAIL = "vshah@netskope.com"

print("=" * 80)
print("END-TO-END TEST: JIRA TICKET → AGENTS 2-5 SYNTHESIS")
print("=" * 80)
print()
print(f"Jira Ticket: {JIRA_TICKET['key']} - {JIRA_TICKET['summary']}")
print(f"User Email: {TICKET_EMAIL}")
print()

# ============================================================================
# AGENT 2 OUTPUT (Database Records)
# ============================================================================
print("Step 1: Agent 2 - Database Agent (Account Lookup)")
print("-" * 80)

agent2_output = {
    "schema_version": "1.0",
    "spec_id": "SPEC-CIAM-0002",
    "agent": "ciam-database-agent",
    "run_id": "agent2-run-001",
    "fetched_at": datetime.now(timezone.utc).isoformat(),
    "account_found": True,
    "accounts": [
        {
            "account_name": "Netskope Customer Account",
            "account_status": "Customer",
            "customer_status": "ACTIVE",
            "active_tenant_count": 2,
            "tenant_url": "https://customer.netskope.com",
            "sf_user_exists": True,
            "sf_user_active": True,
        }
    ],
    "data_freshness": {
        "last_synced_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "age_hours": 2.0,
        "is_stale": False,
    },
    "data_warnings": [],
    "error": None,
}

print(f"✅ Account Found: {agent2_output['account_found']}")
print(f"   Status: {agent2_output['accounts'][0]['account_status']}")
print(f"   Active Tenants: {agent2_output['accounts'][0]['active_tenant_count']}")
print(f"   Salesforce User: {agent2_output['accounts'][0]['sf_user_exists']}")
print()

# ============================================================================
# AGENT 3 OUTPUT (Auth0 User Data)
# ============================================================================
print("Step 2: Agent 3 - Auth0 Agent (User Metadata)")
print("-" * 80)

agent3_output = {
    "schema_version": "1.0",
    "spec_id": "SPEC-CIAM-0003",
    "agent": "ciam-auth0-agent",
    "run_id": "agent3-run-001",
    "fetched_at": datetime.now(timezone.utc).isoformat(),
    "user_found": True,
    "users": [
        {
            "user_id": "samlp|NSKP-Preview|vshah@netskope.com",
            "email": TICKET_EMAIL,
            "connection": "NSKP-Preview",
            "connection_priority": 1,
            "selected": True,
            "created_at": "2025-10-28T18:36:53.509Z",
            "last_login": "2026-07-29T14:32:15.000Z",
            "logins_count": 42,
            "birthright": ["Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "last_sync": None,
            "last_daily_sync": None,
        }
    ],
    "login_history": [],
    "failed_logins_last_7_days": 0,
    "last_failed_login_reason": None,
    "sync_stale": True,
    "sync_stale_reason": "sync_has_never_run",
    "auth0_warnings": [],
    "error": None,
}

print(f"✅ User Found: {agent3_output['user_found']}")
print(f"   User ID: {agent3_output['users'][0]['user_id']}")
print(f"   Connection: {agent3_output['users'][0]['connection']}")
print(f"   Birthright: {agent3_output['users'][0]['birthright']}")
print(f"   Last Login: {agent3_output['users'][0]['last_login']}")
print(f"   Sync Status: {'STALE (never ran)' if agent3_output['sync_stale'] else 'FRESH'}")
print()

# ============================================================================
# AGENT 4 OUTPUT (Knowledge Base Analysis)
# ============================================================================
print("Step 3: Agent 4 - Knowledge Base Agent (Analysis)")
print("-" * 80)

agent4_output = {
    "schema_version": "1.0",
    "spec_id": "SPEC-CIAM-0004",
    "agent": "ciam-knowledge-base-agent",
    "run_id": "agent4-run-001",
    "evaluated_at": datetime.now(timezone.utc).isoformat(),
    "birthright_evaluation": {
        "match": False,
        "persona": "Customer",
        "expected_birthright": ["Community", "Academy", "Support", "Notification", "Dashboard"],
        "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
        "entitlements": [],
        "missing_keywords": ["Support"],
        "extra_keywords": [],
        "entitlements_compensate": False,
        "explicit_block_detected": False,
        "block_keywords_found": [],
        "no_access_configured": False,
        "birthright_correct_but_access_denied": False,
        "sync_never_ran": True,
        "sync_stale": False,
    },
    "fix_classification": {
        "complexity": "SIMPLE_FIX",
        "reason": "Missing entitlements can be safely added; no over-provisioning or provisioning issues detected.",
        "recommended_actions": [
            "Add ['Support'] to entitlements array via Auth0 Management API",
            "Verify access after update",
            "Monitor next sync to confirm birthright recalculation does not remove entitlement",
        ],
        "confidence": "HIGH",
    },
    "knowledge_base_results": {
        "relevant_docs": [
            {
                "title": "portal-access-requirements.md",
                "url": "https://ciam-agent4-kb-docs-786063285476-us-east-1.s3.amazonaws.com/docs/portal-access-requirements.md",
                "excerpt": "Support portal access requires 'Support' keyword in birthright for personas: Customer, Partner, Prospect (w/ Tenant)",
                "relevance_score": 0.84,
            },
            {
                "title": "birthright-entitlement-matrix.md",
                "url": "https://ciam-agent4-kb-docs-786063285476-us-east-1.s3.amazonaws.com/docs/birthright-entitlement-matrix.md",
                "excerpt": "Customer personas should have: Community, Academy, Support, Notification, Dashboard",
                "relevance_score": 0.79,
            },
        ],
        "similar_past_tickets": [
            {
                "ticket_key": "CIAM-4201",
                "summary": "Customer missing Support portal after account upgrade",
                "resolution": "Added Support keyword to birthright",
                "relevance_score": 0.81,
            }
        ],
    },
    "workflow_identification": {
        "workflow_identified": False,
        "workflow_name": None,
        "workflow_script_ref": None,
        "note": "Auth0 workflow scripts not yet provided -- placeholder only",
    },
    "error": None,
}

print(f"✅ Birthright Match: {agent4_output['birthright_evaluation']['match']}")
print(f"   Missing: {agent4_output['birthright_evaluation']['missing_keywords']}")
print(f"   Complexity: {agent4_output['fix_classification']['complexity']}")
print(f"   Confidence: {agent4_output['fix_classification']['confidence']}")
print(f"   KB Docs Found: {len(agent4_output['knowledge_base_results']['relevant_docs'])}")
print(f"   Similar Tickets: {len(agent4_output['knowledge_base_results']['similar_past_tickets'])}")
print()

# ============================================================================
# AGENT 5 SYNTHESIS
# ============================================================================
print("Step 4: Agent 5 - Response Generator (Synthesis)")
print("-" * 80)

agent5_payload = {
    "account_payload": agent2_output,
    "auth0_payload": agent3_output,
    "kb_payload": agent4_output,
    "ticket_email": TICKET_EMAIL,
    "ticket_intent": "ACCESS_DENIED",
    "jira_ticket_key": JIRA_TICKET["key"],
}

try:
    result = handle_response_generation(agent5_payload)

    print(f"✅ SYNTHESIS COMPLETE\n")

    # Convert Pydantic model to dict
    result_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict()

    # Extract nested objects
    root_cause = result_dict.get('root_cause', {})
    resolution = result_dict.get('resolution_path', {})
    metadata = result_dict.get('metadata', {})
    similar_cases = result_dict.get('similar_past_cases', [])

    # Parse result
    print("ROOT CAUSE DIAGNOSIS")
    print("-" * 80)
    print(f"Summary: {root_cause.get('summary')}")
    print(f"Evidence: {root_cause.get('evidence')}")
    print(f"Confidence: {root_cause.get('confidence_determination')}")
    print()

    print("RECOMMENDED RESOLUTION")
    print("-" * 80)
    print(f"Escalation Level: {resolution.get('escalation_level')}")
    print(f"Estimated Time: {resolution.get('estimated_resolution_time')}")
    print(f"Actions:")
    actions = resolution.get('actions', [])
    for i, action in enumerate(actions, 1):
        print(f"  {i}. [{action.get('priority')}] {action.get('action')}")
        print(f"     Rationale: {action.get('rationale')}")
        print(f"     Complexity: {action.get('complexity')}")
    print()

    print("DATA QUALITY")
    print("-" * 80)
    print(f"Completeness: {metadata.get('completeness')}")
    print(f"Data Freshness: {metadata.get('data_freshness_assessment')}")
    print(f"Warnings: {metadata.get('quality_warnings', [])}")
    print()

    print("JIRA TICKET UPDATE")
    print("-" * 80)
    print(f"Title: {result_dict.get('jira_summary')}")
    print(f"Description: {result_dict.get('jira_description')}")
    print()

    print("SIMILAR PAST CASES")
    print("-" * 80)
    if similar_cases:
        for case in similar_cases:
            print(f"  • {case.get('case_key')}: {case.get('summary')}")
            print(f"    Resolution: {case.get('resolution')}")
    else:
        print("  No similar past cases found")
    print()

    # ====================================================================
    # FINAL SUMMARY
    # ====================================================================
    print("=" * 80)
    print("FINAL RESOLUTION FOR JIRA TICKET")
    print("=" * 80)
    print()
    print(f"Ticket: {JIRA_TICKET['key']} - {JIRA_TICKET['summary']}")
    print(f"User: {TICKET_EMAIL}")
    print()
    print("ROOT CAUSE:")
    print(f"  {root_cause.get('summary')}")
    print(f"  Evidence: {root_cause.get('evidence')}")
    print(f"  Confidence: {root_cause.get('confidence_determination')}")
    print()
    print("RECOMMENDED ACTIONS:")
    for i, action in enumerate(actions, 1):
        print(f"  {i}. {action.get('action')}")
        print(f"     ({action.get('complexity')} - ~{action.get('estimated_effort')})")
    print()
    print("ESCALATION:")
    print(f"  Level: {resolution.get('escalation_level')}")
    print(f"  Estimated Time: {resolution.get('estimated_resolution_time')}")
    print()
    print("FOR JIRA TICKET:")
    print(f"  Summary: {result_dict.get('jira_summary')}")
    print()
    print("=" * 80)

except Exception as e:
    print(f"❌ Agent 5 synthesis failed:")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    import traceback
    traceback.print_exc()
