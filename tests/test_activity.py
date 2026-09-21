from hypothesis import given, strategies as st
from pace.activity import verb


def test_bash_lowercases_the_supplied_description():
    assert verb("Bash", {"description": "Run the test suite"}) == "run the test suite"


def test_bash_without_description_falls_back_to_the_binary():
    assert verb("Bash", {"command": "pytest -q tests/"}) == "running pytest"


def test_file_tools_name_the_basename():
    assert verb("Read", {"file_path": "/a/b/fold.py"}) == "reading fold.py"
    assert verb("Edit", {"file_path": "/a/b/fold.py"}) == "editing fold.py"
    assert verb("Write", {"file_path": "/a/b/new.py"}) == "writing new.py"


def test_search_tools_name_the_pattern():
    assert verb("Grep", {"pattern": "def main"}) == "searching for 'def main'"


def test_unknown_tool_degrades_to_its_own_name():
    assert verb("SomeFutureTool", {}) == "SomeFutureTool"


def test_empty_tool_name_is_neutral():
    assert verb("", {}) == "working"


def test_an_escape_sequence_in_a_pattern_is_stripped():
    out = verb("Grep", {"pattern": "\x1b[2Jwiped"})
    assert "\x1b" not in out
    assert out == "searching for '[2Jwiped'"


def test_a_bell_in_a_bash_description_is_stripped():
    assert verb("Bash", {"description": "ring\x07 the bell"}) == "ring the bell"


def test_a_raw_newline_in_a_description_becomes_a_space():
    out = verb("Bash", {"description": "First line\nsecond line"})
    assert out == "first line second line"


def test_an_escape_cannot_survive_the_length_clip():
    long_description = "\x1b[31m" + "a" * 60
    out = verb("Bash", {"description": long_description})
    assert "\x1b" not in out and len(out) <= 48


def test_control_characters_never_reach_a_file_path_verb():
    out = verb("Read", {"file_path": "/a/b/we\x00ird\x1b.py"})
    assert all(ord(c) >= 0x20 and ord(c) != 0x7F for c in out)


@given(name=st.text(), payload=st.dictionaries(st.text(), st.text()))
def test_verb_never_raises_and_stays_short(name, payload):
    out = verb(name, payload)
    assert isinstance(out, str)
    assert len(out) <= 48
    assert "\n" not in out
    assert all(ord(c) >= 0x20 and ord(c) != 0x7F for c in out)
