#!/usr/bin/env python3
"""Deploy CIAM Orchestrator to AWS Lambda with API Gateway."""

import os
import sys
import json
import zipfile
import subprocess
from pathlib import Path
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# AWS Clients
import boto3
from botocore.config import Config

# Configuration
FUNCTION_NAME = "ciam-orchestrator-webhook"
API_NAME = "ciam-orchestrator-api"
STAGE = "prod"
REGION = "us-east-1"
ACCOUNT_ID = "786063285476"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/CIAMOrchestratorLambdaRole"
HANDLER = "lambda_handler.lambda_handler"
TIMEOUT = 60

# Read Jira config from .env
env_file = Path("../.env")
jira_config = {}
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line:
                key, val = line.strip().split("=", 1)
                jira_config[key] = val

print("="*70)
print("CIAM ORCHESTRATOR — AWS LAMBDA DEPLOYMENT")
print("="*70)
print(f"\nConfiguration:")
print(f"  Function: {FUNCTION_NAME}")
print(f"  Region: {REGION}")
print(f"  Jira Instance: {jira_config.get('JIRA_INSTANCE_URL', 'N/A')}")

# Step 1: Create requirements.txt
print("\n[1/4] Creating requirements.txt...")
with open("requirements.txt", "w") as f:
    f.write("""boto3>=1.26.0
requests>=2.28.0
pydantic>=2.0.0
python-dotenv>=1.0.0
""")

# Step 2: Build deployment package
print("[2/4] Building deployment package...")
os.system("rm -rf lambda-build lambda_deployment.zip 2>/dev/null || true")
os.makedirs("lambda-build", exist_ok=True)

# Copy files
os.system("cp -r ciam_orchestrator lambda-build/")
os.system("cp lambda_handler.py lambda-build/")
os.system("cp requirements.txt lambda-build/")

# Install dependencies with manylinux2014 wheels for Lambda compatibility
print("  Installing dependencies (Lambda-compatible wheels)...")
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt",
     "-t", "lambda-build/", "--upgrade", "--quiet",
     "--platform", "manylinux2014_x86_64",
     "--only-binary=:all:",
     "--implementation", "cp",
     "--python-version", "39"],
    check=False
)

