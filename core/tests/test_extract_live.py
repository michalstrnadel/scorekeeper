"""Live golden-set evaluation of the extractor — per-backend (ADR-0003).

Skipped by default; run explicitly:

    SCOREKEEPER_LIVE=1 uv run pytest tests/test_extract_live.py -q          # auto-detect
    SCOREKEEPER_LIVE=1 SCOREKEEPER_MODEL_URL=http://localhost:11434/v1 ...  # local OSS

Prints a per-case scorecard; asserts aggregate recall/precision floors rather
than per-case perfection (models differ — that variance is the measurement).
"""

import os
from pathlib import Path

import pytest
import yaml

from scorekeeper.backends import detect_backend
from scorekeeper.extract import build_turn_text, extract_commitments

GOLDEN = Path(__file__).parent / "golden" / "extraction.yaml"

pytestmark = pytest.mark.skipif(
    not os.environ.get("SCOREKEEPER_LIVE"),
    reason="live extractor eval — set SCOREKEEPER_LIVE=1",
)


def _matches(extracted, exp) -> bool:
    if exp["claim_contains"].lower() not in extracted.claim.lower():
        return False
    if extracted.kind.value != exp["kind"]:
        return False
    sources_ok = {exp["entitlement_source"], exp.get("entitlement_source_alt")}
    if extracted.entitlement.source.value not in sources_ok:
        return False
    attrs = extracted.scope and [s for s in extracted.scope if s.startswith("attr:")] or []
    return all(any(req in a for a in attrs) for req in exp.get("attrs", []))


def test_golden_set_live():
    backend = detect_backend(Path.cwd())
    cases = yaml.safe_load(GOLDEN.read_text())["cases"]
    hits, misses, false_pos = 0, [], []
    total_expected = sum(len(c["expected"]) for c in cases)

    for case in cases:
        turn = build_turn_text(
            case["turn"]["user"], case["turn"]["assistant"], case["turn"].get("tools_used")
        )
        got = extract_commitments(backend, turn)
        for exp in case["expected"]:
            if any(_matches(g, exp) for g in got):
                hits += 1
            else:
                misses.append((case["id"], exp["claim_contains"]))
        for g in got:
            if any(f.lower() in g.claim.lower() for f in case.get("forbidden", [])):
                false_pos.append((case["id"], g.claim))
        if not case["expected"] and got:
            false_pos.extend((case["id"], g.claim) for g in got)

    recall = hits / total_expected if total_expected else 1.0
    print(f"\n[{backend.name}] recall {hits}/{total_expected} = {recall:.0%}")
    print(f"[{backend.name}] over-extractions: {len(false_pos)}")
    for cid, what in misses:
        print(f"  MISS  {cid}: {what}")
    for cid, what in false_pos:
        print(f"  OVER  {cid}: {what}")

    assert recall >= 0.7, f"extractor recall below floor: {recall:.0%}"
    assert len(false_pos) <= 3, f"too many over-extractions: {false_pos}"
