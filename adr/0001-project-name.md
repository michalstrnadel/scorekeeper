# ADR-0001: Project name

- **Status:** Accepted
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

Name is **`scorekeeper`**, tagline **"commitment tracking for LLM agents"**.

Availability verified 2026-07-08:
- PyPI `scorekeeper` — free (HTTP 404).
- GitHub repo `michalstrnadel/scorekeeper` — free (HTTP 404).
- GitHub bare handle `github.com/scorekeeper` — taken by a dormant user (1 repo, no name); irrelevant for a repo hosted under Michal's account. No dedicated org under the bare name.

`agent-scorekeeper` is retained only as a distribution fallback if a collision surfaces later.

## Consequences

Locks the PyPI package name (`scorekeeper`), GitHub repo, MCP server id (`scorekeeper-mcp`), and storage directory (`.scorekeeper/`). Tagline used across README and docs.
