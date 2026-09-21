"""Domain types. All immutable; invariants enforced at construction."""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Calibration:
    """Turn durations in seconds, ascending, from the user's own transcripts."""
    durations_sorted: Tuple[float, ...]
    n: int
    generated_at: float

    def __post_init__(self) -> None:
        d = self.durations_sorted
        if any(d[i] > d[i + 1] for i in range(len(d) - 1)):
            raise ValueError("durations_sorted must be ascending")


@dataclass(frozen=True)
class Position:
    """Where the current turn sits in the historical distribution."""
    fill: float
    threshold: Optional[str]
    beyond_max: bool

    def __post_init__(self) -> None:
        if not 0.0 <= self.fill <= 1.0:
            raise ValueError("fill must be within [0, 1]")


@dataclass(frozen=True)
class Activity:
    """What the model is doing now, resolved at capture time.

    The verb is resolved by the hook rather than the renderer, because
    `tool_input` exists only at the moment of the tool call.
    """
    verb: str
    ts: float
    checklist: Optional[str] = None


@dataclass(frozen=True)
class TurnState:
    """When this session first observed the current prompt_id."""
    prompt_id: Optional[str]
    first_seen: float
