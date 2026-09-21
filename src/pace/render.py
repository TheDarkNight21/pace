"""Compose the status line. Pure: no clock, no disk, no width discovery."""
from typing import Optional

from pace import bar, layout
from pace.model import Calibration
from pace.percentiles import position


def human_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return "%ds" % seconds
    if seconds < 3600:
        return "%dm" % (seconds // 60)
    return "%dh%02dm" % (seconds // 3600, (seconds % 3600) // 60)


def line(elapsed: Optional[float],
         activity_verb: Optional[str],
         cal: Optional[Calibration],
         width: int,
         bar_width: int = 10,
         checklist: Optional[str] = None) -> str:
    """The status line, right-aligned within `width`.

    `elapsed is None` means the session is idle and the line stays empty.
    `cal is None` means there is not enough history for a bar, so no bar is
    drawn at all -- an empty bar would assert the turn had just begun.
    """
    if elapsed is None:
        return ""

    prefix = ""
    threshold = None
    if cal is not None:
        pos = position(cal, elapsed)
        prefix = bar.render(pos.fill, bar_width) + "  "
        threshold = pos.threshold

    body = layout.join([human_duration(elapsed), checklist, activity_verb, threshold])
    return layout.right_align(prefix + body, width)
