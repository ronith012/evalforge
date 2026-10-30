# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Command-line interface (CLI_SPECIFICATION §1 to §4; TRD §10).

Parsing and output live here. Every operation is in ``evalforge.api``, so the CLI and the Python
API return the same results (parity tests in ``tests/test_cli.py``).

Output rules (CLI §1.2): results go to stdout. Diagnostics go to stderr. With ``--format json``
stdout is always one JSON document, including on failure. Exit codes come from the registered error
codes (``ERROR_CODES``), and each command's exit status is the one the specification gives.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Final

from evalforge import api
from evalforge._version import __version__
from evalforge.errors import ERROR_CODES, ErrorInfo, EvalForgeError
from evalforge.models import CaseResult
from evalforge.reporting.comparison_text import render_comparison
from evalforge.reporting.json_report import report_bytes
from evalforge.reporting.sanitize import sanitize_text
from evalforge.reporting.text import render_run
from evalforge.status import RunStatus

EXIT_OK: Final = 0
EXIT_REGRESSION: Final = 1
EXIT_INFRASTRUCTURE: Final = 4
EXIT_REFUSED: Final = 5
VALIDATE_COMMANDS: Final = frozenset({"config validate", "dataset validate"})


def _location(info: ErrorInfo) -> str:
    if info.path is None:
        return ""
    return f"{info.path}:{info.line}" if info.line is not None else info.path


def _emit_json(document: dict[str, object]) -> None:
    sys.stdout.write(report_bytes(document).decode("utf-8"))


def _report_error(exc: EvalForgeError, fmt: str, command: str) -> int:
    """Print a failure and return its exit code (CLI §1.3, §1.4)."""
    code = exc.code
    exit_code = ERROR_CODES[code].exit_code or EXIT_INFRASTRUCTURE
    if fmt == "json":
        if command in VALIDATE_COMMANDS:
            document: dict[str, object] = {
                "valid": False,
                "errors": [_error_dict(item) for item in exc.errors]
                or [{"code": code, "message": exc.message}],
            }
        else:
            document = {"error": {"code": code, "message": exc.message}}
        _emit_json(document)
        return exit_code
    if exc.errors:
        for item in exc.errors:
            location = _location(item)
            prefix = f"{location}: " if location else ""
            sys.stderr.write(f"error[{item.code}]: {prefix}{item.message}\n")
        sys.stderr.write(f"{len(exc.errors)} error(s) found.\n")
    else:
        sys.stderr.write(f"error[{code}]: {exc.message}\n")
    return exit_code


def _error_dict(item: ErrorInfo) -> dict[str, object]:
    return {
        "code": item.code,
        "message": item.message,
        "path": item.path,
        "line": item.line,
        "field": item.field,
    }


def _warn(message: str) -> None:
    sys.stderr.write(f"warning: {message}\n")


def _run_root(args: argparse.Namespace) -> str:
    return args.run_root if args.run_root is not None else api.DEFAULT_RUN_ROOT


# Command handlers -----------------------------------------------------------------------------


def _config_validate(args: argparse.Namespace) -> int:
    document = api.validate_config(
        args.config, check_imports=args.check_imports, check_dataset=args.check_dataset
    )
    if args.format == "json":
        _emit_json(document)
        return EXIT_OK
    sys.stdout.write(f"Configuration valid: {document['config']}\n")
    imports = "imports checked" if args.check_imports else "imports not checked"
    sys.stdout.write(f"  target: {document['target']} ({imports})\n")
    evaluators = document["evaluators"]
    assert isinstance(evaluators, list)
    sys.stdout.write(f"  evaluators: {len(evaluators)} ({', '.join(map(str, evaluators))})\n")
    if "dataset" in document:
        dataset = document["dataset"]
        assert isinstance(dataset, dict)
        sys.stdout.write(f"  dataset: {dataset['cases']} case(s), {dataset['format']}\n")
    return EXIT_OK


def _dataset_validate(args: argparse.Namespace) -> int:
    dataset = api.validate_dataset(args.path)
    document = api.dataset_document(dataset)
    for warning in dataset.warnings:
        _warn(warning)
    if args.format == "json":
        _emit_json(document)
        return EXIT_OK
    tags = document["tags"]
    assert isinstance(tags, dict)
    tag_text = ", ".join(f"{name} ({count})" for name, count in tags.items()) or "none"
    sys.stdout.write(f"Dataset valid: {args.path}\n")
    sys.stdout.write(f"  format:            {document['format']}\n")
    sys.stdout.write(f"  cases:             {document['cases']}\n")
    sys.stdout.write(f"  tags:              {tag_text}\n")
    sys.stdout.write(f"  sha256:            {document['sha256']}\n")
    sys.stdout.write(f"  canonical sha256:  {document['canonical_sha256']}\n")
    return EXIT_OK


