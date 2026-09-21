"""`/pace setup` -- the one settings write a plugin cannot perform itself."""
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

from pace.settings import install, uninstall


def _commands(root: Path) -> "tuple[str, str]":
    return ("%s %s" % (sys.executable, root / "bin" / "pace-statusline"),
            "%s %s" % (sys.executable, root / "bin" / "pace-hook"))


def main(argv: Sequence[str], env: Mapping[str, str], settings_path: Path) -> int:
    root = Path(__file__).resolve().parents[2]
    statusline_cmd, hook_cmd = _commands(root)

    try:
        settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    except (OSError, ValueError):
        sys.stderr.write("Could not read %s; not installing.\n" % settings_path)
        return 1

    if argv and argv[0] == "uninstall":
        settings_path.write_text(json.dumps(uninstall(settings), indent=2))
        print("pace removed from %s" % settings_path)
        return 0

    updated, notes = install(settings, statusline_cmd, hook_cmd)
    settings_path.write_text(json.dumps(updated, indent=2))
    print("pace installed in %s" % settings_path)
    for note in notes:
        print("  note: %s" % note)
    return 0
