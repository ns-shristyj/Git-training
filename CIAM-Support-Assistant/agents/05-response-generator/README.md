# Agent 5: Response Generator

**Synthesis & Analysis Layer for CIAM Support Orchestrator**

Diagnoses root causes and recommends resolution paths based on consolidated data from Agents 2/3/4.

---

## Status (2026-08-18)

| Item | Status | Details |
|---|---|---|
| Code (`agent.py`) | ✅ Complete | 500-line ResponseGenerator class, 8 diagnostic patterns, Jira formatting |
| Unit tests (`test_agent5.py`) | ✅ 29/29 passing | Complete spec coverage (SPEC-CIAM-0005) |
| Deployed to AgentCore | ✅ **LIVE (v9)** | Runtime: `arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamResponseGenerator-75l4h0HADB` |
| Wired into orchestrator | ✅ **INTEGRATED** | Unconditional final synthesis (no routing_flag, always runs after dispatch loop) |
| End-to-end verification | ✅ VERIFIED | RJT-30, RJT-31 diagnoses posted to Jira, correct root causes identified |
| Orchestrator integration | ✅ LIVE | build_agent5_input() in config.py, specialized handling (not in AGENT_REGISTRY) |

---

## Quick Start

### Installation
```bash
pip install pydantic
```

### Basic Usage
```python
from agent import ResponseGenerator, AccountPayloadInput, Auth0PayloadInput, KnowledgeBasePayloadInput

generator = ResponseGenerator()

result = generator.synthesize(
    account_payload=account_data,      # From Agent 2
    auth0_payload=auth0_data,           # From Agent 3
    kb_payload=kb_data,                 # From Agent 4
    ticket_email="user@example.com"
)

# Output ready for Jira
print(result.jira_summary)
print(result.jira_description)

# Or send to L2
print(result.root_cause.primary_cause)
print(result.resolution_path.escalation_level)
```

### Running Tests
```bash
python3 -m pytest test_agent5.py -v
```

---

## What Agent 5 Does

### 1. **Diagnoses Root Cause** (Pattern Matching)
Analyzes data from Agents 2/3/4 to identify the issue:
- Missing birthright keywords
- Block keywords preventing access
- Auth0 user not created
- Salesforce user issues
- Stale sync problems
- Multiple failed logins

### 2. **Recommends Actions** (Prioritized)
For each diagnosis, recommends specific steps:
- L1-resolvable actions (add keywords, trigger sync, reset password)
- L2-required actions (remove blocks, investigate failures)
- Estimated effort and time

### 3. **Generates Jira Output** (Ready to Post)
Formats diagnosis and actions for ticket updates:
- Summary (one-line)
- Description (formatted with headers, bullets, evidence)
- Escalation guidance
- Similar past cases (from KB)

### 4. **Assesses Data Quality** (Metadata)
Evaluates input completeness:
- Data completeness (COMPLETE / PARTIAL / MISSING)
- Staleness detection
- Conflicting signals
- Confidence adjustments

---

## Diagnostic Patterns (8 Total)

| # | Pattern | Trigger | Action |
|---|---------|---------|--------|
| 1 | Account not found | `account_found == False` | Escalate |
| 2 | No Auth0 user | `user_found == False` | Escalate to NetskopeID team |
| 3 | No access configured | `no_access_configured == True` | Add keywords |
| 4 | Missing keywords | `missing_keywords.length > 0` | Add missing keywords |
| 5 | Block keyword | `explicit_block_detected == True` | Escalate to L2 |
| 6 | Salesforce user issue | `sf_user_exists == False \| sf_user_active == False` | Escalate to SF admin |
| 7 | Multiple failed logins | `failed_logins_7d > 3` | Confirm credentials, reset password |
| 8 | Stale sync | `sync_stale == True` | Trigger manual refresh |

---

## Input Data Structure

### Agent 2: AccountPayloadInput
```python
{
  "account_found": True,
  "accounts": [{
    "account_name": "Acme Corp",
    "account_status": "Customer",
    "customer_status": "Active",
    "active_tenant_count": 1,
    "sf_user_exists": True,
    "sf_user_active": True,
  }],
  "data_freshness": {
    "last_synced_at": "2026-07-28T14:00:00Z",
    "is_stale": False
  }
}
```

