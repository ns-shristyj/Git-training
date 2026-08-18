"""Jira webhook listener — receives ticket creation events and invokes the orchestrator.

Start with: python -m orchestrator.webhook_listener
Or deploy as: AWS Lambda function

Expects Jira webhook payload with issue/key, summary, description.
"""

import json
import logging
import sys
import os
from typing import Dict
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add orchestrator to path so we can import ciam_orchestrator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ciam_orchestrator.orchestrator import CIAMOrchestrator
from ciam_orchestrator.schemas import JiraTicket
from ciam_orchestrator.jira_client import get_jira_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ciam-webhook-listener")

app = Flask(__name__)
orchestrator = CIAMOrchestrator()


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route("/webhook/jira", methods=["POST"])
def jira_webhook():
    """Receive Jira webhook for issue.created event.

    Jira sends:
    {
      "issue": {
        "key": "NETSK-20",
        "fields": {
          "summary": "...",
          "description": "..."
        }
      }
    }
    """
    try:
        payload = request.get_json() or {}
        logger.info(f"Received webhook: {json.dumps(payload, indent=2)}")

        # Extract issue details
        issue = payload.get("issue") or {}
        issue_key = issue.get("key")
        fields = issue.get("fields") or {}
        summary = fields.get("summary", "")
        description = fields.get("description", "")

        if not issue_key:
            logger.warning("Missing issue key in webhook payload")
            return jsonify({"error": "missing_issue_key"}), 400

        logger.info(f"Processing ticket: {issue_key}")

        # Create ticket object
        ticket = JiraTicket(
            issue_key=issue_key,
            summary=summary,
            description=description or "",
        )

        # Invoke orchestrator
        orchestrator_output = orchestrator.orchestrate(ticket)

        # Post result back to Jira
        jira_client = get_jira_client()
        if jira_client:
            success = jira_client.post_orchestrator_result(issue_key, orchestrator_output.model_dump())
            if success:
                logger.info(f"Posted results to {issue_key}")
            else:
                logger.error(f"Failed to post results to {issue_key}")
        else:
            logger.warning("Jira client not configured — results not posted to ticket")

        # Return orchestrator output to caller (e.g., Lambda, API caller)
        return jsonify(orchestrator_output.model_dump(default=str)), 200

    except Exception as e:
        logger.error(f"Webhook error: {type(e).__name__}: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Local dev server
    logger.info("Starting webhook listener on http://localhost:5000")
    logger.info("Jira should POST to: http://localhost:5000/webhook/jira")
    app.run(debug=True, port=5000)
