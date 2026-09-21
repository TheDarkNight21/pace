import pytest
from hypothesis import given, strategies as st
from pace.percentiles import calibrate, position, percentile, MIN_TURNS

DURATIONS = [float(i) for i in range(1, 41)]   # 1..40 seconds, 40 samples


def cal():
    c = calibrate(DURATIONS, now=1000.0)
    assert c is not None
    return c


def test_below_min_turns_yields_no_calibration():
    assert calibrate([1.0, 2.0, 3.0], now=0.0) is None
    assert calibrate([], now=0.0) is None


def test_calibration_sorts_and_counts():
    c = calibrate([9.0, 1.0] + DURATIONS, now=5.0)
    assert c.n == 42
    assert c.generated_at == 5.0
    assert list(c.durations_sorted) == sorted([9.0, 1.0] + DURATIONS)


def test_fill_is_empirical_cdf():
    c = cal()
    assert position(c, 0.0).fill == 0.0
    assert position(c, 20.5).fill == pytest.approx(0.5)
    assert position(c, 1000.0).fill == 1.0


def test_beyond_max_is_flagged():
    c = cal()
    assert position(c, 1000.0).beyond_max is True
    assert position(c, 5.0).beyond_max is False


def test_thresholds_appear_at_crossings():
    c = cal()
    assert position(c, 2.0).threshold is None
    assert "half" in position(c, 22.0).threshold   # p50 is 21.0; crossing is strict
    assert "75%" in position(c, 31.0).threshold
    assert "90%" in position(c, 37.0).threshold
    assert "any turn" in position(c, 1000.0).threshold


@given(
    elapsed_a=st.floats(min_value=0, max_value=10_000, allow_nan=False),
    delta=st.floats(min_value=0, max_value=10_000, allow_nan=False),
)
def test_fill_is_monotonic_in_elapsed(elapsed_a, delta):
    """The law: the bar can never run backwards."""
    c = cal()
    assert position(c, elapsed_a).fill <= position(c, elapsed_a + delta).fill


@given(q=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
def test_percentiles_are_within_observed_range(q):
    c = cal()
    v = percentile(c, q)
    assert c.durations_sorted[0] <= v <= c.durations_sorted[-1]
