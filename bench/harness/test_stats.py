"""Unit tests for the small-N statistics module (run: uv run pytest test_stats.py)."""

import math

from stats import (
    clustered_se,
    coefficient_of_variation,
    paired_differences,
    percentile,
    smooth_bootstrap_ci,
    wilson_interval,
)


def test_wilson_stays_in_unit_interval_small_n():
    lo, hi = wilson_interval(0, 3)
    assert 0.0 <= lo <= hi <= 1.0
    lo, hi = wilson_interval(3, 3)
    assert 0.0 <= lo < 1.0 and hi == 1.0 or hi <= 1.0
    # the classic CLT failure case: p=0 gives degenerate [0,0]; Wilson does not
    assert wilson_interval(0, 5)[1] > 0.3


def test_wilson_known_value():
    lo, hi = wilson_interval(8, 10)
    assert 0.49 < lo < 0.51 and 0.94 < hi < 0.95  # canonical 8/10 Wilson bounds


def test_bootstrap_ci_contains_mean():
    values = [10.0, 12.0, 9.0, 11.0, 13.0, 10.5]
    lo, hi = smooth_bootstrap_ci(values, seed=1)
    assert lo < sum(values) / len(values) < hi


def test_bootstrap_deterministic_by_seed():
    values = [1.0, 2.0, 3.0, 4.0]
    assert smooth_bootstrap_ci(values, seed=7) == smooth_bootstrap_ci(values, seed=7)


def test_paired_differences_aligns_keys():
    d = paired_differences({"a": 1.0, "b": 2.0, "x": 9.0}, {"a": 0.5, "b": 3.0, "y": 9.0})
    assert d == {"a": -0.5, "b": 1.0}


def test_clustered_se_widens_vs_naive():
    # two clusters with strongly correlated within-cluster values
    diffs = {"s1a": 2.0, "s1b": 2.1, "s2a": -1.0, "s2b": -0.9}
    clusters = {"s1a": "env1", "s1b": "env1", "s2a": "env2", "s2b": "env2"}
    se_clustered = clustered_se(diffs, clusters)
    import statistics

    se_naive = statistics.stdev(diffs.values()) / math.sqrt(len(diffs))
    assert se_clustered > se_naive  # naive would understate


def test_clustered_se_single_cluster_flags():
    assert clustered_se({"a": 1.0, "b": 2.0}, {"a": "e", "b": "e"}) == float("inf")


def test_cv_gate():
    assert coefficient_of_variation([10.0, 10.0, 10.0]) == 0.0
    assert coefficient_of_variation([10.0, 10.2, 9.8]) < 0.05
    assert coefficient_of_variation([10.0, 15.0, 5.0]) > 0.05


def test_percentiles():
    vals = list(map(float, range(1, 101)))
    assert percentile(vals, 50) == 50.0
    assert percentile(vals, 90) == 90.0
    assert percentile(vals, 99) == 99.0
    assert percentile([], 90) == 0.0


# -- ICC / design effect (run-design inputs, overreach-landscape §6) ------------

from stats import design_effect, icc_anova  # noqa: E402


def test_icc_identical_within_clusters_is_high():
    # every scenario perfectly repeats its outcome -> ICC ~ 1
    assert icc_anova([[1, 1, 1], [0, 0, 0], [1, 1, 1], [0, 0, 0]]) > 0.95


def test_icc_no_cluster_structure_is_low():
    # within-cluster variance dominates -> ICC ~ 0 (clamped at 0)
    assert icc_anova([[0, 1, 0], [1, 0, 1], [0, 1, 1], [1, 0, 0]]) < 0.2


def test_icc_degenerate_inputs_return_zero():
    assert icc_anova([]) == 0.0
    assert icc_anova([[1, 0, 1]]) == 0.0          # one cluster
    assert icc_anova([[1], [0], [1]]) == 0.0      # all singletons


def test_icc_all_identical_outcomes():
    # zero variance everywhere: nothing to attribute -> 0.0, never a crash
    assert icc_anova([[1, 1], [1, 1], [1, 1]]) == 0.0


def test_design_effect():
    assert design_effect(0.0, 3) == 1.0
    assert design_effect(0.3, 3) == 1.6
    assert design_effect(-0.2, 5) == 1.0  # clamped
