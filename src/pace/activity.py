"""Turn a tool call into a short human phrase."""
import os
from typing import Mapping

MAX_VERB = 48


def _clip(text: str) -> str:
    text = " ".join(text.split())
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
