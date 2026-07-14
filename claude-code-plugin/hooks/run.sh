#!/usr/bin/env bash
# scorekeeper hook dispatcher — resolves the CLI wherever it lives:
# 1. installed package on PATH; 2. in-repo dev checkout (via uv);
# 3. zero-setup fetch from PyPI (uvx/pipx). Never breaks the agent (exit 0).
set -euo pipefail

EVENT="${1:?usage: run.sh <hook-event>}"
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The scorer the uvx/pipx paths fetch must at least know this plugin's hook
# events — an older PyPI release rejecting an event blocked every Edit/Write
# (issue #6). Bump in lockstep with the plugin version.
MIN_SCORER="scorekeeper>=0.2.0"

# Hooks run in a non-interactive shell that may not source the user's profile,
# so tools installed by pip --user / uv / homebrew / cargo can be off PATH.
# APPEND the common locations (never prepend: run.sh must not shadow the
# user's own PATH preference with a stale pip --user install).
for d in "$HOME/.local/bin" "$HOME/.cargo/bin" /opt/homebrew/bin /usr/local/bin \
         "$HOME/Library/Python/"*/bin; do
  [ -d "$d" ] && case ":$PATH:" in *":$d:"*) ;; *) PATH="$PATH:$d" ;; esac
done
export PATH

# The hook payload arrives on stdin; buffer it once so every resolver attempt
# gets the full payload (a failed first attempt must not eat it).
PAYLOAD="$(cat 2>/dev/null || true)"

# A legitimate decision (e.g. a Tier-0 gate deny) is JSON on stdout with exit 0
# — the CLI never exits non-zero on purpose (hook errors are caught inside).
# Any non-zero exit is therefore infrastructure: a version-skewed scorer that
# doesn't know this event (issue #6), a network failure, a broken install.
# On failure fall THROUGH to the next resolver (a stale `pip install` must not
# mask a working uvx one line below); only forward stdout on success so a
# partial output can never leak into the hook decision.
try_scorer() {
  local out rc=0
  out="$(printf '%s' "$PAYLOAD" | "$@")" || rc=$?
  if [ "$rc" -eq 0 ]; then
    [ -n "$out" ] && printf '%s\n' "$out"
    exit 0
  fi
  echo "scorekeeper: '$1' failed for event '$EVENT' (exit $rc) — trying next resolver" >&2
  return 1
}

# 1. installed package on PATH (pip install scorekeeper)
if command -v scorekeeper >/dev/null 2>&1; then
  try_scorer scorekeeper hook "$EVENT" || true
fi

# 2. in-repo dev checkout next to this plugin (contributors: --plugin-dir)
CORE_DIR="$PLUGIN_ROOT/../core"
if [ -f "$CORE_DIR/pyproject.toml" ] && command -v uv >/dev/null 2>&1; then
  try_scorer uv run --project "$CORE_DIR" -q scorekeeper hook "$EVENT" || true
fi

# 3. zero-setup fallback: fetch + run from PyPI on demand (marketplace installs,
#    where neither the package nor the repo is present). uvx caches after first run.
if command -v uvx >/dev/null 2>&1; then
  try_scorer uvx --quiet --from "$MIN_SCORER" scorekeeper hook "$EVENT" || true
fi
if command -v pipx >/dev/null 2>&1; then
  try_scorer pipx run --spec "$MIN_SCORER" scorekeeper hook "$EVENT" || true
fi

# Every resolver failed (or none exists). Exit 0 — a dead scorer must never
# deny tool calls — but say so once per session where the user can see it:
# SessionStart stdout is injected into context.
if [ "$EVENT" = "session-start" ]; then
  echo "scorekeeper: no working scorer found — hooks are INACTIVE this session ('pip install scorekeeper' or install uv; see https://github.com/michalstrnadel/scorekeeper)"
fi
echo "scorekeeper: no working scorer for event '$EVENT' — no-op" >&2
exit 0   # never break the agent
