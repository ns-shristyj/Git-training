"""Lambda entry point. Expects a Jira webhook-shaped event (already flattened
to {issue_key, summary, description} — actual Jira `issue_created` webhook
field-mapping happens in front of this, e.g. in API Gateway's mapping template
or a thin adapter Lambda).
"""

import json
import logging
import uuid

from pydantic import ValidationError as PydanticValidationError

from .errors import ValidationError
from .orchestrator import CIAMOrchestrator
from .schemas import JiraTicket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ciam-orchestrator")


def lambda_handler(event: dict, context=None) -> dict:
    run_id = getattr(context, "aws_request_id", None) or str(uuid.uuid4())

    try:
        ticket = JiraTicket(**event)
        orchestrator = CIAMOrchestrator()
        output = orchestrator.orchestrate(ticket)

        return {
            "statusCode": 200,
            "body": json.dumps(output.model_dump(), default=str),
        }

    except (ValidationError, PydanticValidationError) as e:
        logger.warning(f"[{run_id}] Validation error: {e}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e), "run_id": run_id}),
        }

    except Exception as e:
        logger.error(f"[{run_id}] Unhandled error: {type(e).__name__}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "internal_error", "run_id": run_id, "detail": str(e)}
            ),
        }


if __name__ == "__main__":
    # Quick local smoke test
    sample_event = {
        "issue_key": "TQI-9001",
        "summary": "User cannot reset password",
        "description": (
            "Customer at user.account@example.com unable to reset password, "
            "getting error: 'Reset token invalid'. Issue occurred after Nov 1 "
            "CIAM migration. User works in support team."
        ),
    }
    result = lambda_handler(sample_event)
    print(json.dumps(json.loads(result["body"]), indent=2))
