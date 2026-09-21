import json
from pace.transcripts import turn_durations


def rec(ts, type_, prompt_source=None):
    d = {"timestamp": ts, "type": type_}
    if prompt_source:
        d["promptSource"] = prompt_source
    return json.dumps(d)


def test_bounded_turn_is_measured_to_last_record_before_next_prompt():
    lines = [
        rec("2026-09-21T12:00:00Z", "user", "typed"),
        rec("2026-09-21T12:00:30Z", "assistant"),
        rec("2026-09-21T12:02:00Z", "user", "typed"),
        rec("2026-09-21T12:02:10Z", "assistant"),
    ]
    bounded, final = turn_durations(lines)
    assert bounded == [30.0]
    assert final == [10.0]


def test_tool_results_do_not_start_a_turn():
    lines = [
        rec("2026-09-21T12:00:00Z", "user", "typed"),
        rec("2026-09-21T12:00:10Z", "user"),        # tool result, no promptSource
        rec("2026-09-21T12:00:40Z", "assistant"),
    ]
    bounded, final = turn_durations(lines)
    assert bounded == []
    assert final == [40.0]


def test_malformed_lines_are_skipped_not_fatal():
    lines = [
        "not json",
        rec("2026-09-21T12:00:00Z", "user", "typed"),
        json.dumps({"no": "timestamp"}),
        rec("2026-09-21T12:00:20Z", "assistant"),
    ]
    bounded, final = turn_durations(lines)
    assert final == [20.0]


def test_absurd_durations_are_discarded():
    lines = [
        rec("2026-09-21T12:00:00Z", "user", "typed"),
        rec("2026-09-21T20:00:00Z", "assistant"),   # 8 hours: machine left running
    ]
    bounded, final = turn_durations(lines)
    assert final == []


def test_empty_input_yields_empty_lists():
    assert turn_durations([]) == ([], [])
