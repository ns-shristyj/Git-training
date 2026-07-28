# SPEC-CIAM-0005: Response Generator Agent

**Version:** 0.1.0  
**Status:** Implementation Complete  
**Test Coverage:** 22/22 PASSING ✅

---

## 1. Overview

Agent 5 is the **synthesis and response generation** layer of the CIAM orchestrator. It:

1. **Receives** ALL Pydantic-validated JSON outputs from Agents 2/3/4
2. **Diagnoses** the root cause without hallucination (stays true to the facts)
3. **Recommends** specific, prioritized actions with effort estimates
4. **Outputs** structured diagnosis + Jira update + escalation guidance

Agent 5 uses heuristic pattern matching (not LLM) to synthesize, ensuring deterministic, auditable diagnosis.

---

## 2. Input Schema

Agent 5 receives consolidated data from the orchestrator:

### From Agent 2 (AccountPayloadInput)
```python
AccountPayloadInput:
  account_found: bool              # Account exists in Salesforce/NetskopeID
  accounts: List[AccountRecord]    # Account details (status, tenants, SF user state)
  data_freshness: DataFreshness    # When data was last synced
  data_warnings: List[str]         # Warnings from Agent 2
  error: Optional[str]             # Any errors during fetch
```

### From Agent 3 (Auth0PayloadInput)
```python
Auth0PayloadInput:
  user_found: bool                          # User exists in Auth0
  users: List[Auth0UserRecord]              # Auth0 metadata (birthright, entitlements, logins)
  failed_logins_last_7_days: int            # Number of failed login attempts
  sync_stale: bool                          # Auth0 sync older than expected
  auth0_warnings: List[str]                 # Warnings from Agent 3
  error: Optional[str]                      # Any errors during fetch
```

### From Agent 4 (KnowledgeBasePayloadInput)
```python
KnowledgeBasePayloadInput:
  birthright_evaluation: BirthrightEvaluation
    ├─ match: bool                # Birthright correct?
    ├─ persona: str               # Derived persona (Customer, Prospect, Partner, etc.)
    ├─ expected_birthright: []    # What they should have
    ├─ actual_birthright: []      # What they actually have
    ├─ missing_keywords: []       # Missing portals
    ├─ extra_keywords: []         # Unexpected portals
    ├─ block_keywords_found: []   # Block keywords preventing access
    └─ no_access_configured: bool # No keywords at all
  
  fix_classification: FixClassification
    ├─ complexity: enum           # SIMPLE_FIX, ESCALATE_TO_L2, NO_GAP
    ├─ recommended_actions: []    # From KB pattern matching
    └─ confidence: enum           # HIGH, MEDIUM, LOW
  
  knowledge_base_results: KnowledgeBaseResults
    ├─ relevant_docs: []          # KB documents matching the issue
    └─ similar_past_tickets: []   # Similar resolved issues
```

---

## 3. Diagnostic Patterns

Agent 5 identifies root causes using **ordered pattern matching** (first match wins):

### Pattern 1: Account Not Found
**Triggers:** `account_found == False`  
**Root Cause:** "Account not found in Netskope or Salesforce"  
**Confidence:** HIGH  
**Action:** Escalate to investigate  

### Pattern 2: No Auth0 User
**Triggers:** `user_found == False`  
**Root Cause:** "User not created in Auth0"  
**Confidence:** HIGH  
**Action:** Escalate to NetskopeID Sync Team (JIT provisioning may have failed)  

### Pattern 3: No Access Configured
**Triggers:** `birthright_evaluation.no_access_configured == True`  
**Root Cause:** "No portal access configured"  
**Confidence:** HIGH  
**Action:** Add appropriate keywords to birthright  

### Pattern 4: Missing Portal Access
**Triggers:** `len(birthright_evaluation.missing_keywords) > 0`  
**Root Cause:** "Missing portal access: [list of missing portals]"  
**Confidence:** MEDIUM  
**Actions:** Add missing keywords to birthright; if sync stale, trigger refresh  

### Pattern 5: Block Keyword Detected
**Triggers:** `birthright_evaluation.explicit_block_detected == True`  
**Root Cause:** "Access explicitly blocked: [block keywords]"  
**Confidence:** HIGH  
**Action:** Review and remove block keywords (requires L2 authority)  

### Pattern 6: Salesforce User Missing/Inactive
**Triggers:** `sf_user_exists == False OR sf_user_active == False`  
**Root Cause:** "Salesforce user missing or deactivated"  
**Confidence:** HIGH  
**Action:** Escalate to Salesforce Admin  

