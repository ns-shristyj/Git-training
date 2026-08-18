# Complete Orchestrator Flow: Ticket to Diagnosis

**End-to-End Flow: From Jira Ticket Creation → Final Diagnosis Comment**

**Total Time: ~25-35 seconds**

---

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    JIRA TICKET CREATED                              │
│                                                                       │
│   Issue Key: RJT-31                                                 │
│   Summary: "Cannot access Community"                                │
│   Description: "User john@example.com getting 403 Forbidden..."    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │  Webhook: issue.created event          │
        │  webhook_listener.py receives POST     │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  Fetch Full Ticket Details             │
        │  run_ticket.py: fetch_ticket("RJT-31") │
        │  GET /rest/api/3/issue/RJT-31          │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  Create JiraTicket object              │
        │  JiraTicket(issue_key, summary, desc)  │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  ORCHESTRATOR.ORCHESTRATE(ticket)                           │
        │  orchestrator.py:36 - 5-STEP PIPELINE                       │
        └────────┬──────────────────────────────────────┬─────────────┘
                 │                                      │
        ┌────────▼────────────────────────────────┐   │
        │ STEP 1: AGENT 1 (ALWAYS)                │   │
        │ Intent Classifier (v3)                  │   │
        │ • Input: ticket summary + description   │   │
        │ • Output: envelope {intent, email,      │   │
        │           confidence, routing_flags}    │   │
        │ ⏱️  ~2-3 seconds                         │   │
        │ ├─→ Confidence gate: 0.95 > 0.70 ✓      │   │
        │ └─→ auto_escalate: false ✓              │   │
        └────────┬────────────────────────────────┘   │
                 │                                      │
        ┌────────▼──────────────────────────────────┐  │
        │ STEP 2-4: CONDITIONAL DISPATCH (routed)  │  │
        │ Agents 2/3/4 invoked based on routing_flags  │
        │                                            │  │
        │ ├─ AGENT 2 (if invoke_agent_2=true)       │  │
        │ │  Database Agent (v6)                    │  │
        │ │  • Query DynamoDB: NetskopeID table     │  │
        │ │  • Output: account_payload              │  │
        │ │  ⏱️  ~2-3 seconds                        │  │
        │ │  ├─→ account_found: true                │  │
        │ │  └─→ birthright: [Portal, Support]      │  │
        │ │                                          │  │
        │ ├─ AGENT 3 (if invoke_agent_3=true)       │  │
        │ │  Auth0 Agent (v3)                       │  │
        │ │  • Query Auth0 Management API           │  │
        │ │  • Output: auth0_payload                │  │
        │ │  ⏱️  ~2-3 seconds                        │  │
        │ │  ├─→ user_found: true                   │  │
        │ │  └─→ birthright: [Portal, Support]      │  │
        │ │                                          │  │
        │ └─ AGENT 4 (if invoke_agent_4=true)       │  │
        │    Knowledge Base Agent (v14)             │  │
        │    • Compare Salesforce vs Auth0          │  │
        │    • Query Bedrock KB                     │  │
        │    • Output: kb_payload                   │  │
        │    ⏱️  ~4-6 seconds (v13→v14 ABI fixed)    │  │
        │    ├─→ diagnosis: "Missing Community..."  │  │
        │    ├─→ fix_classification: SIMPLE_FIX     │  │
        │    └─→ recommended_actions: [...]         │  │
        └────────┬────────────────────────────────┘   │
                 │                                    │
        ┌────────▼──────────────────────────────────┐ │
        │ ACCUMULATE: output_fields = {             │ │
        │   account_payload: {...},                 │ │
        │   auth0_payload: {...},                   │ │
        │   kb_payload: {...}                       │ │
        │ }                                          │ │
        └────────┬────────────────────────────────┘ │
                 │                                    │
        ┌────────▼────────────────────────────────┐  │
        │ STEP 5: AGENT 5 (UNCONDITIONAL SYNTHESIS)  │
        │ Response Generator (v9)                    │
        │ • Input: ALL outputs from Agents 1-4       │
        │ • Synthesize complete diagnosis            │
        │ • Output: synthesis_payload                │
        │ ⏱️  ~2-3 seconds                           │
        │ ├─→ root_cause: "Missing Community..."     │
        │ ├─→ evidence: [...all findings...]         │
        │ ├─→ jira_description: "formatted text"     │
        │ └─→ escalation_level: "SIMPLE_FIX"         │
        └────────┬────────────────────────────────┘  │
                 │                                    │
        ┌────────▼──────────────────────────────────┐ │
        │ RETURN OrchestratorOutput                   │
        │ • All 5 agent results + synthesis_payload  │
        │ • run_id, timestamps, invocation details   │
        └────────┬──────────────────────────────────┘ │
                 │                                    │
                 └────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │  Jira Client: post_orchestrator_result()  │
        │  jira_client.py:119-143                   │
        │  1. Extract synthesis_payload             │
        │  2. Format as Jira comment               │
        │  3. Call add_comment()                    │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  Jira REST API Call                      │
        │  POST /rest/api/2/issue/RJT-31/comment   │
        │  Request body:                           │
        │  {                                       │
        │    "body": "🤖 CIAM Orchestrator...      │
        │              Root Cause:...              │
        │              Recommended Actions:..."    │
        │  }                                       │
        └────────────┬───────────────────────────┘
                     │
                     ▼ HTTP 201 Created
        ┌────────────────────────────────────────┐
        │  ✅ COMMENT POSTED TO JIRA TICKET       │
        │                                         │
        │  Support team sees complete diagnosis │
        │  with L1 actions ready to execute      │
        └────────────────────────────────────────┘
