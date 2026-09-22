"""Mine local transcripts for turn durations and write a calibration."""
from pathlib import Path
from typing import List, Mapping, Sequence

from pace import store
from pace.percentiles import calibrate
from pace.transcripts import turn_durations


def gather(projects_dir: Path) -> List[float]:
    """Every bounded turn duration in the local transcripts, and only those.

    Final turns are excluded even when that leaves too few to calibrate,
    because a turn that ends at the transcript's last record absorbs however
    long the user then walked away for -- a lunch break would enter the
    distribution as a two-hour turn. Waiting for enough bounded turns shows no
    bar for a while; blending in idle time would show a wrong one.
    """
    bounded: List[float] = []
    if not projects_dir.is_dir():
        return []
    for path in sorted(projects_dir.glob("*/*.jsonl")):
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        b, _final = turn_durations(text.splitlines())
        bounded.extend(b)
    return bounded


def main(argv: Sequence[str], env: Mapping[str, str], now: float) -> int:
    home = Path(env.get("HOME", "~")).expanduser()
    durations = gather(home / ".claude" / "projects")
    cfg = store.read_config(store.state_root(env))
    cal = calibrate(durations, now=now, min_turns=cfg.min_turns)
    if cal is None:
        return 0
    store.write_calibration(store.state_root(env), cal)
    return 0
