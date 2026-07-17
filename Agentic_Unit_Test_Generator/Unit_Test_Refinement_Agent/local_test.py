#!/usr/bin/env python3
"""Local iteration harness — exercises the agent's invoke() logic directly,
without deploying to or running the AgentCore runtime.

Usage:
    # fast path — reads local files, skips GitHub entirely
    python local_test.py <source_file> <test_file>

    # with failure logs
    python local_test.py <source_file> <test_file> --failure-logs <path_to_logs>

    # exercises the real invocation contract: agent fetches the files from
    # GitHub at the given ref, using the PAT in Secrets Manager, exactly as
    # the workflow will
    python local_test.py <source_file> <test_file> --via-github --ref <sha_or_branch> [--repo OWNER/NAME]
"""
import argparse
import json
import sys

from agent import invoke

DEFAULT_REPO = "netSkope/GIS-SecEng-Intern"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_file")
    parser.add_argument("test_file")
    parser.add_argument("--language", default=None)
    parser.add_argument("--framework", default=None)
    parser.add_argument("--failure-logs", default=None, help="path to file containing failure logs or feedback")
    parser.add_argument("--via-github", action="store_true", help="fetch via GitHub Contents API + PAT, matching the real CI contract")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--ref", default=None, help="commit SHA or branch to fetch at (required with --via-github)")
    args = parser.parse_args()

    payload = {"file_path": args.source_file, "test_file_path": args.test_file}
    if args.language:
        payload["language"] = args.language
    if args.framework:
        payload["framework"] = args.framework

    failure_logs = ""
    if args.failure_logs:
        with open(args.failure_logs, "r") as f:
            failure_logs = f.read()
    if failure_logs:
        payload["failure_logs"] = failure_logs

    if args.via_github:
        if not args.ref:
            print("--ref is required with --via-github", file=sys.stderr)
            sys.exit(1)
        payload["repo"] = args.repo
        payload["ref"] = args.ref
    else:
        with open(args.source_file, "r") as f:
            payload["source_code"] = f.read()
        with open(args.test_file, "r") as f:
            payload["test_code"] = f.read()

    result = invoke(payload)

    summary = {k: v for k, v in result.items() if k != "test_code"}
    print(json.dumps(summary, indent=2))

    if result.get("status") == "ok":
        print("\n--- REFINED TEST CODE ---\n")
        print(result["test_code"])
    else:
        print("\nFAILED — no refined test code produced.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