# Create ZIP
print("  Creating ZIP package...")
with zipfile.ZipFile("lambda_deployment.zip", "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk("lambda-build"):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, "lambda-build")
            zf.write(file_path, arcname)

print("  ✅ Package created: lambda_deployment.zip")

# Step 3: Create Lambda Function
print("[3/4] Creating Lambda function...")

try:
    config = Config(
        retries={'max_attempts': 3, 'mode': 'adaptive'},
        connect_timeout=10,
        read_timeout=60
    )
    lambda_client = boto3.client("lambda", region_name=REGION, config=config, verify=False)
    apigateway_client = boto3.client("apigateway", region_name=REGION, config=config, verify=False)

    # Read ZIP file
    with open("lambda_deployment.zip", "rb") as f:
        zip_content = f.read()

    # Check if function exists
    try:
        lambda_client.get_function(FunctionName=FUNCTION_NAME)
        print(f"  Updating existing function: {FUNCTION_NAME}")
        lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content
        )
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"  Creating new function: {FUNCTION_NAME}")
        lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime="python3.9",
            Role=ROLE_ARN,
            Handler=HANDLER,
            Code={"ZipFile": zip_content},
            Timeout=TIMEOUT,
        )

    # Wait for function to be active and not updating
    import time
    print("  Waiting for function to be ready...")
    max_retries = 60
    for i in range(max_retries):
        try:
            func = lambda_client.get_function(FunctionName=FUNCTION_NAME)
            state = func["Configuration"]["State"]
            update_status = func.get("Configuration", {}).get("UpdateStatus", "Successful")
            if state == "Active" and update_status != "InProgress":
                print("  Function is ready!")
                break
        except Exception as e:
            if i == max_retries - 1:
                print(f"  Warning: {e}, continuing anyway...")
        if i < max_retries - 1:
            time.sleep(2)

    # Set environment variables (with retry)
    print("  Setting environment variables...")
    import time
    max_config_retries = 10
    for attempt in range(max_config_retries):
        try:
            time.sleep(3)  # Wait 3 seconds between attempts
            lambda_client.update_function_configuration(
                FunctionName=FUNCTION_NAME,
                Environment={
                    "Variables": {
                        "JIRA_INSTANCE_URL": jira_config.get("JIRA_INSTANCE_URL", ""),
                        "JIRA_EMAIL": jira_config.get("JIRA_EMAIL", ""),
                        "JIRA_API_TOKEN": jira_config.get("JIRA_API_TOKEN", ""),
                        "JIRA_PROJECT_KEY": jira_config.get("JIRA_PROJECT_KEY", "NETSK-20"),
                    }
                }
            )
            print("  ✅ Environment variables set!")
            break
        except Exception as e:
            if attempt < max_config_retries - 1:
                print(f"  Retry {attempt + 1}/{max_config_retries}...")
            else:
                raise

    # Step 4: Setup API Gateway
    print("[4/4] Setting up API Gateway...")

    # Get or create API
    apis = apigateway_client.get_rest_apis()
    api_id = None
    for api in apis.get("items", []):
        if api["name"] == API_NAME:
            api_id = api["id"]
            break

    if not api_id:
        print(f"  Creating API: {API_NAME}")
        api = apigateway_client.create_rest_api(
            name=API_NAME,
            description="Webhook for CIAM orchestrator"
        )
        api_id = api["id"]

    # Get root resource
    resources = apigateway_client.get_resources(restApiId=api_id)
    root_id = resources["items"][0]["id"]

    # Get or create /webhook
    webhook_id = None
    jira_id = None
    for res in resources["items"]:
        if res.get("path") == "/webhook":
            webhook_id = res["id"]
        elif res.get("path") == "/webhook/jira":
            jira_id = res["id"]

    if not webhook_id:
        webhook = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart="webhook"
        )
        webhook_id = webhook["id"]

    if not jira_id:
        jira = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=webhook_id,
            pathPart="jira"
        )
        jira_id = jira["id"]

    # Create POST method
    try:
        apigateway_client.put_method(
            restApiId=api_id,
            resourceId=jira_id,
            httpMethod="POST",
            authorizationType="NONE"
        )
    except:
        pass  # Method might already exist

    # Set Lambda integration
    lambda_arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{FUNCTION_NAME}"
    try:
        apigateway_client.put_integration(
            restApiId=api_id,
            resourceId=jira_id,
            httpMethod="POST",
            type="AWS_PROXY",
            integrationHttpMethod="POST",
            uri=f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
        )
    except:
        pass  # Integration might already exist

    # Deploy
    deployment = apigateway_client.create_deployment(
        restApiId=api_id,
        stageName=STAGE
    )

    webhook_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/{STAGE}/webhook/jira"

    print("\n" + "="*70)
    print("✅ DEPLOYMENT COMPLETE!")
    print("="*70)
    print(f"\n📋 Webhook URL (register in Jira):")
    print(f"   {webhook_url}")
    print(f"\n📊 Lambda Function:")
    print(f"   Name: {FUNCTION_NAME}")
    print(f"   Region: {REGION}")
    print(f"\n🔧 Next Steps:")
    print(f"   1. Copy the Webhook URL above")
    print(f"   2. Go to Jira Settings → Webhooks")
    print(f"   3. Create webhook:")
    print(f"      - Name: CIAM-Orchestrator-Lambda")
    print(f"      - URL: {webhook_url}")
    print(f"      - Events: Issue → Created")
    print(f"   4. Create a test ticket in NETSK-20 project")
    print(f"\n✅ Done! Your orchestrator is now live on AWS Lambda.")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    sys.exit(1)
