# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Run persistence (TRD §7; ARTIFACT_INTEGRITY; DATA_HANDLING §9; EXECUTION_PLAN §4.3).

Layout of one run::

    <run_root>/<run_id>/
        .lock            exclusive; present while the run is being written
        manifest.json    written at start as RUNNING; final version written last
        cases.jsonl      one record per line, appended and flushed as each case completes
        summary.json     aggregates, written after cases.jsonl is complete

Hashes in the manifest cover the exact bytes of ``cases.jsonl`` and ``summary.json``. The
manifest is not hashed. See ARTIFACT_INTEGRITY §3.1.

Files are created owner-only where the platform supports it (OD-22). Windows ignores the mode.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Final

from evalforge import __version__
from evalforge.canon import bytes_sha256
from evalforge.config import EvalForgeConfig
from evalforge.datasets import Dataset
from evalforge.errors import EvalForgeError, StorageError, truncate
from evalforge.evaluators.base import EvaluatorFingerprint
from evalforge.models import CaseResult, ErrorObject
from evalforge.records import (
    config_record,
    dataset_record,
    environment_record,
    fingerprint_record,
    prepare_for_storage,
    summary_record,
)
from evalforge.runner import RunOptions, RunOutcome
from evalforge.serialise import case_result_to_dict
from evalforge.status import RunStatus

LOCK_NAME: Final = ".lock"
MANIFEST_NAME: Final = "manifest.json"
CASES_NAME: Final = "cases.jsonl"
SUMMARY_NAME: Final = "summary.json"
PRIVATE_DIR_MODE: Final = 0o700
PRIVATE_FILE_MODE: Final = 0o600


