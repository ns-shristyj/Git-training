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
import os

import boto3

MODEL_ID = "amazon.nova-lite-v1:0"
REGION = "ap-southeast-2"

SECURITY_CHECKLIST = """You are a security-focused test engineer writing pytest unit tests for one
Python module. You will be given the source code and its module import path.

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

    # Nova uses the Converse API body format (not Anthropic's format)
    body = {
        "system": [
            {"text": SECURITY_CHECKLIST}
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"text": build_user_message(source_code, module_path)}
                ]
            }
        ],
        "inferenceConfig": {
            "max_new_tokens": 4090,
        },
    }

    response = client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )

    payload = json.loads(response["body"].read())

    # Nova response shape: output.message.content[0].text
    stop_reason = payload.get("stopReason")
    if stop_reason == "max_tokens":
        print("WARNING: output was truncated — raise max_new_tokens if tests are incomplete")

    model_text = payload["output"]["message"]["content"][0]["text"]
    test_code = extract_code_block(model_text)

    # print("=" * 60)
    # print("GENERATED TEST FILE CONTENTS:")
    # print("=" * 60)
    # print(test_code)
    # print("=" * 60)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(test_code)

    print(f"Wrote generated test to {output_path}")
    print(f"Stop reason: {stop_reason}")
    print(f"Input tokens:  {payload.get('usage', {}).get('inputTokens')}")
    print(f"Output tokens: {payload.get('usage', {}).get('outputTokens')}")


if __name__ == "__main__":
    main()