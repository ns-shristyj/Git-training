"""Unit tests for Agent 4 (Knowledge Base Agent), mapped to SPEC-CIAM-0004
§9 acceptance criteria. Tool 2 (Bedrock Knowledge Base) calls are mocked --
there is no real KB provisioned yet.
"""

from unittest.mock import patch, MagicMock

import pytest
import requests

from agent import (
    evaluate_ciam_case,
    evaluate_birthright,
    classify_fix_complexity,
    identify_failing_workflow,
    fetch_live_auth0_actions,
    derive_persona,
    derive_pending_login_refresh,
    derive_multi_account_ambiguity,
    assert_posture,
    assert_tool_posture,
    assert_http_posture,
    PostureViolationError,
)


def mock_empty_kb_response():
    return {"retrievalResults": []}


def mock_response(json_body, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    return resp


# AC-1: Customer with missing Support keyword: SIMPLE_FIX classified
def test_ac1_customer_missing_support_simple_fix():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 2,
            "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    be = result["birthright_evaluation"]
    fc = result["fix_classification"]
    assert be["missing_keywords"] == ["Support"]
    assert be["match"] is False
    assert be["persona"] == "Customer"
    assert fc["complexity"] == "SIMPLE_FIX"
    assert any("Support" in a for a in fc["recommended_actions"])


# Regression test (CIAM ops feedback): birthright is Salesforce-computed by
# NetskopeID-Sync-2 and must NEVER be recommended for direct manual edits --
# only entitlements is the manually-editable compensating field. A prior
# version of Agent 5 (not this function) derived its own conflated
# "add to birthright entitlements" wording; this locks down that Agent 4's
# own SIMPLE_FIX text always says "entitlements" and never implies birthright
# itself should be modified.
def test_simple_fix_never_recommends_editing_birthright_directly():
    fc = classify_fix_complexity(
        missing_keywords=["Support"],
        extra_keywords=[],
        account_status="Customer",
        active_tenant_count=2,
        user_found_in_auth0=True,
        explicit_block_detected=False,
        intent="ACCESS_DENIED",
        birthright_correct_but_access_denied=False,
    )
    assert fc.complexity == "SIMPLE_FIX"
    combined_text = " ".join(fc.recommended_actions).lower() + " " + fc.reason.lower()
    assert "birthright entitlements" not in combined_text
    assert "to birthright" not in combined_text
    assert "entitlements" in combined_text


# AC-2: Entitlements compensate for missing birthright keyword -> NO_GAP
def test_ac2_entitlements_compensate_no_gap():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
            "entitlements": ["Support"],
            "user_found_in_auth0": True,
            "intent": "GENERAL_INQUIRY",
        })

    be = result["birthright_evaluation"]
    fc = result["fix_classification"]
    assert be["missing_keywords"] == []
    assert be["match"] is True
    assert be["entitlements_compensate"] is True
    assert fc["complexity"] == "NO_GAP"


# AC-3: Prospect without tenant gets reduced expected birthright
def test_ac3_prospect_without_tenant():
    persona, expected = derive_persona("Prospect", 0)
    assert persona == "Prospect"
    assert expected == ["Community", "Academy", "Dashboard"]

    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Prospect",
            "active_tenant_count": 0,
            "actual_birthright": ["Community", "Academy", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "GENERAL_INQUIRY",
        })

    assert result["birthright_evaluation"]["expected_birthright"] == ["Community", "Academy", "Dashboard"]
    assert result["birthright_evaluation"]["match"] is True
    assert result["fix_classification"]["complexity"] == "NO_GAP"


def test_prospect_with_tenant_gets_full_set():
    persona, expected = derive_persona("Prospect", 1)
    assert persona == "Prospect (w/ Tenant)"
    assert set(expected) == {"Community", "Academy", "Support", "Notification", "Dashboard"}


def test_churn_personas():
    persona, expected = derive_persona("Churn", 0)
    assert persona == "Churn"
    assert expected == ["Community", "Dashboard"]

    persona, expected = derive_persona("Churn", 1)
    assert persona == "Churn (w/ Tenant)"
    assert set(expected) == {"Community", "Academy", "Support", "Notification", "Dashboard"}


def test_qob_persona_matches_by_substring():
    persona, expected = derive_persona("Quarantine", None)
    assert persona == "QOB"
    assert expected == ["Community", "Dashboard"]

    persona, expected = derive_persona("Out of Business", None)
    assert persona == "QOB"


