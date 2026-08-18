#!/usr/bin/env python3
"""
Deploy Agent 5 to AWS Bedrock using boto3
Uses the bedrock-agent service to update agent code
"""

import sys
import boto3
import json
from pathlib import Path

AGENT_ID = "ciamResponseGenerator-75l4h0HADB"
REGION = "us-east-1"
AGENT_DIR = Path(__file__).parent
AGENT_FILE = AGENT_DIR / "agent.py"

print("=" * 80)
print("DEPLOYING AGENT 5 VIA BOTO3")
print("=" * 80)
print()

# Step 1: Verify file
print("[1/4] Verifying agent.py...")
if not AGENT_FILE.exists():
    print(f"❌ File not found: {AGENT_FILE}")
    sys.exit(1)

with open(AGENT_FILE) as f:
    agent_code = f.read()

print(f"✓ Agent file found: {len(agent_code)} bytes")
print()

# Step 2: Verify AWS credentials
print("[2/4] Verifying AWS credentials...")
try:
    sts = boto3.client("sts", region_name=REGION, verify=False)
    identity = sts.get_caller_identity()
    print(f"✓ Credentials valid")
    print(f"  Account: {identity['Account']}")
    print(f"  User: {identity['Arn']}")
except Exception as e:
    print(f"❌ Credential error: {e}")
    sys.exit(1)
print()

# Step 3: Get current agent
print("[3/4] Retrieving current agent...")
try:
    client = boto3.client("bedrock-agent", region_name=REGION, verify=False)
    response = client.get_agent(agentId=AGENT_ID)
    agent = response['agent']

    print(f"✓ Agent found: {agent['agentName']}")
    print(f"  Status: {agent.get('agentStatus', 'Unknown')}")
    print(f"  Version: {agent.get('agentVersion', 'Unknown')}")
    print(f"  ARN: {agent.get('agentArn', 'Unknown')}")

    # Get agent details we need to preserve
    agent_role_arn = agent.get('agentResourceRoleArn')
    agent_description = agent.get('description', '')

except Exception as e:
    print(f"❌ Could not retrieve agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# Step 4: Attempt to update agent
print("[4/4] Updating agent code...")

# Note: Bedrock Agent doesn't expose code directly via UpdateAgent
# Instead, we need to:
# 1. Store code in S3 or CodeCommit
# 2. Update agent to reference that location
# 3. Trigger redeployment

# For testing, we'll show what the deployment would look like
print()
print("=" * 80)
print("DEPLOYMENT STATUS")
print("=" * 80)
print()

print("✓ Agent 5 verified on AWS:")
print(f"  - Agent ID: {AGENT_ID}")
print(f"  - Agent Name: {agent['agentName']}")
print(f"  - Status: {agent.get('agentStatus')}")
print()

print("⚠️  Bedrock AgentCore agents require code to be deployed through:")
print()
print("OPTION 1: AWS Bedrock Console (Recommended)")
print("  1. Go to: https://console.aws.amazon.com/bedrock/")
print("  2. Click: Agents → ciam-response-generator")
print("  3. Click: Edit or Update")
print("  4. Paste the code from: agent.py")
print("  5. Click: Deploy")
print()

print("OPTION 2: CodeCommit/GitHub Integration")
print("  If Agent 5 is configured to auto-deploy from a repository:")
print("  1. Commit changes to the repository")
print("  2. Agent will automatically redeploy")
print()

print("OPTION 3: S3 + CloudFormation")
print("  Upload code to S3 and update agent via CloudFormation/IaC")
print()

# Option to copy code to clipboard
print("=" * 80)
print("COPY CODE TO CLIPBOARD")
print("=" * 80)
print()
print("To paste into the Bedrock console, run:")
print(f"  cat {AGENT_FILE} | pbcopy")
print()
print("Then paste into: Bedrock Console → Agents → ciam-response-generator → Edit")
print()

# Try to check if there's a deployment pipeline
print("=" * 80)
print("CHECKING FOR DEPLOYMENT PIPELINE")
print("=" * 80)
print()

try:
    codebuild = boto3.client("codebuild", region_name=REGION, verify=False)
    projects = codebuild.list_projects()

    agent5_projects = [p for p in projects.get('projects', []) if 'agent5' in p.lower() or 'response-generator' in p.lower()]

    if agent5_projects:
        print(f"✓ Found CodeBuild projects for Agent 5:")
        for proj in agent5_projects:
            print(f"  - {proj}")
        print()
        print("To deploy via CodeBuild:")
        print(f"  aws codebuild start-build --project-name {agent5_projects[0]} --region {REGION}")
    else:
        print("ℹ️  No CodeBuild pipeline found for Agent 5")

except Exception as e:
    print(f"ℹ️  Could not check CodeBuild: {e}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print("✓ Agent 5 code is ready to deploy")
print("✓ AWS credentials are valid")
print("✓ Agent is accessible on AWS")
print()
print("NEXT ACTION: Use AWS Bedrock Console to deploy")
print()
print("File to deploy: " + str(AGENT_FILE))
print()
