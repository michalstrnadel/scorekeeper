"""Statistics for small-N agent evaluation (Addendum-1 §A.2, §A.6).

Binary metrics (SCR pass/fail): Wilson score intervals — CLT-based intervals
demonstrably fail at small N (escape [0,1] or collapse to zero width).
Continuous metrics (tokens, latency): smooth bootstrap, 500–1000 pseudosamples.
Scenarios sharing a repo/environment are NOT independent: cluster-robust SEs
by scenario environment (naive SEs can be ~3x understated). Inference runs on
per-instance paired differences only. Latency is reported at P90/P99, never
as a mean. stdlib-only; deterministic via explicit rng seed.
"""

from __future__ import annotations

import math
import random
import statistics
from collections import defaultdict


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion. Safe at small N."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, center - half), min(1.0, center + half))


def smooth_bootstrap_ci(
    values: list[float],
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float]:
    """Percentile CI of the mean via smooth bootstrap (Gaussian kernel jitter)."""
    if not values:
        return (0.0, 0.0)
    if len(values) == 1:
        return (values[0], values[0])
    rng = random.Random(seed)
    sd = statistics.stdev(values)
    h = 1.06 * sd * len(values) ** (-1 / 5) if sd > 0 else 0.0  # Silverman
    means = []
    for _ in range(n_boot):
        sample = [rng.choice(values) + rng.gauss(0, h) for _ in values]
        means.append(statistics.fmean(sample))
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return (lo, hi)


def paired_differences(
    bare: dict[str, float], treated: dict[str, float]
) -> dict[str, float]:
    """Per-instance treated − bare on the shared keys (paired design)."""
    return {k: treated[k] - bare[k] for k in sorted(set(bare) & set(treated))}


def clustered_se(diffs: dict[str, float], cluster_of: dict[str, str]) -> float:
    """Cluster-robust SE of the mean of paired differences.

    ``cluster_of`` maps instance id -> environment id (scenarios sharing a seed
    repo form one cluster). CR0 estimator on cluster totals.
    """
    if not diffs:
        return 0.0
    clusters: dict[str, list[float]] = defaultdict(list)
    for key, d in diffs.items():
        clusters[cluster_of.get(key, key)].append(d)
    g = len(clusters)
    if g < 2:
        return float("inf")  # cannot estimate — flag, don't fake precision
    n = len(diffs)
    mean = statistics.fmean(diffs.values())
    # sum over clusters of (sum of residuals)^2
    s = sum((sum(v - mean for v in vals)) ** 2 for vals in clusters.values())
    var = s * g / ((g - 1) * n**2)
    return math.sqrt(var)


def icc_anova(clusters: list[list[float]]) -> float:
    """ICC(1) via one-way ANOVA — the intraclass correlation of repeated runs
    within a scenario (the run-design input for the Design Effect,
    overreach-landscape §6: DEFF = 1 + (k-1)·ICC).

    ``clusters``: one list of outcomes (0/1 for binary labels) per scenario.
    Standard ANOVA estimator with the mean cluster size k0 correcting for
    unequal cluster sizes; negative estimates are clamped to 0.0 (the usual
    convention — sampling noise, not real negative correlation). Returns 0.0
    when there is no between- or within-cluster information to estimate from
    (fewer than 2 clusters, or all clusters of size 1).
    """
    groups = [c for c in clusters if c]
    g = len(groups)
    n = sum(len(c) for c in groups)
    if g < 2 or n <= g:
        return 0.0
    grand = sum(sum(c) for c in groups) / n
    ss_between = sum(len(c) * (statistics.fmean(c) - grand) ** 2 for c in groups)
    ss_within = sum(sum((v - statistics.fmean(c)) ** 2 for v in c) for c in groups)
    ms_between = ss_between / (g - 1)
    ms_within = ss_within / (n - g)
    # mean cluster size adjusted for imbalance (Donner & Koval)
    k0 = (n - sum(len(c) ** 2 for c in groups) / n) / (g - 1)
    denom = ms_between + (k0 - 1) * ms_within
    if denom <= 0:
        return 0.0
    return max(0.0, (ms_between - ms_within) / denom)


def design_effect(icc: float, k: int) -> float:
    """Variance inflation of k repeated runs per scenario: DEFF = 1 + (k-1)·ICC."""
    return 1.0 + (k - 1) * max(0.0, icc)


def coefficient_of_variation(values: list[float]) -> float:
    """CV = sd/|mean|; the A.3 meta-evaluation gate metric (threshold 0.05)."""
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if mean == 0:
        return 0.0 if all(v == 0 for v in values) else float("inf")
    return statistics.stdev(values) / abs(mean)


def percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile (q in [0,100]); latency reporting uses P90/P99."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(ordered)))
    return ordered[rank - 1]


def summarize_binary(name: str, successes: int, n: int) -> dict:
    lo, hi = wilson_interval(successes, n)
    return {
        "metric": name,
        "rate": round(successes / n, 3) if n else None,
        "n": n,
        "wilson_95": [round(lo, 3), round(hi, 3)],
    }


def summarize_latency(name: str, values: list[float]) -> dict:
    return {
        "metric": name,
        "p50": percentile(values, 50),
        "p90": percentile(values, 90),
        "p99": percentile(values, 99),
        "n": len(values),
    }
