import pytest
from hypothesis import given, strategies as st
from pace.bar import render, FILLED, EMPTY


def test_endpoints():
    assert render(0.0, 4) == EMPTY * 4
    assert render(1.0, 4) == FILLED * 4


def test_half_fill():
    assert render(0.5, 10) == FILLED * 5 + EMPTY * 5


def test_zero_width_is_empty_string():
    assert render(0.5, 0) == ""


def test_negative_width_is_empty_string():
    assert render(0.5, -3) == ""


def test_fill_outside_unit_interval_is_rejected():
    with pytest.raises(ValueError):
        render(1.2, 5)


@given(fill=st.floats(min_value=0, max_value=1, allow_nan=False),
       width=st.integers(min_value=0, max_value=200))
def test_length_always_equals_width(fill, width):
    assert len(render(fill, width)) == width


@given(a=st.floats(min_value=0, max_value=1, allow_nan=False),
       b=st.floats(min_value=0, max_value=1, allow_nan=False),
       width=st.integers(min_value=1, max_value=200))
def test_more_fill_never_means_fewer_blocks(a, b, width):
    lo, hi = min(a, b), max(a, b)
    assert render(lo, width).count(FILLED) <= render(hi, width).count(FILLED)
