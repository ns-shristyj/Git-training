"""AWS Lambda handler for the CIAM orchestrator webhook.

Receives Jira webhook events, invokes the orchestrator, and posts results back to Jira.
Deploy as: AWS Lambda function with API Gateway trigger.
"""

import json
import os
import sys
import logging
from base64 import b64encode

# Ensure ciam_orchestrator is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ciam_orchestrator.orchestrator import CIAMOrchestrator
from ciam_orchestrator.schemas import JiraTicket
from ciam_orchestrator.jira_client import get_jira_client

logger = logging.getLogger()
logger.setLevel(logging.INFO)

orchestrator = CIAMOrchestrator()


def lambda_handler(event, context):
    """
    AWS Lambda entrypoint for Jira webhooks.

    Receives POST from Jira webhook → processes via orchestrator → posts result back.

    Event structure (from API Gateway + Jira webhook):
    {
      "body": "{\"issue\": {\"key\": \"NETSK-20\", \"fields\": {...}}}"
    }
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Parse request body
        if isinstance(event.get("body"), str):
            payload = json.loads(event["body"])
        else:
            payload = event.get("body", {})

        # Extract issue details
        issue = payload.get("issue") or {}
        issue_key = issue.get("key")
        fields = issue.get("fields") or {}
        summary = fields.get("summary", "")
        description = fields.get("description", "")
        labels = fields.get("labels", [])

        if not issue_key:
            logger.warning("Missing issue key in webhook payload")
            return response(400, {"error": "missing_issue_key"})

        # Check for CIAM-OPS label - only process CIAM tickets
        ciam_labels = {"CIAM-OPS", "IAM-ops"}
        has_ciam_label = bool(ciam_labels & set(labels)) if labels else False

        if not has_ciam_label:
            logger.info(f"Skipping {issue_key}: missing CIAM-OPS or IAM-ops label")
            return response(200, {
                "status": "skipped",
                "reason": "ticket_not_ciam_labeled",
                "ticket": issue_key,
                "message": "Only tickets with CIAM-OPS or IAM-ops label are processed"
            })

        logger.info(f"Processing ticket: {issue_key}")

        # Create ticket object
        ticket = JiraTicket(
            issue_key=issue_key,
            summary=summary,
            description=description or "",
        )

        # Invoke orchestrator
        orchestrator_output = orchestrator.orchestrate(ticket)
        logger.info(f"Orchestrator complete for {issue_key}")

        # Post result back to Jira
        jira_client = get_jira_client()
        if jira_client:
            success = jira_client.post_orchestrator_result(
                issue_key, orchestrator_output.model_dump()
            )
            if success:
                logger.info(f"Posted results to {issue_key}")
            else:
                logger.error(f"Failed to post results to {issue_key}")
        else:
            logger.warning("Jira client not configured — results not posted to ticket")

        # Return success
        return response(
            200,
            {
                "status": "success",
                "ticket": issue_key,
                "run_id": orchestrator_output.run_id,
            },
        )

    except Exception as e:
        logger.error(f"Handler error: {type(e).__name__}: {e}", exc_info=True)
        return response(500, {"error": str(e)})


def response(status_code, body):
    """Format Lambda response for API Gateway."""
    return {
        "statusCode": status_code,
        "body": json.dumps(body),
        "headers": {"Content-Type": "application/json"},
    }


# Local testing (for debugging)
if __name__ == "__main__":
    test_event = {
        "body": json.dumps(
            {
                "issue": {
                    "key": "NETSK-20",
                    "fields": {
                        "summary": "Test: User cannot access Community portal",
                        "description": "Testing orchestrator flow",
                    },
                }
            }
        )
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
