---
description: Install or remove pace's status line and hook
---

Run the setup script, which is the one write a plugin cannot perform itself —
Claude Code's `statusLine` lives in `settings.json` and has no plugin component type.

Run: `python3 ${CLAUDE_PLUGIN_ROOT}/bin/pace-setup $ARGUMENTS`

Then report to the user exactly what it printed, including any note about an
existing status line being left untouched. If the user passed `uninstall`,
confirm that `settings.json` was restored.
