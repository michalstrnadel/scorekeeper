# Model reports

Per-backend experience reports: how a specific model behaves as scorekeeper's
extractor + Tier-1 detector. Extraction/detection quality is measured *per
backend*, never assumed — these reports are the record.

One file per model: `<model-name>.md` (e.g. `qwen3-8b.md`). The first report
defines the format; later reports follow it so results stay comparable.

Each report should cover at least:

- **Model + quant** (exact tag), endpoint and runtime versions
- **Live smoke-test output** — `SCOREKEEPER_LIVE=1 uv run pytest -q tests/test_extract_live.py tests/test_detect_live.py`
- **JSON-schema compliance** — repair-retry count (report it even when zero;
  "no retries needed" is itself a data point)
- **False conflicts** observed, and any skipped cases
- **Rough latency**

Keep observed behavior separate from broader model-quality claims. Start from
the [experience-report issue template](https://github.com/michalstrnadel/scorekeeper/issues/new?template=experience-report.md)
— a docs PR here is the durable version of that issue.

See [issue #2](https://github.com/michalstrnadel/scorekeeper/issues/2) and
CONTRIBUTING.md → "Add a model backend".
