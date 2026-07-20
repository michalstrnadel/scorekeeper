# telos-coder-14b:latest

## Summary

`telos-coder-14b:latest` ran through the live extractor and Tier-1 detector smoke tests on a
local Ollama OpenAI-compatible endpoint. This was a negative quality result: the backend produced
valid enough JSON to exercise the pipeline, but it missed most extraction goldens and produced too
many false conflicts in Tier-1.

Observed only: these numbers do not claim broader model quality outside this scorekeeper fixture
set.

## Environment

| Field | Value |
| --- | --- |
| Date | 2026-07-19 |
| OS | Windows |
| scorekeeper | 0.3.0 source checkout |
| Python | 3.14.6 via uv |
| uv | 0.11.25 |
| Runtime | Ollama 0.32.1 |
| Endpoint | `http://localhost:11434/v1` |
| Model | `telos-coder-14b:latest` |
| Architecture | qwen2 |
| Parameters | 14.8B |
| Context length | 32768 |
| Quantization | Q4_K_M |

## Command

```sh
SCOREKEEPER_LIVE=1 \
SCOREKEEPER_MODEL_URL=http://localhost:11434/v1 \
SCOREKEEPER_MODEL=telos-coder-14b:latest \
uv run pytest -q tests/test_extract_live.py tests/test_detect_live.py -s
```

On this Windows run the equivalent PowerShell environment assignment was used.

## Live smoke-test output

```text
[openai_compat] recall 3/12 = 25%
[openai_compat] over-extractions: 3
  MISS  db-decision: PostgreSQL 16
  MISS  api-promise: response shape
  MISS  version-floor: 3.10
  MISS  tool-backed-assertion: httpmini
  MISS  hallucinated-assertion: retries
  MISS  agent-architectural-choice: cache
  MISS  assumption-explicit: UTF-8
  MISS  refinement: 16.3
  MISS  contract-new-endpoint-compatible: stats
  OVER  narration-only-empty: The test file was renamed to match conventions.
  OVER  narration-only-empty: The test file was renamed to match conventions.
  OVER  scope-suggestion-is-not-a-grant: minted pin ['topic:legacy-cleanup', 'path:legacy/**']
F
[openai_compat] tier1 accuracy 8/10 = 80%, FPR 40%
  WRONG new-endpoint-compatible: expected compatible, got incompatible
  WRONG vacuum-and-match: expected compatible, got incompatible
F
2 failed in 88.79s (0:01:28)
```

## JSON-schema compliance

Extractor repair retries: 1 across 14 extraction golden cases.

Per-case backend call counts from the extractor counting wrapper:

```text
db-decision: calls=1 extracted=1
api-promise: calls=1 extracted=1
version-floor: calls=1 extracted=1
tool-backed-assertion: calls=1 extracted=1
hallucinated-assertion: calls=1 extracted=2
agent-architectural-choice: calls=2 extracted=0
assumption-explicit: calls=1 extracted=2
narration-only-empty: calls=1 extracted=1
refinement: calls=1 extracted=1
dependency-choice-agent: calls=1 extracted=2
contract-new-endpoint-compatible: calls=1 extracted=1
chitchat-empty: calls=1 extracted=0
scope-grant-user: calls=1 extracted=2
scope-suggestion-is-not-a-grant: calls=1 extracted=2
repair_retries=1
```

## False conflicts and false positives

- Tier-1 false-positive rate was 40%, above the 20% ceiling.
- The model marked a compatible new endpoint as incompatible.
- The model marked the match/vacuum pair as incompatible, missing the exception-compatible reading.
- The extractor minted a `path:legacy/**` scope grant from a suggestion that was not a user grant.
- The extractor over-extracted narration about a renamed test file.

## Skipped cases

No live smoke cases were skipped by pytest. One local Windows test outside the live smoke path,
`test_symlink_escape_is_denied`, skips when the OS denies symlink creation privileges.

## Rough latency

- Live extractor + Tier-1 smoke command: 88.79 seconds of pytest runtime on the final tree.
- Extractor call-count pass: 45.5 seconds wall time for 14 extraction cases.

## Setup notes

The first Windows attempt did not reach the model because `scorekeeper.store` imported POSIX-only
`fcntl` during test collection. This report was produced after adding a platform-neutral lock helper
and explicit UTF-8 store I/O in the same branch. Without that compatibility fix, the local Ollama
backend could not be evaluated from this Windows checkout.

## Conclusion

`telos-coder-14b:latest` is currently not a passing backend for the live scorekeeper extractor and
Tier-1 detector thresholds. It is useful as a negative baseline because it exercises the local
OpenAI-compatible path, exposes one repair retry, and shows concrete failure modes in recall,
false-positive conflict detection, and scope-grant discipline.
