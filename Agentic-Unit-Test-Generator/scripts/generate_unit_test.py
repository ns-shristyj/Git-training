#!/usr/bin/env python3
"""
Bedrock-powered security-focused unit test generator (prototype).
Uses InvokeModel API which is supported by the current IAM policy.

Usage:
    python generate_unit_test.py <path_to_source_file> <path_to_output_test_file>
"""
import json
import re
import sys

import boto3

MODEL_ID = "au.anthropic.claude-haiku-4-5-20251001-v1:0"
REGION = "ap-southeast-2"

SECURITY_CHECKLIST = """You are a security-focused test engineer writing pytest unit tests for one
Python module. Isolate the module under test. Mock all dependencies with
unittest.mock. Never do real I/O. For each function, write tests for: input
validation, injection vectors, auth boundaries, error leakage, resource limits,
and mocked-dependency failure modes. Output only one Python code block, no prose."""


def build_user_message(source_code: str, module_path: str) -> str:
    return f"Module: `{module_path}`\n\n```python\n{source_code}\n```"


def extract_code_block(text: str) -> str:
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    if not match:
        raise ValueError(f"No code block found in model output:\n{text}")
    return match.group(1).strip() + "\n"


def main():
    if len(sys.argv) != 3:
        print("Usage: generate_unit_test.py <source_file> <output_test_file>")
        sys.exit(1)

    source_path, output_path = sys.argv[1], sys.argv[2]

    with open(source_path, "r") as f:
        source_code = f.read()

    module_path = source_path.replace("/", ".").removesuffix(".py")

    client = boto3.client("bedrock-runtime", region_name=REGION)
    print(f"DEBUG — using REGION: {REGION}")
    print(f"DEBUG — using MODEL_ID: {MODEL_ID}")
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "system": SECURITY_CHECKLIST,
        "messages": [
            {
                "role": "user",
                "content": build_user_message(source_code, module_path)
            }
        ],
    }

    response = client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )

    payload = json.loads(response["body"].read())

    # check for truncation
    stop_reason = payload.get("stop_reason")
    if stop_reason == "max_tokens":
        print("WARNING: output was truncated — raise max_tokens if tests are incomplete")

    model_text = payload["content"][0]["text"]
    test_code = extract_code_block(model_text)

    print("=" * 60)
    print("GENERATED TEST FILE CONTENTS:")
    print("=" * 60)
    print(test_code)
    print("=" * 60)
    
    with open(output_path, "w") as f:
        f.write(test_code)

    print(f"Wrote generated test to {output_path}")
    print(f"Stop reason: {stop_reason}")
    print(f"Input tokens: {payload.get('usage', {}).get('input_tokens')}")
    print(f"Output tokens: {payload.get('usage', {}).get('output_tokens')}")


if __name__ == "__main__":
    main()