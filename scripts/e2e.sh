#!/usr/bin/env bash
# scorekeeper e2e orchestrator — one command runs everything CI runs.
#
#   scripts/e2e.sh            run all stages, cheapest first, fail-fast
#   scripts/e2e.sh <stage>..  run selected stages (CI jobs call exactly one,
#                             so local runs and CI can never drift)
#   scripts/e2e.sh --list     list stages
#
# macOS/Linux. On Windows, run the printed commands manually — every stage
# echoes exactly what it executes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

STAGES=(docs plugin core bench demo build live)

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  GREEN=$'\033[32m' RED=$'\033[31m' BOLD=$'\033[1m' DIM=$'\033[2m' RESET=$'\033[0m'
else
  GREEN="" RED="" BOLD="" DIM="" RESET=""
fi

log_cmd() { printf '%s$ %s%s\n' "$DIM" "$*" "$RESET"; }
run() { log_cmd "$@"; "$@"; }

# --- stages, cheapest first --------------------------------------------------

stage_docs() {  # internal links in git-tracked markdown (drafts/ 404s on GitHub)
  run python3 "$ROOT/scripts/check_links.py"
}

stage_plugin() {  # the hook dispatcher is release-critical bash (#6 incident)
  run uvx --from shellcheck-py shellcheck \
    "$ROOT/claude-code-plugin/hooks/run.sh" "$ROOT/scripts/e2e.sh"
  local manifest
  for manifest in "claude-code-plugin/.claude-plugin/plugin.json" \
                  "claude-code-plugin/hooks/hooks.json" \
                  ".claude-plugin/marketplace.json"; do
    log_cmd "python3 -c 'json.load(...)' $manifest"
    python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$ROOT/$manifest"
  done
  local payload='{"tool_name":"Edit","tool_input":{"file_path":"/tmp/x.py","new_string":"pass"}}'
  local event
  for event in pre-tool-use session-start definitely-not-an-event; do
    # unknown event = the #6 regression: a hook must never break the agent
    log_cmd "printf <payload> | bash claude-code-plugin/hooks/run.sh $event"
    (cd "$ROOT" && printf '%s' "$payload" | bash claude-code-plugin/hooks/run.sh "$event")
  done
}

stage_core() {  # keep in sync with the `core` job in .github/workflows/ci.yml
  cd "$ROOT/core"
  run uv run ruff check src tests ../bench ../scripts
  run uv run mypy
  run uv run pytest -q --cov --cov-report=term --cov-fail-under=85
  cd "$ROOT"
}

stage_bench() {  # generator + harness tests (relative imports need their cwd)
  cd "$ROOT/bench/harness"
  run uv run --with pytest python -m pytest test_stats.py test_classify.py -q
  cd "$ROOT/bench/deonticbench"
  run uv run --project ../harness --with pytest python -m pytest test_generate.py -q
  cd "$ROOT"
}

stage_demo() {  # deterministic no-LLM walkthrough, ends in a real assertion
  cd "$ROOT"
  run env SCOREKEEPER_DEMO_FAST=1 uv run --project core python demo/drift_demo.py
}

BUILD_TMP=""  # cleaned by the EXIT trap; a RETURN trap would leak past the function in bash

stage_build() {  # never trust core/dist/ — build into a clean temp dir
  BUILD_TMP="$(mktemp -d)"
  cd "$ROOT/core"
  run uv build --out-dir "$BUILD_TMP"
  run uvx twine check "$BUILD_TMP"/*
  # install-smoke from the wheel alone: catches packaging misses (entry
  # points, py.typed) that nothing running from the checkout can catch
  run uv run --isolated --no-project --with "$BUILD_TMP"/scorekeeper-*.whl -- \
    python -m scorekeeper --help
  cd "$ROOT"
}

stage_live() {  # opt-in: needs a model endpoint; never runs in CI
  if [ -z "${SCOREKEEPER_LIVE:-}" ]; then
    printf 'skipped (set SCOREKEEPER_LIVE=1 and point SCOREKEEPER_MODEL_URL at a backend)\n'
    return 0
  fi
  cd "$ROOT/core"
  run uv run pytest -q tests/test_extract_live.py tests/test_detect_live.py
  cd "$ROOT"
}

# --- driver ------------------------------------------------------------------

usage() {
  printf 'usage: scripts/e2e.sh [--list] [stage...]\nstages: %s\n' "${STAGES[*]}"
}

main() {
  local requested=() arg stage known current=""
  for arg in "$@"; do
    case "$arg" in
      --list) printf '%s\n' "${STAGES[@]}"; return 0 ;;
      -h|--help) usage; return 0 ;;
      *)
        known=0
        for stage in "${STAGES[@]}"; do
          [ "$arg" = "$stage" ] && known=1
        done
        if [ "$known" -eq 0 ]; then
          printf 'unknown stage: %s\n' "$arg" >&2; usage >&2; return 2
        fi
        requested+=("$arg") ;;
    esac
  done
  [ "${#requested[@]}" -eq 0 ] && requested=("${STAGES[@]}")

  # fail-fast: set -e aborts on the first failing command; the EXIT trap
  # names the stage so the last line of output is always the verdict
  cleanup() {
    local rc=$?
    [ -n "$BUILD_TMP" ] && rm -rf "$BUILD_TMP"
    if [ "$rc" -ne 0 ] && [ -n "$current" ]; then
      printf '%s[FAIL]%s %s\n' "$RED" "$RESET" "$current" >&2
    fi
  }
  trap cleanup EXIT
  local t0
  for current in "${requested[@]}"; do
    printf '\n%s== %s ==%s\n' "$BOLD" "$current" "$RESET"
    t0=$SECONDS
    "stage_$current"
    printf '%s[ ok ]%s %s (%ss)\n' "$GREEN" "$RESET" "$current" "$((SECONDS - t0))"
  done
  current=""
  printf '\n%sall stages passed:%s %s\n' "$GREEN" "$RESET" "${requested[*]}"
}

main "$@"
