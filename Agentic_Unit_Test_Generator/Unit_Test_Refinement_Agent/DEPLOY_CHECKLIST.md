# Deployment Checklist: Unit Test Refinement Agent

**Status**: Code complete, locally tested, ready for deployment  
**Date**: 2026-07-17  
**Branch**: `ns-apanikar/project/unit-test-generation`

## Prerequisites (Before Deployment)

- [ ] **AWS Credentials**: Fresh credentials or OIDC federation role
  - Test: `aws sts get-caller-identity` should succeed
  - Permissions needed: `bedrock-agentcore:*`, `ecr:*`, `iam:*`, `codebuild:*`, `logs:*`

- [ ] **bedrock-agentcore SDK**: Install locally
  - `pip install bedrock-agentcore` (may be internal/private package)
  - If unavailable on PyPI, contact AWS team for installation source

- [ ] **AWS Account Details**:
  - Account ID: `786063285476`
  - Region: `ap-southeast-2`
  - Verify ECR repository access or auto-create permissions

- [ ] **IAM Execution Role**:
  - Role ARN: `arn:aws:iam::786063285476:role/unit-test-refine-agentcore-execution-role`
  - If role doesn't exist, create it with policies from `DEPLOYMENT.md`

## Deployment Steps

### Step 1: Verify Configuration
```bash
cd Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent

# Check .bedrock_agentcore.yaml
cat .bedrock_agentcore.yaml

# Verify agent name is unique
grep "agent_id" .bedrock_agentcore.yaml
# Should be: `agent_id: null` (filled on first deploy)
```

### Step 2: Update Execution Role (if needed)
```bash
# Check if role exists
aws iam get-role --role-name unit-test-refine-agentcore-execution-role

# If missing, create from DEPLOYMENT.md policy
# Update .bedrock_agentcore.yaml with correct role ARN
```

### Step 3: Deploy Agent
```bash
bedrock-agentcore deploy

# Expected output:
# ✓ Dockerfile built
# ✓ Docker image pushed to ECR
# ✓ Agent registered: unit_test_refine_agent-<ID>
# ✓ Runtime ARN: arn:aws:bedrock-agentcore:ap-southeast-2:786063285476:runtime/unit_test_refine_agent-<ID>
```

### Step 4: Capture Runtime ARN
```bash
# Copy the runtime ARN from deploy output, e.g.:
# arn:aws:bedrock-agentcore:ap-southeast-2:786063285476:runtime/unit_test_refine_agent-ABC123

RUNTIME_ARN="arn:aws:bedrock-agentcore:ap-southeast-2:786063285476:runtime/unit_test_refine_agent-<ID>"
```

### Step 5: Update .bedrock_agentcore.yaml
After successful deploy, the file will auto-populate with:
```yaml
bedrock_agentcore:
  agent_id: unit_test_refine_agent-<ID>
  agent_arn: arn:aws:bedrock-agentcore:ap-southeast-2:786063285476:runtime/unit_test_refine_agent-<ID>
```

Commit this:
```bash
git add .bedrock_agentcore.yaml
git commit -m "Update agent ARN after Bedrock deployment"
git push origin ns-apanikar/project/unit-test-generation
```

### Step 6: Set GitHub Variable
In `https://github.com/netSkope/GIS-SecEng-Intern/settings/variables/actions`:
1. Click **New repository variable**
2. Name: `AGENT_REFINEMENT_AGENT_RUNTIME_ARN`
3. Value: (paste the runtime ARN from Step 4)
4. Click **Add variable**

### Step 7: Verify Deployment
```bash
# Test agent locally before CI
python local_test.py \
  Agentic_Unit_Test_Generator/scripts/calculator.py \
  Agentic_Unit_Test_Generator/tests/test_calculator.py \
  --via-github \
  --ref $(git rev-parse HEAD)

# Should output: Status: ok
```

### Step 8: Trigger Workflow
1. Create a test PR with a change to any test file in `Agentic_Unit_Test_Generator/tests/`
2. Leave reviewer feedback on the test file lines
3. Submit review as "Request changes"
4. `refine-unit-test.yml` workflow should trigger automatically
5. Agent refines tests and pushes to PR branch

## Rollback (if needed)

```bash
# Delete agent from Bedrock AgentCore
bedrock-agentcore delete --agent-id unit_test_refine_agent-<ID>

# Delete ECR image
aws ecr delete-repository \
  --repository-name bedrock-agentcore-unit_test_refine_agent \
  --force \
  --region ap-southeast-2

# Revert .bedrock_agentcore.yaml to null agent_id and agent_arn
git checkout Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent/.bedrock_agentcore.yaml
git commit -m "Rollback agent deployment"
```

## Post-Deployment Validation

- [ ] GitHub variable `AGENT_REFINEMENT_AGENT_RUNTIME_ARN` is set
- [ ] Local test with `--via-github` succeeds
- [ ] Test PR triggers `refine-unit-test.yml` workflow on reviewer feedback
- [ ] Refined tests appear in commit on PR branch
- [ ] Test runner workflow (`run-bot-unit-test.yml`) executes refined tests

## Troubleshooting Reference

See `DEPLOYMENT.md` for:
- IAM policy requirements
- SSL/credential errors
- Bedrock invocation errors
- ECR repository issues

## Contact & Notes

- Internal bedrock-agentcore SDK location: (contact AWS team)
- Generator Agent deployed: 2026-07-14 (reference deployment)
- Deployment type: container
- Platform: linux/arm64
