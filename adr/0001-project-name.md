# ADR-0001: Project name

- **Status:** Proposed (pending Michal's decision)
- **Date:** 2026-07-08

## Context

The specification uses `scorekeeper` as a working name, with alternatives `gogard`, `deontik`, `entitled`. Michal proposed a variant along the lines of *"scorekeeper for agents"*.

The name must satisfy: (a) available as a PyPI package and GitHub repo; (b) evocative of the core idea (deontic scorekeeping of an agent's own commitments); (c) not colliding with a well-known project; (d) short enough for a CLI / import.

## Options

- **`scorekeeper`** — clean, directly names the mechanism (deontic scoreboard). Risk: generic; PyPI name likely taken.
- **`agent-scorekeeper` / `scorekeeper-agent`** — disambiguates the domain (matches Michal's "for agents"). Slightly long; good for the repo, less ideal as an import.
- **`gogard`** — from Brandom's GOGAR. Distinctive, unlikely to collide, but opaque to newcomers.
- **`deontik` / `entitled`** — evoke the normative angle; `entitled` foregrounds the unique entitlement dimension but has negative connotations in English.

## Decision

**Pending.** Leaning: repo/product name `scorekeeper` with the tagline "commitment tracking for LLM agents"; if the PyPI/GitHub name is taken, fall back to `agent-scorekeeper` for distribution while keeping `scorekeeper` as the conceptual name. To be confirmed with Michal before first public release.

## Consequences

Affects PyPI package name, GitHub repo, MCP server id (`scorekeeper-mcp`), and the storage directory (`.scorekeeper/`). Kept flexible until the go decision; this ADR is superseded once the name is locked.
