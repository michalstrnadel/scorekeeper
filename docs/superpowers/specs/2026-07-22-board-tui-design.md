# `scorekeeper board` — terminal dashboard + README GIF (design)

Date: 2026-07-22 · Status: approved by Michal (layout A of three mocked
options; static print v1, `--watch` deferred) · Origin: the README's "What
the board looks like" section shows raw YAML + one log line — visually the
weakest spot of the repo's strongest concept.

## Goal

One command that renders the live scoreboard as a readable, colored
terminal dashboard — and, from it, a VHS-rendered GIF that carries the
README section. The board answers the product's own question at a glance:
*what is this agent entitled to claim and to do, right now?*

## Non-goals (v1)

- No `--watch`/live mode (cheap later extension; static print first).
- No new dependencies — ANSI escapes via a stdlib helper, honoring
  `--no-color`, `NO_COLOR`, and non-tty stdout. Keeps core's stdlib-only
  stance (ADR-0003 spirit).
- No ledger/timeline view (mock B) and no separate `status` command
  (mock C) — the dashboard header already carries C's content; B may become
  `board --log` someday.
- `report` (markdown dump) stays unchanged.

## Components

### 1. Renderer — `core/src/scorekeeper/board.py` (new)

Pure function, no tty inspection inside:

```python
def render_board(store: Store, *, color: bool = True, width: int = 80,
                 events: int = 8) -> str
```

Three sections, per the approved mock:

- **Header:** project dir name; counts — `N active` and `N conflicted` from
  commitment statuses; `N challenged` = ACTIVE commitments that have at
  least one `CHALLENGE` log entry against their id (challenge is an event,
  not a status); `N denies` = count of `*-DENY` log entries whose timestamp
  falls on the current local date (red when > 0, omitted when 0).
- **Active commitments:** short id (`c-0004` from `c-2026-07-21-0004` —
  display-only truncation, full id remains the identity everywhere else),
  kind, claim (wrapped to width); a `scope` line when `path:`/`topic:` pins
  exist; a `from` line with a provenance glyph — `★` for external sources
  (user_utterance / tool_output / document), `⚠` for `none`, plus
  `CHALLENGED` marker when the commitment has an open challenge. Entitlement
  note quoted dim when present.
- **Recent events:** last `events` entries of `store.log_entries()` —
  time (HH:MM), op colored by class (ASSERT/SUPERSEDE green, CHALLENGE
  yellow, `*-DENY` red bold, everything else dim), commitment id, detail
  truncated to width.

Color palette: plain ANSI 16-color codes (green/yellow/red/blue/magenta/
cyan/dim) — no 24-bit codes, so it degrades gracefully in any terminal.
A tiny module-level helper (`_c(code, text, on)`) guards every escape
behind the `color` flag.

### 2. CLI — `board` subcommand in `core/src/scorekeeper/cli.py`

Registered alongside `init/digest/report` (same `--root` pattern), plus
`--events N` (default 8) and `--no-color`. Color auto-detection lives HERE
(not in the renderer): `sys.stdout.isatty()` and `NO_COLOR` env. Missing
`.scorekeeper/` prints "no scoreboard here — run `scorekeeper init`" to
stderr and exits 1.

### 3. GIF — `demo/board_demo.py` + `demo/board.tape` → `docs/assets/board.gif`

`board_demo.py` builds a temp workdir replaying the real 2026-07-21
benchmark story with the same Store APIs the product uses: the scope-grant
commitment (★ user_utterance, `path:app/** tests/** README.md` pins), two
tech decisions, one unentitled assertion carrying a CHALLENGE — prints the
board; then logs the real `TIER0-SCOPE-DENY 'legacy/util.py' outside pinned
write scope` event and prints the board again (the red line landing is the
GIF's payoff). The tape follows `demo/demo.tape` conventions (Catppuccin
Mocha, 1120px, `vhs demo/board.tape` from repo root).

### 4. Docs

README "What the board looks like": GIF leads, the verbatim YAML record and
the deny line stay below it (transparent storage is the feature). One-line
additions to `core/README.md` and `docs/api.md` (CLI table), CHANGELOG
entry under Unreleased.

### 5. Tests — `core/tests/test_board.py`

Render against a Store fixture: header counts; challenged glyph present;
deny appears red in events (and only when color=True); `color=False` output
contains no `\x1b` escapes; empty board renders a friendly line; CLI exits
1 without a store. Follows existing core test style; no snapshot files —
assert on substrings.

## Error handling

The renderer never raises on malformed log entries (skips them, mirrors the
store's tolerance); the CLI never traceback-crashes on a valid store. Wide
unicode in claims is not specially handled in v1 (wrap is char-based).

## Testing / verification

`uv run pytest` in core (new tests green, coverage gate ≥85% holds),
`ruff`, `scripts/e2e.sh core docs`, then `vhs demo/board.tape` and a visual
check of the GIF; README link-check via e2e docs stage.
