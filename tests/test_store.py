# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Run persistence, integrity, io_mode, redaction, and the record round trip.

See EXECUTION_PLAN §4. Test IDs follow TEST_STRATEGY §4.11 (TST-PS), §4.15 (TST-IO, TST-RD,
TST-IN), and §4.8 (TST-SEC-017). Planted secrets are fake strings assembled from fragments.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

import pytest

from evalforge import store
from evalforge.canon import JSONValue, bytes_sha256
from evalforge.config import config_from_mapping
from evalforge.datasets import Dataset, parse_dataset_bytes
from evalforge.errors import EvalForgeError, IntegrityError, RunNotFoundError, StorageError
from evalforge.evaluators.base import fingerprint_of
from evalforge.evaluators.builtin import ExactMatch, Latency
from evalforge.models import CaseResult
from evalforge.reader import load_run
from evalforge.runner import RunOptions, RunOutcome, run_cases
from evalforge.serialise import case_result_from_dict, case_result_to_dict
from evalforge.status import RunStatus
from evalforge.store import RunContext, StorageWriter, acquire_lock, persist_outcome
from evalforge.targets import from_callable

FAKE_KEY = "sk-" + "A1b2C3d4E5f6G7h8I9j0"
RECORDS = b"".join(
    [
        b'{"id": "c1", "input": {"q": "one"}, "expected": "echo: one"}\n',
        b'{"id": "c2", "input": {"q": "two"}, "expected": "echo: two"}\n',
        b'{"id": "c3", "input": {"q": "three"}, "expected": "wrong"}\n',
        b'{"id": "c4", "input": {"q": "four"}}\n',
        b'{"id": "c5", "input": {"q": "five"}, "expected": "echo: five"}\n',
    ]
)


def _dataset(source: str = "datasets/support.jsonl") -> Dataset:
    return parse_dataset_bytes(RECORDS, fmt="jsonl", source_label=source)


def _config(
    config_dir: Path,
    *,
    io_mode: str = "full",
    redaction: bool = True,
    dataset_path: str = "datasets/support.jsonl",
) -> Any:
    return config_from_mapping(
        {
            "schema_version": "1.0",
            "run": {"io_mode": io_mode, "redaction": redaction, "run_root": ".evalforge/runs"},
            "dataset": {"path": dataset_path},
            "target": {"callable": "example:answer", "name": "echo"},
            "evaluators": [{"name": "exact", "type": "exact_match"}],
        },
        config_dir=config_dir,
    )


def _context(
    config_dir: Path,
    *,
    io_mode: str = "full",
    redaction: bool = True,
    dataset_path: str = "datasets/support.jsonl",
) -> RunContext:
    evaluators = (ExactMatch(name="exact"), Latency(name="fast", max_ms=10_000.0))
    return RunContext(
        dataset=_dataset(dataset_path),
        config=_config(config_dir, io_mode=io_mode, redaction=redaction, dataset_path=dataset_path),
        options=RunOptions(),
        io_mode=io_mode,
        redaction=redaction,
        target_name="echo",
        fingerprints=tuple(fingerprint_of(item) for item in evaluators),
    )


def _echo_target(case_input: JSONValue) -> JSONValue:
    assert isinstance(case_input, dict)
    return f"echo: {case_input['q']}"


def _outcome(context: RunContext, target: Any = _echo_target) -> RunOutcome:
    evaluators = (ExactMatch(name="exact"), Latency(name="fast", max_ms=10_000.0))
    return run_cases(
        context.dataset, from_callable(target, name="echo"), evaluators, context.options
    )


def _persist(tmp_path: Path, **kwargs: Any) -> tuple[Path, RunOutcome]:
    context = _context(tmp_path, **kwargs)
    outcome = _outcome(context)
    run_root = tmp_path / ".evalforge" / "runs"
    return persist_outcome(outcome, context, run_root), outcome


