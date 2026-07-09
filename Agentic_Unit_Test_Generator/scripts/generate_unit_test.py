#!/usr/bin/env python3
"""
Bedrock-powered security-focused unit test generator (prototype).
Uploads the source file to S3 and uses the Converse API's S3-referenced
document block, so the model reads the file straight from S3 instead of
having the source embedded inline in the request payload.

Usage:
    python generate_unit_test.py <path_to_source_file> <s3_output_key>
"""
import re
import sys
import os

import boto3

MODEL_ID = "amazon.nova-lite-v1:0"
REGION = "ap-southeast-2"
BUCKET = os.environ.get("UNIT_TEST_GEN_BUCKET", "netskope-unit-test-gen-786063285476-ap-southeast-2")

SECURITY_CHECKLIST = """You are a security-focused test engineer writing pytest unit tests for one
Python module. You will be given the source code as an attached document and its module import path.

CRITICAL RULE: NEVER mock the class or functions you are testing. Only mock
external dependencies the code calls (network, DB, filesystem, other modules).
If the module has no external dependencies, write tests with no mocks at all.

Import the real class directly, e.g.:
from NIC_SecEng_Task.Calculator.calculator import Calculator

Then instantiate and call it for real:
calc = Calculator()
result = calc.add(1, 2)
assert result == 3

For each function write tests for:
- Input validation: None, wrong type, empty, negative, oversized inputs
- Edge cases: zero, boundary values, very large numbers
- Error cases: what exceptions are raised and with what message
- If divide by zero is possible, test it raises the right exception

Output only one Python code block, no prose. Use pytest plain def test_ functions."""


def build_user_message(module_path: str) -> str:
    return f"Module: `{module_path}`\n\nWrite pytest unit tests for the attached source file."


def extract_code_block(text: str) -> str:
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    if not match:
        raise ValueError(f"No code block found in model output:\n{text}")
    return match.group(1).strip() + "\n"


def main():
    if len(sys.argv) != 3:
        print("Usage: generate_unit_test.py <source_file> <s3_output_key>")
        sys.exit(1)

    source_path, s3_output_key = sys.argv[1], sys.argv[2]
    module_path = source_path.replace("/", ".").removesuffix(".py")

    s3 = boto3.client("s3", region_name=REGION)
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)

    s3_source_key = f"source/{source_path}"
    s3.upload_file(source_path, BUCKET, s3_source_key)
    print(f"Uploaded source to s3://{BUCKET}/{s3_source_key}")

    print(f"DEBUG — using REGION: {REGION}")
    print(f"DEBUG — using MODEL_ID: {MODEL_ID}")

    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": SECURITY_CHECKLIST}],
        messages=[
            {
                "role": "user",
                "content": [
                    {"text": build_user_message(module_path)},
                    {
                        "document": {
                            "format": "txt",
                            "name": "SourceModule",
                            "source": {
                                "s3Location": {
                                    "uri": f"s3://{BUCKET}/{s3_source_key}",
                                }
                            },
                        }
                    },
                ],
            }
        ],
        inferenceConfig={"maxTokens": 4090},
    )

    stop_reason = response.get("stopReason")
    if stop_reason == "max_tokens":
        print("WARNING: output was truncated — raise maxTokens if tests are incomplete")

    model_text = response["output"]["message"]["content"][0]["text"]
    test_code = extract_code_block(model_text)

    s3.put_object(Bucket=BUCKET, Key=s3_output_key, Body=test_code.encode("utf-8"))
    print(f"Wrote generated test to s3://{BUCKET}/{s3_output_key}")
    print(f"Stop reason: {stop_reason}")
    usage = response.get("usage", {})
    print(f"Input tokens:  {usage.get('inputTokens')}")
    print(f"Output tokens: {usage.get('outputTokens')}")


if __name__ == "__main__":
    main()
