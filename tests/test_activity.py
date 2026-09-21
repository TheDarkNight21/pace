from hypothesis import given, strategies as st
from pace.activity import verb


def test_bash_uses_the_supplied_description():
    assert verb("Bash", {"description": "Run the test suite"}) == "running the test suite"


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


@given(name=st.text(), payload=st.dictionaries(st.text(), st.text()))
def test_verb_never_raises_and_stays_short(name, payload):
    out = verb(name, payload)
    assert isinstance(out, str)
    assert len(out) <= 48
    assert "\n" not in out
