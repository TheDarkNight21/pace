"""Status line renderer. Runs every couple of seconds, for every live session."""
import dataclasses
import json
from typing import Mapping, Optional, Tuple

from pace import store
from pace.model import Calibration, TurnState
from pace.percentiles import position
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

    cal = store.read_calibration(root)
    fill, threshold = _ratcheted_fill(root, session_id, turn, cal, elapsed)

    return line(elapsed=elapsed,
                activity_verb=current.verb if current else None,
                cal=cal,
                width=terminal_width(env),
                cfg=store.read_config(root),
                checklist=current.checklist if current else None,
                fill=fill,
                threshold=threshold)


def _ratcheted_fill(root, session_id: str, turn: TurnState,
                    cal: Optional[Calibration],
                    elapsed: float) -> "Tuple[Optional[float], Optional[str]]":
    """The fill to draw, never below what this turn has already shown.

    The calibration on disk can be replaced mid-turn by a background refresh,
    which would otherwise move the same elapsed time to a lower percentile and
    run the bar backwards. The peak is carried on the turn, so monotonicity
    holds whatever the cause.
    """
    if cal is None:
        return None, None
    pos = position(cal, elapsed)
    if pos.fill < turn.peak_fill:
        return turn.peak_fill, turn.peak_threshold
    store.write_turn(root, session_id, dataclasses.replace(
        turn, peak_fill=pos.fill, peak_threshold=pos.threshold))
    return pos.fill, pos.threshold
