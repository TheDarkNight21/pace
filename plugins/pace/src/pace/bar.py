"""Bar geometry. Pure; no colour, no width discovery."""

FILLED = "▓"
EMPTY = "░"


def render(fill: float, width: int,
           filled: str = FILLED, empty: str = EMPTY) -> str:
    """A bar of exactly `width` characters, `fill` of them filled."""
    if not 0.0 <= fill <= 1.0:
        raise ValueError("fill must be within [0, 1]")
    if width <= 0:
        return ""
    filled_count = int(round(fill * width))
    filled_count = min(width, max(0, filled_count))
    n = filled_count
    return filled * n + empty * (width - n)
