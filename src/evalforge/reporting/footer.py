# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""The report footer (EVALUATION_METHODOLOGY §12).

Status: approved wording under OD-18 (owner decision, 2026-10-27). Every report carries this
text, and a test fixes it. Changing it requires a new decision.
"""

from __future__ import annotations

from typing import Final

FOOTER_TEXT: Final = (
    "EvalForge reports results of the configured evaluators on the provided cases. "
    "These results do not establish that the system is safe, correct, or reliable in general."
)
