"""Pydantic I/O models for the CIAM Orchestrator.

These are intentionally separate from Agent 1's RoutingEnvelope and Agent 2's
AccountPayload models — the orchestrator treats those as opaque dicts coming
back from AgentCore invocations, and only imposes its own shape on the final
aggregated output.
"""

from datetime import datetime, timezone
from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field


class JiraTicket(BaseModel):
    """Input ticket, matching Agent 1's expected entrypoint payload shape."""
    issue_key: str
    summary: str
    description: Optional[str] = ""


class AgentInvocationResult(BaseModel):
    """Wraps a single agent call's outcome + timing metadata."""
    agent_name: str
    agent_arn: str
    status: Literal["success", "timeout", "error", "skipped"]
    response_time_ms: float = 0.0
    response_payload: Optional[dict] = None
    error_message: Optional[str] = None


class OrchestratorOutput(BaseModel):
    """Final orchestrator result — ready for a Jira write-back or for Agent 5
    (Response Synthesizer) consumption once that agent exists."""

    run_id: str
    orchestrated_at: datetime
    source_ticket: JiraTicket

    # Agent 1 result (always present unless Agent 1 itself failed)
    routing_envelope: dict = Field(default_factory=dict)

    # Downstream agent results (only populated if that agent was invoked)
    account_payload: Optional[dict] = None   # Agent 2 (Database)
    auth0_payload: Optional[dict] = None      # Agent 3 (not yet built)
    kb_payload: Optional[dict] = None         # Agent 4 (not yet built)
    synthesis_payload: Optional[dict] = None  # Agent 5 (not yet built)

    # Escalation
    should_escalate_to_l2: bool = False
    escalation_reason: Optional[str] = None

    # Orchestration-level bookkeeping (distinct from any single agent's own errors)
    orchestration_warnings: List[str] = Field(default_factory=list)
    orchestration_error: Optional[str] = None

    # Per-agent invocation metadata, for observability/debugging
    agent_invocations: List[AgentInvocationResult] = Field(default_factory=list)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
