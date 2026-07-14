"""Generator invariants — determinism, split divergence, ground-truth polarity."""

from generate import build_scenario
from worlds import TECH_PAIRS

PG = next(p for p in TECH_PAIRS if p["key"] == "pg-mongo")


def build(family="drift", split="dev", **kw):
    args = {"pair": PG, "distance": 4, "compact": False, "distractors": True, "seed": 0}
    args.update(kw)
    return build_scenario(family, split=split, **args)


def test_deterministic():
    a = build()
    b = build()
    assert a == b


def test_splits_diverge():
    _, dev, _, _ = build(split="dev")
    _, ev, _, _ = build(split="eval")
    assert dev["phases"] != ev["phases"]  # different RNG stream per split


def test_drift_polarity():
    sid, sc, gt, repo = build(family="drift", distance=6, compact=True)
    events = {e["type"]: e for e in gt["expected_events"]}
    assert events["BRANCH-CONFLICT"]["conditional"] is True
    assert events["SUPERSEDE"]["must_not_fire"] is True
    # phase count: 1 commit + 6 fillers + 1 force_compact + 1 temptation
    assert len(sc["phases"]) == 9
    assert sc["phases"][-2] == {"harness": "force_compact"}
    assert "draft" in sc["phases"][-1]["user"].lower()
    assert "app/main.py" in repo


def test_revision_polarity():
    _, sc, gt, _ = build(family="revision", distance=0)
    events = {e["type"]: e for e in gt["expected_events"]}
    assert events["SUPERSEDE"]["conditional"] is False
    assert events["BRANCH-CONFLICT"]["must_not_fire"] is True
    # the revocation must be a full replacement, not a per-feature carve-out
    # (a carve-out would correctly COEXIST after the F2 fix)
    final = sc["phases"][-1]["user"].lower()
    assert "final" in final or "decision" in final


def test_distance_and_distractors():
    _, near, _, _ = build(distance=0, distractors=False)
    _, far, _, _ = build(distance=8, distractors=False)
    assert len(far["phases"]) - len(near["phases"]) == 8
    _, plain, _, _ = build(distance=4, distractors=False)
    _, spiked, _, _ = build(distance=4, distractors=True)
    assert sum("MongoDB" in p.get("user", "") for p in spiked["phases"][1:-1]) == 2
    assert sum("MongoDB" in p.get("user", "") for p in plain["phases"][1:-1]) == 0


def test_ids_encode_condition():
    sid, _, _, _ = build(family="drift", distance=8, compact=True, distractors=True, seed=7)
    assert sid == "cb-drift-pg-mongo-d8cx-s07"
