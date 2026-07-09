#!/usr/bin/env python3
"""
Invokes the Unit Test Generator Agent (deployed on Bedrock AgentCore) to
generate security-focused unit tests for one source file.

Uploads the source file to S3, invokes the agent with the S3 URI, then
uploads the agent's returned test code back to S3. The agent itself never
writes to S3 — this script owns both the input and output S3 operations.

Usage:
    python generate_unit_test.py <path_to_source_file> <s3_output_key>

Required environment variable:
    AGENT_RUNTIME_ARN — ARN of the deployed AgentCore agent runtime.
"""
import json
import os
import sys
import uuid

import boto3

REGION = "ap-southeast-2"
BUCKET = os.environ.get("UNIT_TEST_GEN_BUCKET", "netskope-unit-test-gen-786063285476-ap-southeast-2")
AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN")


def main():
    if len(sys.argv) != 3:
        print("Usage: generate_unit_test.py <source_file> <s3_output_key>")
        sys.exit(1)

    if not AGENT_RUNTIME_ARN:
        print("ERROR: AGENT_RUNTIME_ARN environment variable is required")
        sys.exit(1)

    source_path, s3_output_key = sys.argv[1], sys.argv[2]

    s3 = boto3.client("s3", region_name=REGION)
    agentcore = boto3.client("bedrock-agentcore", region_name=REGION)

    s3_source_key = f"source/{source_path}"
    s3.upload_file(source_path, BUCKET, s3_source_key)
    print(f"Uploaded source to s3://{BUCKET}/{s3_source_key}")

    payload = json.dumps({
        "s3_uri": f"s3://{BUCKET}/{s3_source_key}",
        "file_path": source_path,
    }).encode("utf-8")

    print(f"DEBUG — invoking agent runtime: {AGENT_RUNTIME_ARN}")
    response = agentcore.invoke_agent_runtime(
        agentRuntimeArn=AGENT_RUNTIME_ARN,
        runtimeSessionId=str(uuid.uuid4()),
        payload=payload,
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["response"].read())

    if result.get("status") != "ok":
        print(f"ERROR: agent did not return a usable test file: {json.dumps(result)}")
        sys.exit(1)

    test_code = result["test_code"]
    s3.put_object(Bucket=BUCKET, Key=s3_output_key, Body=test_code.encode("utf-8"))
    print(f"Wrote generated test to s3://{BUCKET}/{s3_output_key}")
    print(f"Language: {result.get('language')} | Framework: {result.get('framework')}")
    print(f"Attempts: {result.get('attempts')} | Rejection history: {result.get('rejection_history')}")


if __name__ == "__main__":
    main()
