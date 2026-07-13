#!/usr/bin/env python3
"""
Invokes the Unit Test Generator Agent (deployed on Bedrock AgentCore) to
generate security-focused unit tests for one source file.

The agent fetches the source file itself directly from GitHub (at a pinned
commit SHA, authenticated via a PAT it reads from Secrets Manager) and
returns the generated test code in its response. This script just invokes
the agent and writes the result to the local output path — no S3 involved.

Usage:
    python generate_unit_test.py <path_to_source_file> <output_test_file>

Required environment variables:
    AGENT_RUNTIME_ARN  — ARN of the deployed AgentCore agent runtime.
    GITHUB_REPOSITORY  — "owner/repo" (GitHub Actions sets this automatically).
    SOURCE_COMMIT_SHA  — commit SHA to fetch the source file at. Must be the PR
                         head SHA (github.event.pull_request.head.sha), NOT
                         the ambient GITHUB_SHA — for pull_request events
                         GITHUB_SHA is the ephemeral merge commit, not the
                         actual commit that triggered the run.
"""
import json
import os
import sys
import uuid

import boto3

REGION = "ap-southeast-2"
AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
SOURCE_COMMIT_SHA = os.environ.get("SOURCE_COMMIT_SHA")


def main():
    if len(sys.argv) != 3:
        print("Usage: generate_unit_test.py <source_file> <output_test_file>")
        sys.exit(1)

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

    source_path, output_path = sys.argv[1], sys.argv[2]

    agentcore = boto3.client("bedrock-agentcore", region_name=REGION)

    payload = json.dumps({
        "repo": GITHUB_REPOSITORY,
        "ref": SOURCE_COMMIT_SHA,
        "file_path": source_path,
    }).encode("utf-8")

    print(f"DEBUG — invoking agent runtime: {AGENT_RUNTIME_ARN}")
    print(f"DEBUG — repo={GITHUB_REPOSITORY} ref={SOURCE_COMMIT_SHA} file_path={source_path}")
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

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(result["test_code"])

    print(f"Wrote generated test to {output_path}")
    print(f"Language: {result.get('language')} | Framework: {result.get('framework')}")
    print(f"Attempts: {result.get('attempts')} | Rejection history: {result.get('rejection_history')}")


if __name__ == "__main__":
    main()
