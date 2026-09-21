import json

import pytest

from pace import calibrate_cmd, setup_cmd, store


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


def history(tmp_path, hours=24):
    turns = [("2026-09-%02dT12:00:00Z" % (h + 1), "2026-09-%02dT12:00:%02dZ" % (h + 1, 10 + h))
             for h in range(hours)]
    transcript(tmp_path, "a.jsonl", turns)


def test_install_builds_the_first_calibration(tmp_path, capsys):
    env = {"HOME": str(tmp_path)}
    history(tmp_path)
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)

    assert setup_cmd.main([], env, settings, now=1000.0) == 0

    cal = store.read_calibration(store.state_root(env))
    assert cal is not None and cal.generated_at == 1000.0
    assert "Calibrated from %d past turns." % cal.n in capsys.readouterr().out


def test_install_without_history_says_so_and_writes_no_calibration(tmp_path, capsys):
    env = {"HOME": str(tmp_path)}
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)

    assert setup_cmd.main([], env, settings, now=1.0) == 0

    assert store.read_calibration(store.state_root(env)) is None
    out = capsys.readouterr().out
    assert "Not enough history yet (need 20 completed turns)." in out
    assert "elapsed time and current activity work now." in out


def test_a_calibrator_failure_does_not_fail_the_install(tmp_path, monkeypatch, capsys):
    env = {"HOME": str(tmp_path)}
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)

    def boom(argv, env_, now):
        raise RuntimeError("transcripts unreadable")

    monkeypatch.setattr(calibrate_cmd, "main", boom)
    assert setup_cmd.main([], env, settings, now=1.0) == 0

    written = json.loads(settings.read_text())
    assert "pace-statusline" in written["statusLine"]["command"]
    assert "Calibration could not run" in capsys.readouterr().err


def test_uninstall_does_not_calibrate(tmp_path, monkeypatch):
    env = {"HOME": str(tmp_path)}
    history(tmp_path)
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text("{}")

    monkeypatch.setattr(calibrate_cmd, "main",
                        lambda *a, **k: pytest.fail("uninstall must not calibrate"))
    assert setup_cmd.main(["uninstall"], env, settings, now=1.0) == 0