### Pattern 7: Multiple Failed Logins
**Triggers:** `failed_logins_last_7_days > 3`  
**Root Cause:** "Multiple failed login attempts"  
**Confidence:** MEDIUM  
**Actions:** Confirm credentials; offer password reset if needed  

### Pattern 8: Stale Sync
**Triggers:** `sync_stale == True` (during diagnosis of missing keywords)  
**Secondary Cause:** "Auth0 sync may be stale"  
**Action:** Trigger manual NetskopeID sync refresh  

---

## 4. Output Schema

Agent 5 returns a **ResponseGeneratorPayload**:

```python
ResponseGeneratorPayload:
  schema_version: "1.0"
  spec_id: "SPEC-CIAM-0005"
  agent: "ciam-response-generator"
  run_id: str                      # Unique run identifier
  synthesized_at: datetime         # When analysis completed
  
  # Core diagnosis
  root_cause: RootCauseDiagnosis
    ├─ primary_cause: str          # Main issue
    ├─ secondary_causes: []        # Contributing factors
    ├─ evidence: []                # Facts supporting diagnosis
    └─ confidence: enum            # HIGH, MEDIUM, LOW
  
  # Resolution path
  resolution_path: ResolutionPath
    ├─ escalation_level: enum      # L1_RESOLVABLE, ESCALATE_TO_L2, ESCALATE_TO_L3
    ├─ actions: [RecommendedAction]
    │  ├─ priority: enum           # IMMEDIATE, NEXT, OPTIONAL
    │  ├─ action: str              # The specific fix
    │  ├─ rationale: str           # Why this action
    │  ├─ complexity: enum         # SIMPLE, COMPLEX
    │  └─ estimated_effort: str    # Time estimate (e.g., "2 minutes")
    ├─ estimated_resolution_time: str
    └─ fallback_escalation: str    # Team to escalate to if actions fail
  
  # Supporting information
  similar_past_cases: [SimilarPastCase]  # From KB
  
  # Jira integration
  jira_summary: str                # One-line summary for ticket title
  jira_description: str            # Formatted description for ticket body
  
  # Quality metadata
  metadata: AnalysisMetadata
    ├─ data_completeness: enum     # COMPLETE, PARTIAL, MISSING
    ├─ stale_data_detected: bool
    ├─ conflicting_signals: []     # Warnings/inconsistencies
    └─ reasoning_notes: []         # Analysis notes
  
  error: Optional[str]             # Any synthesis errors
```

---

## 5. Resolution Recommendations

### L1-Resolvable Actions
- Add missing birthright keywords (2-5 minutes)
- Trigger manual sync refresh (3 minutes)
- Offer password reset to user (5 minutes)
- Update user metadata in Auth0 (5-10 minutes)

### L2-Required Actions
- Remove block keywords (15-30 minutes, requires management authority)
- Investigate Auth0 user creation failure (30 minutes, requires system access)
- Investigate Salesforce user issues (30 minutes, requires SF admin)
- Debug failed login patterns (15-30 minutes)

### Escalation Routing
```
├─ L1_RESOLVABLE
│  └─ Actions: birthright additions, sync triggers, password resets
├─ ESCALATE_TO_L2
│  ├─ Block keyword review
│  ├─ Auth0/NetskopeID investigation
│  └─ Stale sync investigation
└─ ESCALATE_TO_L3 (rare)
   └─ System-wide issues or data corruption
```

---

## 6. Data Quality Assessment

Agent 5 evaluates input data quality:

### Completeness Levels
- **COMPLETE**: All agents returned data, no errors
- **PARTIAL**: One agent errored or incomplete (can still diagnose)
- **MISSING**: Critical data missing (user not found, account not found)

### Freshness Checks
- Detects if Auth0 sync is stale (> 7 days)
- Detects if database data is old (> 24 hours)
- Notes when data may affect diagnosis confidence

### Conflict Detection
- Flags disagreements between agents (e.g., user in SF but not Auth0)
- Captures all warnings from Agents 2/3/4
- Reduces confidence when conflicts present

---

## 7. Jira Integration

Agent 5 outputs are **ready to paste into Jira tickets**:

### Jira Summary
One-line summary derived from `root_cause.primary_cause`:
```
Example: "Missing portal access: Support, Academy"
```

