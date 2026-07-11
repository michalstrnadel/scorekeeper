#!/usr/bin/env bash
# scorekeeper hook dispatcher — resolves the CLI wherever it lives:
# 1. installed package on PATH; 2. in-repo dev checkout (via uv);
# 3. zero-setup fetch from PyPI (uvx/pipx). Never breaks the agent (exit 0).
set -euo pipefail

EVENT="${1:?usage: run.sh <hook-event>}"
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Hooks run in a non-interactive shell that may not source the user's profile,
# so tools installed by pip --user / uv / homebrew / cargo can be off PATH.
# Prepend the common locations so command -v finds them.
for d in "$HOME/.local/bin" "$HOME/.cargo/bin" /opt/homebrew/bin /usr/local/bin \
         "$HOME/Library/Python/"*/bin; do
  [ -d "$d" ] && case ":$PATH:" in *":$d:"*) ;; *) PATH="$d:$PATH" ;; esac
done
export PATH

# 1. installed package on PATH (pip install scorekeeper)
if command -v scorekeeper >/dev/null 2>&1; then
  exec scorekeeper hook "$EVENT"
fi

# 2. in-repo dev checkout next to this plugin (contributors: --plugin-dir)
CORE_DIR="$PLUGIN_ROOT/../core"
if [ -f "$CORE_DIR/pyproject.toml" ] && command -v uv >/dev/null 2>&1; then
  exec uv run --project "$CORE_DIR" -q scorekeeper hook "$EVENT"
fi

# 3. zero-setup fallback: fetch + run from PyPI on demand (marketplace installs,
#    where neither the package nor the repo is present). uvx caches after first run.
if command -v uvx >/dev/null 2>&1; then
  exec uvx --quiet --from scorekeeper scorekeeper hook "$EVENT"
fi
if command -v pipx >/dev/null 2>&1; then
  exec pipx run --spec scorekeeper scorekeeper hook "$EVENT"
fi

echo "scorekeeper: CLI not found — 'pip install scorekeeper' or install uv (https://docs.astral.sh/uv)" >&2
exit 0   # never break the agent
