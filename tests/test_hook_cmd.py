import json
from pace.hook_cmd import main, STALE_AFTER_SECONDS
from pace.model import Calibration
from pace import store


def payload(**kw):
    base = {"session_id": "s1", "tool_name": "Bash",
            "tool_input": {"description": "Run the test suite"}}
    base.update(kw)
    return json.dumps(base)


def test_hook_records_the_resolved_verb(tmp_path):
    env = {"HOME": str(tmp_path)}
    assert main(payload(), env, now=10.0) == 0
    act = store.read_activity(store.state_root(env), "s1")
    # Bash description is used verbatim (first char lowercased); conjugation was removed
    # to avoid inventing values the caller never supplied (e.g., "fixxing", "triggerring")
    assert act.verb == "run the test suite"
    assert act.ts == 10.0


def test_hook_overwrites_rather_than_appends(tmp_path):
    env = {"HOME": str(tmp_path)}
    main(payload(), env, now=10.0)
    main(payload(tool_name="Read", tool_input={"file_path": "/a/fold.py"}), env, now=11.0)
    act = store.read_activity(store.state_root(env), "s1")
    assert act.verb == "reading fold.py"
    # Activity files stored in sessions/activity/ per current store contract
    # (eliminated collision that silently destroyed turn state in old flat layout)
    session_files = list((store.state_root(env) / "sessions" / "activity").glob("s1.json"))
    assert len(session_files) == 1


def test_malformed_stdin_is_not_fatal(tmp_path):
    assert main("not json", {"HOME": str(tmp_path)}, now=1.0) == 0


def test_missing_session_id_is_not_fatal(tmp_path):
    assert main(json.dumps({"tool_name": "Bash"}), {"HOME": str(tmp_path)}, now=1.0) == 0


def test_todowrite_records_a_checklist_fraction(tmp_path):
    env = {"HOME": str(tmp_path)}
    todos = {"todos": [{"status": "completed"}, {"status": "completed"},
                       {"status": "in_progress"}, {"status": "pending"}]}
    main(payload(tool_name="TodoWrite", tool_input=todos), env, now=10.0)
    assert store.read_activity(store.state_root(env), "s1").checklist == "2/4"


def test_checklist_is_absent_for_other_tools(tmp_path):
    env = {"HOME": str(tmp_path)}
    main(payload(), env, now=10.0)
    assert store.read_activity(store.state_root(env), "s1").checklist is None


def test_stale_calibration_is_detected(tmp_path):
    env = {"HOME": str(tmp_path)}
    root = store.state_root(env)
    store.write_calibration(root, Calibration(
        durations_sorted=tuple(float(i) for i in range(1, 41)), n=40, generated_at=0.0))
    from pace.hook_cmd import calibration_is_stale
    assert calibration_is_stale(root, now=STALE_AFTER_SECONDS + 1) is True
    assert calibration_is_stale(root, now=10.0) is False