# AC-4: Extra keywords in birthright force ESCALATE_TO_L2
def test_ac4_extra_keywords_escalate():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Churn",
            "active_tenant_count": 0,
            "actual_birthright": ["Community", "Dashboard", "Support"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "GENERAL_INQUIRY",
        })

    be = result["birthright_evaluation"]
    fc = result["fix_classification"]
    assert be["extra_keywords"] == ["Support"]
    assert be["match"] is False
    assert fc["complexity"] == "ESCALATE_TO_L2"
    assert "over-provision" in fc["reason"].lower()


# AC-5: Block keyword detected forces ESCALATE_TO_L2 -- real format is
# "Block-Supp" (hyphenated abbreviation), not "block_Support".
def test_ac5_block_keyword_escalate():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Support", "Community", "Academy", "Notification", "Dashboard"],
            "entitlements": ["Block-Supp"],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    be = result["birthright_evaluation"]
    fc = result["fix_classification"]
    assert be["explicit_block_detected"] is True
    assert be["block_keywords_found"] == ["Block-Supp"]
    assert fc["complexity"] == "ESCALATE_TO_L2"
    assert "block" in fc["reason"].lower()


def test_all_real_block_keywords_recognized():
    from agent import BLOCK_KEYWORD_TO_PORTAL
    for block_kw, portal in [
        ("Block-Supp", "Support"), ("Block-Acad", "Academy"),
        ("Block-Comm", "Community"), ("Block-Notif", "Notification"),
        ("Block-Partner", "Partner"), ("Block-Prime", "Prime"),
        ("Block-Dash", "Dashboard"),
    ]:
        assert BLOCK_KEYWORD_TO_PORTAL[block_kw] == portal


# AC-6: User not found in Auth0 forces ESCALATE_TO_L2
def test_ac6_user_not_found_escalate():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": [],
            "entitlements": [],
            "user_found_in_auth0": False,
            "intent": "ACCOUNT_NOT_FOUND",
        })

    fc = result["fix_classification"]
    assert fc["complexity"] == "ESCALATE_TO_L2"
    assert "provision" in fc["reason"].lower()
    assert any("User Creation" in a for a in fc["recommended_actions"])


# AC-7: Birthright correct but ACCESS_DENIED forces ESCALATE_TO_L2
def test_ac7_birthright_correct_but_access_denied():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Support", "Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    be = result["birthright_evaluation"]
    fc = result["fix_classification"]
    assert be["match"] is True
    assert be["birthright_correct_but_access_denied"] is True
    assert fc["complexity"] == "ESCALATE_TO_L2"
    assert "gatekeeper" in fc["reason"].lower()


# AC-8: Knowledge Base timeout is non-fatal; evaluation still returned
def test_ac8_kb_timeout_non_fatal():
    with patch("agent.requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("timed out")
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    assert result["birthright_evaluation"] is not None
    assert result["fix_classification"] is not None
    assert result["knowledge_base_results"]["relevant_docs"] == []
    assert result["knowledge_base_results"]["similar_past_tickets"] == []
    assert result["knowledge_base_error"] == "bedrock_timeout"
    assert result["error"] is None


# AC-9: Agent attempts dynamodb:Query (posture invariant)
def test_ac9_dynamodb_denied():
    with pytest.raises(PostureViolationError):
        assert_posture("dynamodb:Query")


# AC-10: Agent attempts bedrock:StartIngestionJob (posture invariant)
def test_ac10_start_ingestion_job_denied():
    with pytest.raises(PostureViolationError):
        assert_posture("bedrock:StartIngestionJob")


def test_tool_name_posture_denies_unknown_tool():
    with pytest.raises(PostureViolationError):
        assert_tool_posture("get_account_history")


# AC-11: Schema conformance handled implicitly by Pydantic model_dump() in all
# other tests -- if the schema were invalid, model construction would raise.


# AC-12 (updated): null account_status maps to the real "Individual" persona
# (per the Birthright Guide's "No Account Found" row), NOT an "UNKNOWN"
# persona with an empty expected set as an earlier provisional table assumed.
# It still escalates -- classify_fix_complexity treats "no account at all" as
# needing human review regardless of birthright accuracy -- but for the
# correct reason (account_status_unknown), and persona/expected_birthright
# now reflect real data instead of a placeholder empty state.
def test_ac12_no_account_found_maps_to_individual_persona_and_escalates():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": None,
            "active_tenant_count": None,
            "actual_birthright": [],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "GENERAL_INQUIRY",
        })

    be = result["birthright_evaluation"]
    fc = result["fix_classification"]
    assert be["persona"] == "Individual"
    assert be["expected_birthright"] == ["Community", "Dashboard"]
    assert fc["complexity"] == "ESCALATE_TO_L2"
    assert result["error"] is None


