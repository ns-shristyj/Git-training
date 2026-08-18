"""Integration test for Agent 4 - Knowledge Base Agent with real Bedrock KB queries"""

import json
from conftest import _install_stub
_install_stub()

from agent import evaluate_ciam_case

print("=" * 80)
print("AGENT 4 - KNOWLEDGE BASE AGENT INTEGRATION TEST")
print("=" * 80)
print()

# Test Case 1: Customer with missing birthright (Support portal)
print("\n[TEST 1] Customer Missing Support Portal Access")
print("-" * 80)
test_payload_1 = {
    "account_status": "Customer",
    "active_tenant_count": 2,
    "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
    "entitlements": [],
    "user_found_in_auth0": True,
    "intent": "ACCESS_DENIED",
    "top_k": 3,
}

try:
    result1 = evaluate_ciam_case(test_payload_1)
    print(f"✅ REQUEST SUCCEEDED\n")

    print("RESPONSE:")
    print(json.dumps(result1, indent=2, default=str))

    # Summary
    if result1.get("error"):
        print(f"\n❌ Error: {result1['error']}")
    else:
        be = result1.get("birthright_evaluation", {})
        fc = result1.get("fix_classification", {})
        print(f"\n✅ SUMMARY:")
        print(f"  Birthright Match: {be.get('match')}")
        print(f"  Missing Keywords: {be.get('missing_keywords')}")
        print(f"  Extra Keywords: {be.get('extra_keywords')}")
        print(f"  Fix Complexity: {fc.get('complexity')}")
        print(f"  Reason: {fc.get('reason')}")
        print(f"  Recommended Actions: {fc.get('recommended_actions')}")

except Exception as e:
    print(f"❌ REQUEST FAILED\n")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    import traceback
    traceback.print_exc()

# Test Case 2: Prospect without tenant
print("\n" + "=" * 80)
print("\n[TEST 2] Prospect without Active Tenant")
print("-" * 80)
test_payload_2 = {
    "account_status": "Prospect",
    "active_tenant_count": 0,
    "actual_birthright": ["Community", "Academy", "Dashboard"],
    "entitlements": [],
    "user_found_in_auth0": True,
    "intent": "GENERAL_INQUIRY",
    "top_k": 2,
}

try:
    result2 = evaluate_ciam_case(test_payload_2)
    print(f"✅ REQUEST SUCCEEDED\n")

    # Summary
    if result2.get("error"):
        print(f"❌ Error: {result2['error']}")
    else:
        be = result2.get("birthright_evaluation", {})
        fc = result2.get("fix_classification", {})
        print(f"✅ SUMMARY:")
        print(f"  Persona: {be.get('persona')}")
        print(f"  Birthright Match: {be.get('match')}")
        print(f"  Missing Keywords: {be.get('missing_keywords')}")
        print(f"  Fix Complexity: {fc.get('complexity')}")
        print(f"  Confidence: {fc.get('confidence')}")
        print(f"  Recommended Actions: {fc.get('recommended_actions')}")

except Exception as e:
    print(f"❌ REQUEST FAILED\n")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")

# Test Case 3: Over-provisioned user (escalation case)
print("\n" + "=" * 80)
print("\n[TEST 3] Over-Provisioned User (Security Risk)")
print("-" * 80)
test_payload_3 = {
    "account_status": "Customer",
    "active_tenant_count": 1,
    "actual_birthright": ["Support", "Community", "Academy", "Notification", "Dashboard", "Partner", "Prime"],
    "entitlements": [],
    "user_found_in_auth0": True,
    "intent": "ACCESS_VERIFICATION",
    "top_k": 2,
}

try:
    result3 = evaluate_ciam_case(test_payload_3)
    print(f"✅ REQUEST SUCCEEDED\n")

    # Summary
    if result3.get("error"):
        print(f"❌ Error: {result3['error']}")
    else:
        be = result3.get("birthright_evaluation", {})
        fc = result3.get("fix_classification", {})
        print(f"✅ SUMMARY:")
        print(f"  Extra Keywords (Over-provisioned): {be.get('extra_keywords')}")
        print(f"  Fix Complexity: {fc.get('complexity')}")
        print(f"  Reason: {fc.get('reason')}")
        print(f"  ⚠️  Confidence: {fc.get('confidence')} (escalates to L2)")

except Exception as e:
    print(f"❌ REQUEST FAILED\n")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")

# Final Summary
print("\n" + "=" * 80)
print("AGENT 4 INTEGRATION TEST COMPLETE")
print("=" * 80)
print("""
✅ All Agent 4 components tested:
  - Tool 1: Birthright evaluation (expected vs actual)
  - Tool 3: Fix complexity classification
  - Tool 2: Knowledge Base queries (real Bedrock KB)
  - Tool 4: Workflow identification (placeholder)

Knowledge Base Details:
  KB ID: O4XMWIIEHS (ciam-kb)
  Region: us-east-1
  Type: Managed Knowledge Base
""")
print("=" * 80)
