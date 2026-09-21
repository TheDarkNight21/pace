# pace — a live, honest progress indicator for Claude Code

**Status:** design approved in direction, spec under review
**Date:** 2026-09-21
**Name:** `pace` is a working title; renaming touches the repo name, plugin id and command name only.

## The one thing

**Tell me where this turn stands against my own history, and what it's doing right now.**

Everything below serves that sentence. Anything that does not serve it is out.

## Why this shape

The user asked for a progress bar over plan steps. That bar cannot be built honestly:

- The checklist tool (`TodoWrite`) has been called **zero times in 183 local transcripts**. On
  Opus 5 it is not offered unless `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` is set. Building on it means
  changing how the work is done so the gauge has something to read — the instrument eats what it
  measures.
- A step fraction assumes steps are equal-sized. They are not. Checklists are also revised
  mid-turn, so the denominator grows and **the bar runs backwards**.

Measured turn durations, from 126 bounded mid-session turns in the user's own transcripts:

| p25 | p50 | p75 | p90 |
|-----|-----|-----|-----|
| 1.5m | 5.4m | 11.6m | 41.1m |

73% of turns run two minutes or longer. The waiting is real, so the product is real. But the
p50→p90 spread is 8×, so any *point* estimate of remaining time is fiction.

**Resolution:** the bar fills by elapsed time against the empirical CDF of the user's own past
turns. Fill = fraction of historical turns shorter than the current elapsed time. This is
measured, monotonic (so it can never run backwards), needs no checklist, and needs no env var.

## Verified platform facts

All confirmed empirically against Claude Code 2.1.278 on 2026-09-21, not assumed.

| Fact | Evidence |
|---|---|
| statusLine re-renders mid-turn | probe logged ticks every 2s via `refreshInterval`, plus event-driven renders |
| `COLUMNS` / `LINES` exported | observed `254`/`71`; falls back when no tty |
| ANSI allowed in statusLine | `NO_COLOR` unset there (it *is* set for spawned Bash) |
| `prompt_id` is `null` when idle | observed on an idle concurrent session |
| Sessions run concurrently | 4 live sessions observed, differing widths |
| Render cost | 17ms per invocation (python3) |
| `PostToolUse` fires reliably | every Bash call, hook self-time 0.03ms |
| Plugins cannot install a statusLine | plugin component dirs are commands/skills/agents/hooks/themes/output-styles/monitors/workflows |

## Architecture

Pure core, effects only at the edges. The core is testable with no Claude Code, no clock, no disk.

```
pace/
  bin/
    pace-statusline          EDGE  stdin JSON -> one line on stdout
    pace-hook                EDGE  PostToolUse JSON -> activity file
    pace-calibrate           EDGE  transcripts -> calibration.json
  src/pace/
    model.py           PURE  frozen dataclasses: Turn, Activity, Calibration, Segment
    percentiles.py     PURE  durations -> Calibration;  (Calibration, elapsed) -> Position
    activity.py        PURE  (tool_name, tool_input) -> human verb
    bar.py             PURE  Position -> glyphs
    layout.py          PURE  (segments, width) -> right-aligned line
    transcripts.py     PURE  file contents -> durations
  tests/
```

### Components

**`pace-calibrate`** — scans `~/.claude/projects/*/*.jsonl`, extracts turn durations (a turn runs
from a record with `promptSource == "typed"` to the last record before the next one), and writes
percentiles to `~/.claude/pace/calibration.json`. Below 20 recorded turns it writes no
calibration at all: percentiles over a handful of samples are not knowledge, and the line
degrades to elapsed-plus-activity until the data exists. Runs at install. Refresh is triggered by `pace-hook`, which checks the file's age and spawns a
detached refresh when it exceeds 7 days — the statusline never blocks on it. Final turns of a session are recorded separately from bounded ones, since they
can absorb idle time.

**`pace-hook`** — `PostToolUse`, matcher `*`. Writes `{tool, ts}` to
`~/.claude/pace/sessions/<session_id>.json`. Single file, **overwritten**, never appended.

**`pace-statusline`** — reads stdin, and tracks turn start itself: it records the first time it
sees a given `prompt_id`, and resets when `prompt_id` changes. `prompt_id == null` means idle.
This is why no `UserPromptSubmit` or `Stop` hook is needed.

### Data flow

```
PostToolUse ──> sessions/<id>.json ──┐
                                     ├──> pace-statusline ──> "▓▓▓▓▓▓░░░░  5m · running pytest · past half your turns"
stdin (prompt_id, session_id) ───────┤
calibration.json ────────────────────┘
```

## The line

```
▓▓▓▓▓▓░░░░  5m · running pytest · past half your turns
└─ CDF ──┘  └┬┘  └─── from ────┘  └──── threshold ────┘
             │     PostToolUse
        elapsed, from prompt_id first-seen
```

Right-aligned within `COLUMNS`, `padding: 0`. Threshold text appears only at p50/p75/p90
crossings. Beyond the longest recorded turn: "longer than any turn yet".

## Degradation

Every failure states the truth. Nothing is invented.

| Situation | Renders |
|---|---|
| No calibration yet (fewer than 20 recorded turns) | `5m · running pytest` — elapsed and activity, **no bar** |
| `prompt_id == null` | idle: nothing, or a dim `idle` |
| No tool call yet this turn | `12s · thinking` |
| `COLUMNS` unset (headless) | left-aligned, fixed 80 |
| `python3` missing | installer refuses and says why |
| Checklist genuinely present | append ` · 3/7` as **text**, never as bar geometry. Opportunistic only — pace never sets `CLAUDE_CODE_ENABLE_TODO_TOOLS` and never asks the model to keep a checklist |

## Testing

Pure core under property tests (`hypothesis`). Laws:

- **Monotonic:** `elapsed1 <= elapsed2  =>  fill(elapsed1) <= fill(elapsed2)`. The bar can never
  run backwards. This is the law the rejected design could not satisfy.
- **Bounded:** `0 <= fill <= 1`; rendered bar width always equals requested width.
- **Width:** ANSI-stripped length of the rendered line never exceeds `COLUMNS`.
- **Calibration:** percentiles are non-decreasing; empty input yields no calibration, not zeros.
- **Install idempotence:** `apply(apply(s)) == apply(s)` and `uninstall(install(s)) == s`.

Edges tested against recorded stdin fixtures captured from the real probe.

## Distribution

Plugin on a GitHub marketplace, carrying the hook. Because plugins cannot install a statusLine, a
`/pace setup` command performs that one settings write, idempotently.

**Open question for review:** automatic chaining of an existing statusLine is fragile (quoting,
exit codes, stderr, ANSI without trailing newline) and breaks the bottom of the user's terminal
when it goes wrong. Proposed instead: detect an existing statusLine, **print the line to merge**
and let the user paste it. Never rewrite a config we do not own.

## Cut from v1

- Step-fraction bar and measured ETA — cannot be made honest (see Why this shape).
- `subagentStatusLine` per-subagent bars.
- Cross-session ETA learning.
- Sound on turn end — real and cheap, but it is a second product; revisit once the line is proven.