```

---

## Detailed Step-by-Step Flow

### PHASE 1: TICKET CREATION & WEBHOOK (0-2 seconds)

#### ✅ Step 1: User Creates Ticket in Jira
- **Who:** Support engineer in Jira
- **Trigger:** New issue created in NETSK project
- **Webhook Event:** `issue.created` with full issue payload

#### ✅ Step 2: Webhook Listener Receives Event
- **File:** `webhook_listener.py` line 43-60
- **Endpoint:** `POST /webhook/jira`
- **Payload:** Issue key, summary, description

#### ✅ Step 3: Extract & Fetch Full Ticket
- **File:** `run_ticket.py` line 35-57
- **Action:** `fetch_ticket(issue_key)`
- **API:** `GET /rest/api/3/issue/{key}?fields=summary,description`

#### ✅ Step 4: Create JiraTicket Object
- **File:** `run_ticket.py` line 53-57
- **Object:** `JiraTicket(issue_key, summary, description)`

---

### PHASE 2: ORCHESTRATOR 5-STEP PIPELINE (2-30 seconds)

#### ✅ Step 5: Initialize Orchestrator
- **File:** `orchestrator.py` line 36-41
- **Call:** `CIAMOrchestrator().orchestrate(ticket)`
- **Initializations:** `run_id = uuid.uuid4()`, `output_fields = {}`

#### STEP 1: AGENT 1 (INTENT CLASSIFIER) - ALWAYS RUNS

##### ✅ Step 6: Invoke Agent 1
- **File:** `orchestrator.py` line 43-51
- **Agent ARN:** `arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamintentclassifier-a0h3meCoOo` (v3)
- **Payload:** `{issue_key, summary, description}`
- **AgentCore Call:** `bedrock_agentcore.invoke_agent_runtime(...)`
- **⏱️ Latency:** ~2-3 seconds

##### ✅ Step 7: Agent 1 Returns Routing Envelope
- **Response:** `{intent, extracted_email, confidence, invoke_agent_2/3/4, auto_escalate}`
- **Stored as:** `envelope` variable

##### ✅ Step 8: Confidence Gate Check
- **File:** `orchestrator.py` line 66-80
- **Logic:** `if confidence < 0.70 → escalate to L2`
- **Result:** 0.95 > 0.70 ✓ Continue

---

#### STEP 2-4: CONDITIONAL AGENT DISPATCH

All 3 agents (2/3/4) are conditional and routed by Agent 1's envelope. They execute sequentially.

##### ✅ Step 9: Agent 2 (Database Agent)
- **File:** `orchestrator.py` line 97-114 (dispatch loop iteration 1)
- **Check:** `if envelope.get("invoke_agent_2"): INVOKE`
- **Agent ARN:** `arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamDatabaseAgent-rme27a8env` (v6)
- **Input Builder:** `config.py` line 52-53 → `{email, run_id}`
- **Agent Actions:**
  - Query NetskopeID DynamoDB table
  - Find Salesforce account for email
  - Extract birthright, status, recent_changes
- **Output:** `account_payload = {accounts, data_warnings}`
- **Stored:** `output_fields["account_payload"] = account_payload`
- **⏱️ Latency:** ~2-3 seconds

##### ✅ Step 10: Agent 3 (Auth0 Agent)
- **File:** `orchestrator.py` line 97-114 (dispatch loop iteration 2)
- **Check:** `if envelope.get("invoke_agent_3"): INVOKE`
- **Agent ARN:** `arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamAuth0Agent-lVu70L5GK4` (v3)
- **Input Builder:** `config.py` line 56-57 → `{email}`
- **Agent Actions:**
  - Get M2M credentials from Secrets Manager
  - Call Auth0 Management API
  - Fetch user, birthright, entitlements
- **Output:** `auth0_payload = {users, auth0_warnings}`
- **Stored:** `output_fields["auth0_payload"] = auth0_payload`
- **⏱️ Latency:** ~2-3 seconds

##### ✅ Step 11: Agent 4 (Knowledge Base Agent)
- **File:** `orchestrator.py` line 97-114 (dispatch loop iteration 3)
- **Check:** `if envelope.get("invoke_agent_4"): INVOKE`
- **Agent ARN:** `arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamKnowledgeBaseAgent-VdVt7x7TZ1` (v14)
- **Input Builder:** `config.py` line 60-102 (MERGED from Agents 2 & 3)
  ```
  {account_status, actual_birthright, entitlements, user_found_in_auth0,
   last_sync, last_login, recent_changes, accounts_count, auth0_users_count,
   account_data_warnings, auth0_warnings, intent, raw_input}
  ```
- **Agent Actions:**
  - Compare Salesforce vs Auth0 birthright
  - Query Bedrock KB for recommendations
  - Classify fix complexity
- **Output:** `kb_payload = {diagnosis, fix_classification, recommended_actions}`
- **Stored:** `output_fields["kb_payload"] = kb_payload`
- **⏱️ Latency:** ~4-6 seconds (Python 3.13 ABI fixed in v13→v14)

---

#### STEP 5: AGENT 5 (RESPONSE GENERATOR) - UNCONDITIONAL SYNTHESIS

##### ✅ Step 12: Accumulate All Outputs
- **File:** `orchestrator.py` line 111-114
- **State:** `output_fields = {account_payload, auth0_payload, kb_payload}`

##### ✅ Step 13: Build Agent 5 Input
- **File:** `config.py` line 105-122 function `build_agent5_input()`
- **Input Consolidation:**
  ```python
  {
      "account_payload": {...},      # From Agent 2
      "auth0_payload": {...},         # From Agent 3
      "kb_payload": {...},            # From Agent 4
      "ticket_email": "...",          # From Agent 1 envelope
      "ticket_intent": "..."          # From Agent 1 envelope
  }
  ```

##### ✅ Step 14: Invoke Agent 5
- **File:** `orchestrator.py` line 116-127
- **Agent ARN:** `arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamResponseGenerator-75l4h0HADB` (v9)
- **Important:** Agent 5 ALWAYS runs (unconditional, no routing_flag)
- **⏱️ Latency:** ~2-3 seconds

##### ✅ Step 15: Agent 5 Returns Complete Diagnosis
- **Response:** `synthesis_payload = {root_cause, evidence, jira_description, resolution_path}`
- **Stored:** `output_fields["synthesis_payload"] = synthesis_payload`

##### ✅ Step 16: Orchestrator Returns Final Result
- **File:** `orchestrator.py` line 137-146
- **Returns:** `OrchestratorOutput` with all 5 results
- **Total elapsed:** ~20-25 seconds

---

### PHASE 3: POST TO JIRA (30-35 seconds)

##### ✅ Step 17: Webhook Listener Posts Result
- **File:** `webhook_listener.py` line 85-94
- **Call:** `jira_client.post_orchestrator_result(issue_key, orchestrator_output)`

##### ✅ Step 18: Jira Client Processes Result
- **File:** `jira_client.py` line 119-143
- **Extract:** `synthesis_payload.jira_description`, `escalation_level`
- **Format:** Comment with diagnosis + escalation level + run_id + timestamp

##### ✅ Step 19: Jira API Call
- **File:** `jira_client.py` line 63-79 function `add_comment()`
- **HTTP:** `POST /rest/api/2/issue/RJT-31/comment`
- **Response:** HTTP 201 Created

##### ✅ Step 20: RESULT - Comment Posted to Jira
- **Visible to:** All NETSK project members
- **Content:** Complete diagnosis with L1 recommended actions
- **Status:** ✅ COMPLETE

---

## Key Data Structures

### Agent 1 Output (Envelope)
```python
{
    "intent": "ACCESS_DENIED",
    "extracted_email": "john@example.com",
    "confidence": 0.95,
    "invoke_agent_2": true,
    "invoke_agent_3": true,
    "invoke_agent_4": true,
    "auto_escalate": false
}
```

### Agent 2 Output (Account Data)
```python
{
    "account_found": true,
    "accounts": [{
        "account_id": "001d000000IRFmaQAF",
        "account_status": "Active",
        "birthright": ["Portal", "Support"],
        "active_tenant_count": 2
    }],
    "data_warnings": []
}
```

### Agent 3 Output (Auth0 Data)
```python
{
    "user_found": true,
    "users": [{
        "user_id": "auth0|...",
        "email": "john@example.com",
        "birthright": ["Portal", "Support"],
        "entitlements": ["BasicUser"],
        "last_login": "2026-08-18T10:30:00Z"
    }],
    "auth0_warnings": []
}
```

### Agent 4 Output (Diagnosis)
```python
{
    "diagnosis": "Missing 'Community' birthright keyword",
    "missing_keywords": ["Community"],
    "fix_classification": "SIMPLE_FIX",
    "recommended_actions": [
        "Add 'Community' keyword to Salesforce",
        "Trigger manual sync in Auth0"
    ]
}
```

### Agent 5 Output (Final Synthesis)
```python
{
    "root_cause": "Missing 'Community' birthright keyword in Salesforce",
    "evidence": ["Salesforce: ...", "Auth0: ...", "KB: ..."],
    "jira_description": "Root Cause: ...\n\nEvidence: ...\n\nActions: ...",
    "resolution_path": {
        "escalation_level": "SIMPLE_FIX",
        "l1_actions": ["Add keyword", "Trigger sync"],
        "estimated_resolution_time": "5 minutes"
    },
    "confidence": 0.94
}
```

---

## Data Flow Summary

```
Agents 1-4 Outputs
    ├── Agent 1: envelope {intent, email, routing_flags}
    ├── Agent 2: account_payload {accounts, birthright}
    ├── Agent 3: auth0_payload {users, birthright}
    └── Agent 4: kb_payload {diagnosis, fix_class}
            ↓
        output_fields dict (accumulator)
            ↓
        build_agent5_input() consolidation
            ↓
        Agent 5 (receives ALL context)
            ↓
        synthesis_payload {jira_description, actions}
            ↓
        jira_client.post_orchestrator_result()
            ↓
        Jira REST API: POST /issue/{key}/comment
            ↓
        ✅ Comment visible in Jira ticket
