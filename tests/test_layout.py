from hypothesis import given, strategies as st
from pace.layout import visible_len, join, right_align

RED = "\x1b[31m"
RESET = "\x1b[0m"


def test_visible_len_ignores_ansi():
    assert visible_len(RED + "abc" + RESET) == 3


def test_join_drops_empty_segments():
    assert join(["5m", "", "running pytest", None]) == "5m · running pytest"


def test_right_align_pads_to_width():
    assert right_align("abc", 6) == "   abc"


def test_right_align_keeps_ansi_but_measures_without_it():
    out = right_align(RED + "abc" + RESET, 6)
    assert out.startswith("   ")
    assert visible_len(out) == 6


def test_right_align_truncates_from_the_left_when_too_long():
    assert right_align("abcdef", 4) == "cdef"


def test_right_align_with_nonpositive_width_returns_input():
    assert right_align("abc", 0) == "abc"


@given(text=st.text(max_size=50), width=st.integers(min_value=1, max_value=120))
def test_never_exceeds_width(text, width):
    assert visible_len(right_align(text, width)) <= width
