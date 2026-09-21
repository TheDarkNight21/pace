from pace.model import Calibration, Activity, TurnState
from pace import store


def test_state_root_honours_home(tmp_path):
    root = store.state_root({"HOME": str(tmp_path)})
    assert root == tmp_path / ".claude" / "pace"


def test_calibration_round_trips(tmp_path):
    cal = Calibration(durations_sorted=(1.0, 2.0, 3.0), n=3, generated_at=99.0)
    store.write_calibration(tmp_path, cal)
    assert store.read_calibration(tmp_path) == cal


def test_activity_round_trips_per_session(tmp_path):
    store.write_activity(tmp_path, "s1", Activity(verb="running pytest", ts=5.0))
    store.write_activity(tmp_path, "s2", Activity(verb="reading a.py", ts=6.0))
    assert store.read_activity(tmp_path, "s1").verb == "running pytest"
    assert store.read_activity(tmp_path, "s2").verb == "reading a.py"


def test_activity_round_trips_the_checklist(tmp_path):
    store.write_activity(tmp_path, "s1", Activity(verb="x", ts=1.0, checklist="3/7"))
    assert store.read_activity(tmp_path, "s1").checklist == "3/7"


def test_turn_round_trips(tmp_path):
    store.write_turn(tmp_path, "s1", TurnState(prompt_id="p1", first_seen=7.0))
    assert store.read_turn(tmp_path, "s1") == TurnState(prompt_id="p1", first_seen=7.0)


def test_missing_files_read_as_none(tmp_path):
    assert store.read_calibration(tmp_path) is None
    assert store.read_activity(tmp_path, "nope") is None
    assert store.read_turn(tmp_path, "nope") is None


def test_corrupt_file_reads_as_none_not_raise(tmp_path):
    store.write_activity(tmp_path, "s1", Activity(verb="x", ts=1.0))
    (tmp_path / "sessions" / "activity" / "s1.json").write_text("{ this is not json")
    assert store.read_activity(tmp_path, "s1") is None


def test_session_ids_cannot_escape_the_state_root(tmp_path):
    store.write_activity(tmp_path, "../../escaped", Activity(verb="x", ts=1.0))
    assert not (tmp_path.parent.parent / "escaped.json").exists()


def test_activity_and_turn_files_cannot_collide(tmp_path):
    store.write_turn(tmp_path, "s1", TurnState(prompt_id="p1", first_seen=100.0))
    store.write_activity(tmp_path, "s1.turn", Activity(verb="clobber", ts=1.0))
    assert store.read_turn(tmp_path, "s1") == TurnState(prompt_id="p1", first_seen=100.0)


def test_temp_files_do_not_leak_on_write_error(tmp_path):
    import json as json_module

    # Monkeypatch json.dump to raise an error after mkstemp
    original_dump = json_module.dump
    call_count = [0]

    def failing_dump(obj, fp, **kwargs):
        call_count[0] += 1
        raise OSError("simulated write failure")

    json_module.dump = failing_dump
    try:
        store.write_activity(tmp_path, "s1", Activity(verb="x", ts=1.0))
    finally:
        json_module.dump = original_dump

    # Verify that no temp files leaked in the sessions directory
    sessions_dir = tmp_path / "sessions" / "activity"
    if sessions_dir.exists():
        files = list(sessions_dir.glob("*"))
        # Should have no leftover .tmp files
        tmp_files = [f for f in files if f.suffix == ".tmp" or ".tmp" in f.name]
        assert len(tmp_files) == 0, f"Temp files leaked: {tmp_files}"
