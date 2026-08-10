"""Unit tests for AgentInvoker._parse_agent_response, in particular its
datetime.datetime(...) repr conversion (see agent_invoker.py's docstring for
the full history: an earlier version nulled every timestamp, which broke
once Agent 4's sync-timing checks needed real last_login/changed_date
values -- these tests lock down that timestamps now survive the parse as
real ISO-8601 strings, not None, while non-datetime data is unaffected).
"""

from ciam_orchestrator.agent_invoker import AgentInvoker


def test_naive_datetime_is_converted_to_iso_string():
    raw = b'"{\'last_login\': datetime.datetime(2026, 8, 1, 12, 30, 45), \'x\': 1}"'
    result = AgentInvoker._parse_agent_response(raw)
    assert result == {"last_login": "2026-08-01T12:30:45", "x": 1}


def test_utc_aware_datetime_with_tzinfo_is_converted_to_iso_string():
    """The historical bug case: TzInfo(...) nested inside datetime.datetime(...)
    used to corrupt a naive regex. TzInfo(0) is pydantic v2's repr for a
    zero-second UTC offset."""
    raw = (
        b'"{\'changed_date\': datetime.datetime(2026, 7, 15, 9, 0, 0, '
        b"tzinfo=TzInfo(0)), 'field_name': 'account_status'}\""
    )
    result = AgentInvoker._parse_agent_response(raw)
    assert result["changed_date"] == "2026-07-15T09:00:00+00:00"
    assert result["field_name"] == "account_status"


def test_non_utc_offset_tzinfo_is_preserved_correctly():
    raw = b'"{\'ts\': datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=TzInfo(3600))}"'
    result = AgentInvoker._parse_agent_response(raw)
    assert result["ts"] == "2026-01-01T00:00:00+01:00"


def test_multiple_datetimes_in_one_payload_all_convert_independently():
    raw = (
        b'"{\'last_login\': datetime.datetime(2026, 8, 1, 0, 0, 0, tzinfo=TzInfo(0)), '
        b"'last_sync': datetime.datetime(2026, 7, 20, 0, 0, 0, tzinfo=TzInfo(0)), "
        b"'recent_changes': [{'changed_date': datetime.datetime(2026, 8, 5, 0, 0, 0, "
        b"tzinfo=TzInfo(0))}]}\""
    )
    result = AgentInvoker._parse_agent_response(raw)
    assert result["last_login"] == "2026-08-01T00:00:00+00:00"
    assert result["last_sync"] == "2026-07-20T00:00:00+00:00"
    assert result["recent_changes"][0]["changed_date"] == "2026-08-05T00:00:00+00:00"


def test_malformed_datetime_call_falls_back_to_none_not_a_crash():
    """Fail-safe contract: a datetime-shaped call this parser can't make
    sense of must degrade to None (the old universal behavior), never raise
    and take down the whole parse."""
    raw = b'"{\'x\': datetime.datetime(not, valid, args), \'y\': 2}"'
    result = AgentInvoker._parse_agent_response(raw)
    assert result["x"] is None
    assert result["y"] == 2


def test_plain_json_object_passes_through_unchanged():
    raw = b'{"intent": "ACCESS_DENIED", "confidence": 0.9}'
    result = AgentInvoker._parse_agent_response(raw)
    assert result == {"intent": "ACCESS_DENIED", "confidence": 0.9}


def test_unparseable_body_falls_back_to_raw():
    raw = b"not json at all {{{"
    result = AgentInvoker._parse_agent_response(raw)
    assert "_raw" in result
