#!/usr/bin/env python3
"""
CDK App for CIAM Response Generator (Agent 5)

Deploys:
- Lambda function for Agent 5
- IAM execution role with posture invariants
- CloudWatch Logs group
- Secrets Manager integration
"""

import aws_cdk as cdk
import os
import sys

# Add the ciam-response-generator directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ciam-response-generator'))

from stack import CIAMResponseGeneratorStack

# Create CDK app
app = cdk.App()

# Deploy Agent 5 stack
CIAMResponseGeneratorStack(
    app,
    "CIAMResponseGeneratorStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION", "us-east-1")
    ),
    stack_name="ciam-response-generator-stack"
)

# Synthesize
app.synth()
