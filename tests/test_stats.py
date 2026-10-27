# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Wilson interval and nearest-rank percentiles (TEST_STRATEGY §4.6, TST-ST-001 to TST-ST-007).

Expected values are literals. The interval is also checked against a separate derivation: the
bounds are the roots of (p - x)^2 = z^2 x (1 - x) / n, found by bisection rather than the closed
form.
"""

from __future__ import annotations

import math

import pytest

from evalforge.stats import Z_95, nearest_rank_percentile, wilson_interval


def _interval(successes: int, trials: int) -> tuple[float, float]:
    result = wilson_interval(successes, trials)
    assert result is not None
    return result


def _bisect_wilson(successes: int, trials: int) -> tuple[float, float]:
    p = successes / trials
    z2 = Z_95 * Z_95

    def g(x: float) -> float:
        return (p - x) ** 2 - z2 * x * (1 - x) / trials

    def root(lo: float, hi: float) -> float:
        for _ in range(200):
            mid = (lo + hi) / 2
            if (g(lo) < 0) == (g(mid) < 0):
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    lower = root(0.0, p) if 0 < successes else 0.0
    upper = root(p, 1.0) if successes < trials else 1.0
    return lower, upper


# TST-ST-001 / 002 -----------------------------------------------------------------------


def test_no_trials_gives_no_interval() -> None:
    assert wilson_interval(0, 0) is None


# TST-ST-003 -----------------------------------------------------------------------------


def test_wilson_three_of_five_matches_the_literal_value() -> None:
    lower, upper = _interval(3, 5)
    assert lower == pytest.approx(0.2307, abs=5e-5)
    assert upper == pytest.approx(0.8824, abs=5e-5)


# TST-ST-004 / 005 -----------------------------------------------------------------------


def test_zero_successes_has_lower_bound_zero_and_closed_form_upper_bound() -> None:
    lower, upper = _interval(0, 10)
    assert lower == 0.0
    # Closed form for zero successes: Z^2 / (n + Z^2).
    assert upper == pytest.approx(Z_95 * Z_95 / (10 + Z_95 * Z_95), abs=1e-12)
    assert upper == pytest.approx(0.2775, abs=5e-5)


def test_all_successes_has_upper_bound_one() -> None:
    lower, upper = _interval(10, 10)
    assert upper == pytest.approx(1.0, abs=1e-12)
    assert lower == pytest.approx(0.7225, abs=5e-5)


@pytest.mark.parametrize(
    ("successes", "trials"), [(3, 5), (4, 5), (1, 3), (30, 50), (1, 100), (99, 100)]
)
def test_closed_form_agrees_with_independent_bisection(successes: int, trials: int) -> None:
    closed = _interval(successes, trials)
    derived = _bisect_wilson(successes, trials)
    assert closed[0] == pytest.approx(derived[0], abs=1e-9)
    assert closed[1] == pytest.approx(derived[1], abs=1e-9)


def test_invalid_counts_are_refused() -> None:
    with pytest.raises(ValueError):
        wilson_interval(6, 5)
    with pytest.raises(ValueError):
        wilson_interval(-1, 5)


def test_interval_always_contains_the_observed_proportion() -> None:
    for successes in range(0, 21):
        lower, upper = _interval(successes, 20)
        p = successes / 20
        assert lower <= p <= upper
        assert 0.0 <= lower and upper <= 1.0
        assert not math.isnan(lower) and not math.isnan(upper)


# TST-ST-006 / 007 nearest-rank percentiles ----------------------------------------------


def test_nearest_rank_p95_over_twenty_values_is_the_nineteenth() -> None:
    values = [float(i) for i in range(1, 21)]  # 1..20
    assert nearest_rank_percentile(values, 95) == 19.0


def test_nearest_rank_is_order_independent() -> None:
    assert nearest_rank_percentile([5.0, 1.0, 3.0], 50) == 3.0


def test_nearest_rank_p50_over_four_values_is_the_second() -> None:
    assert nearest_rank_percentile([10.0, 20.0, 30.0, 40.0], 50) == 20.0


def test_empty_values_give_no_percentile() -> None:
    assert nearest_rank_percentile([], 95) is None


def test_percentile_bounds_are_checked() -> None:
    with pytest.raises(ValueError):
        nearest_rank_percentile([1.0], 0)
    with pytest.raises(ValueError):
        nearest_rank_percentile([1.0], 101)
