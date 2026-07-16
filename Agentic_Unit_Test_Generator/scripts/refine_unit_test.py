#!/usr/bin/env python3
"""
Refines an existing generated unit test file based on reviewer feedback left
as PR inline comments.

TEMPORARY: no dedicated Refinement Agent exists yet, so this reuses the
Unit Test Generator Agent (same AGENT_RUNTIME_ARN, same request contract as
generate_unit_test.py: {repo, ref, file_path}) just to prove the collect ->
invoke -> write -> commit -> push pipeline works end to end. It regenerates
the test file from scratch — reviewer feedback is collected and logged but
NOT sent to the agent, since the generator agent's contract has no slot for
it. Swap AGENT_RUNTIME_ARN for a real Refinement Agent ARN and extend the
payload with test_code/feedback once that agent exists.

Usage:
    python refine_unit_test.py <test_file> <output_test_file> <feedback_json_path>

feedback_json_path points to a JSON file: a list of
    {"line": int, "diff_hunk": str, "comment": str}
for every reviewer comment left on that test_file.

Required environment variables:
    AGENT_RUNTIME_ARN  — ARN of the deployed AgentCore agent runtime (reusing
                         the Generator Agent's runtime for now).
    GITHUB_REPOSITORY  — "owner/repo".
    SOURCE_COMMIT_SHA  — PR head SHA to fetch the file at.
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
    if len(sys.argv) != 4:
        print("Usage: refine_unit_test.py <test_file> <output_test_file> <feedback_json_path>")
        sys.exit(1)

    test_file, output_path, feedback_path = sys.argv[1], sys.argv[2], sys.argv[3]

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
    print(f"DEBUG — {len(feedback)} reviewer feedback item(s) collected (not sent to agent yet): {feedback}")

    custom_config = Config(
        read_timeout=900,
        connect_timeout=900,
        retries={'max_attempts': 0}
    )
    agentcore = boto3.client("bedrock-agentcore", region_name=REGION, config=custom_config)

    payload = json.dumps({
        "repo": GITHUB_REPOSITORY,
        "ref": SOURCE_COMMIT_SHA,
        "file_path": test_file,
    }).encode("utf-8")

    print(f"DEBUG — invoking agent runtime: {AGENT_RUNTIME_ARN}")
    print(f"DEBUG — repo={GITHUB_REPOSITORY} ref={SOURCE_COMMIT_SHA} file_path={test_file}")
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