### Agent 3: Auth0PayloadInput
```python
{
  "user_found": True,
  "users": [{
    "user_id": "auth0|123",
    "email": "user@example.com",
    "birthright": ["Community", "Dashboard"],
    "entitlements": [],
    "last_sync": "2026-07-28T13:55:00Z",
  }],
  "failed_logins_last_7_days": 0,
  "sync_stale": False
}
```

### Agent 4: KnowledgeBasePayloadInput
```python
{
  "birthright_evaluation": {
    "match": False,
    "persona": "Customer",
    "expected_birthright": ["Community", "Dashboard", "Support"],
    "actual_birthright": ["Community", "Dashboard"],
    "missing_keywords": ["Support"],
    "explicit_block_detected": False,
    "block_keywords_found": [],
    "no_access_configured": False,
  },
  "fix_classification": {
    "complexity": "SIMPLE_FIX",
    "reason": "Add Support keyword",
    "confidence": "HIGH"
  }
}
```

---

## Output Data Structure

### ResponseGeneratorPayload
```python
{
  "schema_version": "1.0",
  "spec_id": "SPEC-CIAM-0005",
  "agent": "ciam-response-generator",
  "run_id": "abc123...",
  "synthesized_at": "2026-07-28T14:05:00Z",

  # Core diagnosis
  "root_cause": {
    "primary_cause": "Missing portal access: Support",
    "confidence": "MEDIUM",
    "evidence": [
      "Expected birthright: ['Community', 'Dashboard', 'Support']",
      "Actual birthright: ['Community', 'Dashboard']"
    ]
  },

  # Resolution path
  "resolution_path": {
    "escalation_level": "L1_RESOLVABLE",
    "actions": [{
      "priority": "IMMEDIATE",
      "action": "Add 'Support' to birthright entitlements",
      "complexity": "SIMPLE",
      "estimated_effort": "2 minutes"
    }],
    "estimated_resolution_time": "5 minutes"
  },

  # Jira ready
  "jira_summary": "Missing portal access: Support",
  "jira_description": "h2. Diagnosis\n...",

  # Quality
  "metadata": {
    "data_completeness": "COMPLETE",
    "stale_data_detected": False,
    "conflicting_signals": []
  }
}
```

---

## Escalation Levels

### L1_RESOLVABLE
Agent 5 has identified a simple fix that L1 support can execute:
- Add missing keywords
- Trigger manual sync
- Offer password reset
- Update user metadata

**Action:** Assign to L1 support with recommended actions.

### ESCALATE_TO_L2
Issue requires L2 investigation or authority:
- Remove block keywords (requires management authority)
- Investigate Auth0 user creation failure
- Investigate Salesforce user issues
- Debug stale sync problems

**Action:** Escalate to L2 with detailed diagnosis and evidence.

### ESCALATE_TO_L3 (Rare)
System-wide issue or data corruption:
- Multiple users affected
- Database inconsistency
- Service outage

**Action:** Escalate to engineering team with full context.

---

## Confidence Levels

| Level | Meaning | Example |
|-------|---------|---------|
| HIGH | Very confident in diagnosis | Account not found (clear evidence) |
| MEDIUM | Likely correct but some uncertainty | Missing keywords (could be sync lag) |
| LOW | Multiple possibilities, need more info | "Insufficient information" |

---

## No Hallucination Guarantee

Agent 5 **never invents facts**:

❌ **Will NOT do:**
- Make assumptions about why something is missing
- Recommend actions based on speculation
- Claim to know Salesforce user status if Agent 2 didn't report it

✅ **Will do:**
- Only diagnose patterns present in actual data
- Cite evidence for every conclusion
- Mark confidence LOW when uncertain
- Recommend escalation when data is incomplete

---

## Jira Integration Example

