"""`/pace setup` -- the one settings write a plugin cannot perform itself."""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Mapping, Optional, Sequence, Tuple

from pace import calibrate_cmd, store
from pace.percentiles import MIN_TURNS
from pace.settings import install, uninstall

BACKUP_SUFFIX = ".pace-backup"


def _backup_path(settings_path: Path) -> Path:
    return settings_path.with_name(settings_path.name + BACKUP_SUFFIX)


def _backup(settings_path: Path) -> "Tuple[Optional[Path], Optional[str]]":
    """Copy the user's settings aside, overwriting any previous backup.

    Returns (backup path, error). Both are None when there was nothing to back
    up, which is the case on a machine with no settings.json yet.
    """
    if not settings_path.exists():
        return None, None
    dest = _backup_path(settings_path)
    try:
        shutil.copyfile(str(settings_path), str(dest))
    except OSError as exc:
        return None, str(exc)
    return dest, None


def _write_atomic(path: Path, text: str) -> Optional[str]:
    """Write `text` through a temp file in the same directory, then rename.

    Returns an error message, or None on success. settings.json is the one
    irreplaceable file pace touches, so it is never truncated in place: a crash
    mid-write would take the user's whole Claude Code configuration with it.
    """
    tmp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        if path.exists():
            os.chmod(tmp, os.stat(str(path)).st_mode & 0o777)
        os.replace(tmp, str(path))
        return None
    except OSError as exc:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return str(exc)


def _write_failed(settings_path: Path, backup: Optional[Path], error: str) -> int:
    where = ("a backup of it is at %s" % backup if backup is not None
             else "it was not created")
    sys.stderr.write("Could not write %s (%s); your settings are unchanged and "
                     "%s.\n" % (settings_path, error, where))
    return 1


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



RUNTIME_DIRNAME = "runtime"


def runtime_root(env: Mapping[str, str]) -> Path:
    """Where the copied runtime lives: inside pace's own state directory."""
    return store.state_root(env) / RUNTIME_DIRNAME


def install_runtime(source_root: Path, target: Path) -> Optional[str]:
    """Copy bin/ and src/ to a location that outlives the plugin directory.

    A plugin is installed into a marketplace cache that is deleted on
    uninstall or rewritten on upgrade. Pointing `statusLine.command` straight
    at it means a removed plugin leaves Claude Code executing a path that no
    longer exists, every two seconds, with no clue why. Copying the runtime
    somewhere pace owns keeps the status line working and makes upgrades an
    explicit, repeatable step rather than an invisible dependency.
    """
    try:
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        for part in ("bin", "src"):
            shutil.copytree(source_root / part, target / part)
        for script in (target / "bin").iterdir():
            script.chmod(0o755)
    except OSError as exc:
        return str(exc)
    return None


def remove_runtime(target: Path) -> None:
    """Best effort: a leftover runtime is clutter, never a failure."""
    try:
        if target.exists():
            shutil.rmtree(target)
    except OSError:
        pass


def main(argv: Sequence[str], env: Mapping[str, str], settings_path: Path,
         now: float) -> int:
    source_root = Path(__file__).resolve().parents[2]
    args = list(argv)
    in_place = "--in-place" in args
    args = [a for a in args if a != "--in-place"]

    root = source_root if in_place else runtime_root(env)
    statusline_cmd, hook_cmd = _commands(root)

    try:
        settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    except (OSError, ValueError):
        sys.stderr.write("Could not read %s; not installing.\n" % settings_path)
        return 1

    backup, backup_error = _backup(settings_path)
    if backup_error is not None:
        sys.stderr.write("Could not back up %s (%s); not writing it.\n"
                         % (settings_path, backup_error))
        return 1

    if args and args[0] == "uninstall":
        error = _write_atomic(settings_path, json.dumps(uninstall(settings), indent=2))
        if error is not None:
            return _write_failed(settings_path, backup, error)
        remove_runtime(runtime_root(env))
        print("pace removed from %s" % settings_path)
        if backup is not None:
            print("  your previous settings were copied to %s" % backup)
        return 0

    if in_place:
        # Settings will point at the source tree, so a runtime copy from a
        # previous default-mode install is now unreferenced. Leaving it would
        # sit there looking authoritative while nothing reads it.
        remove_runtime(runtime_root(env))
    else:
        copy_error = install_runtime(source_root, root)
        if copy_error is not None:
            sys.stderr.write("Could not install the runtime to %s (%s); "
                             "not writing settings.\n" % (root, copy_error))
            return 1

    updated, notes = install(settings, statusline_cmd, hook_cmd)
    error = _write_atomic(settings_path, json.dumps(updated, indent=2))
    if error is not None:
        return _write_failed(settings_path, backup, error)
    print("pace installed in %s" % settings_path)
    if in_place:
        print("  running from the source tree at %s (--in-place)" % source_root)
        print("  edits take effect immediately; moving this directory breaks it")
    else:
        print("  runtime copied to %s" % root)
        print("  re-run setup after upgrading pace to refresh it")
    if backup is not None:
        print("  your previous settings were copied to %s" % backup)
    for note in notes:
        print("  note: %s" % note)
    _report_calibration(env, now)
    return 0
