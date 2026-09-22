"""The only module that touches disk.

Reads never raise: a status line that crashes is worse than one that is blank.
Writes are atomic because several sessions write concurrently.
"""
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Mapping, Optional

from pace.config import Config, parse as parse_config
from pace.model import Activity, Calibration, TurnState

_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


def state_root(env: Mapping[str, str]) -> Path:
    return Path(env.get("HOME", "~")).expanduser() / ".claude" / "pace"


def _safe_name(session_id: str) -> str:
    """Session ids come from outside; never let one address another directory."""
    return _SAFE.sub("_", session_id) or "unknown"


def _read_json(path: Path) -> Optional[dict]:
    try:
        with path.open() as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _write_json(path: Path, payload: dict) -> None:
    tmp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle)
        os.replace(tmp, str(path))
    except (OSError, ValueError):
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _calibration_path(root: Path) -> Path:
    return root / "calibration.json"


def _session_path(root: Path, session_id: str, kind: str) -> Path:
    return root / "sessions" / kind / (_safe_name(session_id) + ".json")


def read_calibration(root: Path) -> Optional[Calibration]:
    data = _read_json(_calibration_path(root))
    if not data:
        return None
    try:
        return Calibration(
            durations_sorted=tuple(float(x) for x in data["durations_sorted"]),
            n=int(data["n"]),
            generated_at=float(data["generated_at"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def write_calibration(root: Path, cal: Calibration) -> None:
    _write_json(_calibration_path(root), {
        "durations_sorted": list(cal.durations_sorted),
        "n": cal.n,
        "generated_at": cal.generated_at,
    })


def read_activity(root: Path, session_id: str) -> Optional[Activity]:
    data = _read_json(_session_path(root, session_id, "activity"))
    if not data:
        return None
    try:
        checklist = data.get("checklist")
        return Activity(
            verb=str(data["verb"]),
            ts=float(data["ts"]),
            checklist=str(checklist) if isinstance(checklist, str) else None,
        )
    except (KeyError, TypeError, ValueError):
        return None


def write_activity(root: Path, session_id: str, activity: Activity) -> None:
    _write_json(_session_path(root, session_id, "activity"),
                {"verb": activity.verb, "ts": activity.ts,
                 "checklist": activity.checklist})


def read_turn(root: Path, session_id: str) -> Optional[TurnState]:
    data = _read_json(_session_path(root, session_id, "turn"))
    if not data:
        return None
    try:
        prompt_id = data.get("prompt_id")
        peak_threshold = data.get("peak_threshold")
        return TurnState(
            prompt_id=str(prompt_id) if prompt_id is not None else None,
            first_seen=float(data["first_seen"]),
            peak_fill=_peak_fill(data.get("peak_fill")),
            peak_threshold=str(peak_threshold) if isinstance(peak_threshold, str) else None,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _peak_fill(value: object) -> float:
    """A turn file written before the ratchet existed simply has no peak."""
    try:
        fill = float(value)            # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, fill))


def write_turn(root: Path, session_id: str, turn: TurnState) -> None:
    _write_json(_session_path(root, session_id, "turn"),
                {"prompt_id": turn.prompt_id, "first_seen": turn.first_seen,
                 "peak_fill": turn.peak_fill, "peak_threshold": turn.peak_threshold})


def config_path(root: Path) -> Path:
    return root / "config.json"


def read_config(root: Path) -> Config:
    """The user's config, or defaults. Never raises — a malformed config
    must cost the user their customisation, never their status line."""
    return parse_config(_read_json(config_path(root)))