def _manifest(run_dir: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    return data


# TST-PS-109 / CO-2 persistence and round trip -------------------------------------------


def test_complete_run_is_written_and_loads_with_integrity_ok(tmp_path: Path) -> None:
    run_dir, outcome = _persist(tmp_path)
    manifest = _manifest(run_dir)
    assert manifest["status"] == "COMPLETED"
    assert manifest["persisted"] is True
    assert manifest["counts"]["selected"] == 5
    stored = load_run(run_dir)
    assert stored.integrity_ok is True
    assert stored.problems == ()
    assert stored.summary is not None
    assert stored.summary["executed"] == 5


def test_stored_cases_match_the_in_memory_results(tmp_path: Path) -> None:
    run_dir, outcome = _persist(tmp_path, io_mode="hashes", redaction=False)
    loaded = list(load_run(run_dir).cases())
    assert [(c.case_id, c.status, c.status_reason) for c in loaded] == [
        (c.case_id, c.status, c.status_reason) for c in outcome.cases
    ]


def test_record_round_trip_is_lossless_for_every_status_shape(tmp_path: Path) -> None:
    context = _context(tmp_path, redaction=False)
    outcome = _outcome(context)
    for original in outcome.cases:
        assert case_result_from_dict(case_result_to_dict(original)) == original


def test_summary_pass_rate_and_interval_match_the_counts(tmp_path: Path) -> None:
    run_dir, _ = _persist(tmp_path)
    summary = load_run(run_dir).summary
    assert summary is not None
    counts: Any = summary["counts"]
    # c4 has no expected value: its exact check is skipped, its latency check passes, so the case is
    # PASS under EVALUATION_METHODOLOGY §3.3 rule 7 (at least one PASS, the rest PASS or SKIPPED).
    assert counts["PASS"] == 4
    assert counts["FAIL"] == 1
    assert summary["executed"] == 5
    assert summary["pass_rate"] == pytest.approx(0.8)


def test_hashes_in_the_manifest_match_the_files(tmp_path: Path) -> None:  # TST-IN-001
    run_dir, _ = _persist(tmp_path)
    manifest = _manifest(run_dir)
    assert manifest["cases_sha256"] == bytes_sha256((run_dir / "cases.jsonl").read_bytes())
    assert manifest["summary_sha256"] == bytes_sha256((run_dir / "summary.json").read_bytes())


# TST-IN-002 / 003 / 004: what the hashes do and do not detect ----------------------------


def test_one_changed_byte_in_cases_is_detected(tmp_path: Path) -> None:  # TST-IN-002
    run_dir, _ = _persist(tmp_path)
    path = run_dir / "cases.jsonl"
    data = bytearray(path.read_bytes())
    data[10] = ord("x") if data[10] != ord("x") else ord("y")
    path.write_bytes(bytes(data))
    with pytest.raises(IntegrityError) as info:
        load_run(run_dir)
    assert info.value.code == "INTEGRITY_MISMATCH"
    lenient = load_run(run_dir, strict=False)
    assert lenient.integrity_ok is False


def test_rewriting_cases_and_recomputing_the_hash_is_not_detected(
    tmp_path: Path,
) -> None:  # TST-IN-003
    # Documented limitation (ARTIFACT_INTEGRITY §5): whoever can write both files defeats the check.
    run_dir, _ = _persist(tmp_path)
    cases = (run_dir / "cases.jsonl").read_bytes().replace(b'"PASS"', b'"FAIL"', 1)
    (run_dir / "cases.jsonl").write_bytes(cases)
    manifest = _manifest(run_dir)
    manifest["cases_sha256"] = bytes_sha256(cases)
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert load_run(run_dir).integrity_ok is True


def test_editing_the_manifest_dataset_hash_is_not_detected(tmp_path: Path) -> None:  # TST-IN-004
    # Documented limitation (ARTIFACT_INTEGRITY §3.1): the manifest is not hashed.
    run_dir, _ = _persist(tmp_path)
    manifest = _manifest(run_dir)
    manifest["dataset"]["canonical_sha256"] = "sha256:" + "0" * 64
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert load_run(run_dir).integrity_ok is True


# TST-PS-101 / 102 / 103 / 104 / 105 / 106 / 107 -------------------------------------------


def test_replacing_the_manifest_is_atomic_and_leaves_no_partial_files(  # TST-PS-101
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    calls: list[str] = []

    def failing_once(src: str, dst: str) -> None:
        calls.append(dst)
        if len(calls) == 3:  # the final manifest write
            raise OSError(28, "No space left on device")
        real_replace(src, dst)

    monkeypatch.setattr("evalforge.store.os.replace", failing_once)
    context = _context(tmp_path)
    run_root = tmp_path / "runs"
    with pytest.raises(StorageError):
        persist_outcome(_outcome(context), context, run_root)
    run_dir = next(run_root.iterdir())
    manifest = _manifest(run_dir)
    assert manifest["status"] == "FAILED"  # the failure was recorded
    assert not list(run_dir.glob(".tmp-*"))  # no temporary file left behind
    assert not (run_dir / ".lock").exists()


def test_unwritable_run_root_is_a_storage_error(tmp_path: Path) -> None:  # TST-PS-102
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("x", encoding="utf-8")
    context = _context(tmp_path)
    with pytest.raises(StorageError) as info:
        persist_outcome(_outcome(context), context, blocker)
    assert info.value.code == "STORAGE_ERROR"


def test_disk_full_during_append_finalises_the_run_as_failed(  # TST-PS-103
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path)
    outcome = _outcome(context)
    writes = {"count": 0}
    original_append = StorageWriter.append

    def flaky_append(self: StorageWriter, result: CaseResult) -> None:
        writes["count"] += 1
        if writes["count"] == 3:
            raise StorageError("STORAGE_ERROR", "disk full")
        original_append(self, result)

    monkeypatch.setattr(StorageWriter, "append", flaky_append)
    with pytest.raises(StorageError):
        persist_outcome(outcome, context, tmp_path / "runs")
    run_dir = tmp_path / "runs" / outcome.run_id
    manifest = _manifest(run_dir)
    assert manifest["status"] == "FAILED"
    assert manifest["error"]["type"] == "StorageError"
    assert len((run_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()) == 2
    assert not (run_dir / ".lock").exists()


def test_summary_write_failure_keeps_the_cases_and_marks_failed(  # TST-PS-104
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_write = store.write_atomic

    def fail_summary(path: Path, data: bytes) -> None:
        if path.name == "summary.json":
            raise StorageError("STORAGE_ERROR", "cannot write summary")
        real_write(path, data)

    monkeypatch.setattr(store, "write_atomic", fail_summary)
    context = _context(tmp_path)
    outcome = _outcome(context)
    with pytest.raises(StorageError):
        persist_outcome(outcome, context, tmp_path / "runs")
    run_dir = tmp_path / "runs" / outcome.run_id
    assert len((run_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()) == 5
    assert _manifest(run_dir)["status"] == "FAILED"
    assert not (run_dir / "summary.json").exists()


def test_crash_leaves_the_manifest_running_and_is_reported_incomplete(  # TST-PS-105
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path)
    outcome = _outcome(context)
    count = {"n": 0}
    original_append = StorageWriter.append

    def crash_after_two(self: StorageWriter, result: CaseResult) -> None:
        count["n"] += 1
        if count["n"] == 3:
            raise KeyboardInterrupt
        original_append(self, result)

    monkeypatch.setattr(StorageWriter, "append", crash_after_two)
    with pytest.raises(KeyboardInterrupt):
        persist_outcome(outcome, context, tmp_path / "runs")
    run_dir = tmp_path / "runs" / outcome.run_id
    stored = load_run(run_dir)  # must not raise
    assert stored.status is RunStatus.RUNNING
    assert stored.integrity_ok is False
    assert any("incomplete" in item for item in stored.problems)
    assert len(list(stored.cases())) == 2


def test_stale_lock_is_reported_and_blocks_a_second_writer(
    tmp_path: Path,
) -> None:  # TST-PS-106, TST-SEC-017
    run_dir, _ = _persist(tmp_path)
    (run_dir / ".lock").write_text("", encoding="utf-8")
    assert any("lock file present" in item for item in load_run(run_dir).problems)
    (run_dir / ".lock").unlink()
    acquire_lock(run_dir)
    with pytest.raises(StorageError) as info:
        acquire_lock(run_dir)
    assert info.value.code == "STORAGE_LOCKED"


def test_read_only_cases_file_can_still_be_read(tmp_path: Path) -> None:  # TST-PS-107
    run_dir, _ = _persist(tmp_path)
    (run_dir / "cases.jsonl").chmod(0o400)
    try:
        assert len(list(load_run(run_dir).cases())) == 5
    finally:
        (run_dir / "cases.jsonl").chmod(0o600)


def test_two_runs_in_one_root_do_not_interfere(tmp_path: Path) -> None:  # TST-PS-109
    first, _ = _persist(tmp_path)
    second, _ = _persist(tmp_path)
    assert first != second
    assert load_run(first).integrity_ok and load_run(second).integrity_ok


def test_a_run_directory_is_never_reused(tmp_path: Path) -> None:
    context = _context(tmp_path)
    outcome = _outcome(context)
    run_root = tmp_path / "runs"
    persist_outcome(outcome, context, run_root)
    with pytest.raises(StorageError, match="already exists"):
        StorageWriter(run_root, outcome.run_id, context)


def test_missing_run_directory_is_run_not_found(tmp_path: Path) -> None:
    with pytest.raises(RunNotFoundError):
        load_run(tmp_path / "absent")


def test_truncated_manifest_is_reported_as_unreadable(tmp_path: Path) -> None:  # TST-MF-007
    run_dir, _ = _persist(tmp_path)
    text = (run_dir / "manifest.json").read_text(encoding="utf-8")
    (run_dir / "manifest.json").write_text(text[: len(text) // 2], encoding="utf-8")
    with pytest.raises(StorageError, match="unreadable"):
        load_run(run_dir)


def test_unsupported_schema_major_is_refused(tmp_path: Path) -> None:  # TST-MF-005
    run_dir, _ = _persist(tmp_path)
    manifest = _manifest(run_dir)
    manifest["schema_version"] = "2.0"
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(EvalForgeError) as info:
        load_run(run_dir)
    assert info.value.code == "SCHEMA_VERSION_UNSUPPORTED"


def test_newer_minor_version_is_accepted(tmp_path: Path) -> None:  # TST-MF-006
    run_dir, _ = _persist(tmp_path)
    manifest = _manifest(run_dir)
    manifest["schema_version"] = "1.9"
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert load_run(run_dir).integrity_ok is True


# TST-IO-001 / 002 / 003: io_mode ---------------------------------------------------------


def test_io_full_stores_content_and_hashes(tmp_path: Path) -> None:  # TST-IO-001
    run_dir, _ = _persist(tmp_path, io_mode="full", redaction=False)
    first = json.loads((run_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert first["input"] == {"q": "one"}
    assert first["expected"] == "echo: one"
    assert first["output"] == "echo: one"
    assert first["input_sha256"].startswith("sha256:")
    assert first["output_sha256"].startswith("sha256:")


def test_io_hashes_stores_no_content(tmp_path: Path) -> None:  # TST-IO-002
    run_dir, _ = _persist(tmp_path, io_mode="hashes", redaction=False)
    first = json.loads((run_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()[0])
    for name in ("input", "expected", "output"):
        assert name not in first
    assert first["output_sha256"].startswith("sha256:")


def test_io_none_stores_neither_content_nor_io_hashes(tmp_path: Path) -> None:  # TST-IO-003
    run_dir, _ = _persist(tmp_path, io_mode="none", redaction=False)
    first = json.loads((run_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()[0])
    for name in ("input", "expected", "output", "input_sha256", "expected_sha256", "output_sha256"):
        assert name not in first or first[name] is None
    assert first["case_sha256"].startswith("sha256:")


# TST-IO-005 / 006 / 007 -------------------------------------------------------------------


def test_target_exception_stores_type_and_message_only(tmp_path: Path) -> None:  # TST-IO-005
    context = _context(tmp_path, redaction=False)

    def raises(case_input: JSONValue) -> JSONValue:
        raise ValueError("bad input shape")

    outcome = _outcome(context, target=raises)
    run_dir = persist_outcome(outcome, context, tmp_path / "runs")
    text = (run_dir / "cases.jsonl").read_text(encoding="utf-8")
    assert "Traceback" not in text
    assert '"type":"ValueError"' in text


def test_configuration_snapshot_uses_portable_paths(tmp_path: Path) -> None:  # TST-IO-006
    context = _context(tmp_path, dataset_path="/private/elsewhere/cases.jsonl")
    run_dir = persist_outcome(_outcome(context), context, tmp_path / "runs")
    manifest = _manifest(run_dir)
    assert manifest["config_snapshot"]["dataset"]["path"] == "<external>/cases.jsonl"
    assert manifest["dataset"]["source_label"] == "<external>/cases.jsonl"
    assert "/private/elsewhere" not in (run_dir / "manifest.json").read_text(encoding="utf-8")


def test_environment_metadata_is_minimal(tmp_path: Path) -> None:  # TST-IO-007
    run_dir, _ = _persist(tmp_path)
    environment = _manifest(run_dir)["environment"]
    assert set(environment) == {"evalforge_version", "python", "os_family", "machine"}
    text = (run_dir / "manifest.json").read_text(encoding="utf-8")
    user = os.environ.get("USER", "")
    if len(user) >= 3:
        assert user not in text


def test_old_runs_are_not_deleted_automatically(tmp_path: Path) -> None:  # TST-IO-009
    first, _ = _persist(tmp_path)
    _persist(tmp_path)
    assert first.exists()


# CO-1 redaction on storage (TST-RD-001 to TST-RD-003, TST-RD-006) ---------------------------


def test_planted_secret_in_target_error_is_redacted_on_disk_but_not_in_memory(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path, redaction=True)

    def leaks(case_input: JSONValue) -> JSONValue:
        raise RuntimeError(f"upstream rejected {FAKE_KEY}")

    outcome = _outcome(context, target=leaks)
    assert FAKE_KEY in (
        outcome.cases[0].target.error.message if outcome.cases[0].target.error else ""
    )
    run_dir = persist_outcome(outcome, context, tmp_path / "runs")
    text = (run_dir / "cases.jsonl").read_text(encoding="utf-8")
    assert FAKE_KEY not in text
    assert "[REDACTED:openai-style-key]" in text
    stored = next(iter(load_run(run_dir).cases()))
    assert stored.redactions >= 1


def test_planted_secret_in_input_is_redacted_when_io_is_full(tmp_path: Path) -> None:
    context = _context(tmp_path, redaction=True)
    dataset = parse_dataset_bytes(
        f'{{"id": "k1", "input": {{"q": "{FAKE_KEY}"}}, "expected": "x"}}\n'.encode(),
        fmt="jsonl",
        source_label="datasets/keys.jsonl",
    )
    context = RunContext(
        dataset=dataset,
        config=context.config,
        options=context.options,
        io_mode="full",
        redaction=True,
        target_name="echo",
        fingerprints=context.fingerprints,
    )
    outcome = run_cases(
        dataset, from_callable(_echo_target, name="echo"), (ExactMatch(name="exact"),)
    )
    run_dir = persist_outcome(outcome, context, tmp_path / "runs")
    assert FAKE_KEY not in (run_dir / "cases.jsonl").read_text(encoding="utf-8")
    # The hash is of the value the target received, before redaction.
    assert outcome.cases[0].input_sha256 is not None


def test_redaction_disabled_is_recorded_in_the_manifest(tmp_path: Path) -> None:  # TST-RD-006
    run_dir, _ = _persist(tmp_path, redaction=False)
    manifest = _manifest(run_dir)
    assert manifest["redaction"] is False


def test_io_none_on_disk_contains_no_case_text(tmp_path: Path) -> None:
    run_dir, _ = _persist(tmp_path, io_mode="none", redaction=False)
    text = (run_dir / "cases.jsonl").read_text(encoding="utf-8")
    assert '"q"' not in text
    assert "echo" not in text


# Permissions (OD-22) -----------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes are not enforced on Windows")
def test_run_directory_and_files_are_owner_only(tmp_path: Path) -> None:
    run_dir, _ = _persist(tmp_path)
    assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
    for name in ("manifest.json", "cases.jsonl", "summary.json"):
        assert stat.S_IMODE((run_dir / name).stat().st_mode) == 0o600


# Errors are never swallowed ---------------------------------------------------------------


def test_storage_errors_are_evalforge_errors(tmp_path: Path) -> None:
    error = StorageError("STORAGE_ERROR", "x")
    assert isinstance(error, EvalForgeError)
