#!/usr/bin/env python3
"""Fetch a Jira ticket by key and run it through the CIAM Orchestrator.

Usage:
    python3 run_ticket.py RJT-31
"""

import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(__file__))

from ciam_orchestrator.orchestrator import CIAMOrchestrator
from ciam_orchestrator.schemas import JiraTicket

requests.packages.urllib3.disable_warnings()


def _adf_to_text(node) -> str:
    """Flattens an Atlassian Document Format body into plain text."""
    if not node:
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = [_adf_to_text(child) for child in node.get("content", [])]
    text = "".join(parts) if node.get("type") == "text" else " ".join(p for p in parts if p)
    if node.get("type") in ("paragraph", "heading", "listItem"):
        text += "\n"
    return text


def fetch_ticket(issue_key: str) -> JiraTicket:
    base_url = os.environ["JIRA_INSTANCE_URL"].rstrip("/")
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_API_TOKEN"]

    resp = requests.get(
        f"{base_url}/rest/api/3/issue/{issue_key}",
        params={"fields": "summary,description"},
        auth=(email, token),
        headers={"Accept": "application/json"},
        verify=False,
        timeout=15,
    )
    resp.raise_for_status()
    fields = resp.json()["fields"]

    description = _adf_to_text(fields.get("description")).strip()

    return JiraTicket(
        issue_key=issue_key,
        summary=fields["summary"],
        description=description,
    )


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <ISSUE-KEY>", file=sys.stderr)
        sys.exit(1)

    issue_key = sys.argv[1]
    ticket = fetch_ticket(issue_key)

    print(f"Fetched {issue_key}: {ticket.summary}")
    print("Running through CIAM Orchestrator (live AgentCore invocations)...\n")

    result = CIAMOrchestrator().orchestrate(ticket)

    for inv in result.agent_invocations:
        print(f"--- {inv.agent_name} ---")
        print(f"  status: {inv.status}  ({inv.response_time_ms:.0f}ms)")
        if inv.error_message:
            print(f"  error: {inv.error_message}")
        print()

    print("=" * 60)
    print(f"should_escalate_to_l2: {result.should_escalate_to_l2}")
    if result.escalation_reason:
        print(f"escalation_reason: {result.escalation_reason}")
    if result.orchestration_warnings:
        print(f"warnings: {result.orchestration_warnings}")

    out_path = f"{issue_key.lower()}_orchestrator_result.json"
    with open(out_path, "w") as f:
        f.write(result.model_dump_json(indent=2))
    print(f"\nFull result saved to {out_path}")


if __name__ == "__main__":
    main()
