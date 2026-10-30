# Changelog

All notable changes are recorded here. The project is pre-alpha; no release has been published.
Version numbers follow the policy in TRD-240 once a release is approved.

## Unreleased

### Added

- Dataset loading and validation for JSON and JSONL, with limits and structured errors (Milestones 3, 5).
- Target interface, timeouts, and the evaluation runner, with the built-in evaluators (Milestones 4 to 6).
- Run storage with integrity hashes, a lock file, and a reader (Milestone 7).
- Text and JSON reports, with a fixed footer on every summary (Milestone 8).
- Run comparison with refusals and explicit overrides (Milestone 9).
- Regression findings with the `[regression]` thresholds (Milestone 10).
- The `evalforge` command line and the Python API (Milestone 11), including progress lines, comparison
  text export, per-target timeouts, and the object-level API (`Suite`, `Run`, `Dataset.from_cases`).
- Security verification: static checks, a network-disabled run, a seeded malformed-input corpus, and a
  verification matrix (Milestone 13). Regex guard for nested repeats.
- End-to-end tests, a seeded regression pair with an expected findings manifest, a requirements
  traceability register, and documentation checks (Milestone 14).
- Packaging checks, a CI workflow with audit, build, DCO, and secret-scan jobs, and synthetic examples
  (Milestone 15).

### Changed

- `run_cases` takes an optional progress callback and honours a per-target timeout.
- `resolve_run` accepts run IDs as plain names only. A reference that reaches outside the run root is
  refused (found during Milestone 13).
- The comparison exit status is `pass`, `regression`, or `refused`.

### Security

- Run references containing path separators or `..` are refused (threat THR-007).
- Nested repeated groups in rule-based regex patterns are refused at configuration time (threat THR-003;
  partial mitigation, see docs/REGEX_REVIEW.md).

### Known limitations

- Targets and custom evaluators are trusted code and are not sandboxed (RR-01).
- Timeouts are best-effort; a timed-out target is not stopped (RR-02).
- Regular-expression matching has no timeout; nested repeats are refused, other slow patterns are not (RR-03).
- Stored artifacts can be rewritten by anyone with write access; the hashes detect accidental change only (RR-04).
- Redaction is heuristic; exception text is redacted on disk but not in memory (RR-05).
- Results are not safety or correctness certifications.

