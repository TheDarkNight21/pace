from hypothesis import given, strategies as st
from pace.settings import install, uninstall, has_foreign_statusline

STATUS = "python3 /opt/pace/bin/pace-statusline"
HOOK = "python3 /opt/pace/bin/pace-hook"


def test_install_into_empty_settings():
    out, notes = install({}, STATUS, HOOK)
    assert out["statusLine"]["command"] == STATUS
    assert out["statusLine"]["padding"] == 0
    assert out["statusLine"]["refreshInterval"] == 2
    assert notes == []


def test_install_adds_the_hook():
    out, _ = install({}, STATUS, HOOK)
    entries = out["hooks"]["PostToolUse"]
    assert any(h["command"] == HOOK for e in entries for h in e["hooks"])


def test_install_is_idempotent():
    once, _ = install({}, STATUS, HOOK)
    twice, _ = install(once, STATUS, HOOK)
    assert once == twice


def test_install_preserves_unrelated_keys():
    out, _ = install({"model": "opus[1m]"}, STATUS, HOOK)
    assert out["model"] == "opus[1m]"


def test_a_foreign_statusline_is_never_overwritten():
    existing = {"statusLine": {"type": "command", "command": "~/my/ps1.sh"}}
    out, notes = install(existing, STATUS, HOOK)
    assert out["statusLine"]["command"] == "~/my/ps1.sh"
    assert any("existing status line" in n for n in notes)
    assert has_foreign_statusline(existing) is True


def test_a_foreign_hook_is_preserved_alongside_ours():
    existing = {"hooks": {"PostToolUse": [
        {"matcher": "*", "hooks": [{"type": "command", "command": "other.sh"}]}]}}
    out, _ = install(existing, STATUS, HOOK)
    commands = [h["command"] for e in out["hooks"]["PostToolUse"] for h in e["hooks"]]
    assert "other.sh" in commands and HOOK in commands


def test_a_non_dict_statusline_is_never_overwritten():
    for value in ("~/my/ps1.sh", ["~/my/ps1.sh"], 42, {}):
        existing = {"statusLine": value}
        out, notes = install(existing, STATUS, HOOK)
        assert out["statusLine"] == value, f"clobbered {value!r}"
        assert any("existing status line" in n for n in notes)
        assert has_foreign_statusline(existing) is True


def test_absent_statusline_is_not_foreign():
    assert has_foreign_statusline({}) is False
    out, notes = install({}, STATUS, HOOK)
    assert out["statusLine"]["command"] == STATUS
    assert notes == []


def test_uninstall_restores_the_original():
    original = {"model": "opus[1m]",
                "hooks": {"PostToolUse": [
                    {"matcher": "*", "hooks": [{"type": "command", "command": "other.sh"}]}]}}
    installed, _ = install(dict(original), STATUS, HOOK)
    assert uninstall(installed) == original


def test_uninstall_leaves_a_foreign_statusline_alone():
    existing = {"statusLine": {"type": "command", "command": "~/my/ps1.sh"}}
    assert uninstall(dict(existing)) == existing


def test_uninstall_leaves_a_foreign_non_dict_statusline_alone():
    for value in ("~/my/ps1.sh", ["~/my/ps1.sh"], 42, {}):
        existing = {"statusLine": value}
        assert uninstall(dict(existing)) == existing, f"uninstall clobbered {value!r}"


@given(extra=st.dictionaries(
    st.text(min_size=1).filter(lambda k: k not in ("statusLine", "hooks")),
    st.integers()))
def test_install_then_uninstall_is_identity(extra):
    """The law: setup must be perfectly reversible."""
    installed, _ = install(dict(extra), STATUS, HOOK)
    assert uninstall(installed) == extra


# --- runtime installation ------------------------------------------------
# A plugin lives in a marketplace cache that is deleted on uninstall and
# rewritten on upgrade. These tests pin the behaviour that keeps a removed
# plugin from leaving Claude Code running a path that no longer exists.

import json as _json

from pace import store
from pace.setup_cmd import install_runtime, main as setup_main, remove_runtime, runtime_root


