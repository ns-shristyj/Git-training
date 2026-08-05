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
AGENT_4_ARN = os.getenv(
    "AGENT_4_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamKnowledgeBaseAgent-VdVt7x7TZ1",
)  # Deployed and tested live. Knowledge Base still holds placeholder docs
# only -- see agents/04-knowledge-base-agent/README.md.
AGENT_5_ARN = os.getenv(
    "AGENT_5_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamResponseGenerator-75l4h0HADB",
)  # Deployed and verified live 2026-08-04. Unlike Agents 2/3/4, Agent 5 has no
# routing_flag in Agent 1's envelope -- it's the final synthesis step, run
# unconditionally after the dispatch loop whenever Agent 4 succeeded (see
# orchestrator.py's dedicated Agent 5 call after the AGENT_REGISTRY loop).

# Confidence gating (SPEC-CIAM-0001 §6): below this, Agent 1 sets auto_escalate
# itself, but the orchestrator re-checks independently as defense-in-depth.
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.70"))

# Per-agent invocation timeout
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "30"))

# Posture guard: orchestrator itself must never request anything beyond
# invoking agent runtimes — no direct DynamoDB/Auth0/etc access.
ALLOWED_ORCHESTRATOR_ACTIONS = frozenset({"bedrock-agentcore:InvokeAgentRuntime"})


def _agent2_input_builder(envelope: dict, output_fields: dict, ticket) -> dict:
    return {"email": envelope.get("extracted_email"), "run_id": envelope.get("run_id", "")}


def _agent3_input_builder(envelope: dict, output_fields: dict, ticket) -> dict:
    return {"email": envelope.get("extracted_email")}


def _agent4_input_builder(envelope: dict, output_fields: dict, ticket) -> dict:
    """Agent 4 (SPEC-CIAM-0004 §3) needs fields from BOTH Agent 2's
    account_payload and Agent 3's auth0_payload, not just Agent 1's
    envelope -- this is why input_builder receives the accumulated
    output_fields dict, unlike Agents 2/3 which only need the envelope."""
    account_payload = output_fields.get("account_payload") or {}
    auth0_payload = output_fields.get("auth0_payload") or {}

    accounts = account_payload.get("accounts") or []
    account = accounts[0] if accounts else {}

    users = auth0_payload.get("users") or []
    user = users[0] if users else {}
    user_found = auth0_payload.get("user_found", False)

    raw_input = " ".join(filter(None, [ticket.summary, ticket.description]))

    return {
        "account_status": account.get("account_status"),
        "active_tenant_count": account.get("active_tenant_count"),
        "actual_birthright": user.get("birthright", []) if user_found else [],
        "entitlements": user.get("entitlements", []) if user_found else [],
        "user_found_in_auth0": user_found,
        "last_sync": user.get("last_sync") if user_found else None,
        "intent": envelope.get("intent"),
        "raw_input": raw_input,
    }


def build_agent5_input(envelope: dict, output_fields: dict, ticket) -> dict:
    """Agent 5 (Response Generator) needs the RAW dicts Agents 2/3/4 already
    returned (account_payload/auth0_payload/kb_payload), plus the ticket
    email/intent from Agent 1's envelope -- it does not use output_key
    dispatch like the AGENT_REGISTRY entries since it has no routing_flag
    (it's an unconditional final step, not one Agent 1 opts into per-ticket).

    NOTE: orchestrator/agent5_builder.py exists but is unimportable (wrong
    module paths -- `agents.agent2_database_agent` doesn't exist; real dirs
    are `agents/02-database-agent` etc., not valid Python package names
    either way). This function replaces it for actual orchestrator use."""
    return {
        "account_payload": output_fields.get("account_payload") or {},
        "auth0_payload": output_fields.get("auth0_payload") or {},
        "kb_payload": output_fields.get("kb_payload") or {},
        "ticket_email": envelope.get("extracted_email"),
        "ticket_intent": envelope.get("intent"),
    }


# Agent Registry — the single source of truth for "what downstream agents exist
# and how to invoke them". Each entry:
#   name            — human-readable agent name (used in logs/metrics)
#   arn             — deployed AgentCore runtime ARN (None if not yet built)
#   enabled         — feature flag; false skips invocation even if the routing
#                     flag is true (useful for staged rollout of new agents)
#   routing_flag    — key in Agent 1's RoutingEnvelope that gates this call
#   input_builder   — function(envelope, output_fields, ticket) -> dict payload
#                     to send to the agent. output_fields accumulates prior
#                     agents' results *within this same dispatch loop*, so an
#                     agent can depend on an earlier agent's output only if it
#                     appears LATER in this dict (insertion order == dispatch
#                     order). Agent 4 depends on Agent 2 and Agent 3's outputs
#                     this way — it must stay after both in this dict.
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
        "enabled": os.getenv("ENABLE_AGENT_4", "true").lower() == "true",
        "routing_flag": "invoke_agent_4",
        "input_builder": _agent4_input_builder,
        "output_key": "kb_payload",
    },
}
