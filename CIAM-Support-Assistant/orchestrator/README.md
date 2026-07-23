# CIAM Orchestrator

Dispatches a Jira ticket through Agent 1 (Intent Classifier), then
conditionally through Agents 2/3/4 based on Agent 1's `RoutingEnvelope`,
per the binding note in `specs/01-Intent-Classifier-Agent/spec.md` (§1, OQ-6):

> "This consumer obligation is binding on whichever spec defines the
> orchestrator/Agent 5 behavior, even though that spec does not yet exist."

## Status

| Component | Status |
|---|---|
| Agent 1 (Intent Classifier) | ✅ Deployed, wired in |
| Agent 2 (Database Agent) | ✅ Deployed, wired in |
| Agent 3 (Auth0 Agent) | ⏳ Not built — registry slot ready |
| Agent 4 (Knowledge Base Agent) | ⏳ Not built — registry slot ready |
| Agent 5 (Response Synthesizer) | ⏳ Not built — not yet wired |

## Architecture

```
JiraTicket -> Agent 1 (classify) -> RoutingEnvelope
                                        |
                          confidence < 0.70 OR auto_escalate=true?
                                        |
                          yes -> escalate to L2 (skip everything below)
                          no  -> for each enabled agent in AGENT_REGISTRY:
                                    if envelope[routing_flag]: invoke it
                                        |
                                 aggregate into OrchestratorOutput
```

The **Agent Registry** (`ciam_orchestrator/config.py`) is the extensibility
seam — adding Agent 3 or 4 later is a config change (ARN + `enabled: true`),
not a code change to `orchestrator.py`'s dispatch loop.

## Files

- `ciam_orchestrator/schemas.py` — Pydantic I/O models (`JiraTicket`, `OrchestratorOutput`, `AgentInvocationResult`)
- `ciam_orchestrator/config.py` — Agent ARNs, confidence threshold, the Agent Registry
- `ciam_orchestrator/agent_invoker.py` — thin wrapper over `bedrock-agentcore` `invoke_agent_runtime`, with posture guard + timeout handling
- `ciam_orchestrator/orchestrator.py` — core dispatch logic
- `ciam_orchestrator/handler.py` — Lambda entry point (also runnable directly for a smoke test)
- `tests/test_orchestrator.py` — unit tests (all agent calls mocked)
- `scripts/local_test.py` — CLI script that hits the **real** deployed Agent 1/2

## Running locally

```bash
cd orchestrator
pip install -r requirements.txt
python -m pytest tests/ -v

# Hits the real deployed agents:
python scripts/local_test.py \
  --issue-key TQI-9001 \
  --summary "User cannot reset password" \
  --description "Customer at user.account@example.com unable to reset password, getting error: 'Reset token invalid'."
```

## Posture guard

The orchestrator itself is restricted (via `assert_posture()` in
`agent_invoker.py`) to only ever call
`bedrock-agentcore:InvokeAgentRuntime` — it has no direct DynamoDB, Auth0, or
other AWS service access. This mirrors the same defense-in-depth pattern used
inside Agent 1 and Agent 2.
