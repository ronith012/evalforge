# EvalForge — Development Tasks

Status: **Milestone 1 implemented; completion record pending owner approval.** **Milestone 2 implemented; completion record in `docs/MILESTONE_2_RECORD.md`, pending owner approval.** **Milestone 3 implemented; completion record in `docs/MILESTONE_3_RECORD.md`, pending owner approval.** **Milestone 4 committed (1fc4789); completion record in `docs/MILESTONE_4_RECORD.md`.** **Milestone 5 implemented (uncommitted); completion record in `docs/MILESTONE_5_RECORD.md`. Approved by "proceed".** **Milestone 6 approved.** **Milestone 7 implemented (uncommitted); completion record in `docs/MILESTONE_7_RECORD.md`, pending owner approval.** Tasks are in priority order. Each milestone ends with a
completion record and an owner approval before the next milestone starts (IMPLEMENTATION_PLAN §5).
Effort figures are the plan's rough sizing, not commitments.

Gate status:

- **G-1** (verify tooling before any install): **Recorded**, see [docs/TOOLING_VERIFICATION.md](docs/TOOLING_VERIFICATION.md).
- **G-2** (publication checks): **Not complete.** The PyPI name `evalforge` is already in use by another project. See OPEN_DECISIONS OD-10.

## Before any code

1. Verify G-1 for Hatchling and uv. *Done.*
2. Confirm the copyright-year placeholder approach. *Used in M1 as `YEAR_OF_INITIAL_PUBLICATION`; not yet confirmed.*
3. Decide DCO enforcement method (OD-32). *Required before external contributions, not before M1.*
4. Decide the distribution name in light of the PyPI name conflict (OD-10). *Required before M16, not before M1.*
5. Decide OD-07 by M5, OD-11/12/21/22/27/30 by M7, OD-18 by M8, OD-09/13/28 by M9, OD-08 by M10, OD-25/26 by M11, OD-17/20/23/24 by M15.
6. Housekeeping: stale "Proposed — awaiting approval" status lines in `docs/PRD.md` and `docs/TRD.md`.

## Milestone 1: project foundation (about 1–3 days)

7. `pyproject.toml`: metadata, Apache-2.0, Python 3.11–3.13, Hatchling backend, zero runtime dependencies.
8. `src/evalforge/` layout with version-only `__init__.py` and `py.typed` marker.
9. `LICENSE`, `NOTICE`, `README.md` placeholder, `.gitignore` (includes `.evalforge/`), `CONTRIBUTING.md` (DCO requirement).
10. Short Apache-2.0 header on each source file, with the year placeholder.
11. uv environment and `uv.lock`.
12. ruff and `mypy --strict` configuration.
13. One smoke test and a dependency-list test.
14. CI skeleton: Linux, macOS, Windows × Python 3.11, 3.12, 3.13.

## Milestone 2: data models and validation (about 3–5 days)

15. Frozen dataclasses for case, config, manifest, case result, evaluator result, summary, comparison, finding.
16. Validation functions per model (no third-party validation library).
17. Canonical JSON serialisation and SHA-256 hashing.
18. Reason-code and error registries (DATA_MODELS §9).
19. Configuration validation: unknown-key and override-key rejection.
20. Limit constants (TRD §4.2).
21. Hand-written canonical-hash test vectors.

## Milestone 3: dataset loading

22. JSON and JSONL loaders with encoding, size, line-length, depth, and string limits.
23. Validator collecting up to 100 errors (file, line, field).
24. Duplicate-ID detection.
25. Synthetic fixture corpus, including malformed inputs.

## Milestone 4: target interface

26. Target protocol and callable adapter.
27. `module:attribute` reference resolution, documented as trusted-code loading.
28. Input deep copy; output-serialisability check.
29. Example adapter for interface conformance.

## Milestone 5: deterministic evaluators and registry

30. Six built-in evaluators: exact match, normalised text, JSON structure, required fields, rule-based, latency.
31. Custom evaluator interface and loading; fingerprints include the source-file hash.
32. Regex length limits.
33. Table-driven tests with hand-written expected values. Built-ins never return INCONCLUSIVE.