def test_genuinely_unrecognized_account_status_is_unknown():
    persona, expected = derive_persona("Some Future Status Nobody Has Seen Yet", 1)
    assert persona == "UNKNOWN"
    assert expected == []


# AC-13: no_access_configured flagged when both arrays are empty
def test_ac13_no_access_configured():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": [],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    be = result["birthright_evaluation"]
    fc = result["fix_classification"]
    assert be["no_access_configured"] is True
    assert set(be["missing_keywords"]) == {"Support", "Community", "Academy", "Notification", "Dashboard"}
    assert fc["complexity"] == "SIMPLE_FIX"


# Real Partner persona (per the actual Birthright & Entitlements Guide) gets
# nearly the FULL portal set -- Support, Community, Academy, Partner,
# Notification, Dashboard (6 keywords) -- not the reduced 3-4 keyword set an
# earlier provisional table assumed.
def test_partner_persona_gets_real_keyword_set():
    persona, expected = derive_persona("Partner", 0)
    assert persona == "Partner"
    assert set(expected) == {"Support", "Community", "Academy", "Partner", "Notification", "Dashboard"}


def test_partner_is_a_known_portal_keyword():
    from agent import KNOWN_PORTAL_KEYWORDS
    assert "Partner" in KNOWN_PORTAL_KEYWORDS
    assert "Prime" in KNOWN_PORTAL_KEYWORDS


