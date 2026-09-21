from hypothesis import given, strategies as st
from pace.model import Calibration
from pace.render import human_duration, line
from pace.layout import visible_len
from pace.bar import FILLED, EMPTY

CAL = Calibration(durations_sorted=tuple(float(i) for i in range(1, 41)),
                  n=40, generated_at=0.0)


def test_human_duration_scales():
    assert human_duration(12) == "12s"
    assert human_duration(300) == "5m"
    assert human_duration(3840) == "1h04m"


def test_idle_renders_nothing():
    assert line(None, None, CAL, width=80).strip() == ""


def test_without_calibration_there_is_no_bar():
    out = line(120.0, "running pytest", None, width=80)
    assert FILLED not in out and EMPTY not in out
    assert "2m" in out and "running pytest" in out


def test_with_calibration_the_bar_appears():
    out = line(22.0, "running pytest", CAL, width=80)  # p50 is 21.0 and the crossing is strict
    assert FILLED in out
    assert "half" in out


def test_checklist_is_appended_as_text_only():
    out = line(21.0, "running pytest", CAL, width=80, checklist="3/7")
    assert "3/7" in out
    assert out.count(FILLED + FILLED) >= 1      # the bar is still the only bar


def test_activity_absent_yields_elapsed_only():
    out = line(12.0, None, None, width=80)
    assert out.strip() == "12s"


@given(elapsed=st.floats(min_value=0, max_value=100_000, allow_nan=False),
       width=st.integers(min_value=10, max_value=200))
def test_line_never_exceeds_width(elapsed, width):
    out = line(elapsed, "editing fold.py", CAL, width=width)
    assert visible_len(out) <= width
