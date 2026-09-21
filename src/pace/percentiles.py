"""Empirical distribution of turn durations, and where a turn sits in it."""
import bisect
from typing import Optional, Sequence

from pace.model import Calibration, Position

MIN_TURNS = 20

# (quantile, message) — highest crossed quantile wins.
_THRESHOLDS = (
    (0.50, "past half your turns"),
    (0.75, "longer than 75% of turns"),
    (0.90, "longer than 90% of turns"),
)


def calibrate(durations: Sequence[float], now: float,
              min_turns: int = MIN_TURNS) -> Optional[Calibration]:
    """Build a Calibration, or None when there is not enough history.

    Returning None rather than a degenerate Calibration is deliberate: a
    percentile over a handful of samples is not knowledge, and the caller
    must render no bar at all.
    """
    usable = sorted(float(d) for d in durations if d > 0)
    if len(usable) < min_turns:
        return None
    return Calibration(durations_sorted=tuple(usable), n=len(usable), generated_at=now)


def percentile(cal: Calibration, q: float) -> float:
    """Nearest-rank percentile of the observed durations."""
    d = cal.durations_sorted
    idx = min(len(d) - 1, max(0, int(round(q * (len(d) - 1)))))
    return d[idx]


def position(cal: Calibration, elapsed: float) -> Position:
    """Where `elapsed` sits in the distribution, as the empirical CDF."""
    d = cal.durations_sorted
    shorter = bisect.bisect_left(d, elapsed)
    fill = shorter / len(d)
    beyond_max = elapsed > d[-1]

    threshold = None
    for q, message in _THRESHOLDS:
        if elapsed > percentile(cal, q):
            threshold = message
    if beyond_max:
        threshold = "longer than any turn yet"
    return Position(fill=min(1.0, max(0.0, fill)), threshold=threshold,
                    beyond_max=beyond_max)