### Jira Description
Formatted with Jira markup (h2 for headers, * for bullets):
```
h2. Diagnosis
*Root Cause:* ...
*Confidence:* HIGH
*Evidence:*
* ...

h2. Recommended Actions
*Escalation Level:* L1_RESOLVABLE
*Estimated Time:* 5 minutes
1. [IMMEDIATE] Add 'Support' to birthright...
```

---

## 8. No Hallucination Guarantee

Agent 5 **never invents facts**. It:

1. Only diagnoses patterns that match actual data from Agents 2/3/4
2. Falls back to "Insufficient information" if data doesn't match any pattern
3. Always cites evidence (shows which fields/values led to conclusion)
4. Marks confidence as LOW when data is incomplete or conflicting
5. Recommends escalation when uncertain

**Example:** If a user is missing from Auth0 but NOT in Salesforce, Agent 5 will NOT assume they need account creation (that's for L2 to investigate). Instead: "User not created in Auth0" with "But user exists in Salesforce" as evidence.

---

## 9. Test Coverage

### Diagnostic Tests (10)
- ✅ Missing birthright keywords
- ✅ Block keyword detected
- ✅ User not in Auth0
- ✅ Account not found
- ✅ Salesforce user missing
- ✅ Salesforce user inactive
- ✅ No access configured
- ✅ Stale sync
- ✅ Multiple failed logins
- ✅ Healthy user (no issues)

### Resolution Path Tests (4)
- ✅ L1-resolvable birthright fix
- ✅ L2-escalation for block keyword
- ✅ L2-escalation for missing Auth0 user
- ✅ Estimated time accuracy

### Data Quality Tests (3)
- ✅ Complete data assessment
- ✅ Partial data detection
- ✅ Stale data detection

### Jira Integration Tests (3)
- ✅ Summary generation
- ✅ Description includes diagnosis
- ✅ Description includes all actions

### Error Handling Tests (2)
- ✅ Synthesis with agent errors
- ✅ Missing KB results

**Total: 22/22 tests PASSING**

---

## 10. Integration Points

### Input from Orchestrator
```
POST /agents/05-response-generator
{
  "account_payload": {...},      # From Agent 2
  "auth0_payload": {...},        # From Agent 3
  "kb_payload": {...},           # From Agent 4
  "ticket_email": "user@...",    # Original ticket
  "ticket_intent": "..."         # User's stated intent (optional)
}
```

### Output to Jira/L2
```
POST /jira/tickets/{ticket_id}/update
{
  "summary": agent5_output.jira_summary,
  "description": agent5_output.jira_description,
  "escalation_level": agent5_output.resolution_path.escalation_level,
  "assignee": agent5_output.resolution_path.fallback_escalation,
}

# Or notify L2 team
POST /l2-slack-webhook
{
  "root_cause": agent5_output.root_cause.primary_cause,
  "actions": agent5_output.resolution_path.actions,
  "confidence": agent5_output.root_cause.confidence,
}
```

---

## 11. Known Limitations & Future Work

### Current Limitations
1. **Pattern-based diagnosis only** — cannot handle novel patterns (by design)
2. **Auth0 sync field granularity** — only knows "sync_stale", not specific failure reasons
3. **No machine learning** — uses hand-crafted patterns, not trained models

### Future Enhancements
1. **Custom workflow identification** — map issues to specific Auth0 Action/Rule scripts (blocked by OQ-8)
2. **Confidence scoring refinement** — calibrate confidence thresholds against real tickets
3. **Pattern learning** — periodically review L2 resolutions to add new diagnostic patterns
4. **Similar case scoring** — improve KB relevance ranking for better pattern matching

---

## 12. Appendix: Diagnostic Decision Tree

```
Is account found?
  NO → Pattern 1: "Account not found"
  YES → Is user in Auth0?
    NO → Pattern 2: "User not created in Auth0"
    YES → Does user have any keywords?
      NO → Pattern 3: "No portal access configured"
      YES → Are block keywords present?
        YES → Pattern 5: "Access explicitly blocked"
        NO → Are keywords missing?
          YES → Pattern 4: "Missing portal access"
          NO → Is Salesforce user active?
            NO → Pattern 6: "Salesforce user missing/inactive"
            YES → Did user fail logins?
              YES (>3) → Pattern 7: "Multiple failed logins"
              NO → Confidence is HIGH, no gap
```

---

**Prepared by:** CIAM Engineering  
**Last Updated:** 2026-07-28  
**Next Review:** Post-production monitoring (1-2 weeks)
