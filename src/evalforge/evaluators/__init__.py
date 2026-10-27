# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Evaluators: protocol, built-ins, custom loading, fingerprints, and the registry."""

from evalforge.evaluators.base import (
    Evaluator,
    EvaluatorFingerprint,
    apply_evaluator,
    fingerprint_of,
    make_result,
)
from evalforge.evaluators.builtin import (
    ExactMatch,
    JsonStructure,
    Latency,
    NormalizedText,
    RequiredFields,
    RuleBased,
)
from evalforge.evaluators.custom import LoadedCustomEvaluator, load_custom_evaluator
from evalforge.evaluators.registry import build_evaluator, build_evaluators

__all__ = [
    "Evaluator",
    "EvaluatorFingerprint",
    "ExactMatch",
    "JsonStructure",
    "Latency",
    "LoadedCustomEvaluator",
    "NormalizedText",
    "RequiredFields",
    "RuleBased",
    "apply_evaluator",
    "build_evaluator",
    "build_evaluators",
    "fingerprint_of",
    "load_custom_evaluator",
    "make_result",
]
