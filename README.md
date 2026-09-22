# pace

A status line for [Claude Code](https://claude.com/claude-code) that answers one question:

> **Is it still working, and how much longer is this likely to take?**

```
▓▓▓▓▓▓▓▓░░  15m · editing statusline_cmd.py · longer than 75% of turns
```

The bar does not track plan steps. It fills by **elapsed time measured against your own
history** — the distribution of how long your turns actually take, mined from your local
Claude Code transcripts. When it is 80% full, you are further into this turn than 80% of the
turns you have ever run.

---

## Why not a step counter, and why no ETA

Two things you might expect are deliberately absent.

**There is no "step 3 of 7" bar.** A step fraction assumes steps are the same size. They are
not — one step reads a config file, the next makes a test suite pass. Worse, a checklist gets
revised mid-turn, so the denominator grows and the bar *runs backwards*. A progress bar that
goes backwards is worse than none, because you learn not to trust it and still have to look.

**There is no "4m remaining".** Across a real sample of 126 turns, the spread from the median
to the 90th percentile was roughly **eightfold**. Any single predicted number would be
decoration with a formula taped to it. So pace shows you where you are in a distribution and
lets you draw your own conclusion.

What is left is small, and every part of it is measured.

## Install

Requires **Python 3.9+** on your PATH. No third-party packages. No network. Nothing leaves
your machine.

```bash
git clone https://github.com/TheDarkNight21/pace
cd pace
python3 bin/pace-setup
```

Or as a Claude Code plugin, from your local clone:

```
/plugin marketplace add /path/to/pace
/plugin install pace
/pace setup
```

Setup does exactly three things:

1. Copies your `~/.claude/settings.json` to `settings.json.pace-backup`.
2. Adds two keys — `statusLine`, and one `PostToolUse` hook entry. Nothing else, and no
   environment variables.
3. Builds your first calibration from `~/.claude/projects/`, and tells you how many turns it
   found.

**If you already have a status line, pace will not touch it.** It prints the command for you
to merge in yourself. Overwriting a config you did not write is worse than not installing.

Restart Claude Code, or open a new session, and the line appears.

### Uninstall

```bash
python3 bin/pace-setup uninstall
```

Removes exactly what it added and leaves everything else untouched.

## What you will see

| Situation | Line |
|---|---|
| Normal turn | `▓▓▓▓▓░░░░░  5m · running pytest · past half your turns` |
| Long turn | `▓▓▓▓▓▓▓▓▓▓  1h23m · waiting on a build · longer than any turn yet` |
| Fewer than 20 recorded turns | `2m · running pytest` — **no bar**, because there is nothing to compare against yet |
| Between turns | *(nothing — the line is empty when Claude is idle)* |

That empty state matters. With too little history pace draws **no bar at all**, rather than an
empty one — an empty bar would claim the turn had just started, which is a different and
false statement.

## How it works

Three pieces, each doing one thing:

| Piece | Runs | Job |
|---|---|---|
| `bin/pace-calibrate` | at install, then weekly in the background | Reads `~/.claude/projects/*.jsonl`, extracts turn durations, writes percentiles to `~/.claude/pace/calibration.json` |
| `bin/pace-hook` | after every tool call | Records what Claude is doing right now (`reading fold.py`, `running pytest`) |
| `bin/pace-statusline` | every 2 seconds | Reads both, renders one line |

The status line tracks turn boundaries itself, by watching Claude Code's `prompt_id` change —
which is why there is no session-lifecycle hook to install. When `prompt_id` is absent, the
session is idle and the line goes blank.

**Only bounded turns are measured.** A turn that ends because you sent the next prompt has a
known end time. The last turn in a transcript does not — it absorbs however long you were at
lunch — so those are excluded rather than blended in.

**The bar cannot run backwards.** Fill is the empirical CDF of elapsed time, which only
increases, and each turn additionally ratchets its own peak so a mid-turn calibration refresh
cannot shrink it. Both properties are enforced by property-based tests, not just intended.

## Customize

Create `~/.claude/pace/config.json`. Every key is optional.

```json
{
  "bar_width": 10,
  "filled": "▓",
  "empty": "░",
  "separator": " · ",
  "show_bar": true,
  "show_threshold": true,
  "min_turns": 20
}
```

| Key | Default | Notes |
|---|---|---|
| `bar_width` | `10` | Characters. 1–40. |
| `filled` / `empty` | `▓` / `░` | Must be **exactly one character** — a wider glyph breaks the width guarantees. Try `=` and `-`, or `█` and `·`. |
| `separator` | `" · "` | Between segments. Up to 8 characters. |
| `show_bar` | `true` | `false` keeps elapsed time and activity, drops the bar. |
| `show_threshold` | `true` | `false` drops the `longer than 75% of turns` clause. |
| `min_turns` | `20` | Turns required before any bar is drawn. Floor of 5 — below that a percentile is noise, and you would be reading a shape rather than a fact. |

```
default    ▓▓▓▓▓▓▓▓░░  15m · running pytest · longer than 75% of turns
bar_width  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░  15m · running pytest · longer than 75% of turns
ascii      ========    15m · running pytest · longer than 75% of turns
minimal    ▓▓▓▓▓▓▓▓░░  15m | running pytest
```

A bad value falls back to its default **on its own**, without costing you the rest of the
file, and a malformed config costs you your customisation rather than your status line.

Refresh rate lives in Claude Code's own settings, not here — change `statusLine.refreshInterval`
in `~/.claude/settings.json`.

## Performance

A render takes about 26 ms on the machine it was developed on (median of 40 warmed
invocations), against a 2-second refresh interval. Over half of that is Python interpreter
startup rather than pace's own work, so expect it to track your `python3 -c pass` time. An
unwarmed first run costs more.

## Files it touches

| Path | What |
|---|---|
| `~/.claude/pace/calibration.json` | Your turn-duration distribution |
| `~/.claude/pace/config.json` | Your settings, if you make one |
| `~/.claude/pace/sessions/` | Per-session state, one small file per kind |
| `~/.claude/settings.json` | Two keys, on install only — backed up first |

`~/.claude/projects/` is only ever **read**.

## Development

```bash
python3 -m pytest        # 130 tests
```

The core is pure — transcript parsing, percentiles, bar geometry, layout and composition have
no clock, no disk and no environment. All I/O lives in `store.py` and the three `bin/` scripts.
That is why the interesting properties can be property-tested directly.

Design notes, including why the first version of this was scrapped, are in
[`docs/superpowers/specs/`](docs/superpowers/specs/). The full build log — every decision
taken during implementation, with its reasoning and what it costs if wrong — is in
[`docs/superpowers/`](docs/superpowers/).

## License

MIT
