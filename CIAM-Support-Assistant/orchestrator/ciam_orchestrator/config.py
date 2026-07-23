"""Configuration and the Agent Registry.

The registry is the extensibility seam: adding Agent 3/4/5 later should only
require a new entry here (plus setting its ARN env var) — no changes to
orchestrator.py's dispatch loop.
"""

import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Deployed agent ARNs (Agent 1 and 2 are live; 3/4/5 are placeholders until built)
AGENT_1_ARN = os.getenv(
    "AGENT_1_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamintentclassifier-a0h3meCoOo",
)
AGENT_2_ARN = os.getenv(
    "AGENT_2_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamDatabaseAgent-rme27a8env",
)
AGENT_3_ARN = os.getenv(
    "AGENT_3_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamAuth0Agent-lVu70L5GK4",
)  # Deployed, but Secrets Manager still holds placeholder credentials —
# see agents/03-auth0-agent/README.md. Real invocations will return
# error: "auth0_token_acquisition_failed" until real Auth0 M2M creds are set.
AGENT_4_ARN = os.getenv("AGENT_4_ARN")  # Knowledge Base Agent — not yet deployed
AGENT_5_ARN = os.getenv("AGENT_5_ARN")  # Response Synthesizer — not yet deployed

# Confidence gating (SPEC-CIAM-0001 §6): below this, Agent 1 sets auto_escalate
# itself, but the orchestrator re-checks independently as defense-in-depth.
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.70"))

# Per-agent invocation timeout
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "30"))

# Posture guard: orchestrator itself must never request anything beyond
# invoking agent runtimes — no direct DynamoDB/Auth0/etc access.
ALLOWED_ORCHESTRATOR_ACTIONS = frozenset({"bedrock-agentcore:InvokeAgentRuntime"})


def _agent2_input_builder(envelope: dict) -> dict:
    return {"email": envelope.get("extracted_email"), "run_id": envelope.get("run_id", "")}


def _agent3_input_builder(envelope: dict) -> dict:
    return {"email": envelope.get("extracted_email")}


def _agent4_input_builder(envelope: dict) -> dict:
    return {"intent": envelope.get("intent"), "portal_hint": envelope.get("portal_hint")}


# Agent Registry — the single source of truth for "what downstream agents exist
# and how to invoke them". Each entry:
#   name            — human-readable agent name (used in logs/metrics)
#   arn             — deployed AgentCore runtime ARN (None if not yet built)
#   enabled         — feature flag; false skips invocation even if the routing
#                     flag is true (useful for staged rollout of new agents)
#   routing_flag    — key in Agent 1's RoutingEnvelope that gates this call
#   input_builder   — function(envelope) -> dict payload to send to the agent
#   output_key      — field name on OrchestratorOutput to store the response under
AGENT_REGISTRY = {
    "agent_2": {
        "name": "ciam-database-agent",
        "arn": AGENT_2_ARN,
        "enabled": os.getenv("ENABLE_AGENT_2", "true").lower() == "true",
        "routing_flag": "invoke_agent_2",
        "input_builder": _agent2_input_builder,
        "output_key": "account_payload",
    },
    "agent_3": {
        "name": "ciam-auth0-agent",
        "arn": AGENT_3_ARN,
        "enabled": os.getenv("ENABLE_AGENT_3", "true").lower() == "true",
        "routing_flag": "invoke_agent_3",
        "input_builder": _agent3_input_builder,
        "output_key": "auth0_payload",
    },
    "agent_4": {
        "name": "ciam-kb-agent",
        "arn": AGENT_4_ARN,
        "enabled": os.getenv("ENABLE_AGENT_4", "false").lower() == "true",
        "routing_flag": "invoke_agent_4",
        "input_builder": _agent4_input_builder,
        "output_key": "kb_payload",
    },
}
