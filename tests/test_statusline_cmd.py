import json
import tempfile

from hypothesis import given, strategies as st

from pace.model import Activity, Calibration
from pace.statusline_cmd import main, terminal_width
from pace import store
from pace.bar import FILLED

CAL = Calibration(durations_sorted=tuple(float(i) for i in range(1, 41)),
                  n=40, generated_at=0.0)


def payload(**kw):
    base = {"session_id": "s1", "prompt_id": "p1"}
    base.update(kw)
    return json.dumps(base)


def test_first_sight_of_a_prompt_records_turn_start(tmp_path):
    env = {"HOME": str(tmp_path), "COLUMNS": "80"}
    main(payload(), env, now=100.0)
    turn = store.read_turn(store.state_root(env), "s1")
    assert turn.prompt_id == "p1" and turn.first_seen == 100.0


def test_elapsed_grows_within_the_same_prompt(tmp_path):
    env = {"HOME": str(tmp_path), "COLUMNS": "80"}
    main(payload(), env, now=100.0)
    assert "30s" in main(payload(), env, now=130.0)


def test_a_new_prompt_id_resets_elapsed(tmp_path):
    env = {"HOME": str(tmp_path), "COLUMNS": "80"}
    main(payload(), env, now=100.0)
    main(payload(), env, now=200.0)
    assert "0s" in main(payload(prompt_id="p2"), env, now=300.0)


def test_null_prompt_id_renders_idle_blank(tmp_path):
    env = {"HOME": str(tmp_path), "COLUMNS": "80"}
    assert main(payload(prompt_id=None), env, now=100.0).strip() == ""


def test_activity_from_a_previous_turn_is_discarded(tmp_path):
    env = {"HOME": str(tmp_path), "COLUMNS": "80"}
    root = store.state_root(env)
    store.write_activity(root, "s1", Activity(verb="reading old.py", ts=50.0))
    out = main(payload(), env, now=100.0)
    assert "old.py" not in out


def test_checklist_reaches_the_line(tmp_path):
    env = {"HOME": str(tmp_path), "COLUMNS": "80"}
    main(payload(), env, now=100.0)
    store.write_activity(store.state_root(env), "s1",
                         Activity(verb="x", ts=105.0, checklist="3/7"))
    assert "3/7" in main(payload(), env, now=110.0)


def test_current_activity_is_shown(tmp_path):
    env = {"HOME": str(tmp_path), "COLUMNS": "80"}
    main(payload(), env, now=100.0)
    store.write_activity(store.state_root(env), "s1",
                         Activity(verb="running pytest", ts=105.0))
    assert "running pytest" in main(payload(), env, now=110.0)


def test_bar_appears_only_with_calibration(tmp_path):
    env = {"HOME": str(tmp_path), "COLUMNS": "80"}
    main(payload(), env, now=100.0)
    assert FILLED not in main(payload(), env, now=130.0)
    store.write_calibration(store.state_root(env), CAL)
    assert FILLED in main(payload(), env, now=130.0)


def test_malformed_stdin_yields_empty_line(tmp_path):
    assert main("not json", {"HOME": str(tmp_path)}, now=1.0) == ""


def test_terminal_width_prefers_columns_then_falls_back():
    assert terminal_width({"COLUMNS": "254"}) == 254
    assert terminal_width({"COLUMNS": "0"}) == 80
    assert terminal_width({}) == 80


# Two calibrations that disagree: under SHORT, 100s is already past half the
# turns; under LONG, 101s is past only a fifth of them. A background refresh can
# swap one for the other in the middle of a turn.
SHORT = Calibration(
    durations_sorted=tuple(float(i) for i in range(1, 21))
    + tuple(float(200 + i) for i in range(20)),
    n=40, generated_at=0.0)
LONG = Calibration(
    durations_sorted=tuple(float(i) for i in range(1, 9))
    + tuple(float(200 + i) for i in range(32)),
    n=40, generated_at=0.0)


def test_the_bar_never_shrinks_when_the_calibration_is_replaced(tmp_path):
    env = {"HOME": str(tmp_path), "COLUMNS": "80"}
    root = store.state_root(env)
    store.write_calibration(root, SHORT)
    main(payload(), env, now=0.0)

    before = main(payload(), env, now=100.0).count(FILLED)
    store.write_calibration(root, LONG)
    after = main(payload(), env, now=101.0).count(FILLED)

    assert before == 5                     # the pre-refresh reading, for the record
    assert after >= before


def test_a_new_prompt_id_releases_the_ratchet(tmp_path):
    env = {"HOME": str(tmp_path), "COLUMNS": "80"}
    store.write_calibration(store.state_root(env), SHORT)
    main(payload(), env, now=0.0)
    main(payload(), env, now=300.0)                       # ratchets to a full bar
    out = main(payload(prompt_id="p2"), env, now=301.0)   # a fresh turn starts empty
    assert out.count(FILLED) == 0


CALIBRATIONS = (SHORT, LONG, CAL)


@given(steps=st.lists(st.tuples(st.floats(min_value=0.0, max_value=5000.0,
                                          allow_nan=False, allow_infinity=False),
                                st.integers(min_value=0, max_value=len(CALIBRATIONS) - 1)),
                      min_size=1, max_size=12))
def test_filled_glyphs_never_decrease_as_elapsed_grows(steps):
    """Non-decreasing elapsed, any calibration at any moment: the bar only grows."""
    elapsed_points = sorted(e for e, _ in steps)
    choices = [i for _, i in steps]
    with tempfile.TemporaryDirectory() as tmp:
        env = {"HOME": tmp, "COLUMNS": "80"}
        root = store.state_root(env)
        main(payload(), env, now=0.0)
        seen = 0
        for elapsed, choice in zip(elapsed_points, choices):
            store.write_calibration(root, CALIBRATIONS[choice])
            filled = main(payload(), env, now=elapsed).count(FILLED)
            assert filled >= seen
            seen = filled
