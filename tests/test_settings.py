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
