# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Status enumerations (EVALUATION_METHODOLOGY §3)."""

from enum import StrEnum


class Status(StrEnum):
    """Evaluator-level and case-level outcome.

    PASS and FAIL are judgements about output. ERROR is an execution or infrastructure problem,
    not a quality verdict. SKIPPED means the check was intentionally not run. INCONCLUSIVE means
    a verdict could not be reached without an error.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"
    INCONCLUSIVE = "INCONCLUSIVE"


class RunStatus(StrEnum):
    """Run-level status recorded in the manifest (EVALUATION_METHODOLOGY §3.4)."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"
