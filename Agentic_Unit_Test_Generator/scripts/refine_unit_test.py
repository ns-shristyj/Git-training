#!/usr/bin/env python3
"""
Refines an existing generated unit test file based on reviewer feedback left
as PR inline comments.

The Refinement Agent fetches both the source file and test file from GitHub,
reviews the test against the source code and failure feedback, and returns a
corrected test file.

Usage:
    python refine_unit_test.py <test_file> <output_test_file> <feedback_json_path> [--source-file <path>]

feedback_json_path points to a JSON file: a list of
    {"line": int, "diff_hunk": str, "comment": str}
for every reviewer comment left on that test_file. diff_hunk is forwarded to
the agent alongside line/comment since line numbers drift across refine
cycles — the diff context is what actually pins the comment to a function.

If --source-file is not provided, the Refinement Agent itself derives it from
the test file name (reversing the naming convention, test_module.py ->
module.py) and locates the real path by searching the repo tree at `ref` —
this script does not touch GitHub or Secrets Manager directly, since the CI
role that runs this script has no secretsmanager:GetSecretValue permission
(only the agent's own execution role does).

Required environment variables:
    AGENT_RUNTIME_ARN  — ARN of the deployed AgentCore agent runtime (Refinement Agent).
    GITHUB_REPOSITORY  — "owner/repo".
    SOURCE_COMMIT_SHA  — PR head SHA to fetch files at.
"""
import json
import os
import sys
import uuid

import boto3
from botocore.config import Config

REGION = "ap-southeast-2"
AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
SOURCE_COMMIT_SHA = os.environ.get("SOURCE_COMMIT_SHA")


def main():
    if len(sys.argv) < 4:
        print("Usage: refine_unit_test.py <test_file> <output_test_file> <feedback_json_path> [--source-file <path>]")
        sys.exit(1)

    test_file = sys.argv[1]
    output_path = sys.argv[2]
    feedback_path = sys.argv[3]
    source_file_override = None

    if len(sys.argv) >= 6 and sys.argv[4] == "--source-file":
        source_file_override = sys.argv[5]

    missing = [
        name
        for name, value in (
            ("AGENT_RUNTIME_ARN", AGENT_RUNTIME_ARN),
            ("GITHUB_REPOSITORY", GITHUB_REPOSITORY),
            ("SOURCE_COMMIT_SHA", SOURCE_COMMIT_SHA),
        )
        if not value
    ]
    if missing:
        print(f"ERROR: missing required environment variable(s): {', '.join(missing)}")
        sys.exit(1)

    with open(feedback_path) as f:
        feedback = json.load(f)

    feedback_text = "\n\n".join(
        f"Line {item.get('line', '?')}: {item.get('comment', '')}\n"
        f"Diff context:\n{item.get('diff_hunk', '(none)')}"
        for item in feedback
    )
    print(f"DEBUG — {len(feedback)} reviewer feedback item(s) collected:\n{feedback_text}")

    custom_config = Config(
        read_timeout=900,
        connect_timeout=900,
        retries={'max_attempts': 0}
    )
    agentcore = boto3.client("bedrock-agentcore", region_name=REGION, config=custom_config)

    payload_dict = {
        "repo": GITHUB_REPOSITORY,
        "ref": SOURCE_COMMIT_SHA,
        "test_file_path": test_file,
        "failure_logs": feedback_text,
    }
    if source_file_override:
        payload_dict["file_path"] = source_file_override
    payload = json.dumps(payload_dict).encode("utf-8")

    print(f"DEBUG — invoking Refinement Agent runtime: {AGENT_RUNTIME_ARN}")
    print(f"DEBUG — repo={GITHUB_REPOSITORY} ref={SOURCE_COMMIT_SHA} "
          f"source_file={source_file_override or '(resolved by agent)'} test_file={test_file}")
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

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(result["test_code"])

    print(f"Wrote refined test to {output_path}")
    print(f"Language: {result.get('language')} | Framework: {result.get('framework')}")
    print(f"Attempts: {result.get('attempts')} | Rejection history: {result.get('rejection_history')}")


if __name__ == "__main__":
    main()
