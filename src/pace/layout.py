"""Line assembly. Pure; callers supply the width."""
import re
from typing import Optional, Sequence

SEPARATOR = " · "
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def visible_len(text: str) -> int:
    """Length of `text` as the terminal will show it."""
    return len(_ANSI.sub("", text))


def join(segments: Sequence[Optional[str]]) -> str:
    """Join non-empty segments. An absent segment contributes nothing."""
    return SEPARATOR.join(s for s in segments if s)


def right_align(text: str, width: int) -> str:
    """Pad `text` to `width`, or trim it from the left if it overflows."""
    if width <= 0:
        return text
    shown = visible_len(text)
    if shown == width:
        return text
    if shown < width:
        return " " * (width - shown) + text
    plain = _ANSI.sub("", text)
    return plain[len(plain) - width:]