```

---

## Code References

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Webhook Listener | `webhook_listener.py` | 43-97 | Receives issue.created events |
| Ticket Fetch | `run_ticket.py` | 35-57 | Fetches full ticket from Jira |
| Orchestrator Core | `orchestrator.py` | 27-146 | 5-step agent dispatch pipeline |
| Agent Invoker | `agent_invoker.py` | 26-57 | AWS Bedrock AgentCore calls |
| Config (Routing) | `config.py` | 13-165 | Agent ARNs, AGENT_REGISTRY, input builders |
| Jira Client | `jira_client.py` | 26-156 | Posts results back to Jira |
| Schemas | `schemas.py` | — | Pydantic types for I/O |

---

## Timing Breakdown

| Phase | Component | Time |
|-------|-----------|------|
| Webhook → Orchestrator | Ticket fetch + setup | ~1-2s |
| Agent 1 | Intent classifier | ~2-3s |
| Confidence gate | Orchestrator check | <1s |
| Agent 2 | Database lookup | ~2-3s |
| Agent 3 | Auth0 API call | ~2-3s |
| Agent 4 | KB query + diagnosis | ~4-6s |
| Agent 5 | Synthesis | ~2-3s |
| Jira posting | Comment creation + API | ~1-2s |
| **TOTAL** | **End-to-end** | **~25-35s** |

---

## Architecture Notes

1. **All agents execute sequentially** (not parallel) within Bedrock AgentCore
2. **Agent 5 is special:** No routing flag, always runs after dispatch loop
3. **Each agent output accumulates** in `output_fields` dict for downstream use
4. **Agent 4 depends on Agents 2/3:** Receives merged output_fields as input
5. **Agent 5 receives all prior outputs:** Can synthesize complete diagnosis
6. **Jira comment is final step:** Support team sees diagnosis immediately

---

**Last Updated:** 2026-08-18  
**Verified Against:** RJT-30, RJT-31 (real Jira tickets)  
**Deployment:** AWS Bedrock AgentCore (all agents v3+, live)  
**Python Version:** 3.13 (pinned for Agent 4 v13→v14 ABI fix)
