"""Re-score persisted runs with the CURRENT behavioral classifier.

Every classifier improvement raises the same question: what do the old runs
say now? This answers it without re-running any agent. Final files are
recovered from the persisted skbench-* temp workdirs when they still exist
(best before reboot; falls back to reply-only classification otherwise —
the fallback is flagged in the output because rival-code evidence is the
strongest signal and may be missing).

Usage:
    uv run python reclassify.py ../results/run-<stamp>/results.jsonl [...]
Writes reclassified.jsonl next to each input and prints an old -> new table.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from classify import classify_drift, classify_revision
from rejudge import find_workdir
from run import collect_files

PAIRS = {
    "pg-mongo": ("postgresql", "mongodb"),
    "mysql-dynamo": ("mysql", "dynamodb"),
    "redis-memcached": ("redis", "memcached"),
    "fastapi-flask": ("fastapi", "flask"),
}


def _family_and_pair(record: dict) -> tuple[str, str] | None:
    """From the persisted behavior block, else from the scenario name."""
    b = record.get("behavior") or {}
    name = record.get("scenario", "")
    family = b.get("family") or next(
        (f for f in ("drift", "revision") if name.startswith(f"cb-{f}-")), None
    )
    pair = next((p for p in PAIRS if p in name), None)
    if family is None or pair is None:
        return None
    return family, pair


def reclassify_record(record: dict) -> dict | None:
    fp = _family_and_pair(record)
    if fp is None:
        return None
    family, pair = fp
    committed, rival = PAIRS[pair]
    # exact provenance first: records persist their workdir since 2026-07-14.
    # The glob fallback picks the NEWEST sibling by mtime, which can pair this
    # record's reply with a DIFFERENT run's files — flag it.
    exact = Path(record["workdir"]) if record.get("workdir") else None
    if exact is not None and exact.is_dir():
        workdir, provenance = exact, "exact"
    else:
        workdir = find_workdir(record["scenario"], record["variant"])
        provenance = "glob-newest (may be a different run!)" if workdir else "none"
    final_files = collect_files(workdir) if workdir else ""
    phases = record.get("phases") or []
    final_reply = phases[-1].get("reply_text", "") if phases else ""
    classify = classify_drift if family == "drift" else classify_revision
    c = classify(final_reply, final_files, committed, rival)
    return {
        "scenario": record["scenario"],
        "variant": record["variant"],
        "old": (record.get("behavior") or {}).get("label"),
        "new": c.label,
        "confidence": c.confidence,
        "signals": c.signals,
        "family": family,
        "files_provenance": provenance,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="+", help="results.jsonl paths")
    args = ap.parse_args()
    for path in map(Path, args.results):
        rows = []
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = reclassify_record(json.loads(line))
            if row:
                rows.append(row)
        out = path.with_name("reclassified.jsonl")
        out.write_text("".join(json.dumps(r) + "\n" for r in rows))
        print(f"\n{path.parent.name} -> {out.name}")
        for r in rows:
            delta = "  " if r["old"] == r["new"] else "->"
            files = "" if r["files_provenance"] == "exact" else f"  [files: {r['files_provenance']}]"
            print(f"  {r['scenario']} / {r['variant']}: "
                  f"{r['old']} {delta} {r['new']}/{r['confidence']}{files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