def test_partner_missing_keyword_does_not_trigger_unrecognized_escalation():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Partner",
            "active_tenant_count": 0,
            "actual_birthright": ["Support", "Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    be = result["birthright_evaluation"]
    fc = result["fix_classification"]
    assert be["missing_keywords"] == ["Partner"]
    # Partner accounts still escalate per spec's SIMPLE_FIX criteria (only
    # Customer / Prospect-with-tenant qualify) -- but the reason should NOT
    # be "unrecognized keyword", since Partner is now a known keyword.
    assert fc["complexity"] == "ESCALATE_TO_L2"
    assert "unrecognized" not in fc["reason"].lower()


# AC-14: Bedrock Knowledge Base returns relevant docs and past tickets
def test_ac14_kb_returns_docs_and_tickets():
    fake_response = {
        "retrievalResults": [
            {
                "content": {"text": "Birthright guide excerpt"},
                "metadata": {"_document_title": "Birthright Guide"},
                "location": {"s3Location": {"uri": "s3://kb/birthright.md"}},
                "score": 0.92,
            },
            {
                "content": {"text": "Resolved by adding Support keyword"},
                "metadata": {
                    "_document_title": "TQI-1234",
                    "ticket_key": "TQI-1234",
                    "summary": "User missing Support access",
                    "resolution": "Added Support to entitlements",
                },
                "location": {},
                "score": 0.85,
            },
        ]
    }
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(fake_response)
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Community"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    kb = result["knowledge_base_results"]
    assert len(kb["relevant_docs"]) == 1
    assert len(kb["similar_past_tickets"]) == 1
    assert kb["relevant_docs"][0]["title"] == "Birthright Guide"
    assert kb["similar_past_tickets"][0]["ticket_key"] == "TQI-1234"
    assert result["knowledge_base_error"] is None


def test_kb_excerpt_never_leaks_source_code():
    """The KB now indexes raw Auth0 Action scripts (auth0-action-*.md) --
    a retrieved chunk can land mid-function with no surrounding markdown
    fence. A code-like excerpt from a characterized action must be replaced
    with its curated plain-English summary (informative, but zero literal
    code) before it can reach a user-facing (e.g. Jira) response."""
    code_chunk = (
        "const UPDATED = await update_netskopeid_user(dbKey, build_hourly_updates(roles, birthright));\n"
        "            if (UPDATED !== true) {\n"
        "                const errorCode = await error_code_generator(new Error(), \"1061\");\n"
        "            }\n"
        "            api.user.setAppMetadata('birthright', birthright);\n"
    )
    fake_response = {
        "retrievalResults": [
            {
                "content": {"text": code_chunk},
                "metadata": {"_document_title": "auth0-action-netskopeid-sync-2.md"},
                "location": {"s3Location": {"uri": "s3://kb/auth0-action-netskopeid-sync-2.md"}},
                "score": 0.44,
            },
        ]
    }
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(fake_response)
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Community"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    excerpt = result["knowledge_base_results"]["relevant_docs"][0]["excerpt"]
    assert "const " not in excerpt
    assert "setAppMetadata" not in excerpt
    assert "birthright engine" in excerpt.lower()
    assert "Salesforce" in excerpt


def test_kb_excerpt_falls_back_for_uncharacterized_action():
    """An action code leak with no curated summary yet still must not print
    code -- falls back to a generic note that at least names the doc."""
    code_chunk = "const x = await foo(); let y = 1; api.user.setUserMetadata('z', y); exports.bar = () => {};"
    fake_response = {
        "retrievalResults": [
            {
                "content": {"text": code_chunk},
                "metadata": {"_document_title": "auth0-action-some-future-action.md"},
                "location": {},
                "score": 0.30,
            },
        ]
    }
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(fake_response)
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Community"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    excerpt = result["knowledge_base_results"]["relevant_docs"][0]["excerpt"]
    assert "const " not in excerpt
    assert "omitted" in excerpt.lower()


def test_kb_results_deduplicated():
    """CIAM-4602 regression: two distinct code chunks from the same Action
    both sanitize to the identical curated summary, which must collapse to
    ONE entry rather than eating multiple top_k slots with a duplicate."""
    code_chunk_a = "const a = await foo(); let b = 1; api.user.setAppMetadata('z', b); exports.bar = () => {};"
    code_chunk_b = "const c = await bar(); let d = 2; api.user.setAppMetadata('y', d); exports.baz = () => {};"
    fake_response = {
        "retrievalResults": [
            {
                "content": {"text": code_chunk_a},
                "metadata": {"_document_title": "auth0-action-provisioner.md"},
                "location": {},
                "score": 0.52,
            },
            {
                "content": {"text": code_chunk_b},
                "metadata": {"_document_title": "auth0-action-provisioner.md"},
                "location": {},
                "score": 0.52,
            },
            {
                "content": {"text": "Distinct prose excerpt, no dedup expected here."},
                "metadata": {"_document_title": "portal-access-requirements.md"},
                "location": {},
                "score": 0.60,
            },
        ]
    }
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(fake_response)
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Community"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    docs = result["knowledge_base_results"]["relevant_docs"]
    assert len(docs) == 2, f"Expected 2 distinct docs after dedup, got {len(docs)}"
    titles = [d["title"] for d in docs]
    assert titles.count("auth0-action-provisioner.md") == 1


# AC-15: Workflow identification always returns the placeholder stub
def test_ac15_workflow_identification_resolved():
    """Tool 4 now maps failures to real Auth0 Actions fetched from the nskp
    tenant (see fetch_auth0_workflow_scripts.py) -- resolves former OQ-8
    placeholder."""
    wf = identify_failing_workflow("Support")
    assert wf.workflow_identified is True
    assert wf.workflow_name == "NetskopeID-Sync-2"
    assert wf.workflow_script_ref == "bb237d59-6ef7-420e-881a-345c8d0bc3a2"
    assert wf.enforcement_workflow_name == "Gatekeeper"
    assert "Support" in wf.note

    wf_block = identify_failing_workflow("explicit_block_detected")
    assert wf_block.workflow_identified is True
    assert wf_block.workflow_name == "Gatekeeper"

    wf_none = identify_failing_workflow(None)
    assert wf_none.workflow_identified is False

    # Ticket about a *specific* portal (e.g. Partner) must not get a note
    # that only mentions the alphabetically-first gap (e.g. Academy) when
    # multiple keywords are missing -- CIAM-4602 regression.
    wf_multi = identify_failing_workflow(
        "Academy", ["Academy", "Dashboard", "Notification", "Partner"]
    )
    assert "Partner" in wf_multi.note
    assert "Academy" in wf_multi.note
    assert "Dashboard" in wf_multi.note

    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    wi = result["workflow_identification"]
    assert wi["workflow_identified"] is True
    assert wi["workflow_name"] == "NetskopeID-Sync-2"
    # complexity classification is unaffected by workflow identification
    assert result["fix_classification"]["complexity"] == "SIMPLE_FIX"


def test_invalid_input_returns_structured_error():
    result = evaluate_ciam_case({"account_status": "Customer"})  # missing required fields
    assert result["error"] == "invalid_input"
    assert result["birthright_evaluation"] is None


# ============================================================================
# Tool 5 (fetch_live_auth0_actions) + Tool 4 live-verification / drift
# detection -- CIAM ops feedback: Auth0 Actions are edited independently of
# this agent's deploys, so a hardcoded understanding of what an Action does
# must be re-verified live on every invocation, not trusted from a
# point-in-time snapshot. Note: the autouse `_no_live_auth0_fetch` fixture in
# conftest.py patches `fetch_live_auth0_actions` to a network-free default
# for every OTHER test in this file -- these tests override that default
# explicitly to exercise the real function body via lower-level mocks.
# ============================================================================

def _mock_auth0_token_response():
    return mock_response({"access_token": "fake-token", "expires_in": 3600})


def _mock_auth0_actions_list_response(actions):
    return mock_response({"actions": actions})


def test_fetch_live_auth0_actions_success_no_drift(monkeypatch):
    """Happy path: live fetch succeeds, both actions found, code contains all
    expected markers -- no drift, live-verified IDs differ from (and take
    precedence over) the offline fallback IDs."""
    monkeypatch.setattr(
        "agent._get_auth0_workflows_credentials",
        lambda: {"client_id": "x", "client_secret": "y"},
    )
    live_actions_payload = [
        {
            "name": "NetskopeID-Sync-2",
            "id": "LIVE-sync2-id-currently-in-tenant",
            "status": "built",
            "updated_at": "2026-08-01T00:00:00.000Z",
            "code": "const x = Account_Status__c; const y = Customer_Status__c; user.birthright = [];",
        },
        {
            "name": "Gatekeeper",
            "id": "LIVE-gatekeeper-id-currently-in-tenant",
            "status": "built",
            "updated_at": "2026-08-01T00:00:00.000Z",
            "code": "if (!entitlements.includes(x) && !birthright.includes(x)) deny();",
        },
    ]

    def fake_post(url, **kwargs):
        return _mock_auth0_token_response()

    def fake_get(url, **kwargs):
        return _mock_auth0_actions_list_response(live_actions_payload)

    monkeypatch.setattr("agent.requests.post", fake_post)
    monkeypatch.setattr("agent.requests.get", fake_get)

    live_actions, error = fetch_live_auth0_actions(["NetskopeID-Sync-2", "Gatekeeper"])

    assert error is None
    assert live_actions["NetskopeID-Sync-2"].action_id == "LIVE-sync2-id-currently-in-tenant"
    assert live_actions["NetskopeID-Sync-2"].code_drift_detected is False
    assert live_actions["Gatekeeper"].action_id == "LIVE-gatekeeper-id-currently-in-tenant"
    assert live_actions["Gatekeeper"].code_drift_detected is False

    wf = identify_failing_workflow("Support", ["Support"], live_actions, error)
    assert wf.live_verified is True
    assert wf.code_drift_detected is False
    # Live IDs must win over the hardcoded offline fallback constants.
    assert wf.workflow_script_ref == "LIVE-sync2-id-currently-in-tenant"
    assert wf.enforcement_workflow_script_ref == "LIVE-gatekeeper-id-currently-in-tenant"
    assert "LIVE-VERIFIED" in wf.note


def test_fetch_live_auth0_actions_detects_code_drift(monkeypatch):
    """If the live Action's current code no longer contains a marker this
    agent's diagnosis assumes (e.g. someone edited NetskopeID-Sync-2 to stop
    reading Customer_Status__c), that must surface as a flagged warning, not
    be silently ignored -- this is what lets Agent 4 say 'the Action code
    itself might be the problem' instead of always blaming Salesforce data."""
    monkeypatch.setattr(
        "agent._get_auth0_workflows_credentials",
        lambda: {"client_id": "x", "client_secret": "y"},
    )
    drifted_payload = [
        {
            "name": "NetskopeID-Sync-2",
            "id": "sync2-id",
            "status": "built",
            "updated_at": "2026-08-09T00:00:00.000Z",
            # Customer_Status__c marker removed -- simulates someone editing
            # the Action's calculation logic.
            "code": "const x = Account_Status__c; user.birthright = [];",
        },
        {
            "name": "Gatekeeper",
            "id": "gatekeeper-id",
            "status": "built",
            "updated_at": "2026-08-01T00:00:00.000Z",
            "code": "if (!entitlements.includes(x) && !birthright.includes(x)) deny();",
        },
    ]
    monkeypatch.setattr("agent.requests.post", lambda url, **kw: _mock_auth0_token_response())
    monkeypatch.setattr("agent.requests.get", lambda url, **kw: _mock_auth0_actions_list_response(drifted_payload))

    live_actions, error = fetch_live_auth0_actions(["NetskopeID-Sync-2", "Gatekeeper"])

    assert error is None
    assert live_actions["NetskopeID-Sync-2"].code_drift_detected is True
    assert "Customer_Status__c" in live_actions["NetskopeID-Sync-2"].code_drift_note

    wf = identify_failing_workflow("Support", ["Support"], live_actions, error)
    assert wf.code_drift_detected is True
    assert "WARNING" in wf.note


def test_fetch_live_auth0_actions_renamed_or_missing_falls_back(monkeypatch):
    """If an expected Action can't be found by name in the live tenant (e.g.
    renamed or deleted), Tool 4 must fall back to the offline reference ID
    for that action and must NOT claim live_verified."""
    monkeypatch.setattr(
        "agent._get_auth0_workflows_credentials",
        lambda: {"client_id": "x", "client_secret": "y"},
    )
    # "Gatekeeper" is missing entirely from the live list.
    partial_payload = [
        {
            "name": "NetskopeID-Sync-2",
            "id": "sync2-id",
            "status": "built",
            "updated_at": "2026-08-01T00:00:00.000Z",
            "code": "Account_Status__c Customer_Status__c birthright",
        },
    ]
    monkeypatch.setattr("agent.requests.post", lambda url, **kw: _mock_auth0_token_response())
    monkeypatch.setattr("agent.requests.get", lambda url, **kw: _mock_auth0_actions_list_response(partial_payload))

    live_actions, error = fetch_live_auth0_actions(["NetskopeID-Sync-2", "Gatekeeper"])

    assert error is None
    assert live_actions["Gatekeeper"].action_id == ""
    assert live_actions["Gatekeeper"].code_drift_detected is True

    wf = identify_failing_workflow("Support", ["Support"], live_actions, error)
    assert wf.live_verified is False  # Gatekeeper couldn't be confirmed live
    assert wf.enforcement_workflow_script_ref == "35d76097-24c1-4b5b-b3cc-e853e286b7e6"  # offline fallback


def test_fetch_live_auth0_actions_network_failure_is_non_fatal(monkeypatch):
    """Any failure fetching live Auth0 data (credentials, network, Auth0 API
    error) must never crash Agent 4 -- it degrades to the offline snapshot,
    same non-fatal contract as Tool 2's KB failure handling."""
    def raise_error():
        raise RuntimeError("secrets manager unavailable")

    monkeypatch.setattr("agent._get_auth0_workflows_credentials", lambda: raise_error())

    live_actions, error = fetch_live_auth0_actions(["NetskopeID-Sync-2", "Gatekeeper"])

    assert live_actions == {}
    assert error is not None
    assert "auth0_live_fetch_error" in error

    # Tool 4 must still produce a complete, non-crashing result using the
    # offline fallback.
    wf = identify_failing_workflow("Support", ["Support"], live_actions, error)
    assert wf.workflow_identified is True
    assert wf.live_verified is False
    assert wf.live_fetch_error == error
    assert wf.workflow_script_ref == "bb237d59-6ef7-420e-881a-345c8d0bc3a2"  # offline fallback
    assert "Live verification unavailable" in wf.note


def test_expected_code_markers_are_verified_against_real_archived_source():
    """Regression test for a real bug caught during Fix #2 verification: the
    first version of _EXPECTED_CODE_MARKERS used "Tenant_Requests__c" for
    NetskopeID-Sync-2 -- a paraphrase from a code COMMENT ("Salesforce
    Account Status and Tenant Requests"), not a literal token anywhere in
    the real fetched source. That would have fired a false "code drift"
    warning against the live tenant on every single ticket, defeating the
    entire point of the drift detector. This test asserts every marker in
    _EXPECTED_CODE_MARKERS literally appears in the corresponding archived
    Action source file, so a marker can never again be inferred from a
    summary instead of copy-verified from the real code."""
    import os
    from agent import _EXPECTED_CODE_MARKERS

    action_to_filename = {
        "NetskopeID-Sync-2": "auth0-action-netskopeid-sync-2.md",
        "Gatekeeper": "auth0-action-gatekeeper.md",
    }
    scripts_dir = os.path.join(os.path.dirname(__file__), "auth0_workflow_scripts")

    for action_name, markers in _EXPECTED_CODE_MARKERS.items():
        filename = action_to_filename.get(action_name)
        assert filename, f"no archived source mapping for '{action_name}' -- add one to this test"
        path = os.path.join(scripts_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        for marker in markers:
            assert marker in source, (
                f"marker '{marker}' for '{action_name}' does not literally appear in "
                f"{filename} -- it was likely inferred from a comment/summary instead of "
                "copy-verified from the real code (see this test's docstring)"
            )


def test_http_posture_rejects_disallowed_host_and_path():
    with pytest.raises(PostureViolationError):
        assert_http_posture("evil.example.com", "/oauth/token", "POST")
    with pytest.raises(PostureViolationError):
        assert_http_posture("netskope-dev.us.auth0.com", "/api/v2/users", "GET")
    # Allowed combination must not raise.
    assert_http_posture("netskope-dev.us.auth0.com", "/api/v2/actions/actions", "GET")


def test_entrypoint_only_attempts_live_fetch_when_there_is_a_gap(monkeypatch):
    """No point spending the extra round trip when birthright already
    matches -- Tool 5 must only be invoked when there's an actual gap for
    Tool 4 to explain."""
    calls = []
    monkeypatch.setattr(
        "agent.fetch_live_auth0_actions",
        lambda names: (calls.append(names) or ({}, None)),
    )
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Community", "Academy", "Support", "Notification", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    assert result["birthright_evaluation"]["match"] is True
    assert calls == []  # fetch_live_auth0_actions must not have been called


# ============================================================================
# Sync edge-case detection -- CIAM ops feedback: a birthright gap can look
# identical whether it's (a) a real gap, (b) a pending sync that just
# hasn't run yet because the user hasn't logged in since the Salesforce
# change, or (c) the wrong account/user record entirely because multiple
# exist for this email. These tests cover (a)/(b) distinction and (c);
# (code drift, the third confounder) is covered above in the Tool 5 tests
# and wired into classify_fix_complexity below.
# ============================================================================

def test_pending_login_refresh_no_recent_changes():
    detected, note = derive_pending_login_refresh("2026-08-01T00:00:00+00:00", [])
    assert detected is False
    assert note is None


def test_pending_login_refresh_change_before_last_login_is_fine():
    """Salesforce changed BEFORE the user's last login -- sync already had
    a chance to pick it up, so this is a real gap, not a pending refresh."""
    detected, note = derive_pending_login_refresh(
        "2026-08-05T00:00:00+00:00",
        [{"field_name": "account_status", "changed_date": "2026-08-01T00:00:00+00:00"}],
    )
    assert detected is False


def test_pending_login_refresh_change_after_last_login_detected():
    detected, note = derive_pending_login_refresh(
        "2026-08-01T00:00:00+00:00",
        [{"field_name": "account_status", "changed_date": "2026-08-05T00:00:00+00:00"}],
    )
    assert detected is True
    assert "account_status" in note
    assert "2026-08-05" in note


def test_pending_login_refresh_never_logged_in_with_changes_detected():
    detected, note = derive_pending_login_refresh(
        None,
        [{"field_name": "account_status", "changed_date": "2026-08-05T00:00:00+00:00"}],
    )
    assert detected is True
    assert "no recorded login" in note


def test_pending_login_refresh_unparseable_dates_fail_safe():
    detected, note = derive_pending_login_refresh(
        "not-a-date",
        [{"field_name": "account_status", "changed_date": "also-not-a-date"}],
    )
    assert detected is False
    assert note is None


def test_multi_account_ambiguity_none_when_single_account_and_user():
    detected, reasons = derive_multi_account_ambiguity([], [], 1, 1)
    assert detected is False
    assert reasons == []


def test_multi_account_ambiguity_detected_via_agent2_warning():
    detected, reasons = derive_multi_account_ambiguity(["multiple_accounts_found"], [], 1, 1)
    assert detected is True
    assert any("Agent 2" in r for r in reasons)


def test_multi_account_ambiguity_detected_via_agent3_warning():
    detected, reasons = derive_multi_account_ambiguity([], ["multiple_users_found"], 1, 1)
    assert detected is True
    assert any("Agent 3" in r for r in reasons)


def test_multi_account_ambiguity_detected_via_raw_counts_without_warning():
    """Even if neither agent explicitly flagged a warning string, counts > 1
    on their own must still be treated as ambiguous -- don't rely solely on
    the upstream agent remembering to set the warning."""
    detected, reasons = derive_multi_account_ambiguity([], [], 3, 1)
    assert detected is True
    assert any("3 accounts" in r for r in reasons)


def test_classify_fix_complexity_multi_account_ambiguity_escalates_first():
    """Ambiguity must be checked BEFORE extra_keywords/other signals --
    those signals could belong to the wrong account entirely."""
    fc = classify_fix_complexity(
        missing_keywords=[],
        extra_keywords=["Partner"],  # would normally trigger the over-provisioned path
        account_status="Customer",
        active_tenant_count=1,
        user_found_in_auth0=True,
        explicit_block_detected=False,
        intent="ACCESS_DENIED",
        birthright_correct_but_access_denied=False,
        multi_account_ambiguity=True,
        multi_account_ambiguity_reasons=["2 Auth0 user records found for this email"],
    )
    assert fc.complexity == "ESCALATE_TO_L2"
    assert fc.confidence == "LOW"
    assert "disambiguation" in fc.reason.lower() or "which record" in fc.reason.lower()
    assert "2 Auth0 user records" in fc.reason


def test_classify_fix_complexity_code_drift_escalates():
    fc = classify_fix_complexity(
        missing_keywords=["Support"],
        extra_keywords=[],
        account_status="Customer",
        active_tenant_count=1,
        user_found_in_auth0=True,
        explicit_block_detected=False,
        intent="ACCESS_DENIED",
        birthright_correct_but_access_denied=False,
        code_drift_detected=True,
        code_drift_note="Action 'NetskopeID-Sync-2' current live code no longer contains expected marker(s)",
    )
    assert fc.complexity == "ESCALATE_TO_L2"
    assert "no longer contains expected marker" in fc.reason


def test_classify_fix_complexity_pending_login_refresh_prefers_relogin():
    fc = classify_fix_complexity(
        missing_keywords=["Support"],
        extra_keywords=[],
        account_status="Customer",
        active_tenant_count=1,
        user_found_in_auth0=True,
        explicit_block_detected=False,
        intent="ACCESS_DENIED",
        birthright_correct_but_access_denied=False,
        pending_login_refresh=True,
        pending_login_refresh_note="Account field 'account_status' changed on 2026-08-05, after last login.",
    )
    assert fc.complexity == "SIMPLE_FIX"
    assert fc.confidence == "HIGH"
    # The FIRST recommended action must be to try a fresh login, not an
    # immediate manual entitlements edit.
    assert "log" in fc.recommended_actions[0].lower() and "in" in fc.recommended_actions[0].lower()
    assert any("entitlements" in a.lower() for a in fc.recommended_actions)


def test_entrypoint_surfaces_multi_account_ambiguity_end_to_end(monkeypatch):
    monkeypatch.setattr("agent.fetch_live_auth0_actions", lambda names: ({}, None))
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
            "auth0_users_count": 2,
            "auth0_warnings": ["multiple_users_found"],
        })

    assert result["fix_classification"]["complexity"] == "ESCALATE_TO_L2"
    assert result["sync_diagnostics"]["multi_account_ambiguity"] is True
    assert any("Agent 3" in r for r in result["sync_diagnostics"]["multi_account_ambiguity_reasons"])


