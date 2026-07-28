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
    derive_persona,
    assert_posture,
    assert_tool_posture,
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
    persona, expected = derive_persona("Prospect - Net New", 0)
    assert persona == "Prospect without Tenant"
    assert expected == ["Community", "Academy", "Dashboard"]

    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Prospect - Net New",
            "active_tenant_count": 0,
            "actual_birthright": ["Community", "Academy", "Dashboard"],
            "entitlements": [],
            "user_found_in_auth0": True,
            "intent": "GENERAL_INQUIRY",
        })

    assert result["birthright_evaluation"]["expected_birthright"] == ["Community", "Academy", "Dashboard"]
    assert result["birthright_evaluation"]["match"] is True
    assert result["fix_classification"]["complexity"] == "NO_GAP"


# AC-4: Extra keywords in birthright force ESCALATE_TO_L2
def test_ac4_extra_keywords_escalate():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Former Customer",
            "active_tenant_count": 0,
            "actual_birthright": ["Community", "Academy", "Dashboard", "Support"],
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


# AC-5: Block keyword detected forces ESCALATE_TO_L2
def test_ac5_block_keyword_escalate():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Customer",
            "active_tenant_count": 1,
            "actual_birthright": ["Support", "Community", "Academy", "Notification", "Dashboard"],
            "entitlements": ["block_Support"],
            "user_found_in_auth0": True,
            "intent": "ACCESS_DENIED",
        })

    be = result["birthright_evaluation"]
    fc = result["fix_classification"]
    assert be["explicit_block_detected"] is True
    assert be["block_keywords_found"] == ["block_Support"]
    assert fc["complexity"] == "ESCALATE_TO_L2"
    assert "block" in fc["reason"].lower()


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


# AC-12: Unknown account_status returns UNKNOWN persona and escalates
def test_ac12_unknown_account_status_escalates():
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
    assert be["persona"] == "UNKNOWN"
    assert be["expected_birthright"] == []
    assert fc["complexity"] == "ESCALATE_TO_L2"
    assert result["error"] is None


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


# Regression test: "Partner" persona's expected_birthright previously omitted
# the "Partner" keyword itself, and KNOWN_PORTAL_KEYWORDS didn't recognize it
# -- an inconsistency with Agent 1, which treats "Partner" as a valid portal.
def test_partner_persona_includes_partner_keyword():
    persona, expected = derive_persona("Partner", 0)
    assert persona == "Partner"
    assert "Partner" in expected
    assert set(expected) == {"Partner", "Community", "Academy", "Dashboard"}


def test_partner_is_a_known_portal_keyword():
    from agent import KNOWN_PORTAL_KEYWORDS
    assert "Partner" in KNOWN_PORTAL_KEYWORDS


def test_partner_missing_keyword_does_not_trigger_unrecognized_escalation():
    with patch("agent.requests.post") as mock_post:
        mock_post.return_value = mock_response(mock_empty_kb_response())
        result = evaluate_ciam_case({
            "account_status": "Partner",
            "active_tenant_count": 0,
            "actual_birthright": ["Community", "Academy", "Dashboard"],
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


# AC-15: Workflow identification always returns the placeholder stub
def test_ac15_workflow_identification_placeholder():
    wf = identify_failing_workflow("step_6_netskopeid_sync_2")
    assert wf.workflow_identified is False
    assert wf.workflow_name is None
    assert wf.workflow_script_ref is None
    assert "placeholder" in wf.note.lower()

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
    assert wi["workflow_identified"] is False
    # complexity is unaffected by the placeholder
    assert result["fix_classification"]["complexity"] == "SIMPLE_FIX"


def test_invalid_input_returns_structured_error():
    result = evaluate_ciam_case({"account_status": "Customer"})  # missing required fields
    assert result["error"] == "invalid_input"
    assert result["birthright_evaluation"] is None
