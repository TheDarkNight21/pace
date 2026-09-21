# pace

A Claude Code status line that answers one question: **is it still working, and
how long is this turn running compared to my own history?**

    ▓▓▓▓▓▓░░░░  5m · running pytest · past half your turns

The bar fills by elapsed time against the empirical distribution of your own past
turns, read from your local transcripts. It is not a plan-step fraction: steps are
not equal-sized, and a checklist revised mid-turn would make such a bar run
backwards. Elapsed time only increases, so this bar cannot — that property is
covered by a property test.

There is no estimate of time remaining. Across a real sample the p50-to-p90 spread
is roughly eightfold, so a point estimate would be decoration, not information.

## Install

pace is not published to a public repository yet, so install it from a local
clone. Point the marketplace at the directory holding
`.claude-plugin/marketplace.json` — that is this repository's root:

    /plugin marketplace add /path/to/pace
    /plugin install pace
    /pace setup

(Once it is published, the first line becomes `/plugin marketplace add
<owner>/pace`. That form does not work today — there is no published repository
behind it.)

`/pace setup` writes two things to `~/.claude/settings.json` and nothing else:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 /path/to/pace/bin/pace-statusline",
    "padding": 0,
    "refreshInterval": 2
  }
}
```

...and a `PostToolUse` hook running `bin/pace-hook`.

If you already have a status line, pace **will not touch it**. It never wraps or
chains an existing status line — setup leaves it completely untouched and prints
the command for you to merge in yourself.

Remove everything with `/pace setup uninstall`. This removes exactly the two
things `install` added and restores `settings.json` to what it was before.

Every write to `settings.json` — install and uninstall alike — first copies it
to `settings.json.pace-backup` and then replaces it atomically, so an interrupted
write cannot leave you with a truncated configuration.

## What it needs

Python 3.9+ on PATH. Nothing else — no third-party packages, no network. All
runtime dependencies are the Python standard library.

## Calibration

`bin/pace-calibrate` reads turn durations from `~/.claude/projects/*/*.jsonl`.
It counts **bounded turns only** — turns followed by another typed prompt, so
their end is known — and ignores the last turn of each transcript, because that
one runs to the transcript's final record and so absorbs however long you were
away afterwards.

Below 20 bounded turns it writes no calibration and **no bar is drawn** — you get
elapsed time and the current activity until the history exists. `/pace setup`
builds the first calibration and tells you which of the two you have. The hook
refreshes calibration in the background when it is more than seven days old, at
most once every 30 minutes.

## What it doesn't do

- It never auto-chains or wraps an existing status line. See Install, above.
- It never enables Claude Code's todo tools and never asks the model to keep a
  checklist. If a checklist happens to exist in the transcript it is shown as
  plain text (e.g. `3/7`), never as bar geometry.
- It never estimates time remaining, for the reason given above.

## Performance

On the machine it was developed on, a render takes about 26 ms (median of 40 warmed
invocations), against Claude Code's 2-second refresh interval. Roughly half of that is
Python interpreter startup rather than pace's own work, so expect it to track your
machine's `python3 -c pass` time. An unwarmed first run costs noticeably more.
