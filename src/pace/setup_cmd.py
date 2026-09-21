"""`/pace setup` -- the one settings write a plugin cannot perform itself."""
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

from pace import calibrate_cmd, store
from pace.percentiles import MIN_TURNS
from pace.settings import install, uninstall


def _commands(root: Path) -> "tuple[str, str]":
    return ("%s %s" % (sys.executable, root / "bin" / "pace-statusline"),
            "%s %s" % (sys.executable, root / "bin" / "pace-hook"))


def _report_calibration(env: Mapping[str, str], now: float) -> None:
    """Build the first calibration and say what came of it.

    Nothing else invokes the calibrator on a fresh machine, so without this the
    bar would never appear. A calibrator failure is reported but never fails the
    install: the settings write is the part that matters.
    """
    try:
        calibrate_cmd.main([], env, now)
        cal = store.read_calibration(store.state_root(env))
    except Exception as exc:                  # noqa: BLE001 - install must survive
        sys.stderr.write("Calibration could not run (%s); "
                         "the bar will appear after the next refresh.\n" % exc)
        return
    if cal is None:
        print("Not enough history yet (need %d completed turns). The bar will "
              "appear once you have them; elapsed time and current activity "
              "work now." % MIN_TURNS)
    else:
        print("Calibrated from %d past turns." % cal.n)


def main(argv: Sequence[str], env: Mapping[str, str], settings_path: Path,
         now: float) -> int:
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
    _report_calibration(env, now)
    return 0
