# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Target interface, adapter, reference resolution, and invocation (TEST_STRATEGY §4.3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from evalforge.canon import JSONValue
from evalforge.errors import TargetLoadError
from evalforge.models import ABSENT
from evalforge.targets import (
    CallableTarget,
    from_callable,
    invoke_target,
    resolve_target,
)

FIXTURES = Path(__file__).parent / "fixtures" / "targets"


@pytest.fixture(autouse=True)
def _fixture_modules_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(FIXTURES))


def _echo(case_input: JSONValue) -> JSONValue:
    return {"seen": case_input}


# TST-TG-001 / PRD-F-005 -------------------------------------------------------------------


def test_callable_is_invoked_with_the_case_input() -> None:
    calls: list[JSONValue] = []

    def recorder(case_input: JSONValue) -> JSONValue:
        calls.append(case_input)
        return {"ok": True}

    target = from_callable(recorder)
    inputs: list[JSONValue] = [{"n": 1}, {"n": 2}]
    for case_input in inputs:
        invocation = invoke_target(target, case_input)
        assert invocation.result.status == "OK"
    assert calls == [{"n": 1}, {"n": 2}]


def test_default_name_is_the_qualified_name() -> None:
    assert from_callable(_echo).name.endswith("_echo")


def test_explicit_name_overrides_the_default() -> None:
    assert from_callable(_echo, name="support-bot-v2").name == "support-bot-v2"


def test_empty_or_overlong_names_are_rejected() -> None:
    with pytest.raises(TargetLoadError, match="1 to 128"):
        from_callable(_echo, name="")
    with pytest.raises(TargetLoadError, match="1 to 128"):
        from_callable(_echo, name="x" * 129)


def test_non_callable_is_rejected() -> None:
    with pytest.raises(TargetLoadError, match="must be callable"):
        from_callable(42)  # type: ignore[arg-type]


# TST-TG-002 -------------------------------------------------------------------------------


def test_output_and_duration_are_recorded() -> None:
    invocation = invoke_target(from_callable(_echo), {"q": 1})
    assert invocation.result.status == "OK"
    assert invocation.result.error_code is None
    assert invocation.result.duration_ms >= 0.0
    assert invocation.output == {"seen": {"q": 1}}


# TST-TG-003 -------------------------------------------------------------------------------


def test_exception_is_recorded_for_its_case_and_the_next_case_still_runs() -> None:
    def fragile(case_input: JSONValue) -> JSONValue:
        if case_input == "boom":
            raise ValueError("secret-free failure")
        return {"ok": True}

    target = from_callable(fragile)
    first = invoke_target(target, "boom")
    second = invoke_target(target, "fine")
    assert first.result.status == "ERROR"
    assert first.result.error_code == "TARGET_EXCEPTION"
    assert first.result.error is not None
    assert first.result.error.type_name == "ValueError"
    assert first.output is ABSENT
    assert second.result.status == "OK"


def test_long_exception_messages_are_truncated() -> None:
    def verbose(case_input: JSONValue) -> JSONValue:
        raise RuntimeError("x" * 2000)

    invocation = invoke_target(from_callable(verbose), None)
    assert invocation.result.error is not None
    assert len(invocation.result.error.message) == 500


# TST-TG-005 -------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["returns_a_set", "returns_bytes", "returns_nan"])
def test_non_serialisable_output_is_an_output_error(name: str) -> None:
    import example_bot

    invocation = invoke_target(from_callable(getattr(example_bot, name)), {})
    assert invocation.result.status == "ERROR"
    assert invocation.result.error_code == "TARGET_OUTPUT_INVALID"
    assert invocation.output is ABSENT


# TST-TG-006 -------------------------------------------------------------------------------


def test_target_cannot_change_the_stored_input() -> None:
    import example_bot

    original: dict[str, Any] = {"question": "hi"}
    invocation = invoke_target(from_callable(example_bot.mutates_its_input), original)
    assert invocation.result.status == "OK"
    assert original == {"question": "hi"}


# TST-TG-007 / TST-TG-008 ------------------------------------------------------------------


def test_none_output_is_recorded_as_json_null() -> None:
    import example_bot

    invocation = invoke_target(from_callable(example_bot.returns_none), {})
    assert invocation.result.status == "OK"
    assert invocation.output is None


def test_empty_string_output_is_recorded_as_is() -> None:
    import example_bot

    invocation = invoke_target(from_callable(example_bot.returns_empty_string), {})
    assert invocation.result.status == "OK"
    assert invocation.output == ""


# TST-TG-010 / TST-TG-011 / PRD-F-028 ------------------------------------------------------


def test_reference_resolves_a_function() -> None:
    target = resolve_target("example_bot:answer")
    assert target.name == "example_bot:answer"
    invocation = invoke_target(target, {"question": "refund?"})
    assert invocation.output == {"answer": "echo: refund?"}


def test_reference_to_an_object_with_a_declared_name_uses_that_name() -> None:
    target = resolve_target("example_bot:bot")
    assert target.name == "support-bot-v2"
    assert invoke_target(target, {}).output == {"answer": "from-class"}


def test_explicit_name_overrides_a_declared_name() -> None:
    assert resolve_target("example_bot:bot", name="candidate").name == "candidate"


def test_reference_to_an_object_without_a_name_uses_the_reference_text() -> None:
    assert resolve_target("example_bot:anonymous").name == "example_bot:anonymous"


def test_unknown_module_is_a_load_error() -> None:
    with pytest.raises(TargetLoadError) as info:
        resolve_target("no_such_module_for_evalforge:answer")
    assert info.value.code == "TARGET_LOAD_FAILED"


def test_module_that_fails_on_import_is_a_load_error() -> None:
    with pytest.raises(TargetLoadError, match="RuntimeError"):
        resolve_target("broken_import:anything")


def test_missing_attribute_is_a_load_error() -> None:
    with pytest.raises(TargetLoadError, match="has no attribute"):
        resolve_target("example_bot:does_not_exist")


def test_class_reference_is_refused_rather_than_instantiated() -> None:
    with pytest.raises(TargetLoadError, match="is a class"):
        resolve_target("example_bot:NotAnInstance")


def test_non_callable_attribute_is_refused() -> None:
    with pytest.raises(TargetLoadError, match="not callable"):
        resolve_target("example_bot:__name__")


@pytest.mark.parametrize("reference", ["no_colon", "a:b:c", "1bad:name", "mod:1bad"])
def test_malformed_references_are_refused(reference: str) -> None:
    with pytest.raises(TargetLoadError, match="module:attribute"):
        resolve_target(reference)


# TST-TG-013 and interruption behaviour ----------------------------------------------------


def test_system_exit_from_a_target_is_recorded_as_an_error() -> None:
    import example_bot

    invocation = invoke_target(from_callable(example_bot.exits_the_process), {})
    assert invocation.result.status == "ERROR"
    assert invocation.result.error is not None
    assert invocation.result.error.type_name == "SystemExit"


def test_keyboard_interrupt_propagates_so_the_runner_can_stop() -> None:
    import example_bot

    with pytest.raises(KeyboardInterrupt):
        invoke_target(from_callable(example_bot.interrupts), {})


def test_callable_target_type_is_the_adapter() -> None:
    assert isinstance(from_callable(_echo), CallableTarget)
