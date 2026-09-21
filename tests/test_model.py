import dataclasses
import pytest
from pace.model import Calibration, Position, Activity, TurnState


def test_types_are_frozen():
    for cls in (Calibration, Position, Activity, TurnState):
        assert dataclasses.is_dataclass(cls)
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} must be frozen"


def test_calibration_rejects_unsorted_durations():
    with pytest.raises(ValueError):
        Calibration(durations_sorted=(5.0, 1.0), n=2, generated_at=0.0)


def test_position_rejects_fill_outside_unit_interval():
    with pytest.raises(ValueError):
        Position(fill=1.5, threshold=None, beyond_max=False)
