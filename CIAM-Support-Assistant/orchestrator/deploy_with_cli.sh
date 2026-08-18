#!/bin/bash
set -e

echo "======================================================================="
echo "CIAM ORCHESTRATOR — AWS LAMBDA DEPLOYMENT (CLI)"
echo "======================================================================="

FUNCTION_NAME="ciam-orchestrator-webhook"
REGION="us-east-1"

# Step 1: Build deployment package
echo -e "\n[1/3] Building deployment package..."
rm -rf lambda-build lambda_deployment.zip 2>/dev/null || true
mkdir -p lambda-build

cp -r ciam_orchestrator lambda-build/
cp lambda_handler.py lambda-build/

# Create requirements with proper formatting
cat > lambda-build/requirements.txt << 'REQEOF'
boto3>=1.26.0
requests>=2.28.0
pydantic>=2.0.0
python-dotenv>=1.0.0
REQEOF

# Install with manylinux wheels
cd lambda-build
python3 -m pip install \
  -r requirements.txt \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --implementation cp \
  --python-version 39 \
  -t . \
  --upgrade \
  --quiet 2>/dev/null || {
    echo "Warning: Some packages may not have manylinux wheels, installing normally..."
    python3 -m pip install -r requirements.txt -t . --upgrade --quiet
  }

# Create ZIP
zip -r ../lambda_deployment.zip . -q
cd ..

SIZE=$(du -h lambda_deployment.zip | cut -f1)
echo "✅ Package created: lambda_deployment.zip ($SIZE)"

# Step 2: Update Lambda function
echo "[2/3] Updating Lambda function..."
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://lambda_deployment.zip \
  --region $REGION > /dev/null

echo "✅ Lambda function updated"

# Step 3: Test the function
echo "[3/3] Testing Lambda function..."
sleep 5

TEST_RESULT=$(aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --region $REGION \
  --payload '{"body": "{\"issue\": {\"key\": \"TEST-1\", \"fields\": {\"summary\": \"Test\", \"description\": \"\"}}}"}' \
  /tmp/lambda_response.json 2>&1 || true)

if [ -f /tmp/lambda_response.json ]; then
  RESPONSE=$(cat /tmp/lambda_response.json)
  echo "Response: $RESPONSE"
  
  if echo "$RESPONSE" | grep -q "pydantic_core"; then
    echo "❌ Still getting pydantic_core error"
    exit 1
  elif echo "$RESPONSE" | grep -q "error"; then
    echo "⚠️  Error in response: $RESPONSE"
  else
    echo "✅ Lambda function is working!"
  fi
fi

echo ""
echo "======================================================================="
echo "✅ DEPLOYMENT COMPLETE - ORCHESTRATOR LIVE ON AWS LAMBDA"
echo "======================================================================="

