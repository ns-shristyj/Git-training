# Deployment Guide: Unit Test Refinement Agent

## Prerequisites

1. **AWS Account Access**: Credentials or OIDC role with permissions to:
   - `bedrock-agentcore:*` (agent creation, deployment, invocation)
   - `ecr:*` (ECR repository management)
   - `iam:*` (IAM role creation/assumption)
   - `codebuild:*` (CodeBuild project management)
   - `logs:*` (CloudWatch Logs)

2. **Bedrock AgentCore SDK Installed**:
   ```bash
   pip install bedrock-agentcore
   ```

3. **AWS CLI v2** configured with appropriate credentials or OIDC federation.

## Deployment Steps

### Step 1: Configure AWS Credentials
```bash
# Option A: Use AWS CLI configured profile
aws configure

# Option B: Use IAM role via OIDC (for CI/CD)
# Set up AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE, etc.
```

### Step 2: Update Execution Role & ECR Repository

Edit `.bedrock_agentcore.yaml` and set:
- `execution_role`: ARN of IAM role for agent execution (must have `secretsmanager:GetSecretValue` for GitHub PAT + `bedrock:Converse`)
- `ecr_repository`: ECR repo URL for Docker image storage
- `account`: AWS account ID (default: `786063285476`)
- `region`: AWS region (default: `ap-southeast-2`)

### Step 3: Deploy the Agent
```bash
cd Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent

# Deploy using bedrock-agentcore CLI
bedrock-agentcore deploy

# You should see output like:
# ✓ Agent created: unit_test_refine_agent-<ID>
# ✓ Docker image pushed to ECR
# ✓ Runtime ARN: arn:aws:bedrock-agentcore:ap-southeast-2:786063285476:runtime/unit_test_refine_agent-<ID>
```

### Step 4: Update GitHub Variables
After deployment, set these in the GitHub repo:
- `AGENT_REFINEMENT_AGENT_RUNTIME_ARN`: The runtime ARN from Step 3
- Ensure `GITHUB_PAT_SECRET_ARN` points to the AWS Secrets Manager secret containing your GitHub PAT

### Step 5: Verify Deployment
```bash
# Test locally first (fastest iteration):
python local_test.py <source_file> <test_file> [--failure-logs <path>]

# Example:
python local_test.py my_module.py Agentic_Unit_Test_Generator/tests/test_my_module.py
```

## Execution Role IAM Policy

The agent execution role must have (at minimum):
```json
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
      "Resource": "<GITHUB_PAT_SECRET_ARN>"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:ap-southeast-2:*:log-group:/aws/bedrock/agentcore/*"
    }
  ]
}
```

## Troubleshooting

### Issue: `bedrock-agentcore: command not found`
```bash
# Install or reinstall the SDK
pip install --upgrade bedrock-agentcore
```

### Issue: ECR repository does not exist
```bash
# The SDK can auto-create if you set:
# In .bedrock_agentcore.yaml:
# ecr_auto_create: true
```

### Issue: Authorization errors during deployment
```bash
# Verify AWS credentials are loaded
aws sts get-caller-identity

# Ensure the role has necessary permissions (see Execution Role section above)
```

### Issue: Docker build fails
```bash
# Verify Dockerfile and requirements.txt are present
ls -la Dockerfile requirements.txt

# Build locally to test:
docker build -t unit_test_refine_agent:latest .
```

## CI Integration

Once deployed, update `.github/workflows/refine-unit-test.yml`:
1. Ensure `AGENT_REFINEMENT_AGENT_RUNTIME_ARN` is set in GitHub variables
2. The workflow will invoke the agent via `scripts/refine_unit_test.py`
3. No further manual steps needed — the workflow handles the rest

## Rollback / Undeploy

To delete the agent from Bedrock AgentCore:
```bash
# List deployed agents
bedrock-agentcore list

# Delete specific agent
bedrock-agentcore delete --agent-id <agent_id>
```

Note: You may also want to delete the associated ECR repository and IAM role if they're no longer needed.
