# Agent 5 Deployment Guide

**Status:** Ready for Bedrock AgentCore Deployment  
**Version:** 0.2.0  
**Spec:** SPEC-CIAM-0005

---

## Prerequisites

- ✅ AWS CLI configured with appropriate credentials
- ✅ CDK installed (`npm install -g aws-cdk`)
- ✅ Python 3.9+ with required dependencies
- ✅ Bedrock AgentCore access (requires preview signup)

---

## Step 1: Deploy Infrastructure (CDK)

### 1.1 Prepare CDK Stack

```bash
cd infra/aws/ciam-response-generator

# Install CDK dependencies
npm install

# Synthesize CloudFormation template
cdk synth
```

### 1.2 Deploy to AWS

```bash
# Deploy the stack
cdk deploy \
  --require-approval=always \
  --context environment=prod

# Outputs will include:
# - Agent5FunctionArn
# - Agent5FunctionName
# - Agent5LogGroup
# - Agent5ExecutionRoleArn
```

**What this deploys:**
- ✅ Lambda function for Agent 5
- ✅ IAM execution role with proper permissions
- ✅ CloudWatch Logs group
- ✅ Secrets Manager access for Slack/Jira (Phase 1C)
- ✅ Explicit security denies (DynamoDB, Bedrock KB access blocked)

---

## Step 2: Create Bedrock Agent

### 2.1 Register in Bedrock Console

1. Go to **AWS Bedrock Console** → **Agents**
2. Click **Create Agent**
3. Fill in:
   - **Name:** `ciam-response-generator`
   - **Description:** `CIAM Response Generator — Agent 5`
   - **Model:** Claude Sonnet 4.5
   - **IAM Role:** Select `ciam-response-generator-execution-role`

### 2.2 Configure Action Group

1. Click **Action Groups**
2. Add **New Action Group:**
   - **Name:** `synthesize_diagnosis`
   - **Description:** `Synthesize root cause diagnosis from upstream agent outputs`
   - **Lambda Function:** Select the deployed Lambda from Step 1
   - **API Schema:** Use default (agent.py defines input schema)

### 2.3 Add Agent Alias

1. Click **Aliases** → **Create Alias**
2. **Alias Name:** `prod`
3. **Agent Version:** Latest
4. Save and note the **Agent ID** and **Alias ID**

---

## Step 3: Wire into Orchestrator

### 3.1 Update Orchestrator Configuration

In `orchestrator/config.py`:

```python
AGENT_ENDPOINTS = {
    "agent1_intent_classifier": "...",
    "agent2_database_agent": "...",
    "agent3_auth0_agent": "...",
    "agent4_knowledge_base_agent": "...",
    "agent5_response_generator": {
        "type": "bedrock_agent",
        "agent_id": "<AGENT_ID_FROM_CONSOLE>",
        "agent_alias_id": "<ALIAS_ID_FROM_CONSOLE>",
        "region": "us-east-1",
    }
}
```

### 3.2 Update Orchestrator Pipeline

In `orchestrator/pipeline.py`:

```python
from orchestrator.agent5_builder import build_agent5_input

async def run_agent5(
    agent2_output: AccountPayload,
    agent3_output: Auth0Payload,
    agent4_output: KnowledgeBasePayload,
    ticket_email: str,
    ticket_intent: Optional[str],
) -> ResponseGeneratorPayload:
    """Invoke Agent 5 via Bedrock AgentCore."""
    
    # Build input
    agent5_input = build_agent5_input(
        agent2_output=agent2_output,
        agent3_output=agent3_output,
        agent4_output=agent4_output,
        ticket_email=ticket_email,
        ticket_intent=ticket_intent,
    )
    
    # Invoke Bedrock Agent
    response = await bedrock_runtime.invoke_agent(
        agentId=config.AGENT_ENDPOINTS["agent5_response_generator"]["agent_id"],
        agentAliasId=config.AGENT_ENDPOINTS["agent5_response_generator"]["agent_alias_id"],
        inputText=json.dumps(agent5_input),
    )
    
    return ResponseGeneratorPayload.parse_obj(json.loads(response["output"]))
```

---

## Step 4: Test Deployment

### 4.1 Unit Tests

```bash
cd agents/05-response-generator

# Run all tests
python3 -m pytest test_agent5.py -v

# Expected: 22/22 PASSING
```