def test_entrypoint_surfaces_pending_login_refresh_end_to_end(monkeypatch):
    monkeypatch.setattr("agent.fetch_live_auth0_actions", lambda names: ({}, None))
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
            "last_login": "2026-08-01T00:00:00+00:00",
            "recent_changes": [
                {"field_name": "account_status", "changed_date": "2026-08-05T00:00:00+00:00"}
            ],
        })

    assert result["fix_classification"]["complexity"] == "SIMPLE_FIX"
    assert result["sync_diagnostics"]["pending_login_refresh"] is True
    assert "log" in result["fix_classification"]["recommended_actions"][0].lower()


def test_entrypoint_without_new_fields_behaves_exactly_as_before(monkeypatch):
    """Backward compatibility: a payload that doesn't send any of the new
    fields (e.g. an orchestrator that hasn't been redeployed yet) must
    produce the exact same classification as before this change."""
    monkeypatch.setattr("agent.fetch_live_auth0_actions", lambda names: ({}, None))
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 2,
            "actual_birthright": ["Community", "Academy", "Notification", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    assert result["fix_classification"]["complexity"] == "SIMPLE_FIX"
    assert result["sync_diagnostics"]["pending_login_refresh"] is False
    assert result["sync_diagnostics"]["multi_account_ambiguity"] is False
