# Command-Line Reference

Status: **Pre-alpha. Implemented in Milestone 11 and 15. Matches `evalforge <command> --help` and CLI_SPECIFICATION §3.**

Run the tool as `evalforge` (after installing the package) or `python -m evalforge`.

```
evalforge [--version] COMMAND
```

## Global behaviour

- Results go to **stdout**. Diagnostics and errors go to **stderr**.
- `--format json` makes stdout one JSON document, including on failure. For `config validate` and
  `dataset validate` the failure document is `{"valid": false, "errors": [...]}`. For other commands it is
  `{"error": {"code": ..., "message": ...}}`.
- Options are accepted **after** the command name, for example `evalforge run --format json`. Placing
  `--format` before the command is an error (argparse exit 2).
- Not implemented yet: `--quiet`, `--verbose`, `--no-color`. No output is coloured.

## Exit codes

| Code | Meaning | Examples |
|---|---|---|
| 0 | Success | Valid configuration; run completed; comparison has no error findings |
| 1 | Regression, or a `--fail-on` match | `compare` with a finding of severity error; `run --fail-on error` with an ERROR case |
| 2 | Usage, configuration, or unknown run | Unknown option; `CONFIG_INVALID`; `RUN_NOT_FOUND`; `USAGE_ERROR` |
| 3 | Dataset invalid | `DATASET_INVALID`, `DATASET_DUPLICATE_ID` |
| 4 | Infrastructure | Storage failure; `INTEGRITY_MISMATCH`; aborted or failed run; unexpected fault |
| 5 | Comparison refused | Dataset or evaluators differ without an override; `--strict` with an override |

If a command meets several conditions, it stops at the first fatal one, so precedence is by construction.

## Commands

### `evalforge config validate [CONFIG] [--check-imports] [--check-dataset] [--format text|json]`

Checks a configuration file without running anything. Default `CONFIG` is `evalforge.toml`.
Without `--check-imports`, target and evaluator modules are not imported.

### `evalforge dataset validate PATH [--format text|json]`

Validates a `.json` or `.jsonl` dataset. Prints counts, tags, the raw SHA-256, and the canonical SHA-256.
Warnings (for example, a symbolic link) go to stderr.

### `evalforge run [--config CONFIG] [--out RUN_ROOT] [--run-root PATH] [--case ID]... [--tag TAG]... [--timeout SECONDS] [--io-mode {full,hashes,none}] [--no-redaction] [--fail-on STATUS[,STATUS...]] [--format text|json]`

Runs the configured target over the selected cases and stores the run.

- `--case` and `--tag` cannot be combined. An unknown `--case` is a usage error.
- `--out` overrides the run root. Without it, `--run-root`, then `run_root` in the configuration (relative to the configuration file), applies.
- `--fail-on` takes `fail`, `error`, `inconclusive`, comma separated. Exit 1 when any case has one of them.
- `--no-redaction` is recorded in the manifest and prints a warning.
- In text mode on a terminal, one progress line is printed per case to stderr. It shows the case ID, status and duration, never inputs or outputs.

### `evalforge inspect RUN [--run-root PATH] [--case ID] [--status STATUS] [--limit N] [--show-io] [--format text|json]`

Shows a stored run: summary, a case list, or one case in detail.

- `RUN` is a run ID (a unique prefix of at least 8 characters) or a path to a run directory.
- The case list hides inputs and outputs unless `--show-io` is given.
- `--limit` is 0 to 1000. `0` means the maximum, 1000.
- A run still marked `RUNNING` is shown as incomplete with exit 0. A comparison refuses it.

### `evalforge compare BASELINE CANDIDATE [--run-root PATH] [--config CONFIG] [--allow-dataset-change] [--allow-evaluator-change] [--strict] [--out PATH] [--format text|json]`

Compares two runs.

- Both runs must be completed. Incompatible runs are refused (exit 5) and every refusal is listed.
- `--allow-dataset-change` and `--allow-evaluator-change` allow a difference. The comparison shows a banner and records the override.
- `--strict` refuses any overridden comparison.
- `--config` supplies the `[regression]` thresholds. Without it, the built-in defaults apply (TRD §9.1 proposed; OD-08 not yet confirmed).
- `--out` writes the comparison JSON to a new file. An existing file is never overwritten.

Exit: 0 when there are no error findings, 1 when there are, 5 when refused.

### `evalforge report export SOURCE --out PATH [--run-root PATH] [--format json|text] [--include-io]`

Writes a report for a run, or re-exports a comparison file.

- The default format is `json`. Text exports use the same renderer as the terminal.
- `--include-io` is JSON only and needs a run stored with `io_mode = full`. Otherwise exit 2 (`IO_NOT_STORED`).
- The default export contains no case inputs or outputs.
- An existing `--out` file is never overwritten (exit 4).

## Run root default

`inspect`, `compare` and `report export` look in `.evalforge/runs` under the current directory unless `--run-root`
is given. `run` uses its configuration's `run_root` unless `--out` or `--run-root` is given.
