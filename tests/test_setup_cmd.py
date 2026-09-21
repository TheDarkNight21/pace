import json
import os

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


def test_existing_settings_are_backed_up_and_the_path_is_reported(tmp_path, capsys):
    env = {"HOME": str(tmp_path)}
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"model": "opus"}))

    assert setup_cmd.main([], env, settings, now=1.0) == 0

    backup = tmp_path / ".claude" / "settings.json.pace-backup"
    assert json.loads(backup.read_text()) == {"model": "opus"}
    assert str(backup) in capsys.readouterr().out
    assert json.loads(settings.read_text())["model"] == "opus"


def test_a_missing_settings_file_needs_no_backup(tmp_path):
    env = {"HOME": str(tmp_path)}
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)

    assert setup_cmd.main([], env, settings, now=1.0) == 0
    assert not (tmp_path / ".claude" / "settings.json.pace-backup").exists()
    assert "statusLine" in json.loads(settings.read_text())


def test_a_failed_write_leaves_the_settings_intact_and_fails(tmp_path, monkeypatch, capsys):
    env = {"HOME": str(tmp_path)}
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    original = json.dumps({"model": "opus"})
    settings.write_text(original)

    def boom(src, dst):
        raise OSError("no space left on device")

    monkeypatch.setattr(os, "replace", boom)
    assert setup_cmd.main([], env, settings, now=1.0) == 1

    assert settings.read_text() == original
    err = capsys.readouterr().err
    assert "no space left on device" in err
    assert "settings.json.pace-backup" in err
    leftovers = [f for f in settings.parent.iterdir() if f.suffix == ".tmp"]
    assert leftovers == []


def test_uninstall_backs_up_and_writes_atomically(tmp_path, monkeypatch):
    env = {"HOME": str(tmp_path)}
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    setup_cmd.main([], env, settings, now=1.0)
    installed = settings.read_text()

    assert setup_cmd.main(["uninstall"], env, settings, now=2.0) == 0
    assert "statusLine" not in json.loads(settings.read_text())
    backup = tmp_path / ".claude" / "settings.json.pace-backup"
    assert backup.read_text() == installed

    def boom(src, dst):
        raise OSError("read-only file system")

    monkeypatch.setattr(os, "replace", boom)
    before = settings.read_text()
    assert setup_cmd.main(["uninstall"], env, settings, now=3.0) == 1
    assert settings.read_text() == before