### 4.2 Integration Test (Manual)

```bash
# Test via AWS Lambda console or CLI
aws lambda invoke \
  --function-name ciam-response-generator \
  --payload file://test_payload.json \
  response.json

cat response.json
```

**Test payload format:**

```json
{
  "account_payload": { "agent": "ciam-database-agent", "account_found": true, "accounts": [...] },
  "auth0_payload": { "agent": "ciam-auth0-agent", "user_found": true, "users": [...] },
  "kb_payload": { "agent": "ciam-knowledge-base-agent", "birthright_evaluation": {...} },
  "ticket_email": "user@example.com",
  "ticket_intent": "Cannot access Support portal"
}
```

### 4.3 Orchestrator Integration Test

```bash
cd orchestrator

# Run end-to-end test
python3 -m pytest test_orchestrator.py::test_agent5_synthesis -v

# Expected: All agents 1-5 work together
```

---

## Step 5: Configure Output Delivery (Phase 1C)

### 5.1 Store Slack Token

```bash
aws secretsmanager create-secret \
  --name ciam-agent/slack-bot-token \
  --secret-string '{"token":"xoxb-...","channel":"C0..."}' \
  --kms-key-id arn:aws:kms:us-east-1:123456789:key/...
```

### 5.2 Store Jira Token

```bash
aws secretsmanager create-secret \
  --name ciam-agent/jira-api-token \
  --secret-string '{"host":"jira.company.com","token":"...","user":"ciam-agent"}' \
  --kms-key-id arn:aws:kms:us-east-1:123456789:key/...
```

---

## Monitoring & Logs

### View Agent 5 Logs

```bash
# CloudWatch Logs
aws logs tail /ciam/response-generator/agent-logs --follow

# Or via console:
# CloudWatch → Log Groups → /ciam/response-generator/agent-logs
```

### Monitor Execution

```bash
# Recent invocations
aws logs describe-log-streams \
  --log-group-name /ciam/response-generator/agent-logs \
  --order-by LastEventTime \
  --descending
```

---

## Troubleshooting

### Issue: Lambda timeout
**Solution:** Increase timeout in CDK stack (currently 30s)
```python
timeout=Duration.seconds(60)  # Increase to 60s
```

### Issue: Permission denied (Secrets Manager)
**Solution:** Verify KMS key policy grants access to Lambda role
```bash
aws kms describe-key --key-id <KMS_KEY_ARN>
# Ensure ciam-response-generator-execution-role is in key policy
```

### Issue: Agent not responding
**Solution:** Check Bedrock Agent configuration
```bash
aws bedrock describe-agent --agent-id <AGENT_ID>
# Verify: Model=claude-sonnet-4-5, Status=PREPARED
```

---

## Security Checklist

Before production deployment, verify:

- ✅ Lambda function has explicit DynamoDB `Deny` policy
- ✅ Lambda function has explicit Bedrock KB `Deny` policy
- ✅ Lambda role is scoped to minimal necessary permissions
- ✅ Slack/Jira tokens are encrypted in Secrets Manager
- ✅ CloudWatch Logs are encrypted
- ✅ No credentials are logged (validate via log tail)
- ✅ No `user_id` values exposed in output (check jira_description format)

---

## Rollback

If deployment needs to be reverted:

```bash
# Delete CDK stack
cdk destroy --force

# Delete Bedrock Agent (via console or CLI)
aws bedrock delete-agent --agent-id <AGENT_ID>

# Verify Lambda is removed
aws lambda list-functions | grep ciam-response-generator
```

---

## Production Readiness

Agent 5 is ready for production once:

- ✅ All unit tests passing (22/22)
- ✅ Integration tests passing (Agents 1-5)
- ✅ CloudWatch logs verified
- ✅ Security audit complete
- ✅ Slack/Jira delivery tested (Phase 1C)
- ✅ Performance baseline established

---

## Support

**Questions about deployment?**
- See SPEC-CIAM-0005.md for agent specification
- See README.md for integration documentation
- See ALIGNMENT_WITH_SPEC.md for implementation status

**Found an issue?**
- Check CloudWatch logs: `/ciam/response-generator/agent-logs`
- Run unit tests: `pytest test_agent5.py -v`
- Review IAM role permissions

---

*Deployment Guide v0.2.0*  
*Last Updated: 2026-07-28*  
*Ready for production deployment*
