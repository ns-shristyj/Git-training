# Agent 3 — CIAM Auth0 Agent

Implements SPEC-CIAM-0003. Deterministic Auth0 Management API lookup agent —
no LLM reasoning, same pattern as Agent 2 (see spec §4 note).

## Status

| Item | Status |
|---|---|
| Code (`agent.py`) | ✅ Written, matches spec §4–§8 |
| Unit tests (`test_agent3.py`) | ✅ 17/17 passing, mapped to spec §9 acceptance criteria |
| Real Auth0 M2M credentials | ❌ **Blocker** — not yet set up |
| Deployed to AgentCore | ❌ Not yet — blocked on credentials |
| Wired into orchestrator | ⏳ Ready — `AGENT_REGISTRY["agent_3"]` already points at the right input shape; just needs `AGENT_3_ARN` set and `ENABLE_AGENT_3=true` once deployed |

## What's needed before this can go live

1. **An Auth0 M2M (Machine-to-Machine) application** registered in the `nskp`
   Auth0 tenant, authorized for the Management API, with scopes `read:users`
   and `read:logs`.
2. **Store its credentials in AWS Secrets Manager** at path
   `ciam-agent/auth0` as `{"client_id": "...", "client_secret": "..."}`.
3. **Create the IAM execution role** (per spec §4): `secretsmanager:GetSecretValue`
   scoped to `ciam-agent/auth0-*`, plus `kms:Decrypt` on the CIAM CMK. No
   Bedrock, no DynamoDB — same minimal-scope pattern as Agent 2's
   `CIAMAgentDynamoDBAccessRole`.
4. Deploy to AgentCore (same pattern as Agent 1/2: package `agent.py` +
   dependencies, upload to S3, `update-agent-runtime` or `create-agent-runtime`).
5. Set `AGENT_3_ARN` and `ENABLE_AGENT_3=true` for the orchestrator.

## Running the tests

```bash
cd agents/03-auth0-agent
pip install -r requirements.txt pytest
python -m pytest test_agent3.py -v
```

`conftest.py` stubs `bedrock_agentcore.BedrockAgentCoreApp` for local testing —
the real SDK (bundled only in the AWS deployment zip) isn't needed to test
the agent's logic in isolation.

## Key implementation notes

- **Connection priority (§6.3):** federated SSO > `NetskopeID` > `Netskope-Partners`,
  resolved by exclusion (`get_connection_priority`) — see spec OQ-3 for the
  known limitation of this approach.
- **M2M token caching:** cached in process memory for the token's TTL;
  refreshed automatically on `HTTP 401` (§4.1). See spec OQ-1 — this caching
  strategy assumes a long-lived container; if deployed to a cold-start-per-
  invocation Lambda, the cache provides no cross-invocation benefit.
- **Tool 2 (login history) failure is non-fatal** — the payload is still
  returned with Tool 1 data populated (§6 step 4, AC-7).
