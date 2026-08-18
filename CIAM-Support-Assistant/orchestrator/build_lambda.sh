#!/bin/bash
set -e

echo "======================================================================="
echo "BUILDING LAMBDA PACKAGE WITH LINUX-COMPATIBLE DEPENDENCIES"
echo "======================================================================="

# Step 1: Clean old build
echo -e "\n[1/5] Cleaning old build..."
rm -rf lambda-build lambda_deployment.zip
mkdir -p lambda-build

# Step 2: Build dependencies in Lambda-compatible Docker image
echo "[2/5] Building dependencies in Lambda Docker image..."
docker run --rm \
  -v $(pwd):/var/task \
  public.ecr.aws/lambda/python:3.9 \
  bash -c "pip install boto3 requests pydantic python-dotenv -t /var/task/lambda-build/ --quiet"

echo "✅ Dependencies built for Lambda environment"

# Step 3: Copy code
echo "[3/5] Copying Lambda handler and agent code..."
cp -r ciam_orchestrator lambda-build/
cp lambda_handler.py lambda-build/
cp requirements.txt lambda-build/

# Step 4: Create deployment ZIP
echo "[4/5] Creating deployment package..."
cd lambda-build
zip -r ../lambda_deployment.zip . -q
cd ..

SIZE=$(du -h lambda_deployment.zip | cut -f1)
echo "✅ Package created: lambda_deployment.zip ($SIZE)"

# Step 5: Update Lambda
echo "[5/5] Updating Lambda function..."
aws lambda update-function-code \
  --function-name ciam-orchestrator-webhook \
  --zip-file fileb://lambda_deployment.zip \
  --region us-east-1 > /dev/null

echo "✅ Lambda function updated!"

echo ""
echo "======================================================================="
echo "✅ DEPLOYMENT COMPLETE - PYDANTIC ISSUE FIXED"
echo "======================================================================="
echo ""
echo "Your orchestrator is now ready to process Jira tickets!"

