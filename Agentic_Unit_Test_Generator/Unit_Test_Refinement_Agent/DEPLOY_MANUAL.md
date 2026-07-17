# Manual Deployment: Unit Test Refinement Agent

**bedrock-agentcore SDK is not available on public PyPI.** Use this guide to deploy manually via AWS CLI + CodeBuild + ECR.

## Prerequisites

✓ AWS credentials configured (`aws sts get-caller-identity` succeeds)  
✓ Code committed to branch  
✓ All files validated (`python validate_structure.py`)

## Manual Deployment Steps

### Step 1: Push Docker Image to ECR

```bash
cd Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent

# Create ECR repository if it doesn't exist
aws ecr create-repository \
  --repository-name bedrock-agentcore-unit_test_refine_agent \
  --region ap-southeast-2 \
  2>/dev/null || echo "Repository already exists"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-southeast-2"
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bedrock-agentcore-unit_test_refine_agent"

# Login to ECR
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ECR_URI

# Build Docker image
docker build -t unit_test_refine_agent:latest .

# Tag for ECR
docker tag unit_test_refine_agent:latest $ECR_URI:latest

# Push to ECR
docker push $ECR_URI:latest

echo "✓ Image pushed to: $ECR_URI:latest"
```

### Step 2: Create IAM Execution Role

```bash
# Create trust policy document
cat > /tmp/trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name unit-test-refine-agentcore-execution-role \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --region ap-southeast-2 \
  2>/dev/null || echo "Role already exists"

# Create and attach policy
cat > /tmp/execution-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:Converse",
      "Resource": "arn:aws:bedrock:ap-southeast-2::foundation-model/anthropic.claude-sonnet-5-v2"
    },
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:ap-southeast-2:786063285476:secret:github-pat-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:ap-southeast-2:*:log-group:/aws/bedrock/agentcore/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name unit-test-refine-agentcore-execution-role \
  --policy-name unit-test-refine-agentcore-policy \
  --policy-document file:///tmp/execution-policy.json
```

### Step 3: Create Bedrock AgentCore Runtime via AWS Console

Since the SDK is unavailable, use the AWS Console:

1. Go to **AWS Console** → **Bedrock** → **AgentCore** → **Agents**
2. Click **Create Agent**
3. Fill in:
   - **Agent Name**: `unit_test_refine_agent`
   - **Description**: `Unit test refinement agent for PR review feedback`
   - **Type**: `Container`
   - **Execution Role**: `arn:aws:iam::786063285476:role/unit-test-refine-agentcore-execution-role`
   - **Container Image URI**: `$ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com/bedrock-agentcore-unit_test_refine_agent:latest`
   - **Port**: `8080` (default)
4. Click **Create**

### Step 4: Get Runtime ARN

After creation, copy the **Runtime ARN** from the agent details page:
```
arn:aws:bedrock-agentcore:ap-southeast-2:786063285476:runtime/unit_test_refine_agent-<ID>
```

### Step 5: Update .bedrock_agentcore.yaml

```bash
# Edit .bedrock_agentcore.yaml and fill in:
# agent_id: unit_test_refine_agent-<ID>
# agent_arn: arn:aws:bedrock-agentcore:ap-southeast-2:786063285476:runtime/unit_test_refine_agent-<ID>

git add .bedrock_agentcore.yaml
git commit -m "Update agent ARN after manual deployment"
```

### Step 6: Set GitHub Variable

In **Settings** → **Variables** → **Actions**:
- Name: `AGENT_REFINEMENT_AGENT_RUNTIME_ARN`
- Value: (paste the Runtime ARN from Step 4)

### Step 7: Test

```bash
python local_test.py \
  Agentic_Unit_Test_Generator/scripts/calculator.py \
  Agentic_Unit_Test_Generator/tests/test_calculator.py \
  --via-github \
  --ref $(git rev-parse HEAD)
```

## Automated Deployment (If CLI Available)

If you can access the bedrock-agentcore SDK:

```bash
# Install SDK
pip install bedrock-agentcore

# Deploy from agent directory
cd Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent
bedrock-agentcore deploy

# Copy runtime ARN from output
# Set GitHub variable with ARN
```

## Troubleshooting

### "bedrock-agentcore not found on PyPI"
→ It's an internal AWS package. Contact your AWS team for installation method or use manual deployment above.

### Docker push fails with authentication error
```bash
# Re-authenticate to ECR
aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin $ECR_URI
```

### Agent creation fails with "Invalid execution role"
→ Wait 30 seconds for IAM policy propagation, then retry.

### "Container image not found" after agent creation
→ Verify image was pushed successfully:
```bash
aws ecr describe-images \
  --repository-name bedrock-agentcore-unit_test_refine_agent \
  --region ap-southeast-2
```

## Cleanup

```bash
# Delete agent (via AWS Console → Bedrock → Agents → Delete)

# Delete ECR image
aws ecr delete-repository \
  --repository-name bedrock-agentcore-unit_test_refine_agent \
  --force \
  --region ap-southeast-2

# Delete IAM role
aws iam delete-role-policy \
  --role-name unit-test-refine-agentcore-execution-role \
  --policy-name unit-test-refine-agentcore-policy

aws iam delete-role \
  --role-name unit-test-refine-agentcore-execution-role
```
