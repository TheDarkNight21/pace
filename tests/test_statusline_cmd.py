import json
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
