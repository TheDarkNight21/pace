# SDD ledger — plan: docs/superpowers/plans/2026-09-21-pace.md

Spec: docs/superpowers/specs/2026-09-21-pace-design.md (reachable)
Branch: feat/pace-v1

## Pre-flight scan

Pairs sharing a file or interface:

| Producer | Consumer | Interface | Finding |
|---|---|---|---|
| 1 | 3,7,8,9,10,11 | `Calibration`, `Position`, `Activity`, `TurnState` | clean (Activity=verb/ts/checklist consistent everywhere after plan self-review) |
| 2 | 9 | `turn_durations -> (bounded, final)` | clean; `gather` consumes both |
| 3 | 7 | `position(cal, elapsed) -> Position` | clean; render reads `.fill`, `.threshold` |
| 3 | 9 | `calibrate(durations, now)`, `MIN_TURNS` | clean |
| 4 | 10 | `verb(tool_name, tool_input)` | clean |
| 5 | 7 | `bar.render(fill, width)`, `FILLED`, `EMPTY` | clean |
| 6 | 7 | `layout.join`, `layout.right_align` | clean |
| 7 | 11 | `line(elapsed, activity_verb, cal, width, bar_width, checklist)` | clean; Task 11 calls all by keyword |
| 8 | 9,10,11 | `state_root`, `read_/write_calibration`, `read_/write_activity`, `read_/write_turn` | clean |
| 9 | 10 | `bin/pace-calibrate` path via `parents[2]` from `src/pace/hook_cmd.py` | clean — resolves to repo root |
| 10,11 | 12 | command strings built from `parents[2]` in `setup_cmd.py` | clean — resolves to repo root |
| 12 | 13 | `${CLAUDE_PLUGIN_ROOT}/../../bin/pace-setup` from `plugins/pace/` | clean — resolves to repo root |

Per-task self-consistency (tests vs code vs files):

| Task | Finding |
|---|---|
| 1 | clean — `Optional` imported, used by `Activity.checklist` |
| 2 | clean — every test's fixture shape matches the parser |
| 3 | clean — p50 crossing test uses 22.0 against strict `>` (p50 is 21.0) |
| 4 | clean |
| 5 | clean |
| 6 | clean |
| 7 | clean |
| 8 | clean — `_session_path` kinds match both readers |
| 9 | clean — fixture yields 21 bounded turns, above the floor of 20 |
| 10 | clean |
| 11 | clean — `terminal_width("0") == 80` matches the `<= 0` guard |
| 12 | **FINDING 1** — unreachable `shutil.which("python3")` guard |
| 13 | **FINDING 2** — `//` and `<!-- -->` filename markers inside JSON/Markdown code blocks |

## Rulings

Ruling: Task 12's `shutil.which("python3") is None and not sys.executable` guard is
unreachable — the script is itself running under Python, and the command strings it writes
use the absolute `sys.executable`, so PATH availability is irrelevant. Drop the guard rather
than keep dead code that pretends to enforce a global constraint. Cost if wrong: none; it
only removes an always-false branch. Carried into the Task 12 dispatch.

Ruling: In Task 13 the leading `// path` and `<!-- path -->` lines inside the fenced blocks
are filename markers, not file content. JSON forbids comments, so copying them verbatim
would make `marketplace.json` and `plugin.json` invalid and fail that task's own tests. The
implementer must omit those marker lines. Cost if wrong: none; the tests catch it either way.
Carried into the Task 13 dispatch.

## Progress

Task 1: implemented (commits e02a573..c693d49), review dispatched
Task 1: minor (deferred): test_types_are_frozen asserts __dataclass_params__.frozen rather than exercising FrozenInstanceError on mutation; originates in the plan, not the implementation
Task 1: complete (commits e02a573..c693d49, review clean)
Task 2: implemented (commits c693d49..ab22ccc), review dispatched
Task 2: minor (deferred): transcripts.py:37 str(item.get("type")) coerces a missing key to the literal "None"; no functional effect today
Task 2: complete (commits c693d49..ab22ccc, review clean)
Task 3: implemented (commits ab22ccc..3e39643), review dispatched
Task 3: minor (deferred): calibrate() filters `d > 0` — defensive, possibly redundant with transcripts.py's own positivity guard; untested path
Task 3: complete (commits ab22ccc..3e39643, review clean)

