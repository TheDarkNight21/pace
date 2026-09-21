"""Pure parsing of Claude Code transcript lines into turn durations."""
import json
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

MAX_PLAUSIBLE_TURN_SECONDS = 3 * 3600


def _parse_ts(value: object) -> Optional[float]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def turn_durations(lines: Iterable[str]) -> Tuple[List[float], List[float]]:
    """Return (bounded, final) turn durations in seconds.

    A bounded turn is followed by another typed prompt, so its end is known.
    A final turn ends at the transcript's last record and may include idle time,
    so callers can weigh it separately.
    """
    records: List[Tuple[float, str, Optional[str]]] = []
    for line in lines:
        try:
            item = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(item, dict):
            continue
        ts = _parse_ts(item.get("timestamp"))
        if ts is None:
            continue
        source = item.get("promptSource")
        records.append((ts, str(item.get("type")), source if isinstance(source, str) else None))

    records.sort(key=lambda r: r[0])
    starts = [i for i, (_, type_, src) in enumerate(records)
              if type_ == "user" and src == "typed"]

    bounded: List[float] = []
    final: List[float] = []
    for k, i in enumerate(starts):
        is_final = k + 1 >= len(starts)
        end = len(records) - 1 if is_final else starts[k + 1] - 1
        if end <= i:
            continue
        duration = records[end][0] - records[i][0]
        if not 0 < duration < MAX_PLAUSIBLE_TURN_SECONDS:
            continue
        (final if is_final else bounded).append(duration)
    return bounded, final