def _fake_source(tmp_path):
    src = tmp_path / "source"
    (src / "bin").mkdir(parents=True)
    (src / "src" / "pace").mkdir(parents=True)
    (src / "bin" / "pace-statusline").write_text("#!/usr/bin/env python3\n")
    (src / "src" / "pace" / "__init__.py").write_text("")
    return src


def test_install_runtime_copies_bin_and_src(tmp_path):
    target = tmp_path / "runtime"
    assert install_runtime(_fake_source(tmp_path), target) is None
    assert (target / "bin" / "pace-statusline").exists()
    assert (target / "src" / "pace" / "__init__.py").exists()


def test_installed_scripts_are_executable(tmp_path):
    target = tmp_path / "runtime"
    install_runtime(_fake_source(tmp_path), target)
    assert (target / "bin" / "pace-statusline").stat().st_mode & 0o111


def test_install_runtime_replaces_a_previous_copy(tmp_path):
    source, target = _fake_source(tmp_path), tmp_path / "runtime"
    install_runtime(source, target)
    (target / "bin" / "stale-leftover").write_text("x")
    install_runtime(source, target)
    assert not (target / "bin" / "stale-leftover").exists()


def test_remove_runtime_is_silent_when_absent(tmp_path):
    remove_runtime(tmp_path / "never-existed")      # must not raise


def test_setup_points_settings_at_the_copied_runtime(tmp_path):
    env = {"HOME": str(tmp_path)}
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    assert setup_main([], env, settings, now=0.0) == 0
    command = _json.loads(settings.read_text())["statusLine"]["command"]
    assert str(runtime_root(env)) in command
    assert (runtime_root(env) / "bin" / "pace-statusline").exists()


def test_in_place_points_settings_at_the_source_tree(tmp_path):
    env = {"HOME": str(tmp_path)}
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    assert setup_main(["--in-place"], env, settings, now=0.0) == 0
    command = _json.loads(settings.read_text())["statusLine"]["command"]
    assert str(runtime_root(env)) not in command
    assert not runtime_root(env).exists()


def test_uninstall_removes_the_copied_runtime(tmp_path):
    env = {"HOME": str(tmp_path)}
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    setup_main([], env, settings, now=0.0)
    assert runtime_root(env).exists()
    assert setup_main(["uninstall"], env, settings, now=0.0) == 0
    assert not runtime_root(env).exists()
    assert "statusLine" not in _json.loads(settings.read_text())


def test_switching_to_in_place_clears_a_stale_runtime_copy(tmp_path):
    """Settings stop referencing the copy, so it must not be left behind."""
    env = {"HOME": str(tmp_path)}
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    setup_main([], env, settings, now=0.0)              # default: copies runtime
    assert runtime_root(env).exists()
    setup_main(["--in-place"], env, settings, now=0.0)  # switch modes
    assert not runtime_root(env).exists()
    command = _json.loads(settings.read_text())["statusLine"]["command"]
    assert str(runtime_root(env)) not in command


def test_reinstalling_from_a_new_root_moves_the_hook_too(tmp_path):
    """A hook left pointing at a deleted path fails every single tool call."""
    old_status = "python3 /old/root/bin/pace-statusline"
    old_hook = "python3 /old/root/bin/pace-hook"
    installed, _ = install({}, old_status, old_hook)

    new_status = "python3 /new/root/bin/pace-statusline"
    new_hook = "python3 /new/root/bin/pace-hook"
    moved, _ = install(installed, new_status, new_hook)

    assert moved["statusLine"]["command"] == new_status
    commands = [h["command"] for e in moved["hooks"]["PostToolUse"] for h in e["hooks"]]
    assert commands == [new_hook], "the stale hook survived a reinstall"


def test_reinstalling_does_not_duplicate_the_hook(tmp_path):
    once, _ = install({}, STATUS, HOOK)
    twice, _ = install(once, STATUS, HOOK)
    commands = [h["command"] for e in twice["hooks"]["PostToolUse"] for h in e["hooks"]]
    assert commands.count(HOOK) == 1
