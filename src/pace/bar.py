"""Bar geometry. Pure; no colour, no width discovery."""

FILLED = "▓"
EMPTY = "░"


def render(fill: float, width: int) -> str:
    """A bar of exactly `width` characters, `fill` of them filled."""
    if not 0.0 <= fill <= 1.0:
        raise ValueError("fill must be within [0, 1]")
    if width <= 0:
        return ""
    filled = int(round(fill * width))
    filled = min(width, max(0, filled))
    return FILLED * filled + EMPTY * (width - filled)
