#!/usr/bin/env python3
"""Run the orchestrator locally against the REAL deployed Agent 1 and Agent 2
(no mocks) — useful for a quick end-to-end sanity check from the terminal.

Usage:
    python scripts/local_test.py \
        --issue-key TQI-9001 \
        --summary "User cannot access portal" \
        --description "user.account@example.com getting Access Denied error"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ciam_orchestrator.orchestrator import CIAMOrchestrator
from ciam_orchestrator.schemas import JiraTicket


def main():
    parser = argparse.ArgumentParser(description="Run CIAM Orchestrator locally")
    parser.add_argument("--issue-key", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    ticket = JiraTicket(
        issue_key=args.issue_key,
        summary=args.summary,
        description=args.description,
    )

    orchestrator = CIAMOrchestrator()
    output = orchestrator.orchestrate(ticket)

    print(json.dumps(output.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    main()
