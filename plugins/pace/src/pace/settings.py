"""Pure transforms on a Claude Code settings dictionary.

Confined to the `statusLine` key and the `hooks.PostToolUse` array. Anything
the user put there themselves is left exactly as found.
"""
import copy
from typing import Dict, List, Tuple

MARKER = "pace-statusline"
HOOK_MARKER = "pace-hook"


def _is_ours(command: object) -> bool:
    return isinstance(command, str) and MARKER in command


def has_foreign_statusline(settings: Dict) -> bool:
    """Leave a statusLine we did not write untouched, because overwriting a
    config we do not own is worse than not installing."""
    existing = settings.get("statusLine")
    if existing is None:
        return False                      # nothing there: ours to write
    if not isinstance(existing, dict):
        return True                       # present but malformed: not ours to touch
    return not _is_ours(existing.get("command"))


def install(settings: Dict, statusline_cmd: str,
            hook_cmd: str) -> Tuple[Dict, List[str]]:
    """Add pace's status line and hook. Returns (settings, notes)."""
    out = copy.deepcopy(settings)
    notes: List[str] = []

    if has_foreign_statusline(out):
        notes.append(
            "An existing status line was found and left untouched. To use pace, "
            "set statusLine.command to: %s" % statusline_cmd)
    else:
        out["statusLine"] = {"type": "command", "command": statusline_cmd,
                             "padding": 0, "refreshInterval": 2}

    hooks = out.setdefault("hooks", {})
    entries = hooks.setdefault("PostToolUse", [])
    already = any(HOOK_MARKER in h.get("command", "")
                  for e in entries if isinstance(e, dict)
                  for h in e.get("hooks", []) if isinstance(h, dict))
    if not already:
        entries.append({"matcher": "*",
                        "hooks": [{"type": "command", "command": hook_cmd}]})
    return out, notes


def uninstall(settings: Dict) -> Dict:
    """Remove only what install() added, restoring the original shape."""
    out = copy.deepcopy(settings)

    existing = out.get("statusLine")
    if isinstance(existing, dict) and _is_ours(existing.get("command")):
        del out["statusLine"]

    hooks = out.get("hooks")
    if isinstance(hooks, dict) and isinstance(hooks.get("PostToolUse"), list):
        kept = []
        for entry in hooks["PostToolUse"]:
            if not isinstance(entry, dict):
                kept.append(entry)
                continue
            inner = [h for h in entry.get("hooks", [])
                     if not (isinstance(h, dict) and HOOK_MARKER in h.get("command", ""))]
            if inner:
                kept.append({**entry, "hooks": inner})
        if kept:
            hooks["PostToolUse"] = kept
        else:
            del hooks["PostToolUse"]
        if not hooks:
            del out["hooks"]
    return out
