"""Mine local transcripts for turn durations and write a calibration."""
from pathlib import Path
from typing import List, Mapping, Sequence

from pace import store
from pace.percentiles import MIN_TURNS, calibrate
from pace.transcripts import turn_durations


def gather(projects_dir: Path) -> List[float]:
    """All bounded turn durations, falling back to final turns if too few."""
    bounded: List[float] = []
    final: List[float] = []
    if not projects_dir.is_dir():
        return []
    for path in sorted(projects_dir.glob("*/*.jsonl")):
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        b, f = turn_durations(text.splitlines())
        bounded.extend(b)
        final.extend(f)
    if len(bounded) >= MIN_TURNS:
        return bounded
    return bounded + final


def main(argv: Sequence[str], env: Mapping[str, str], now: float) -> int:
    home = Path(env.get("HOME", "~")).expanduser()
    durations = gather(home / ".claude" / "projects")
    cal = calibrate(durations, now=now)
    if cal is None:
        return 0
    store.write_calibration(store.state_root(env), cal)
    return 0
