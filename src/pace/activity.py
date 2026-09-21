"""Turn a tool call into a short human phrase."""
import os
from typing import Mapping

MAX_VERB = 48

# Descriptions, paths and patterns are model-supplied and reach the terminal
# verbatim every refresh, so an ESC in one would be a live escape sequence.
# Control characters are removed; the whitespace ones become a space first so
# that stripping them cannot run two words together.
_CONTROL = dict.fromkeys(range(0x20), None)
_CONTROL[0x7F] = None
for _whitespace in (0x09, 0x0A, 0x0B, 0x0C, 0x0D):
    _CONTROL[_whitespace] = " "


def _clip(text: str) -> str:
    """Strip control characters, collapse whitespace, then clip to MAX_VERB.

    The strip runs before the clip so a cut can never leave a severed escape.
    """
    text = " ".join(text.translate(_CONTROL).split())
    return text if len(text) <= MAX_VERB else text[: MAX_VERB - 1] + "…"


def verb(tool_name: str, tool_input: Mapping[str, object]) -> str:
    """A short phrase for what the model is doing right now.

    Unknown tools return their own name: naming the tool is true, whereas
    inventing an activity for it is not.
    """
    def field(key: str) -> str:
        value = tool_input.get(key) if isinstance(tool_input, Mapping) else None
        return value if isinstance(value, str) else ""

    if not tool_name:
        return "working"

    if tool_name == "Bash":
        description = field("description")
        if description:
            return _clip(description[0].lower() + description[1:]
                         if description[:1].isupper() else description)
        command = field("command").strip()
        if command:
            return _clip("running " + os.path.basename(command.split()[0]))
        return "running a command"

    if tool_name in ("Read", "Edit", "Write", "NotebookEdit"):
        name = os.path.basename(field("file_path")) or "a file"
        action = {"Read": "reading", "Edit": "editing",
                  "Write": "writing", "NotebookEdit": "editing"}[tool_name]
        return _clip("%s %s" % (action, name))

    if tool_name in ("Grep", "Glob"):
        pattern = field("pattern")
        return _clip("searching for '%s'" % pattern) if pattern else "searching"

    if tool_name in ("WebFetch", "WebSearch"):
        return "searching the web"

    if tool_name == "Task" or tool_name == "Agent":
        return "running a subagent"

    return _clip(tool_name)
