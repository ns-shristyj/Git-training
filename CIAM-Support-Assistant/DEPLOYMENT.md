# CIAM Orchestrator — AWS Lambda Deployment

Deploy the webhook listener as a serverless Lambda function with API Gateway.

## Prerequisites

- AWS CLI configured with credentials: `aws configure`
- Your Jira sandbox credentials in `.env` file
- Python 3.9+

## Deployment Steps

### 1. Create Lambda Function

```bash
cd orchestrator

# Create deployment package
mkdir -p lambda-build
cp -r ciam_orchestrator lambda-build/
cp lambda_handler.py lambda-build/
cp requirements.txt lambda-build/  # (see below for creating this)

# Install dependencies into package
pip3 install -r requirements.txt -t lambda-build/ --upgrade

# Create ZIP file
cd lambda-build
zip -r ../lambda_deployment.zip .
cd ..
```

### 2. Create requirements.txt

Create `orchestrator/requirements.txt`:

```
boto3>=1.26.0
requests>=2.28.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

### 3. Create Lambda Function (via AWS Console or CLI)

**Option A: AWS Console (Easier)**

1. Go to AWS Lambda console: `https://console.aws.amazon.com/lambda`
2. Click **Create Function**
3. Name: `ciam-orchestrator-webhook`
4. Runtime: **Python 3.9**
5. Execution role: Use existing role `CIAMAgentKnowledgeBaseAccessRole` (or create new with DynamoDB + Auth0 secret access)
6. Click **Create**
7. Go to **Code** tab → **Upload from** → **.zip file**
8. Upload `lambda_deployment.zip`
9. Set **Handler** to: `lambda_handler.lambda_handler`
10. Increase **Timeout** to 60 seconds (Agents 2-5 take ~30-50s)

**Option B: AWS CLI**

```bash
aws lambda create-function \
  --function-name ciam-orchestrator-webhook \
  --runtime python3.9 \
  --role arn:aws:iam::786063285476:role/CIAMAgentKnowledgeBaseAccessRole \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 60 \
  --environment Variables={JIRA_INSTANCE_URL=https://netskope-sandbox.atlassian.net,JIRA_EMAIL=shristyj@netskope.com,JIRA_PROJECT_KEY=NETSK-20}
```

### 4. Create API Gateway Endpoint

**Option A: AWS Console**

1. Go to API Gateway: `https://console.aws.amazon.com/apigateway`
2. Click **Create API** → **REST API**
3. Name: `ciam-orchestrator-api`
4. Create a **POST** method on `/webhook/jira` resource
5. Integration: Select Lambda function → `ciam-orchestrator-webhook`
6. Deploy to stage: **prod**
7. Copy the **Invoke URL** (looks like: `https://abc123.execute-api.us-east-1.amazonaws.com/prod/webhook/jira`)

**Option B: AWS CLI**

```bash
# Create REST API
API_ID=$(aws apigateway create-rest-api \
  --name ciam-orchestrator-api \
  --description "Webhook for CIAM orchestrator" \
  --query 'id' --output text)

# Get root resource ID
ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --query 'items[0].id' --output text)

# Create /webhook/jira resource
RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part webhook \
  --query 'id' --output text)

JIRA_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $RESOURCE_ID \
  --path-part jira \
  --query 'id' --output text)

# Create POST method
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $JIRA_ID \
  --http-method POST \
  --authorization-type NONE

# Set Lambda integration
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $JIRA_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:786063285476:function:ciam-orchestrator-webhook/invocations

# Deploy to prod stage
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod

# Get invoke URL
echo "Invoke URL: https://$API_ID.execute-api.us-east-1.amazonaws.com/prod/webhook/jira"
```

### 5. Set Environment Variables in Lambda

Go to Lambda function → **Configuration** → **Environment variables**

Add:

```
JIRA_INSTANCE_URL=https://netskope-sandbox.atlassian.net
JIRA_EMAIL=shristyj@netskope.com
JIRA_API_TOKEN=your_api_token_here
JIRA_PROJECT_KEY=NETSK-20
```

### 6. Test the Endpoint

```bash
curl -X POST https://abc123.execute-api.us-east-1.amazonaws.com/prod/webhook/jira \
  -H "Content-Type: application/json" \
  -d '{
    "issue": {
      "key": "NETSK-20",
      "fields": {
        "summary": "Test: User cannot access Community",
        "description": "Testing Lambda deployment"
      }
    }
  }'
```

Expected response:
```json
{
  "status": "success",
  "ticket": "NETSK-20",
  "run_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### 7. Register Webhook in Jira

1. Jira Settings → **Webhooks**
2. Create webhook:
   - **Name:** `CIAM-Orchestrator-Lambda`
   - **URL:** `https://abc123.execute-api.us-east-1.amazonaws.com/prod/webhook/jira`
   - **Events:** `Issue → Created`
3. Save

### 8. Test End-to-End

1. Create a new ticket in Jira (NETSK-20 project)
2. Watch Lambda CloudWatch logs: `aws logs tail /aws/lambda/ciam-orchestrator-webhook --follow`
3. Check the Jira ticket for orchestrator's comment with diagnosis

## Monitoring

Check Lambda logs:

```bash
aws logs tail /aws/lambda/ciam-orchestrator-webhook --follow
```

Check Lambda metrics:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=ciam-orchestrator-webhook \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Average,Maximum
```

## Cleanup

```bash
# Delete Lambda function
aws lambda delete-function --function-name ciam-orchestrator-webhook

# Delete API Gateway
aws apigateway delete-rest-api --rest-api-id abc123
```
