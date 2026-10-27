# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Synthetic target modules used only by the test suite. Not an example of production code."""

from __future__ import annotations

from evalforge.canon import JSONValue


def answer(case_input: JSONValue) -> JSONValue:
    if isinstance(case_input, dict) and "question" in case_input:
        return {"answer": f"echo: {case_input['question']}"}
    raise KeyError("question")


def returns_none(case_input: JSONValue) -> None:
    return None


def returns_empty_string(case_input: JSONValue) -> str:
    return ""


def returns_a_set(case_input: JSONValue) -> object:
    return {1, 2}


def returns_bytes(case_input: JSONValue) -> object:
    return b"raw"


def returns_nan(case_input: JSONValue) -> object:
    return float("nan")


def mutates_its_input(case_input: JSONValue) -> JSONValue:
    if isinstance(case_input, dict):
        case_input["mutated"] = True
    return {"ok": True}


def exits_the_process(case_input: JSONValue) -> JSONValue:
    raise SystemExit(3)


def interrupts(case_input: JSONValue) -> JSONValue:
    raise KeyboardInterrupt


class SupportBot:
    """Callable object with a declared name."""

    name = "support-bot-v2"

    def __call__(self, case_input: JSONValue) -> JSONValue:
        return {"answer": "from-class"}


class BotWithoutName:
    def __call__(self, case_input: JSONValue) -> JSONValue:
        return {"answer": "anonymous"}


class NotAnInstance:
    """A class, not an instance. Resolution must refuse it."""


bot = SupportBot()
anonymous = BotWithoutName()
