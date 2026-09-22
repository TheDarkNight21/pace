import json

from hypothesis import given, strategies as st

from pace import store
from pace.config import DEFAULTS, MIN_TURNS_FLOOR, Config, parse
from pace.model import Calibration
from pace.render import line

CAL = Calibration(durations_sorted=tuple(float(i) for i in range(1, 41)),
                  n=40, generated_at=0.0)


def test_absent_config_is_defaults():
    assert parse(None) == DEFAULTS
    assert parse({}) == DEFAULTS


def test_each_field_overrides_independently():
    cfg = parse({"bar_width": 20, "show_threshold": False})
    assert cfg.bar_width == 20
    assert cfg.show_threshold is False
    assert cfg.filled == DEFAULTS.filled          # untouched keys keep defaults


def test_one_bad_key_does_not_discard_the_others():
    cfg = parse({"bar_width": "wide", "empty": "-"})
    assert cfg.bar_width == DEFAULTS.bar_width    # rejected
    assert cfg.empty == "-"                       # accepted


def test_multi_character_glyphs_are_rejected():
    # A wider glyph would silently break every width guarantee in the project.
    assert parse({"filled": "ab"}).filled == DEFAULTS.filled
    assert parse({"filled": ""}).filled == DEFAULTS.filled


def test_control_characters_are_rejected_everywhere():
    assert parse({"filled": "\x1b"}).filled == DEFAULTS.filled
    assert parse({"separator": " \x07 "}).separator == DEFAULTS.separator


def test_booleans_are_not_accepted_as_integers():
    assert parse({"bar_width": True}).bar_width == DEFAULTS.bar_width


def test_min_turns_is_clamped_to_the_floor():
    assert parse({"min_turns": 1}).min_turns == DEFAULTS.min_turns
    assert parse({"min_turns": MIN_TURNS_FLOOR}).min_turns == MIN_TURNS_FLOOR


def test_config_round_trips_through_disk(tmp_path):
    store.config_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    store.config_path(tmp_path).write_text(json.dumps({"bar_width": 4, "filled": "#"}))
    cfg = store.read_config(tmp_path)
    assert cfg.bar_width == 4 and cfg.filled == "#"


def test_a_corrupt_config_file_yields_defaults_not_a_crash(tmp_path):
    store.config_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    store.config_path(tmp_path).write_text("{ not json")
    assert store.read_config(tmp_path) == DEFAULTS


def test_a_missing_config_file_yields_defaults(tmp_path):
    assert store.read_config(tmp_path) == DEFAULTS


def test_config_visibly_changes_the_rendered_line():
    plain = line(30.0, "running pytest", CAL, width=90)
    custom = line(30.0, "running pytest", CAL, width=90,
                  cfg=Config(bar_width=4, filled="#", empty="-",
                             separator=" | ", show_threshold=False))
    # fill is 0.725, so a 4-wide bar is three filled and one empty
    assert "###-" in custom
    assert DEFAULTS.filled not in custom and DEFAULTS.filled in plain
    assert " | " in custom and " · " not in custom
    # p75 is exactly 30.0 and the crossing is strict, so 30s reads as "past half"
    assert "past half" in plain and "past half" not in custom


def test_show_bar_false_removes_the_bar_but_keeps_the_text():
    out = line(30.0, "running pytest", CAL, width=90,
               cfg=Config(show_bar=False))
    assert DEFAULTS.filled not in out and DEFAULTS.empty not in out
    assert "running pytest" in out


@given(raw=st.dictionaries(st.text(max_size=12),
                           st.one_of(st.integers(), st.text(max_size=12),
                                     st.booleans(), st.none())))
def test_parse_never_raises_and_always_yields_a_usable_bar_width(raw):
    cfg = parse(raw)
    assert isinstance(cfg, Config)
    assert 1 <= cfg.bar_width <= 40
    assert len(cfg.filled) == 1 and len(cfg.empty) == 1
    assert cfg.min_turns >= MIN_TURNS_FLOOR


def test_default_glyphs_track_the_bar_module():
    """One source of truth. These were declared independently in two places,
    so editing bar.FILLED changed nothing and looked like a broken install."""
    from pace import bar
    assert DEFAULTS.filled == bar.FILLED
    assert DEFAULTS.empty == bar.EMPTY
