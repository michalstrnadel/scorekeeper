#!/usr/bin/env bash
# scorekeeper hook dispatcher — resolves the CLI wherever it lives.
# 1. installed package on PATH; 2. in-repo dev checkout next to this plugin (via uv).
set -euo pipefail

EVENT="${1:?usage: run.sh <hook-event>}"
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v scorekeeper >/dev/null 2>&1; then
  exec scorekeeper hook "$EVENT"
fi

CORE_DIR="$PLUGIN_ROOT/../core"
if [ -f "$CORE_DIR/pyproject.toml" ] && command -v uv >/dev/null 2>&1; then
  exec uv run --project "$CORE_DIR" -q scorekeeper hook "$EVENT"
fi

echo "scorekeeper: CLI not found (install the package or run from the repo with uv)" >&2
exit 0   # never break the agent
