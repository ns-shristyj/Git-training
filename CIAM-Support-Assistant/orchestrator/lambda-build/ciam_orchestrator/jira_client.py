"""Jira API client for posting orchestrator results back to tickets.

Handles authentication, comment posting, and ticket updates.
"""

import os
import logging
import base64
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("ciam-jira-client")

# Configuration from environment
JIRA_INSTANCE_URL = os.getenv("JIRA_INSTANCE_URL", "").rstrip("/")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "NETSK-20")

# Validation
if not all([JIRA_INSTANCE_URL, JIRA_EMAIL, JIRA_API_TOKEN]):
    logger.warning("Jira credentials incomplete — post-back disabled")


class JiraClient:
    """Posts orchestrator findings back to Jira tickets."""

    def __init__(self, instance_url: str, email: str, api_token: str, verify_ssl: bool = True):
        self.instance_url = instance_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self.auth = HTTPBasicAuth(email, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[dict]:
        """Generic request wrapper with error handling."""
        url = f"{self.instance_url}/rest/api/2{endpoint}"
        try:
            response = requests.request(
                method,
                url,
                auth=self.auth,
                headers=self.headers,
                verify=self.verify_ssl,
                timeout=30,
                **kwargs,
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Jira API error: {e}")
            return None

    def get_issue(self, issue_key: str) -> Optional[dict]:
        """Fetch issue details."""
        return self._request("GET", f"/issues/{issue_key}")

    def add_comment(self, issue_key: str, comment_body: str) -> bool:
        """Post a comment to a Jira issue.

        Args:
            issue_key: e.g., 'NETSK-20'
            comment_body: Plain text comment

        Returns:
            True if successful, False otherwise
        """
        payload = {"body": comment_body}
        result = self._request("POST", f"/issue/{issue_key}/comment", json=payload)
        if result:
            logger.info(f"Posted comment to {issue_key}")
            return True
        logger.error(f"Failed to post comment to {issue_key}")
        return False

    def update_issue(
        self,
        issue_key: str,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[list] = None,
    ) -> bool:
        """Update issue fields.

        Args:
            issue_key: e.g., 'NETSK-20'
            status: e.g., 'In Progress', 'Done'
            assignee: account ID or email
            labels: list of label strings

        Returns:
            True if successful, False otherwise
        """
        update_fields = {}

        if status:
            update_fields["status"] = {"name": status}
        if assignee:
            update_fields["assignee"] = {"name": assignee}
        if labels:
            update_fields["labels"] = labels

        if not update_fields:
            return True

        payload = {"fields": update_fields}
        result = self._request("PUT", f"/issues/{issue_key}", json=payload)
        if result is not None:
            logger.info(f"Updated {issue_key}: {update_fields}")
            return True
        logger.error(f"Failed to update {issue_key}")
        return False

    def post_orchestrator_result(self, issue_key: str, orchestrator_output: dict) -> bool:
        """Post full orchestrator result as a Jira comment.

        Args:
            issue_key: e.g., 'NETSK-20'
            orchestrator_output: full OrchestratorOutput dict from orchestrator.orchestrate()

        Returns:
            True if successful, False otherwise
        """
        synthesis = orchestrator_output.get("synthesis_payload") or {}
        jira_desc = synthesis.get("jira_description", "No diagnosis available")
        escalation_level = synthesis.get("resolution_path", {}).get("escalation_level", "UNKNOWN")

        # Format as Jira comment (plain text for now; ADF/markdown in production)
        comment = f"""🤖 CIAM Orchestrator Diagnosis

{jira_desc}

---
*Escalation Level:* {escalation_level}
*Run ID:* {orchestrator_output.get('run_id')}
*Timestamp:* {orchestrator_output.get('orchestrated_at')}
"""
        return self.add_comment(issue_key, comment)


# Singleton instance
_client = None


def get_jira_client() -> Optional[JiraClient]:
    """Get or create Jira client from environment credentials."""
    global _client
    if _client is None and JIRA_INSTANCE_URL and JIRA_EMAIL and JIRA_API_TOKEN:
        _client = JiraClient(JIRA_INSTANCE_URL, JIRA_EMAIL, JIRA_API_TOKEN)
    return _client
