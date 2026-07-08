"""Live golden-pair evaluation of Tier-1 — per-backend (ADR-0003).

    SCOREKEEPER_LIVE=1 uv run pytest tests/test_detect_live.py -q -s

Asserts an accuracy floor and, separately, an FPR ceiling on the
compatible-labelled probes (precision > recall — SPEC §4.4).
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from scorekeeper.backends import detect_backend
from scorekeeper.detect.tier1 import judge
from scorekeeper.model import Commitment, Kind

GOLDEN = Path(__file__).parent / "golden" / "detection.yaml"

pytestmark = pytest.mark.skipif(
    not os.environ.get("SCOREKEEPER_LIVE"),
    reason="live detector eval — set SCOREKEEPER_LIVE=1",
)


def test_golden_pairs_live():
    backend = detect_backend(Path.cwd())
    pairs = yaml.safe_load(GOLDEN.read_text())["pairs"]
    correct, wrong, false_pos, compat_total = 0, [], 0, 0

    for pair in pairs:
        existing = Commitment(
            id="c-golden-0001",
            ts=datetime(2026, 7, 8, tzinfo=UTC),
            claim=pair["existing"],
            kind=Kind.DECISION,
        )
        verdicts = judge(backend, pair["new"], [existing])
        got = verdicts[0].verdict.value if verdicts else "(no verdict)"
        expected = pair["verdict"]
        if expected == "compatible":
            compat_total += 1
            if got in ("incompatible", "needs_clarification"):
                false_pos += 1
        if got == expected:
            correct += 1
        else:
            wrong.append((pair["id"], expected, got))

    accuracy = correct / len(pairs)
    fpr = false_pos / compat_total if compat_total else 0.0
    print(
        f"\n[{backend.name}] tier1 accuracy {correct}/{len(pairs)} = {accuracy:.0%}, FPR {fpr:.0%}"
    )
    for pid, exp, got in wrong:
        print(f"  WRONG {pid}: expected {exp}, got {got}")

    assert accuracy >= 0.7, f"tier1 accuracy below floor: {accuracy:.0%}"
    assert fpr <= 0.2, f"tier1 FPR above ceiling: {fpr:.0%}"
