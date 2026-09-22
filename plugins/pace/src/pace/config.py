"""User-facing configuration.

Pure: turns an untrusted mapping into a validated Config. Every field falls
back to its default independently, so one bad key never costs the user the
rest of their settings, and a malformed file never costs them the status line.
"""
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from pace.bar import EMPTY, FILLED

# The floor on `min_turns`. Percentiles over a handful of samples are not
# knowledge; below this the distribution is noise wearing a bar's clothes.
MIN_TURNS_FLOOR = 5


@dataclass(frozen=True)
class Config:
    bar_width: int = 10
    filled: str = FILLED
    empty: str = EMPTY
    separator: str = " · "
    show_threshold: bool = True
    show_bar: bool = True
    min_turns: int = 20


DEFAULTS = Config()


def _int(raw: Mapping[str, Any], key: str, default: int,
         low: int, high: int) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value if low <= value <= high else default


def _glyph(raw: Mapping[str, Any], key: str, default: str) -> str:
    value = raw.get(key, default)
    # Exactly one character: a wider "glyph" would silently break bar geometry,
    # which every width guarantee in this project depends on.
    if not isinstance(value, str) or len(value) != 1:
        return default
    return default if ord(value) < 32 or ord(value) == 127 else value


def _text(raw: Mapping[str, Any], key: str, default: str, limit: int) -> str:
    value = raw.get(key, default)
    if not isinstance(value, str) or not 0 < len(value) <= limit:
        return default
    return default if any(ord(c) < 32 or ord(c) == 127 for c in value) else value


def _flag(raw: Mapping[str, Any], key: str, default: bool) -> bool:
    value = raw.get(key, default)
    return value if isinstance(value, bool) else default


def parse(raw: Optional[Mapping[str, Any]]) -> Config:
    """Build a Config from untrusted data. Never raises."""
    if not isinstance(raw, Mapping):
        return DEFAULTS
    return Config(
        bar_width=_int(raw, "bar_width", DEFAULTS.bar_width, 1, 40),
        filled=_glyph(raw, "filled", DEFAULTS.filled),
        empty=_glyph(raw, "empty", DEFAULTS.empty),
        separator=_text(raw, "separator", DEFAULTS.separator, 8),
        show_threshold=_flag(raw, "show_threshold", DEFAULTS.show_threshold),
        show_bar=_flag(raw, "show_bar", DEFAULTS.show_bar),
        min_turns=_int(raw, "min_turns", DEFAULTS.min_turns, MIN_TURNS_FLOOR, 10000),
    )
