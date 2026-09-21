import json
from pace.calibrate_cmd import gather, main
from pace import store


def transcript(tmp, name, turns):
    """turns: list of (start_iso, end_iso) pairs."""
    d = tmp / ".claude" / "projects" / "proj"
    d.mkdir(parents=True, exist_ok=True)
    lines = []
    for start, end in turns:
        lines.append(json.dumps({"timestamp": start, "type": "user",
                                 "promptSource": "typed"}))
        lines.append(json.dumps({"timestamp": end, "type": "assistant"}))
    (d / name).write_text("\n".join(lines))


def test_gather_reads_every_transcript(tmp_path):
    transcript(tmp_path, "a.jsonl", [("2026-09-21T12:00:00Z", "2026-09-21T12:00:30Z"),
                                     ("2026-09-21T13:00:00Z", "2026-09-21T13:01:00Z")])
    durations = gather(tmp_path / ".claude" / "projects")
    assert sorted(durations) == [30.0, 60.0]


def test_main_writes_no_calibration_below_the_floor(tmp_path):
    transcript(tmp_path, "a.jsonl", [("2026-09-21T12:00:00Z", "2026-09-21T12:00:30Z")])
    code = main([], {"HOME": str(tmp_path)}, now=1.0)
    assert code == 0
    assert store.read_calibration(store.state_root({"HOME": str(tmp_path)})) is None


def test_main_writes_calibration_above_the_floor(tmp_path):
    turns = [("2026-09-21T%02d:00:00Z" % h, "2026-09-21T%02d:00:%02dZ" % (h, 10 + h))
             for h in range(0, 22)]
    transcript(tmp_path, "a.jsonl", turns)
    assert main([], {"HOME": str(tmp_path)}, now=42.0) == 0
    cal = store.read_calibration(store.state_root({"HOME": str(tmp_path)}))
    assert cal is not None and cal.n >= 20 and cal.generated_at == 42.0


def test_missing_projects_dir_is_not_an_error(tmp_path):
    assert main([], {"HOME": str(tmp_path)}, now=1.0) == 0