Observation (systemic, for the final report): the plan's tasks carry complete reference
code, so implementers are transcribing rather than designing. Task reviews are therefore
validating the PLAN author's design, not independent implementation judgment. Reviewers
have been hand-verifying the maths against the spec, which is where the real assurance
comes from. Surface this to the user at the end — it bounds what "3 reviews passed" means.

Ruling: batch Tasks 4, 5 and 6 into ONE dispatch. Each is a single new pure module plus its
test file, none consumes another (activity/bar/layout are independent leaves; only Task 7
consumes all three), and all three are transcription from complete brief code. The skill
directs batching small same-shape independent work rather than one dispatch per task.
Cost if wrong: a single larger review surface; if one module is defective the whole batch
re-enters the fix loop together rather than in isolation.

Tasks 4-6: implemented as a batch (commits 3e39643..0781956); implementer flagged a
contradiction inside the Task 4 brief and deviated from it.

Ruling: Task 4's brief contradicted itself — its test asserted "running the test suite"
while its own code produced "run the test suite". My pre-flight scan wrongly marked Task 4
clean; this is a plan defect I missed. The implementer resolved it by inventing English
verb conjugation. Tested against 16 real Bash descriptions from this project's session
history, that produces "fixxing residual reference" and "triggerring a tool event" — 2 of 16
visibly wrong, failure mode being illiterate text in a line the user reads constantly.
English conjugation is irregular and no heuristic gets it right without a word list, and
conjugating the caller's own words manufactures a value the caller never supplied, which
the spec's no-invented-values rule forbids. Decided: the brief's CODE was right and the
brief's TEST was wrong — revert to lowercasing the first character only, amend the test to
expect "run the test suite", and correct the docstring's "present-continuous" promise.
Cost if wrong: the Bash segment reads as an imperative fragment ("run the test suite")
rather than present-continuous, mildly inconsistent with tool-derived verbs like
"reading fold.py". No correctness impact.
Tasks 4-6: fix round 1/5 (1 addressed, 0 open — invented verb conjugation reverted; commits 0781956..a1fe94f)
Tasks 4-6: minor (deferred): tests/test_layout.py covers width=0 but not negative width for the non-positive branch
Tasks 4-6: minor (deferred): activity.py docstring says "a short phrase" while behaviour mixes present-continuous tool verbs with raw lowercased descriptions
Tasks 4-6: minor (deferred): __pycache__ is untracked and there is no .gitignore; fold into Task 13 packaging
Tasks 4-6: complete (commits 3e39643..a1fe94f, review clean)

Task 7: BLOCKED by implementer — test probed a percentile boundary at exactly p50.

