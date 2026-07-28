"""
Agent 5 Input Builder — Orchestrator Integration

Constructs Agent 5 (Response Generator) inputs from consolidated
payloads from Agents 2, 3, and 4.

This builder is called by the orchestrator after all upstream agents
have completed their work.
"""

import logging
from typing import Dict, Any, Optional

from agents.agent2_database_agent.agent import AccountPayload
from agents.agent3_auth0_agent.agent import Auth0Payload
from agents.agent4_knowledge_base_agent.agent import KnowledgeBasePayload

logger = logging.getLogger("agent5-builder")


def build_agent5_input(
    agent2_output: AccountPayload,
    agent3_output: Auth0Payload,
    agent4_output: KnowledgeBasePayload,
    ticket_email: str,
    ticket_intent: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build Agent 5 input from consolidated upstream payloads.

    Args:
        agent2_output: AccountPayload from Agent 2 (database records)
        agent3_output: Auth0Payload from Agent 3 (Auth0 metadata)
        agent4_output: KnowledgeBasePayload from Agent 4 (KB evaluation)
        ticket_email: Original ticket email address
        ticket_intent: User's stated intent (from Agent 1, optional)
        run_id: Run ID for tracing (optional, AgentCore will provide)

    Returns:
        Dictionary ready to pass to Agent 5 handler
    """
    payload = {
        "account_payload": agent2_output.dict(),
        "auth0_payload": agent3_output.dict(),
        "kb_payload": agent4_output.dict(),
        "ticket_email": ticket_email,
    }

    if ticket_intent:
        payload["ticket_intent"] = ticket_intent

    if run_id:
        payload["run_id"] = run_id

    logger.info(
        f"Built Agent 5 input for {ticket_email} "
        f"(intent: {ticket_intent or 'unknown'})"
    )

    return payload


def validate_agent5_inputs(
    agent2_output: AccountPayload,
    agent3_output: Auth0Payload,
    agent4_output: KnowledgeBasePayload,
) -> tuple[bool, Optional[str]]:
    """
    Validate that all required upstream outputs are present.

    Args:
        agent2_output: From Agent 2
        agent3_output: From Agent 3
        agent4_output: From Agent 4

    Returns:
        Tuple of (is_valid, error_message)
    """
    if agent2_output is None:
        return False, "Agent 2 output (AccountPayload) is missing"

    if agent3_output is None:
        return False, "Agent 3 output (Auth0Payload) is missing"

    if agent4_output is None:
        return False, "Agent 4 output (KnowledgeBasePayload) is missing"

    # Allow partial data within each payload (error fields can be set)
    # Agent 5 will handle gracefully
    logger.info("Agent 5 inputs valid — all upstream payloads present")
    return True, None
