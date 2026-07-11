<!-- Thanks for contributing! Keep PRs small and reviewable. -->

## What & why

<!-- What does this change, and what problem does it solve? Link any issue. -->

## Checklist

- [ ] `cd core && uv run ruff check src tests` passes
- [ ] `cd core && uv run pytest -q` passes (added a regression test if this fixes a bug)
- [ ] `CHANGELOG.md` updated for user-visible changes
- [ ] Keeps the **scaffolded-not-extended** stance (the agent does not edit its own scoreboard at runtime — see `docs/theory.md` §5). If this is a design decision, I added an ADR in `adr/`.
- [ ] No secrets in code, logs, or fixtures
