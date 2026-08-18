#!/usr/bin/env python3
import json
import os
import sys
import requests
from pathlib import Path

# Disable SSL warnings
import urllib3
urllib3.disable_warnings()

# Load AWS credentials from environment or CLI
import subprocess
result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                       capture_output=True, text=True, 
                       env={**os.environ, 'AWS_CA_BUNDLE': ''})

if result.returncode != 0:
    print("Error: AWS CLI not configured")
    sys.exit(1)

# Read ZIP file
with open('lambda_deployment.zip', 'rb') as f:
    zip_content = f.read()

print(f"ZIP file size: {len(zip_content) / 1024 / 1024:.1f}MB")

# Get AWS credentials via CLI
creds_result = subprocess.run(
    ['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'],
    capture_output=True, text=True,
    env={**os.environ, 'AWS_CA_BUNDLE': ''}
)

print(f"AWS Account: {creds_result.stdout.strip()}")

# Use AWS Lambda API endpoint
FUNCTION_NAME = "ciam-orchestrator-webhook"
REGION = "us-east-1"
ACCOUNT_ID = creds_result.stdout.strip()

# Lambda update via presigned URL or direct call
print(f"\n✅ ZIP package ready ({len(zip_content)} bytes)")
print("Using AWS CLI to update Lambda...")

# Use subprocess to call AWS with no SSL verification
update_result = subprocess.run([
    'aws', 'lambda', 'update-function-code',
    '--function-name', FUNCTION_NAME,
    '--zip-file', f'fileb://lambda_deployment.zip',
    '--region', REGION,
    '--cli-read-timeout', '0',
    '--cli-connect-timeout', '60'
], env={**os.environ, 'AWS_CA_BUNDLE': ''}, capture_output=True, text=True)

if update_result.returncode == 0:
    print("\n✅ Lambda function updated successfully!")
    result_data = json.loads(update_result.stdout)
    print(f"Function: {result_data.get('FunctionName')}")
    print(f"Runtime: {result_data.get('Runtime')}")
    print(f"CodeSize: {result_data.get('CodeSize')} bytes")
else:
    print(f"Error: {update_result.stderr}")
    print(f"\nTrying alternative method...")
    # Try using boto3 directly with requests session
    import boto3
    from botocore.awsrequest import AWSRequest
    
    s3 = boto3.client('s3', region_name=REGION, verify=False)
    lam = boto3.client('lambda', region_name=REGION, verify=False)
    
    try:
        response = lam.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content
        )
        print(f"✅ Lambda updated via boto3")
        print(f"CodeSize: {response.get('CodeSize')} bytes")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

