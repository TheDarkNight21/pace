"""Status line renderer. Runs every couple of seconds, for every live session."""
import json
from typing import Mapping

from pace import store
from pace.model import TurnState
from pace.render import line

DEFAULT_WIDTH = 80


def terminal_width(env: Mapping[str, str]) -> int:
    """Claude Code exports COLUMNS from its own stdout; fall back when headless."""
    try:
        width = int(env.get("COLUMNS", "") or 0)
    except ValueError:
        return DEFAULT_WIDTH
    return width if width > 0 else DEFAULT_WIDTH


def main(stdin_text: str, env: Mapping[str, str], now: float) -> str:
    try:
        payload = json.loads(stdin_text)
    except (ValueError, TypeError):
        return ""
    if not isinstance(payload, dict):
        return ""

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return ""

    prompt_id = payload.get("prompt_id")
    prompt_id = prompt_id if isinstance(prompt_id, str) else None
    root = store.state_root(env)

    if prompt_id is None:
        return ""                      # idle: the session is waiting for the user

    turn = store.read_turn(root, session_id)
    if turn is None or turn.prompt_id != prompt_id:
        turn = TurnState(prompt_id=prompt_id, first_seen=now)
        store.write_turn(root, session_id, turn)

    elapsed = max(0.0, now - turn.first_seen)

    activity = store.read_activity(root, session_id)
    current = activity if activity and activity.ts >= turn.first_seen else None

    return line(elapsed=elapsed,
                activity_verb=current.verb if current else None,
                cal=store.read_calibration(root),
                width=terminal_width(env),
                checklist=current.checklist if current else None)