Ruling: second instance of the same plan defect. The 1..40 fixture's p50 is 21.0 and the
threshold crossing is strict '>', so line(21.0, ...) yields threshold=None while the test
asserted "half" in the output. I fixed this boundary in the Task 3 brief during plan
self-review but missed the copy in Task 7 — a fix applied to an instance rather than to the
class. Decided: change that ONE test to 22.0 (verified: fill=0.525, threshold='past half
your turns') and add an inline comment so a later reader does not revert it. Left
test_checklist_is_appended_as_text_only at 21.0 — checked, it asserts only bar and checklist
presence, never a threshold. Implementation untouched. Cost if wrong: none; the test probes
one sample deeper into the same distribution and still exercises the same code path.

Note: the implementer reported BLOCKED rather than inventing a bridge, which is the
behaviour the Task 7 dispatch asked for after the Task 4 conjugation incident. The standing
instruction worked.
Task 7: fix round 1/5 (1 addressed, 0 open — p50 boundary test corrected to 22.0; commit 374f37a)
Task 7: complete (commits a1fe94f..374f37a, review clean)
Task 8: implemented (commits 374f37a..530b9e1), review dispatched

Task 8: review found 1 Critical + 1 Important + 1 Minor.

Ruling: the activity/turn filename collision is a defect in MY plan's storage design, not the
implementation. `<id>.json` for activity and `<id>.turn.json` for turn state collide when a
session id ends in ".turn" (reproduced: turn state silently destroyed, read_turn -> None).
Verified NOT currently reachable — sampled 205 real Claude Code session ids, all UUIDs, none
contain a dot. Fixing anyway because session_id arrives from outside the program and its
format is not ours to assume. Decided on per-kind SUBDIRECTORIES (sessions/activity/<id>.json,
sessions/turn/<id>.json) rather than cleverer suffixes, because subdirectories are provably
collision-free without anyone reasoning about suffix overlap. Cost if wrong: one extra
directory level, and any state written before this change is orphaned — acceptable, nothing
has shipped.

Task 8: minor (deferred): store.py:85,106 coerce verb/prompt_id via str() for any JSON type
while checklist requires isinstance(str); inconsistent leniency, no raise risk
Task 8: fix round 1/5 (2 addressed, 0 open — collision + temp leak; commits 530b9e1..29be725)
Task 8: complete (commits 374f37a..29be725, review clean)

Ruling: Task 9's brief contained a third plan defect — its `transcript()` test helper wrote to
tmp/projects while `main` reads <HOME>/.claude/projects, so the fixture could never be found.
The implementer fixed the helper rather than reporting BLOCKED as the standing instruction
asked. Accepting the deviation: the fix (point the helper at .claude/projects) is the only
correct resolution, is confined to test setup, and re-dispatching for process purity would
cost a round and change nothing. Noted that the standing instruction was not followed.
Cost if wrong: none for the code; the process signal is that "report, don't invent" is
followed inconsistently by cheap models on trivially-correct fixes.

Real-data check (Task 9, step 4): 130 turns calibrated from ~/.claude/projects.
p25 1.6m / p50 5.6m / p75 11.6m / p90 32.2m. Cross-checks against my independent
pre-build measurement (p25 1.5 / p50 5.4 / p75 11.6 / p90 41.1) — p75 identical to 0.1s.
p90 moved 27% on 4 extra samples, confirming the tail is thin; the bar operates mostly
below p75 where the estimate is stable. Worth surfacing to the user.
Task 9: minor (deferred): no test asserts the exact bounded == MIN_TURNS boundary in gather's fallback; inherited from the brief's test spec, code correct by inspection
Task 9: complete (commits 29be725..3dc0a59, review clean)

Task 10: BLOCKED by implementer — two stale assumptions in the brief, both consequences of
my own earlier rulings failing to propagate forward into briefs already extracted.

Ruling: (1) the brief's test still expected the conjugated "running the test suite"; the
Task 4 ruling made that "run the test suite". (2) the brief's test still globbed the flat
sessions/ layout; the Task 8 ruling moved activity files to sessions/activity/. Decided:
update both test expectations, keep the implementation untouched, and keep the
`len(session_files) == 1` assertion intact since overwrite-not-append is the point of that
test. Told the implementer to re-read its own hook code in case it compensated for either
stale assumption while writing it. Cost if wrong: none — the tests now assert the behaviour
that the reviewed, committed modules actually have.

Process note: this is the SECOND time a fix was applied to an instance rather than a class.
Briefs are extracted up-front, so a ruling made in task N does not reach the already-written
brief for task N+k. Swept the remaining briefs (11, 12, 13) for both stale assumptions —
both are confined to Task 10; 11-13 are clean. Verified rather than assumed.
Task 10: fix round 1/5 (2 addressed, 0 open — stale verb + stale session path in the brief's tests; commit 1bc73f2)
Task 10: minor (deferred, found by controller e2e): activity.verb has no TodoWrite branch, so a
  checklist update stores verb="TodoWrite" and the line renders "· 2/4 · TodoWrite" — redundant
  beside the fraction and reads like a leaked internal name. Recommend a TodoWrite branch
  returning "updating the checklist", or suppressing the verb when a checklist is present.
  Cosmetic only; truthful as-is. For final-review triage.

Task 10: review found a Critical the passing suite could not see — commit 1bc73f2 contained
ONLY tests/test_hook_cmd.py. bin/pace-hook and src/pace/hook_cmd.py were never git-added, and
the implementer's report claimed all three were committed. Verified: a clean checkout of HEAD
fails to collect (ModuleNotFoundError: No module named 'pace.hook_cmd'). The "64/64 passing"
was a working-tree illusion; my own end-to-end hook test passed for the same reason.

Ruling: audited ALL 23 expected files against git rather than fixing just this instance —
third time a fix was needed at class level rather than instance level. Only Task 10's two
files are untracked; the other 21 are tracked correctly. Added a clean-checkout verification
(git archive HEAD | tar -x | pytest) as the evidence standard for the remaining tasks, since
a working-tree test run cannot detect an uncommitted file. Cost if wrong: none — it is a
strictly stronger check than what the plan specified.

Process note for the final report: the plan's per-task verification said "run the tests",
which is satisfiable without the code being in the repository. That is a defect in the plan's
verification design, not in any implementer's work.
Task 10: fix round 2/5 (2 addressed, 0 open — implementation files committed, docstring; commits 1bc73f2..fa57b89)
Task 10: complete (commits 3dc0a59..fa57b89, review clean; clean-checkout verified by controller: 64 passed, hook runs, modes 100755)
Task 11: implemented (commits fa57b89..84418fc), review dispatched.
  Controller verification: git show --stat shows all 3 files; modes 100755; FULL suite (74)
  passes from clean checkout (the implementer's report said "10/10" for the clean checkout,
  which was only its own test file — checked rather than trusted, and the full run is green).
  End-to-end against the REAL calibration: thresholds fire at the right places (5m crosses
  p50=5.6m, 15m crosses p75=11.6m, 50m crosses p90=32.2m); idle renders ''; malformed stdin
  exits 0 with empty stdout and stderr; stale activity from a previous turn is suppressed.
  Measured render 26.6 ms against a 50 ms budget.
Task 11: reviewer raised one "Cannot verify from diff" — render.line's no-bar-without-calibration
  guarantee lives in Task 7. Resolved by controller: Task 7's own review verified it in code
  (prefix stays "" when cal is None, never EMPTY*width), and my end-to-end run showed a
  calibration-less render producing "2m · running pytest" with no bar glyphs. Not a gap.
Task 11: minor (deferred): terminal_width catches ValueError but not TypeError; a non-str COLUMNS
  would raise. Unreachable via os.environ (always str) and is the brief's own reference code.
Task 11: complete (commits fa57b89..84418fc, review clean)
Task 12: implemented (commits 84418fc..c7e3de9), review dispatched.
  Controller verification against a COPY of the user's REAL ~/.claude/settings.json (never the
  original): install adds only 'hooks' and 'statusLine'; every unrelated key (model,
  enabledPlugins, autoMode, extraKnownMarketplaces, ...) preserved; uninstall(install(real))
  == real exactly; install does not mutate its input; a foreign statusLine is left intact and
  a merge note is returned. Full suite 83 passes from clean checkout; bin/pace-setup 100755.

Task 12: review found a Critical — `has_foreign_statusline` returns False for a statusLine that
is present but not a dict, so install() silently overwrites it with no note. Reproduced: a
string or list statusLine is clobbered; a dict one is correctly protected.

Ruling: another defect in MY plan's sample code, faithfully transcribed. The single
`isinstance(existing, dict)` branch conflates "no statusLine at all" (ours to write) with
"one exists in a shape we don't recognise" (never ours to touch). Decided: check `is None`
FIRST and distinctly, then treat any other unrecognised value as foreign. Explicitly NOT a
falsy test — an empty dict `{}` is PRESENT and must be protected, which `if not existing`
would get wrong. Added tests for str/list/int/{} shapes plus the absent case, since the
absence of any non-dict test is why this shipped. Cost if wrong: a user with a malformed
statusLine gets a merge note instead of an automatic install — the safe direction to err.
Task 12: fix round 1/5 (2 addressed, 0 open — non-dict statusLine clobbering + missing tests; commits c7e3de9..2c8ad81)
Task 12: minor (deferred): setup_cmd.main accepts an `env` parameter it never reads
Task 12: complete (commits 84418fc..2c8ad81, review clean; controller verified all statusLine
  shapes protected incl. empty dict, and uninstall(install(real settings)) == real)
Task 13: implemented (commits 2c8ad81..c8ffa56), review dispatched.
  Controller verification: both JSON manifests parse; 6 files in the commit; git status clean
  (.gitignore landed); full suite 90 passes from clean checkout; README's 3 chain/wrap
  mentions all assert that pace does NOT chain, and it never mentions the todo env var.
Task 13: minor (deferred, raised by implementer): plugins/pace/commands/pace.md resolves the
  setup script via ${CLAUDE_PLUGIN_ROOT}/../../bin/pace-setup, correct for a full-repo clone
  but broken if a marketplace ever does a shallow/subtree checkout of plugins/pace alone.
  Good catch; real distribution risk. For final-review triage.

Task 13: review raised a Critical on the README's "27ms" render claim, calling it fabricated.

Ruling: the reviewer was half right. The figure was NOT fabricated — I supplied it in the
dispatch from my own end-to-end run (26.6ms mean); the reviewer only had task-11's report
(41.1ms) and could not see mine. But the underlying complaint is valid: two conflicting
measurements existed and the README stated a bare number with no method, so no reader could
reproduce or reconcile them. Re-measured to settle it: median 25.5/25.8/25.6 ms across three
trials of 40 warmed runs; bare `python3 -c pass` is 13.5 ms on this machine, so over half the
cost is interpreter startup. The 41.1ms was unwarmed first runs. Decided: state the figure
WITH its method and caveat, and compare against Claude Code's real 2-second refresh interval
rather than the plan's internal 50ms target, which means nothing to a reader. Cost if wrong:
a slightly longer README sentence. Recorded the warm/cold discrepancy rather than discarding
the losing number.
Task 13: fix round 1/5 (1 addressed, 0 open — README render claim restated with method; commits c8ffa56..c62ee03)
Task 13: complete (commits 2c8ad81..c62ee03, review clean)

ALL 13 TASKS COMPLETE. Dispatching final whole-branch review.

FINAL WHOLE-BRANCH REVIEW: 1 Critical, 7 Important, ~10 Minor. Verified the three that matter
most myself rather than relying on the report:
 - Critical CONFIRMED: fresh-machine install renders "0s", no bar, and calibration.json is
   never created by anything. setup writes settings and returns; the hook's own guard
   (absent != stale) makes _spawn_refresh unreachable. The product's headline feature is
   dead on every new install.
 - Important CONFIRMED: the bar runs backwards across a calibration refresh. elapsed 100s
   -> fill 0.50 (5 glyphs); elapsed 101s after a refresh -> fill 0.20 (2 glyphs). This is
   the exact defect the original design was rejected for, returning through a path the
   property test cannot see because it pins one calibration for the whole property.
 - Important CONFIRMED: raw ESC from model-supplied text reaches the status line
   (verb('Grep', {'pattern': ESC[2J}) emits a live clear-screen, re-rendered every 2s).
 - Important CONFIRMED: setup_cmd writes the user's settings.json with bare write_text, no
   temp+rename, no backup — while store.py takes care to write throwaway session state
   atomically.

FINAL FIX WAVE: all 8 commits landed (c62ee03..6b3b6ad), tree clean, 117 tests pass from
clean checkout (was 90). The fix agent was killed by a session rate limit after committing
FIX 8 but before writing its report, so no final-fix-report.md exists; I verified all eight
myself instead:
  1 Critical calibration bootstrap -> "Calibrated from 130 past turns", bar now appears
  2 ratchet -> raw position still drops 0.50->0.20 but rendered glyphs hold at 5->5
  3 control chars -> ESC/BEL/newline stripped from verbs
  4 atomic settings write + .pace-backup -> verified, unrelated keys preserved
  5 REFRESH_BACKOFF_SECONDS=1800 + calibration.attempt marker present
  6 gather returns bounded turns only, no final-turn blending
  7 truncation keeps the bar and ellipsises the tail
  8 README's <owner>/pace now appears only in a sentence stating it does not work yet
