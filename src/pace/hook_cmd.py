"""PostToolUse hook: record what the model is doing, then get out of the way."""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Optional

from pace import store
from pace.activity import verb
from pace.model import Activity

STALE_AFTER_SECONDS = 7 * 24 * 3600


def checklist_fraction(tool_name: str, tool_input: Mapping) -> Optional[str]:
    """done/total" when a checklist tool was used, else None.

    Opportunistic only: pace never enables the todo tools and never asks the
    model to keep a checklist. When one happens to exist, it is reported as
    text -- never as bar geometry, because a revised checklist can shrink.
    """
    if tool_name != "TodoWrite":
        return None
    todos = tool_input.get("todos")
    if not isinstance(todos, list) or not todos:
        return None
    done = sum(1 for t in todos
               if isinstance(t, dict) and t.get("status") == "completed")
    return "%d/%d" % (done, len(todos))


def calibration_is_stale(root: Path, now: float) -> bool:
    cal = store.read_calibration(root)
    if cal is None:
        return False          # absent, not stale: install handles the first build
    return (now - cal.generated_at) > STALE_AFTER_SECONDS


def _spawn_refresh() -> None:
    script = Path(__file__).resolve().parents[2] / "bin" / "pace-calibrate"
    if not script.exists():
        return
    try:
        subprocess.Popen([sys.executable, str(script)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def main(stdin_text: str, env: Mapping[str, str], now: float) -> int:
    try:
        event = json.loads(stdin_text)
    except (ValueError, TypeError):
        return 0
    if not isinstance(event, dict):
        return 0

    session_id = event.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return 0

    tool_input = event.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    tool_name = str(event.get("tool_name") or "")

    root = store.state_root(env)
    store.write_activity(root, session_id, Activity(
        verb=verb(tool_name, tool_input),
        ts=now,
        checklist=checklist_fraction(tool_name, tool_input),
    ))

    if calibration_is_stale(root, now):
        _spawn_refresh()
    return 0
