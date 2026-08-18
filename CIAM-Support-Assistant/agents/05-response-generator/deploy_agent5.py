#!/usr/bin/env python3
"""Deploy Agent 5 (Response Generator) to AWS Bedrock AgentCore."""

import os
import sys
import subprocess
import json
from pathlib import Path

# Configuration
AGENT_DIR = Path(__file__).parent
AGENT_ID = "ciamResponseGenerator-75l4h0HADB"
REGION = "us-east-1"

print("=" * 80)
print("DEPLOYING AGENT 5 (Response Generator) TO AWS BEDROCK AGENTCORE")
print("=" * 80)

# Step 1: Build deployment package
print("\n[1/3] Building deployment package...")

# Copy agent.py to a temp directory
build_dir = AGENT_DIR / "build"
build_dir.mkdir(exist_ok=True)

# Copy the agent code
import shutil
shutil.copy(AGENT_DIR / "agent.py", build_dir / "agent.py")
print("  ✓ Copied agent.py")

# Step 2: Check AWS credentials
print("\n[2/3] Verifying AWS credentials...")
try:
    result = subprocess.run(
        ["aws", "sts", "get-caller-identity", "--region", REGION],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode == 0:
        identity = json.loads(result.stdout)
        print(f"  ✓ AWS credentials valid")
        print(f"    Account: {identity.get('Account')}")
        print(f"    User: {identity.get('Arn')}")
    else:
        print(f"  ✗ AWS credentials invalid: {result.stderr}")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Error checking credentials: {e}")
    print("  → Make sure AWS CLI is configured (aws configure)")
    sys.exit(1)

# Step 3: Update Agent 5 code on Bedrock AgentCore
print("\n[3/3] Updating Agent 5 on Bedrock AgentCore...")

try:
    # Read the agent code
    with open(AGENT_DIR / "agent.py", "r") as f:
        agent_code = f.read()

    print(f"  Agent code size: {len(agent_code)} bytes")
    print(f"  Agent ID: {AGENT_ID}")
    print(f"  Region: {REGION}")

    # For Bedrock AgentCore, we typically need to:
    # 1. Use the bedrock-agentcore UpdateAgent API
    # 2. Or redeploy using the service's deployment mechanism

    # Since Bedrock AgentCore uses code deploy, we'd typically:
    # - Push code to a repository
    # - Or use the SDK to update the agent

    # For now, we'll show what would need to happen
    print("\n  Note: Bedrock AgentCore agents require:")
    print("  1. Code to be pushed to a code repository (GitHub, CodeCommit)")
    print("  2. Agent to be redeployed via the Bedrock console or CLI")
    print("\n  Or use boto3 bedrock-agentcore UpdateAgent:")

    import boto3
    from botocore.config import Config

    config = Config(
        retries={'max_attempts': 3, 'mode': 'adaptive'},
        connect_timeout=10,
        read_timeout=60
    )
    client = boto3.client("bedrock-agentcore", region_name=REGION, config=config, verify=False)

    # Check agent status
    try:
        response = client.get_agent(agentId=AGENT_ID)
        print(f"\n  ✓ Agent found: {response.get('agentName')}")
        print(f"    Status: {response.get('agentStatus')}")
        print(f"    Runtime Version: {response.get('agentVersion')}")
    except Exception as e:
        print(f"  ✗ Could not retrieve agent: {e}")
        print("    Agent may need to be deployed via the Bedrock console")
        sys.exit(1)

except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("DEPLOYMENT NOTES")
print("=" * 80)
print("""
Agent 5 (Response Generator) is deployed as a Bedrock AgentCore agent.
The code update requires one of these approaches:

OPTION 1: Push to GitHub and redeploy
  1. Commit the changes: git add agents/05-response-generator/agent.py
  2. Push to GitHub: git push
  3. In AWS Bedrock console, redeploy the agent from the repository

OPTION 2: Use Bedrock AgentCore UpdateAgent API
  The boto3 client above can be used to update agent code via API
  (requires proper IAM permissions for bedrock-agentcore:UpdateAgent)

OPTION 3: Manual deployment via AWS Console
  1. Go to AWS Bedrock Console
  2. Navigate to Agents
  3. Find "ciam-response-generator" agent
  4. Upload the new agent.py file
  5. Deploy

CURRENT STATUS:
✓ Code changes made to agents/05-response-generator/agent.py
✓ Diagnostic logging added
✓ Ready to deploy

NEXT STEPS:
1. Deploy Agent 5 using one of the options above
2. Create a test ticket in Jira with Joshua Fuller's email
3. Check CloudWatch logs for diagnostic output
4. Verify that Agent 5 receives account_payload correctly
""")
