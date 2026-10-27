# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Loading stored runs (PRD-F-017, PRD-NF-009; ARTIFACT_INTEGRITY §4).

Loading checks, in order:

1. the manifest is readable JSON (otherwise the run is unreadable: ``STORAGE_ERROR``);
2. the schema major version is 1 (otherwise ``SCHEMA_VERSION_UNSUPPORTED``);
3. a RUNNING manifest is reported as incomplete, not as corrupt. ``integrity_ok`` is False;
4. ``cases.jsonl`` and ``summary.json`` match the hashes in the manifest. A mismatch raises
   ``INTEGRITY_MISMATCH`` when strict, or sets ``integrity_ok = False`` when lenient.

Case records are parsed only when the caller asks for them, and each one is validated again.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from evalforge.canon import bytes_sha256
from evalforge.errors import IntegrityError, RunNotFoundError, StorageError
from evalforge.models import CaseResult, ValidationError, check_schema_version
from evalforge.serialise import case_result_from_dict
from evalforge.status import RunStatus
from evalforge.store import CASES_NAME, LOCK_NAME, MANIFEST_NAME, SUMMARY_NAME


@dataclass(frozen=True, slots=True)
class StoredRun:
    """A run read from disk. ``problems`` lists everything the loader noticed."""

    path: Path
    manifest: Mapping[str, object]
    summary: Mapping[str, object] | None
    status: RunStatus
    integrity_ok: bool
    problems: tuple[str, ...]

    def cases(self) -> Iterator[CaseResult]:
        """Yield the case results in file order. Each record is validated again."""
        try:
            lines = (self.path / CASES_NAME).read_bytes().split(b"\n")
        except FileNotFoundError as exc:
            raise StorageError("STORAGE_ERROR", f"cases file missing ({self.path})") from exc
        for number, raw in enumerate(lines, start=1):
            if not raw.strip():
                continue
            try:
                data = json.loads(raw.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("record is not an object")
                yield case_result_from_dict(data)
            except (ValueError, ValidationError) as exc:
                raise StorageError(
                    "STORAGE_ERROR", f"invalid case record at line {number}: {exc}"
                ) from exc


def _read_manifest(path: Path) -> Mapping[str, object]:
    try:
        raw = (path / MANIFEST_NAME).read_bytes()
    except FileNotFoundError as exc:
        raise StorageError("STORAGE_ERROR", f"manifest missing ({path})") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise StorageError(
            "STORAGE_ERROR", "manifest is unreadable (truncated or corrupt)"
        ) from exc
    if not isinstance(data, dict):
        raise StorageError("STORAGE_ERROR", "manifest is not a JSON object")
    return data


def load_run(path: str | Path, *, strict: bool = True) -> StoredRun:
    """Load a run directory.

    With ``strict=True`` an integrity mismatch raises ``IntegrityError``.
    """
    run_dir = Path(path)
    if not run_dir.is_dir():
        raise RunNotFoundError("RUN_NOT_FOUND", f"run directory not found: {run_dir}")
    manifest = _read_manifest(run_dir)
    try:
        check_schema_version(manifest.get("schema_version"))
        status = RunStatus(str(manifest.get("status")))
    except ValidationError as exc:
        raise StorageError("STORAGE_ERROR", f"manifest is invalid: {exc}") from exc
    except ValueError as exc:
        raise StorageError("STORAGE_ERROR", f"manifest has an unknown run status: {exc}") from exc

    problems: list[str] = []
    if (run_dir / LOCK_NAME).exists():
        problems.append("lock file present: the run is active or was interrupted")

    if status is RunStatus.RUNNING:
        problems.append("run is incomplete: the manifest is still RUNNING")
        return StoredRun(run_dir, manifest, None, status, False, tuple(problems))

    integrity_ok = True
    summary: Mapping[str, object] | None = None
    cases_hash = manifest.get("cases_sha256")
    summary_hash = manifest.get("summary_sha256")
    checks = (
        (CASES_NAME, cases_hash, "cases file"),
        (SUMMARY_NAME, summary_hash, "summary file"),
    )
    for name, expected, label in checks:
        target = run_dir / name
        if not target.exists():
            if expected is not None:
                integrity_ok = False
                problems.append(f"{label} missing")
            continue
        actual = bytes_sha256(target.read_bytes())
        if expected != actual:
            integrity_ok = False
            problems.append(f"{label} does not match its recorded hash")
    if not integrity_ok and strict:
        raise IntegrityError("INTEGRITY_MISMATCH", "; ".join(problems))
    summary_path = run_dir / SUMMARY_NAME
    if summary_path.exists():
        try:
            parsed = json.loads(summary_path.read_bytes().decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise StorageError("STORAGE_ERROR", "summary file is unreadable") from exc
        if isinstance(parsed, dict):
            summary = parsed
    return StoredRun(run_dir, manifest, summary, status, integrity_ok, tuple(problems))