## Milestone 6: evaluation runner

34. Sequential case loop.
35. Best-effort worker-thread timeout with `threads_possibly_running` counter.
36. Case-status aggregation (one test per row of EVALUATION_METHODOLOGY §3.3).
37. Interrupt handling that finalises the run as ABORTED.
38. Engine-error boundary.

## Milestone 7: normalisation and persistence

39. Run directories with unique IDs, written atomically.
40. Exclusive lock file per run.
41. `io_mode` (`full`, `hashes`, `none`).
42. Redaction module: key-based and pattern-based, with counted replacements.
43. Tracebacks never stored; exception messages truncated and redacted.
44. Integrity hashes for `cases.jsonl` and `summary.json`.
45. Environment metadata limited to the approved set.
46. Wilson interval and nearest-rank percentiles, checked against independently derived values.
47. Windows file-replace and locking tests.

## Milestone 8: reporting

48. Terminal output with control-character sanitisation.
49. JSON reports with `schema_version`.
50. Hand-written JSON Schema files, validated by tests.
51. Golden-output fixtures.
52. Report footer (pending OD-18).
53. Banned-claims scan.

## Milestone 9: run comparison

54. Compatibility checks: dataset hash, evaluator fingerprints, schema version, run status, integrity.
55. Case categories: regressed, recovered, unchanged, changed, missing, new, changed_input.
56. Explicit override flags with banner, `compatibility.overrides`, and `COMPARISON_OVERRIDDEN` warning.
57. `--strict` mode.
58. Byte-identical output for identical inputs.

## Milestone 10: regression detection

59. Thresholds from the `[regression]` table.
60. Finding codes and golden messages.
61. Infrastructure errors never reported as `CASE_REGRESSED_TO_FAIL`.

## Milestone 11: CLI and Python API

62. `argparse` CLI with all commands in CLI_SPECIFICATION §3.
63. Exit codes 0–5 with precedence rules.
64. Public API surface with `__all__`.
65. CLI/API parity tests.
66. Executable documentation checks.

## Milestone 12: SQLite (deferred)

67. Not scheduled. Starts only with new approval (OD-05).

## Milestone 13: security hardening and isolation decision

68. Verify every threat in THREAT_MODEL with a passing test, or record an approved residual risk.
69. Static checks for forbidden constructs (`eval`, `exec`, `pickle`, unsafe YAML, `shell=True`).
70. Network-isolation test.
71. Dependency audit.
72. Written process-isolation reassessment (OD-06). **No isolation code in M13.**

## Milestone 14: integration and end-to-end tests

73. Quick start from a clean environment.
74. Seeded regression pair with expected findings.
75. Traceability check: every requirement covered by a test.
76. Documentation-to-model consistency check.

## Milestone 15: packaging and documentation

77. README: installation, quick start, limits.
78. API and CLI reference.
79. CI workflows: matrix, mypy, lint, tests, audit, build, and the `dco` job. **The DCO job must be running before external contributions are accepted (OD-31).**
80. Example GitHub Actions workflow that uploads summaries only (OD-23).
81. `CODE_OF_CONDUCT.md` (OD-17), `SECURITY.md` contact (OD-20), secret-scanner choice (OD-24).
82. Synthetic example datasets, each labelled as synthetic.

## Milestone 16: release readiness (no publication without approval)

83. Complete the release checklist with evidence.
84. Replace the copyright-year placeholder with the year of initial publication.
85. Complete G-2: package-index and trademark checks. **Resolve the PyPI name conflict first.**
86. Record residual risks RR-01 to RR-08 as accepted.
87. Prepare release notes and submit the decision request.

## Milestone 17: optional process isolation (only if approved after M13)

88. Opt-in isolation for `module:attribute` targets only.
89. JSON protocol over a pipe; fresh process per case; crash detection (`TARGET_CRASHED`).
90. Tests on all three operating systems.

## Ongoing

91. Record each approved change with its impact on milestones, tests, and security.
92. Report exact test results. Never claim a check passed unless it was run.