def _split_values(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def _stderr_is_terminal() -> bool:
    return sys.stderr.isatty()


def _progress_line(position: int, total: int, case: CaseResult) -> str:
    reason = f"  {case.status_reason}" if case.status_reason else ""
    return (
        f"  [{position}/{total}] {sanitize_text(case.case_id)}  {case.status.value}  "
        f"{case.target.duration_ms:.0f} ms{sanitize_text(reason)}\n"
    )


def _run(args: argparse.Namespace) -> int:
    progress = None
    if args.format == "text" and _stderr_is_terminal():

        def progress(position: int, total: int, case: CaseResult) -> None:
            sys.stderr.write(_progress_line(position, total, case))

    result = api.run_configured(
        args.config,
        on_progress=progress,
        run_root=args.out if args.out is not None else args.run_root,
        case_ids=args.case,
        tags=args.tag,
        timeout_seconds=args.timeout,
        io_mode=args.io_mode,
        redaction=False if args.no_redaction else None,
        fail_on=_split_values(args.fail_on),
    )
    stored = result.stored
    for warning in result.dataset_warnings:
        _warn(warning)
    if not result.redaction:
        _warn("redaction is disabled for this run; the manifest records redaction: false.")
    status = stored.status
    counts = None if stored.summary is None else stored.summary.get("counts")
    if args.format == "json":
        _emit_json(
            {
                "run_id": stored.manifest.get("run_id"),
                "status": status.value,
                "stored": str(stored.path),
                "counts": counts,
                "fail_on": list(result.fail_on),
                "fail_on_matches": result.fail_on_matches,
                "redaction": result.redaction,
            }
        )
    elif stored.summary is None:
        sys.stdout.write(
            f"Run {sanitize_text(str(stored.manifest.get('run_id')))}\n"
            f"Status: {status.value}\nStored: {stored.path}\n"
        )
    else:
        sys.stdout.write(render_run(stored))

    if status is RunStatus.ABORTED:
        sys.stderr.write("error[RUN_ABORTED]: the run was interrupted; it is stored as ABORTED.\n")
        return EXIT_INFRASTRUCTURE
    if status is RunStatus.FAILED:
        sys.stderr.write("error[ENGINE_ERROR]: the run failed while being stored.\n")
        return EXIT_INFRASTRUCTURE
    if result.fail_on_matches > 0:
        return EXIT_REGRESSION
    return EXIT_OK


def _inspect(args: argparse.Namespace) -> int:
    stored = api.inspect_run(args.run, _run_root(args))
    if args.format == "json":
        _emit_json(
            api.inspect_document(
                stored,
                case_id=args.case,
                status=args.status,
                limit=args.limit,
                show_io=args.show_io,
            )
        )
    else:
        sys.stdout.write(
            api.inspect_text(
                stored,
                case_id=args.case,
                status=args.status,
                limit=args.limit,
                show_io=args.show_io,
            )
        )
    return EXIT_OK


def _compare(args: argparse.Namespace) -> int:
    result = api.compare_stored(
        args.baseline,
        args.candidate,
        run_root=_run_root(args),
        config_path=args.config,
        allow_dataset_change=args.allow_dataset_change,
        allow_evaluator_change=args.allow_evaluator_change,
        strict=args.strict,
    )
    if args.out is not None:
        api.write_new(args.out, report_bytes(result.to_dict()))
    if args.format == "json":
        _emit_json(result.to_dict())
    else:
        sys.stdout.write(render_comparison(result.to_dict()))
    status = result.comparison.exit_status
    if status == "refused":
        return EXIT_REFUSED
    if status == "regression":
        return EXIT_REGRESSION
    return EXIT_OK


def _report_export(args: argparse.Namespace) -> int:
    data = api.export_bytes(
        args.source,
        run_root=_run_root(args),
        fmt=args.format,
        include_io=args.include_io,
    )
    target = api.write_new(args.out, data)
    sys.stdout.write(f"Wrote {target} (format {args.format}, {len(data)} bytes)\n")
    return EXIT_OK


# Parser ---------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="evalforge",
        description="Evaluation and regression testing for AI applications.",
    )
    root.add_argument("--version", action="version", version=f"evalforge {__version__}")
    commands = root.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # Options shared by several commands. Options are accepted after the command name.
    fmt = argparse.ArgumentParser(add_help=False)
    fmt.add_argument("--format", choices=("text", "json"), default="text")
    run_root = argparse.ArgumentParser(add_help=False)
    run_root.add_argument("--run-root", metavar="PATH", default=None)

    config = commands.add_parser("config", help="configuration commands")
    config_commands = config.add_subparsers(dest="subcommand", required=True, metavar="ACTION")
    config_validate = config_commands.add_parser("validate", parents=[fmt])
    config_validate.add_argument("config", nargs="?", default=api.DEFAULT_CONFIG_NAME)
    config_validate.add_argument("--check-imports", action="store_true")
    config_validate.add_argument("--check-dataset", action="store_true")
    config_validate.set_defaults(handler=_config_validate, command_path="config validate")

    dataset = commands.add_parser("dataset", help="dataset commands")
    dataset_commands = dataset.add_subparsers(dest="subcommand", required=True, metavar="ACTION")
    dataset_validate = dataset_commands.add_parser("validate", parents=[fmt])
    dataset_validate.add_argument("path", metavar="PATH")
    dataset_validate.set_defaults(handler=_dataset_validate, command_path="dataset validate")

    run = commands.add_parser("run", parents=[fmt, run_root], help="run the configured target")
    run.add_argument("--config", default=api.DEFAULT_CONFIG_NAME, metavar="CONFIG")
    run.add_argument("--out", metavar="RUN_ROOT", default=None)
    run.add_argument("--case", action="append", metavar="ID", default=None)
    run.add_argument("--tag", action="append", metavar="TAG", default=None)
    run.add_argument("--timeout", type=float, metavar="SECONDS", default=None)
    run.add_argument("--io-mode", choices=api.IO_MODES, default=None)
    run.add_argument("--no-redaction", action="store_true")
    run.add_argument("--fail-on", metavar="STATUS[,STATUS...]", default=None)
    run.set_defaults(handler=_run, command_path="run")

    inspect = commands.add_parser("inspect", parents=[fmt, run_root], help="show a stored run")
    inspect.add_argument("run", metavar="RUN")
    inspect.add_argument("--case", metavar="ID", default=None)
    inspect.add_argument("--status", metavar="STATUS", default=None)
    inspect.add_argument("--limit", type=int, default=api.INSPECT_LIMIT_DEFAULT)
    inspect.add_argument("--show-io", action="store_true")
    inspect.set_defaults(handler=_inspect, command_path="inspect")

    compare = commands.add_parser("compare", parents=[fmt, run_root], help="compare two runs")
    compare.add_argument("baseline", metavar="BASELINE")
    compare.add_argument("candidate", metavar="CANDIDATE")
    compare.add_argument("--config", metavar="CONFIG", default=None)
    compare.add_argument("--allow-dataset-change", action="store_true")
    compare.add_argument("--allow-evaluator-change", action="store_true")
    compare.add_argument("--strict", action="store_true")
    compare.add_argument("--out", metavar="PATH", default=None)
    compare.set_defaults(handler=_compare, command_path="compare")

    report = commands.add_parser("report", help="report commands")
    report_commands = report.add_subparsers(dest="subcommand", required=True, metavar="ACTION")
    export = report_commands.add_parser("export", parents=[run_root])
    export.add_argument("source", metavar="SOURCE")
    export.add_argument("--out", metavar="PATH", required=True)
    export.add_argument("--format", choices=("json", "text"), default="json")
    export.add_argument("--include-io", action="store_true")
    export.set_defaults(handler=_report_export, command_path="report export")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the exit status. Never raises for expected failures."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_INFRASTRUCTURE
    fmt = str(getattr(args, "format", "text"))
    command = str(getattr(args, "command_path", ""))
    try:
        handler = args.handler
        return int(handler(args))
    except EvalForgeError as exc:
        return _report_error(exc, fmt, command)
    except KeyboardInterrupt:
        sys.stderr.write("error[ENGINE_ERROR]: interrupted before the command finished.\n")
        return EXIT_INFRASTRUCTURE
    except Exception as exc:  # Unexpected faults: no traceback, no detail (TRD-202).
        sys.stderr.write(
            f"error[ENGINE_ERROR]: unexpected {type(exc).__name__}; "
            "no further detail is recorded.\n"
        )
        return EXIT_INFRASTRUCTURE