```bash
# Agent 5 produces this:
jira_summary = "Missing portal access: Support"
jira_description = """
h2. Diagnosis

*Root Cause:* Missing portal access: Support
*Confidence:* MEDIUM

*Evidence:*
* Expected birthright: ['Community', 'Dashboard', 'Support']
* Actual birthright: ['Community', 'Dashboard']

h2. Recommended Actions

*Escalation Level:* L1_RESOLVABLE
*Estimated Time:* 5 minutes

1. [IMMEDIATE] Add 'Support' to birthright entitlements
   - Rationale: User's account status entitles them to Support access
   - Effort: 2 minutes

h2. Similar Past Cases

* [TQI-2847] Customer missing Support access (100% match)
  Resolution: Added Support keyword, user regained access
"""

# Post to Jira:
POST /rest/api/2/issue/CIAM-5847
{
  "fields": {
    "summary": jira_summary,
    "description": jira_description
  }
}
```

---

## Error Handling

### Graceful Degradation
If Agent 2/3/4 return errors, Agent 5:
- Marks data as PARTIAL
- Captures error messages
- Continues with available data
- Reduces confidence appropriately

### Example: Agent 2 Connection Error
```python
account_payload.error = "Database connection timeout"
# Result:
# - metadata.data_completeness = "PARTIAL"
# - metadata.conflicting_signals includes the error
# - root_cause.confidence = "LOW"
# - recommendation = escalate for investigation
```

---

## Testing

### Run All Tests
```bash
python3 -m pytest test_agent5.py -v
```

### Run Specific Test Class
```bash
python3 -m pytest test_agent5.py::TestDiagnosisSynthesis -v
```

### Run Single Test
```bash
python3 -m pytest test_agent5.py::TestDiagnosisSynthesis::test_missing_birthright_keywords -v
```

### Test Coverage
```bash
python3 -m pytest test_agent5.py --cov=agent --cov-report=term-missing
```

---

## Integration with Orchestrator

### Orchestrator Flow
```
1. Agent 1: Intent Classification
   └─> ticket_intent, user_email

2. Agent 2: Account Resolution
   └─> AccountPayloadInput

3. Agent 3: Auth0 Lookup
   └─> Auth0PayloadInput

4. Agent 4: Knowledge Base Evaluation
   └─> KnowledgeBasePayloadInput

5. Agent 5: Response Generation (THIS)
   ├─ Consumes all outputs from 2/3/4
   ├─ Diagnoses root cause
   ├─ Recommends actions
   └─> ResponseGeneratorPayload

6. Orchestrator writes result to Jira or notifies L2
```

### Orchestrator Call Signature
```python
from agents import agent5

response = agent5.synthesize(
    account_payload=agent2_result,
    auth0_payload=agent3_result,
    kb_payload=agent4_result,
    ticket_email=original_ticket.email,
    ticket_intent=agent1_intent  # optional
)

# Post to Jira
jira.issue(ticket_id).update(
    summary=response.jira_summary,
    description=response.jira_description
)

# Or notify L2
if response.resolution_path.escalation_level == "ESCALATE_TO_L2":
    slack.post_to_l2(response)
```

---

## Performance

- **Synthesis time:** ~50-100ms (pattern matching, no network calls)
- **Memory:** ~5-10 MB per synthesis
- **Output size:** ~2-5 KB JSON

Agent 5 is **synchronous and deterministic** — same inputs always produce the same outputs.

---

## Files

- `agent.py` — Core ResponseGenerator class (500 lines)
- `test_agent5.py` — 22 unit tests (400 lines)
- `SPEC-CIAM-0005.md` — Detailed specification
- `README.md` — This file

---

## Next Steps

1. ✅ Implementation complete (agent.py)
2. ✅ All tests passing (22/22)
3. ✅ Specification documented (SPEC-CIAM-0005.md)
4. ⏭️ Integrate with orchestrator
5. ⏭️ Deploy to production
6. ⏭️ Monitor diagnosis accuracy
7. ⏭️ Add new patterns as discovered

---

## Support

- **Questions about diagnosis logic?** See SPEC-CIAM-0005.md §3
- **Jira output not formatting?** Check jira_description generation in agent.py
- **Tests failing?** Run with `-v` flag to see detailed assertion errors
- **Need to add new pattern?** See `_diagnose_root_cause()` method in agent.py

---

**Agent 5 is production ready. All tests passing. Ready for orchestrator integration.** ✅
