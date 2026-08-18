#!/bin/bash

# Deploy Agent 5 to AWS Bedrock AgentCore using AWS CLI

set -e

AGENT_ID="ciamResponseGenerator-75l4h0HADB"
REGION="us-east-1"
AGENT_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/agent.py"

echo "=================================================="
echo "DEPLOYING AGENT 5 TO AWS BEDROCK AGENTCORE"
echo "=================================================="
echo ""
echo "Agent ID: $AGENT_ID"
echo "Region: $REGION"
echo "File: $AGENT_FILE"
echo ""

# Step 1: Verify file exists
if [ ! -f "$AGENT_FILE" ]; then
    echo "❌ Error: agent.py not found at $AGENT_FILE"
    exit 1
fi

echo "✓ agent.py found ($(wc -c < "$AGENT_FILE") bytes)"
echo ""

# Step 2: Verify AWS CLI is configured
echo "[1/3] Verifying AWS credentials..."
if aws sts get-caller-identity --region "$REGION" > /dev/null 2>&1; then
    ACCOUNT=$(aws sts get-caller-identity --region "$REGION" --query 'Account' --output text)
    USER=$(aws sts get-caller-identity --region "$REGION" --query 'Arn' --output text)
    echo "✓ AWS credentials valid"
    echo "  Account: $ACCOUNT"
    echo "  User: $USER"
else
    echo "❌ AWS credentials failed. Run: aws configure or aws sso login"
    exit 1
fi
echo ""

# Step 3: Check if agent exists
echo "[2/3] Checking agent status..."
AGENT_INFO=$(aws bedrock-agent get-agent \
    --agent-id "$AGENT_ID" \
    --region "$REGION" 2>&1) || true

if echo "$AGENT_INFO" | grep -q "agentName"; then
    AGENT_NAME=$(echo "$AGENT_INFO" | jq -r '.agent.agentName // "Unknown"')
    AGENT_STATUS=$(echo "$AGENT_INFO" | jq -r '.agent.agentStatus // "Unknown"')
    echo "✓ Agent found: $AGENT_NAME"
    echo "  Status: $AGENT_STATUS"
else
    echo "⚠️  Could not retrieve agent status"
    echo "  Continuing with deployment..."
fi
echo ""

# Step 4: Deploy using bedrock-agent update-agent-action-group
echo "[3/3] Deploying Agent 5..."
echo ""

# For Bedrock agents, we need to update via CodeBuild or direct model deployment
# Since Agent 5 is a Python agent running on Bedrock AgentCore, we'll use UpdateAgent

# First, check if there's a source code location we need to update
echo "Attempting to update agent code..."

# Create a temporary manifest with the updated code
MANIFEST_FILE="/tmp/agent5_manifest.json"
cat > "$MANIFEST_FILE" << 'MANIFEST_EOF'
{
  "agentId": "ciamResponseGenerator-75l4h0HADB",
  "agentName": "ciam-response-generator",
  "agentVersion": "v0.2.1-diagnostic"
}
MANIFEST_EOF

# Note: Direct code update via CLI is not straightforward for Bedrock AgentCore
# The agent needs to be redeployed through the service's deployment pipeline
# For now, we'll show the deployment steps

echo ""
echo "=================================================="
echo "DEPLOYMENT INFORMATION"
echo "=================================================="
echo ""
echo "Agent 5 is a Bedrock AgentCore managed service."
echo "Deployment requires one of these approaches:"
echo ""
echo "OPTION 1: Deploy via AWS Bedrock Console (Fastest)"
echo "  1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents"
echo "  2. Click: ciam-response-generator"
echo "  3. Click: Edit or Update Code"
echo "  4. Paste the contents of: $AGENT_FILE"
echo "  5. Click: Save → Deploy"
echo ""
echo "OPTION 2: Deploy from GitHub/CodeCommit (If configured)"
echo "  1. Commit changes: git push"
echo "  2. In Bedrock Console, trigger deployment from repository"
echo ""
echo "OPTION 3: Deploy via CodeBuild"
echo "  aws codebuild start-build --project-name agent5-deploy --region $REGION"
echo ""

# Step 5: Try using bedrock-agentcore UpdateAgent API
echo "[INFO] Attempting direct API update..."

# Try to update the agent with the new code
# This requires the code to be in a deployable format

# For Bedrock managed agents, the best approach is to use UpdateAgent with source
AGENT_UPDATE=$(aws bedrock-agent update-agent \
    --agent-id "$AGENT_ID" \
    --agent-name "ciam-response-generator" \
    --region "$REGION" 2>&1) || true

if echo "$AGENT_UPDATE" | grep -q "agentId"; then
    echo "✓ Agent update initiated"
    echo "  Version: $(echo "$AGENT_UPDATE" | jq -r '.agent.agentVersion // "Unknown"')"
    echo "  Status: $(echo "$AGENT_UPDATE" | jq -r '.agent.agentStatus // "Unknown"')"
else
    echo "⚠️  Standard update didn't work. Agent may need console deployment."
fi

echo ""
echo "=================================================="
echo "NEXT STEPS"
echo "=================================================="
echo ""
echo "1. Deploy via AWS Console (Recommended)"
echo "2. Wait for agent status to show 'Active'"
echo "3. Run the test:"
echo ""
echo "   cd /Users/shristyj/repos/GIS-SecEng-Intern/CIAM-Support-Assistant/orchestrator"
echo "   python3 << 'EOF'"
echo "   from ciam_orchestrator.orchestrator import CIAMOrchestrator"
echo "   from ciam_orchestrator.schemas import JiraTicket"
echo "   ticket = JiraTicket(issue_key='RJT-29', summary='Test: Joshua Fuller', description='Test')"
echo "   result = CIAMOrchestrator().orchestrate(ticket)"
echo "   print(result.synthesis_payload.get('root_cause', {}).get('primary_cause'))"
echo "   EOF"
echo ""
echo "4. Check CloudWatch logs:"
echo "   aws logs tail /aws/bedrock/agents/ciamResponseGenerator-75l4h0HADB --follow --region $REGION"
echo ""
