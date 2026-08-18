#!/bin/bash
set -e

# CIAM Orchestrator — AWS Lambda Deployment Script
# Automates: package creation, Lambda deployment, API Gateway setup

echo "======================================================================"
echo "CIAM ORCHESTRATOR — AWS LAMBDA DEPLOYMENT"
echo "======================================================================"

# Configuration
FUNCTION_NAME="ciam-orchestrator-webhook"
API_NAME="ciam-orchestrator-api"
STAGE="prod"
RESOURCE_PATH="webhook/jira"
REGION="us-east-1"
RUNTIME="python3.9"
TIMEOUT=60
HANDLER="lambda_handler.lambda_handler"

# AWS Account
ACCOUNT_ID="786063285476"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/CIAMAgentKnowledgeBaseAccessRole"

# Jira Config (from .env)
JIRA_INSTANCE_URL=$(grep JIRA_INSTANCE_URL ../.env | cut -d= -f2)
JIRA_EMAIL=$(grep JIRA_EMAIL ../.env | cut -d= -f2)
JIRA_API_TOKEN=$(grep JIRA_API_TOKEN ../.env | cut -d= -f2)
JIRA_PROJECT_KEY=$(grep JIRA_PROJECT_KEY ../.env | cut -d= -f2)

echo "Configuration:"
echo "  Function Name: $FUNCTION_NAME"
echo "  Region: $REGION"
echo "  Runtime: $RUNTIME"
echo "  Jira Instance: $JIRA_INSTANCE_URL"
echo ""

# Step 1: Create requirements.txt
echo "[1/5] Creating requirements.txt..."
cat > requirements.txt << 'EOF'
boto3>=1.26.0
requests>=2.28.0
pydantic>=2.0.0
python-dotenv>=1.0.0
EOF

# Step 2: Build deployment package
echo "[2/5] Building deployment package..."
rm -rf lambda-build lambda_deployment.zip 2>/dev/null || true
mkdir -p lambda-build

cp -r ciam_orchestrator lambda-build/
cp lambda_handler.py lambda-build/
cp requirements.txt lambda-build/

# Install dependencies
pip3 install -r requirements.txt -t lambda-build/ --upgrade --quiet

# Create ZIP
cd lambda-build
zip -r ../lambda_deployment.zip . -q
cd ..
echo "  Package created: lambda_deployment.zip"

# Disable SSL verification for corporate proxy
export AWS_CA_BUNDLE=""

# Step 3: Create/Update Lambda Function
echo "[3/5] Creating/updating Lambda function..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --no-verify-ssl &>/dev/null; then
    echo "  Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_deployment.zip \
        --region $REGION > /dev/null
else
    echo "  Creating new function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler $HANDLER \
        --zip-file fileb://lambda_deployment.zip \
        --timeout $TIMEOUT \
        --region $REGION > /dev/null
fi

# Set environment variables
echo "[4/5] Setting environment variables..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment "Variables={JIRA_INSTANCE_URL=$JIRA_INSTANCE_URL,JIRA_EMAIL=$JIRA_EMAIL,JIRA_API_TOKEN=$JIRA_API_TOKEN,JIRA_PROJECT_KEY=$JIRA_PROJECT_KEY}" \
    --region $REGION > /dev/null

# Step 5: Create API Gateway (or update if exists)
echo "[5/5] Setting up API Gateway..."

# Check if API exists
API_ID=$(aws apigateway get-rest-apis --region $REGION --query "items[?name=='$API_NAME'].id" --output text)

if [ -z "$API_ID" ]; then
    echo "  Creating new API..."
    API_ID=$(aws apigateway create-rest-api \
        --name $API_NAME \
        --description "Webhook for CIAM orchestrator" \
        --region $REGION \
        --query 'id' --output text)
fi

# Get root resource ID
ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query 'items[0].id' --output text)

# Get or create webhook resource
WEBHOOK_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query "items[?path=='/webhook'].id" --output text)

if [ -z "$WEBHOOK_ID" ]; then
    WEBHOOK_ID=$(aws apigateway create-resource \
        --rest-api-id $API_ID \
        --parent-id $ROOT_ID \
        --path-part webhook \
        --region $REGION \
        --query 'id' --output text)
fi

# Get or create jira resource
JIRA_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query "items[?path=='/webhook/jira'].id" --output text)

if [ -z "$JIRA_ID" ]; then
    JIRA_ID=$(aws apigateway create-resource \
        --rest-api-id $API_ID \
        --parent-id $WEBHOOK_ID \
        --path-part jira \
        --region $REGION \
        --query 'id' --output text)
fi

# Create or update POST method
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $JIRA_ID \
    --http-method POST \
    --authorization-type NONE \
    --region $REGION > /dev/null 2>&1 || true

# Set integration
LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"

aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $JIRA_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations" \
    --region $REGION > /dev/null 2>&1 || true

# Create or update deployment
DEPLOYMENT=$(aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name $STAGE \
    --region $REGION \
    --query 'id' --output text 2>/dev/null || true)

echo ""
echo "======================================================================"
echo "✅ DEPLOYMENT COMPLETE"
echo "======================================================================"
echo ""
echo "Webhook URL (register this in Jira):"
echo "  https://${API_ID}.execute-api.${REGION}.amazonaws.com/${STAGE}/webhook/jira"
echo ""
echo "Lambda Function:"
echo "  Name: $FUNCTION_NAME"
echo "  Region: $REGION"
echo "  CloudWatch Logs: /aws/lambda/$FUNCTION_NAME"
echo ""
echo "Next Steps:"
echo "  1. Copy the Webhook URL above"
echo "  2. Go to Jira Settings → Webhooks"
echo "  3. Create webhook with:"
echo "     - Name: CIAM-Orchestrator-Lambda"
echo "     - URL: <paste URL from above>"
echo "     - Events: Issue → Created"
echo "  4. Create a test ticket in NETSK-20 project"
echo "  5. Check Lambda logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