def utc_now() -> str:
    """RFC 3339 UTC timestamp with millisecond precision and a ``Z`` suffix (DATA_MODELS §1)."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _storage(message: str, path: Path | None = None) -> StorageError:
    detail = message if path is None else f"{message} ({path})"
    return StorageError("STORAGE_ERROR", detail)


def acquire_lock(run_dir: Path) -> None:
    """Create the exclusive lock file. A second writer fails with ``STORAGE_LOCKED`` (TRD-121)."""
    try:
        fd = os.open(run_dir / LOCK_NAME, os.O_CREAT | os.O_EXCL | os.O_WRONLY, PRIVATE_FILE_MODE)
    except FileExistsError as exc:
        raise StorageError(
            "STORAGE_LOCKED", f"run directory is locked by another writer ({run_dir})"
        ) from exc
    except OSError as exc:
        raise _storage(f"cannot create lock: {exc.strerror}", run_dir) from exc
    os.close(fd)


def release_lock(run_dir: Path) -> None:
    try:
        (run_dir / LOCK_NAME).unlink()
    except FileNotFoundError:
        pass


def write_atomic(path: Path, data: bytes) -> None:
    """Write through a temporary file in the same directory, then replace (TRD-112).

    An operating-system error becomes ``STORAGE_ERROR``. The temporary file is removed on failure.
    """
    try:
        descriptor, temporary = tempfile.mkstemp(
            dir=str(path.parent), prefix=".tmp-", suffix=".part"
        )
    except OSError as exc:
        raise _storage(
            f"cannot create a temporary file: {exc.strerror or type(exc).__name__}", path
        ) from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        _remove_quietly(temporary)
        raise _storage(
            f"cannot write {path.name}: {exc.strerror or type(exc).__name__}", path
        ) from exc
    except BaseException:
        _remove_quietly(temporary)
        raise


def _remove_quietly(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _json_bytes(value: Mapping[str, object], *, compact: bool = False) -> bytes:
    if compact:
        text = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    else:
        text = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    return (text + "\n").encode("utf-8")


@dataclass(frozen=True, slots=True)
class RunContext:
    """Facts that are fixed when a run starts and copied into every manifest."""

    dataset: Dataset
    config: EvalForgeConfig
    options: RunOptions
    io_mode: str
    redaction: bool
    target_name: str
    fingerprints: tuple[EvaluatorFingerprint, ...]


class StorageWriter:
    """Writes one run. Create it, append cases, then call ``finish`` or ``abort``."""

    def __init__(
        self, run_root: Path, run_id: str, context: RunContext, *, started_at: str | None = None
    ) -> None:
        self.run_id = run_id
        self.context = context
        self.started_at = started_at or utc_now()
        self.run_dir = run_root / run_id
        self._cases: IO[bytes] | None = None
        self._counts: dict[str, int] = {}
        self._config_snapshot, self._config_redactions = config_record(context.config)
        self._create(run_root)

    def _create(self, run_root: Path) -> None:
        try:
            run_root.mkdir(parents=True, exist_ok=True, mode=PRIVATE_DIR_MODE)
            if not run_root.is_dir():
                raise NotADirectoryError(str(run_root))
            self.run_dir.mkdir(mode=PRIVATE_DIR_MODE, exist_ok=False)
        except FileExistsError as exc:
            raise _storage("run directory already exists", self.run_dir) from exc
        except OSError as exc:
            raise _storage(
                f"cannot create run directory: {exc.strerror or type(exc).__name__}", run_root
            ) from exc
        acquire_lock(self.run_dir)
        try:
            fd = os.open(
                self.run_dir / CASES_NAME, os.O_CREAT | os.O_EXCL | os.O_WRONLY, PRIVATE_FILE_MODE
            )
            self._cases = os.fdopen(fd, "wb")
            self._write_manifest(RunStatus.RUNNING, None, None, None, None)
        except OSError as exc:
            release_lock(self.run_dir)
            raise _storage(
                f"cannot start the run: {exc.strerror or type(exc).__name__}", self.run_dir
            ) from exc

    def append(self, result: CaseResult) -> None:
        """Append one case as one JSON line and flush it (TRD-102)."""
        if self._cases is None:
            raise EvalForgeError("ENGINE_ERROR", "append after the run was closed")
        stored = prepare_for_storage(result, self.context.io_mode, self.context.redaction)
        line = _json_bytes(case_result_to_dict(stored), compact=True)  # ends with one newline
        try:
            self._cases.write(line)
            self._cases.flush()
        except OSError as exc:
            raise _storage(
                f"cannot append case: {exc.strerror or type(exc).__name__}", self.run_dir
            ) from exc

    def _close_cases(self) -> None:
        if self._cases is not None:
            try:
                self._cases.close()
            finally:
                self._cases = None

    def _manifest(
        self,
        status: RunStatus,
        finished_at: str | None,
        cases_sha256: str | None,
        summary_sha256: str | None,
        error: ErrorObject | None,
    ) -> dict[str, object]:
        ctx = self.context
        return {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "status": status.value,
            "started_at": self.started_at,
            "finished_at": finished_at,
            "tool": {"name": "evalforge", "version": __version__},
            "environment": environment_record(),
            "dataset": dataset_record(ctx.dataset, ctx.config.config_dir),
            "target": {"name": ctx.target_name, "callable": ctx.config.target.callable_ref},
            "evaluators": [fingerprint_record(item) for item in ctx.fingerprints],
            "config_snapshot": self._config_snapshot,
            "config_redactions": self._config_redactions,
            "timeout_seconds": ctx.options.timeout_seconds,
            "grace_seconds": ctx.options.grace_seconds,
            "persisted": True,
            "io_mode": ctx.io_mode,
            "redaction": ctx.redaction,
            "case_selection": _selection_record(ctx.options),
            "counts": self._counts,
            "cases_sha256": cases_sha256,
            "summary_sha256": summary_sha256,
            "error": None if error is None else {"type": error.type_name, "message": error.message},
        }

    def _write_manifest(
        self,
        status: RunStatus,
        finished_at: str | None,
        cases_sha256: str | None,
        summary_sha256: str | None,
        error: ErrorObject | None,
    ) -> None:
        data = _json_bytes(self._manifest(status, finished_at, cases_sha256, summary_sha256, error))
        write_atomic(self.run_dir / MANIFEST_NAME, data)

    def _cases_hash(self) -> str:
        return bytes_sha256((self.run_dir / CASES_NAME).read_bytes())

    def finish(self, outcome: RunOutcome) -> Path:
        """Write the summary and the final manifest, then release the lock."""
        self._counts = _counts_record(outcome)
        self._close_cases()
        cases_sha = self._cases_hash()
        summary = summary_record(self.run_id, outcome)
        summary_bytes = _json_bytes(summary)
        write_atomic(self.run_dir / SUMMARY_NAME, summary_bytes)
        summary_sha = bytes_sha256(summary_bytes)
        self._write_manifest(outcome.status, utc_now(), cases_sha, summary_sha, outcome.error)
        release_lock(self.run_dir)
        return self.run_dir

    def abort(self, status: RunStatus, error: ErrorObject) -> None:
        """Finalise a run that failed. The summary is not written. The lock is released."""
        self._close_cases()
        cases_sha: str | None = None
        try:
            cases_sha = self._cases_hash()
        except OSError:
            cases_sha = None
        self._write_manifest(status, utc_now(), cases_sha, None, error)
        release_lock(self.run_dir)


def _counts_record(outcome: RunOutcome) -> dict[str, int]:
    counts = outcome.counts()
    return {
        "selected": len(outcome.cases),
        "executed": counts["executed"],
        "not_executed": outcome.not_executed,
        "threads_possibly_running": outcome.threads_possibly_running,
    }


def _selection_record(options: RunOptions) -> dict[str, object]:
    if options.case_ids is not None:
        return {"mode": "ids", "ids": sorted(options.case_ids)}
    if options.tags is not None:
        return {"mode": "tags", "tags": sorted(options.tags)}
    return {"mode": "all"}


def persist_outcome(
    outcome: RunOutcome,
    context: RunContext,
    run_root: Path,
) -> Path:
    """Write a complete in-memory outcome to disk and return the run directory.

    A storage failure during writing finalises the run as FAILED with ``STORAGE_ERROR`` and raises.
    Any other exception, including ``KeyboardInterrupt``, leaves the manifest as RUNNING. That
    is the crash signature that ``inspect`` reports as incomplete.
    """
    writer = StorageWriter(run_root, outcome.run_id, context)
    try:
        for case in outcome.cases:
            writer.append(case)
        return writer.finish(outcome)
    except StorageError as exc:
        writer.abort(
            RunStatus.FAILED,
            ErrorObject(type_name="StorageError", message=truncate(exc.message)),
        )
        raise


def new_run_id() -> str:
    return str(uuid.uuid4())


__all__ = [
    "CASES_NAME",
    "LOCK_NAME",
    "MANIFEST_NAME",
    "SUMMARY_NAME",
    "RunContext",
    "StorageWriter",
    "acquire_lock",
    "new_run_id",
    "persist_outcome",
    "release_lock",
    "utc_now",
    "write_atomic",
]
