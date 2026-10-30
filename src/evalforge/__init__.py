# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""EvalForge: evaluation and regression testing for AI applications.

Pre-alpha. The public operations are listed below. Their behaviour and limits are documented in
docs/API_DESIGN.md (the parts marked as deferred there are not implemented).
"""

from evalforge._version import __version__
from evalforge.api import (
    ComparisonResult,
    RunResult,
    compare_stored,
    export_bytes,
    inspect_document,
    inspect_run,
    run_configured,
    validate_config,
    validate_dataset,
    write_new,
)
from evalforge.compare import Comparison
from evalforge.datasets import Dataset
from evalforge.errors import EvalForgeError
from evalforge.evaluators.base import Evaluator
from evalforge.evaluators.builtin import (
    ExactMatch,
    JsonStructure,
    Latency,
    NormalizedText,
    RequiredFields,
    RuleBased,
)
from evalforge.evaluators.custom import CustomEvaluator
from evalforge.models import Case, EvaluatorResult
from evalforge.objects import (
    RegressionFinding,
    Run,
    RunSummary,
    Suite,
    Thresholds,
    compare,
    load_config,
    run_from_config,
)
from evalforge.status import RunStatus, Status
from evalforge.targets import Target

__all__ = [
    "Case",
    "Comparison",
    "ComparisonResult",
    "CustomEvaluator",
    "Dataset",
    "EvalForgeError",
    "Evaluator",
    "EvaluatorResult",
    "ExactMatch",
    "JsonStructure",
    "Latency",
    "NormalizedText",
    "RegressionFinding",
    "RequiredFields",
    "RuleBased",
    "Run",
    "RunResult",
    "RunStatus",
    "RunSummary",
    "Status",
    "Suite",
    "Target",
    "Thresholds",
    "__version__",
    "compare",
    "compare_stored",
    "export_bytes",
    "inspect_document",
    "inspect_run",
    "load_config",
    "run_configured",
    "run_from_config",
    "validate_config",
    "validate_dataset",
    "write_new",
]
