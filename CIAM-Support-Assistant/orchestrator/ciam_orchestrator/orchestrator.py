"""Core orchestration logic: Agent 1 (classify) -> confidence gate ->
conditionally Agent 2/3/4 (execute) -> aggregate.

Mirrors SPEC-CIAM-0001's binding note on the orchestrator: `auto_escalate:
true` from Agent 1 is a hard stop — Agents 2-4 are skipped regardless of
their individual invoke_agent_* flags.
"""

import logging
import uuid

from .agent_invoker import AgentInvoker
from .config import (
    AGENT_1_ARN,
    AGENT_REGISTRY,
    CONFIDENCE_THRESHOLD,
    AGENT_TIMEOUT_SECONDS,
)
from .errors import ValidationError
from .schemas import JiraTicket, OrchestratorOutput, AgentInvocationResult, now_utc

logger = logging.getLogger("ciam-orchestrator")


class CIAMOrchestrator:
    """Dispatches a Jira ticket through Agent 1, then conditionally through
    whichever of Agents 2/3/4 the routing envelope calls for."""

    def __init__(self):
        self.invoker_1 = AgentInvoker(
            AGENT_1_ARN, "ciam-intent-classifier", timeout_sec=AGENT_TIMEOUT_SECONDS
        )

    def orchestrate(self, ticket: JiraTicket) -> OrchestratorOutput:
        run_id = str(uuid.uuid4())
        invocations: list[AgentInvocationResult] = []
        warnings: list[str] = []

        self._validate_input(ticket)

        # Step 1: classify via Agent 1
        logger.info(f"[{run_id}] Invoking Agent 1 (ciam-intent-classifier)")
        agent1_result = self.invoker_1.invoke(
            {
                "issue_key": ticket.issue_key,
                "summary": ticket.summary,
                "description": ticket.description or "",
            }
        )
        invocations.append(agent1_result)

        if agent1_result.status != "success":
            return OrchestratorOutput(
                run_id=run_id,
                orchestrated_at=now_utc(),
                source_ticket=ticket,
                should_escalate_to_l2=True,
                escalation_reason=f"agent1_failed: {agent1_result.error_message}",
                agent_invocations=invocations,
            )

        envelope = agent1_result.response_payload or {}

        # Step 2: confidence gate (defense-in-depth re-check of Agent 1's own gating)
        confidence = envelope.get("confidence", 0.0)
        if confidence < CONFIDENCE_THRESHOLD:
            logger.info(
                f"[{run_id}] confidence {confidence} < {CONFIDENCE_THRESHOLD} -> escalate"
            )
            return OrchestratorOutput(
                run_id=run_id,
                orchestrated_at=now_utc(),
                source_ticket=ticket,
                routing_envelope=envelope,
                should_escalate_to_l2=True,
                escalation_reason=envelope.get("escalation_reason") or "low_confidence",
                agent_invocations=invocations,
            )

        # Step 3: honor Agent 1's own auto_escalate as a hard stop (binding per spec)
        if envelope.get("auto_escalate", False):
            logger.info(f"[{run_id}] Agent 1 set auto_escalate=true -> escalate")
            return OrchestratorOutput(
                run_id=run_id,
                orchestrated_at=now_utc(),
                source_ticket=ticket,
                routing_envelope=envelope,
                should_escalate_to_l2=True,
                escalation_reason=envelope.get("escalation_reason", "agent1_auto_escalate"),
                agent_invocations=invocations,
            )

        # Step 4: dispatch to whichever downstream agents the envelope calls for
        output_fields: dict = {}
        for agent_key, agent_cfg in AGENT_REGISTRY.items():
            if not agent_cfg["enabled"]:
                continue
            if not envelope.get(agent_cfg["routing_flag"], False):
                continue

            invoker = AgentInvoker(
                agent_cfg["arn"], agent_cfg["name"], timeout_sec=AGENT_TIMEOUT_SECONDS
            )
            payload = agent_cfg["input_builder"](envelope)
            logger.info(f"[{run_id}] Invoking {agent_cfg['name']}")
            result = invoker.invoke(payload)
            invocations.append(result)

            if result.status == "success":
                output_fields[agent_cfg["output_key"]] = result.response_payload
            else:
                warnings.append(f"{agent_cfg['name']} {result.status}: {result.error_message}")

        return OrchestratorOutput(
            run_id=run_id,
            orchestrated_at=now_utc(),
            source_ticket=ticket,
            routing_envelope=envelope,
            should_escalate_to_l2=False,
            orchestration_warnings=warnings,
            agent_invocations=invocations,
            **output_fields,
        )

    @staticmethod
    def _validate_input(ticket: JiraTicket) -> None:
        if not ticket.issue_key:
            raise ValidationError("Missing issue_key")
        if not ticket.summary and not ticket.description:
            raise ValidationError("Ticket has neither summary nor description")
