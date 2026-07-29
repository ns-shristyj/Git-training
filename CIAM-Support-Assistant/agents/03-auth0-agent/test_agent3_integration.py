"""Integration test for Agent 3 - uses REAL Auth0 credentials from Secrets Manager"""

import json
import sys
from conftest import _install_stub
_install_stub()

from agent import fetch_auth0_data

# Test with a real email to see actual Auth0 data
TEST_EMAIL = "vshah@netskope.com"  # Real Netskope user for integration testing

print("=" * 80)
print("AGENT 3 - REAL AUTH0 INTEGRATION TEST")
print("=" * 80)
print(f"\nTest: Fetching real Auth0 data for {TEST_EMAIL}")
print(f"Using credentials from: AWS Secrets Manager (ciam-agent/auth0)")
print()

try:
    result = fetch_auth0_data({"email": TEST_EMAIL})

    print("✅ REQUEST SUCCEEDED\n")
    print("RESPONSE:")
    print("-" * 80)
    print(json.dumps(result, indent=2, default=str))
    print("-" * 80)

    # Parse and summarize
    print("\nSUMMARY:")
    print(f"  User Found: {result.get('user_found', False)}")
    print(f"  Number of Users: {len(result.get('users', []))}")
    if result.get('users'):
        user = result['users'][0]
        print(f"  User ID: {user.get('user_id')}")
        print(f"  Email: {user.get('email')}")
        print(f"  Connection: {user.get('connection')}")
        print(f"  Birthright: {user.get('birthright')}")
        print(f"  Entitlements: {user.get('entitlements')}")
        print(f"  Last Login: {user.get('last_login')}")
        print(f"  Logins Count: {user.get('logins_count')}")
        print(f"  Sync Status: {'STALE' if result.get('sync_stale') else 'FRESH'}")

    print(f"  Login History Events: {len(result.get('login_history', []))}")
    print(f"  Failed Logins (7 days): {result.get('failed_logins_last_7_days', 0)}")
    print(f"  Error: {result.get('error', 'None')}")

    if result.get('auth0_warnings'):
        print(f"  Warnings: {result.get('auth0_warnings')}")

except Exception as e:
    print(f"❌ REQUEST FAILED\n")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
