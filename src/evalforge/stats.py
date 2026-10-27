# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Summary statistics (EVALUATION_METHODOLOGY §7; TRD §8.3, DATA_MODELS §10).

Standard library only. The Wilson interval is the closed form of the score interval.
Percentiles use the nearest-rank definition. Both are checked against values derived separately
in the tests.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Final

Z_95: Final = 1.959963984540054


def wilson_interval(successes: int, trials: int) -> tuple[float, float] | None:
    """95% Wilson score interval for a proportion. Returns ``None`` when there are no trials."""
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("successes must be between 0 and trials")
    if trials == 0:
        return None
    p = successes / trials
    z2 = Z_95 * Z_95
    centre = (p + z2 / (2 * trials)) / (1 + z2 / trials)
    half = Z_95 * math.sqrt(p * (1 - p) / trials + z2 / (4 * trials * trials)) / (1 + z2 / trials)
    return max(0.0, centre - half), min(1.0, centre + half)


def nearest_rank_percentile(values: Sequence[float], percent: float) -> float | None:
    """Nearest-rank percentile: the value at rank ceil(percent/100 * n), counting from 1."""
    if not 0.0 < percent <= 100.0:
        raise ValueError("percent must be greater than 0 and at most 100")
    if not values:
        return None
    ordered = sorted(values)
    rank = math.ceil(percent / 100.0 * len(ordered))
    return ordered[rank - 1]
