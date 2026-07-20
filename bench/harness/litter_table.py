"""Clean litter numbers for the report: persisted tree diffs re-filtered with
the CURRENT skip rules (.git / venv / caches were added to the skip list after
some runs were scored, so their persisted diffs still carry the noise)."""
import glob
import json
import os
import sys

import yaml

sys.path.insert(0, "bench/harness")
from classify import TreeDiff, _skip_part, out_of_scope_touched  # noqa: E402

SPECS = "bench/deonticbench/generated/dev"


def spec(name):
    p = os.path.join(SPECS, name, "scenario.yaml")
    return yaml.safe_load(open(p)) if os.path.exists(p) else {}


def clean(paths):
    return [p for p in paths if not any(_skip_part(part) for part in p.split("/"))]


rows = []
for f in sorted(glob.glob("bench/results/run-2026*/results.jsonl")):
    for line in open(f):
        r = json.loads(line)
        b = r.get("behavior") or {}
        if b.get("family") not in ("overreach", "expansion"):
            continue
        td = r.get("tree_diff") or {}
        d = TreeDiff(
            added=clean(td.get("added", [])),
            modified=clean(td.get("modified", [])),
            deleted=clean(td.get("deleted", [])),
        )
        s = spec(r["scenario"])
        litter = out_of_scope_touched(d, s.get("granted_paths") or [],
                                      s.get("protected_paths") or ["legacy/**"])
        rows.append({
            "run": os.path.basename(os.path.dirname(f)),
            "scenario": r["scenario"].replace("cb-", ""),
            "variant": r["variant"],
            "effort": r.get("effort") or "-",
            "verdict": b.get("label"),
            "authored": len(d.added) + len(d.modified),
            "litter": len(litter),
            "litter_files": litter[:8],
        })

hdr = f"{'run':22}{'scenario':36}{'variant':22}{'eff':5}{'verdict':13}{'auth':6}{'litter'}"
print(hdr)
for x in rows:
    print(f"{x['run']:22}{x['scenario']:36}{x['variant']:22}{x['effort']:5}"
          f"{str(x['verdict']):13}{x['authored']:<6}{x['litter']}  {','.join(x['litter_files'][:4])}")

print()
for v in sorted({x["variant"] for x in rows}):
    g = [x for x in rows if x["variant"] == v]
    tot = sum(x["litter"] for x in g)
    withl = sum(1 for x in g if x["litter"])
    print(f"{v:22} n={len(g):2}  runs-with-litter={withl}/{len(g)}  total-litter-files={tot}")
