# Residual Risks for Written Acceptance (RR-01 to RR-08)

Status: **Presented for decision. Not accepted.** The acceptance fields are blank and must be completed by the owner
before release (THREAT_MODEL §6; RELEASE_CHECKLIST). The evidence column names what is verified today and what is
not.

| ID | Residual risk | Evidence today | Open items | Severity (threat model) |
|---|---|---|---|---|
| RR-01 | Targets and custom evaluators run unsandboxed, with the user's privileges | Documented as trusted code; configuration reading does not import by default (`test_config_validate_does_not_import_the_target`); datasets never trigger imports (`test_dataset_strings_are_never_executed`) | None in code; a user who runs untrusted targets is outside the design | High |
| RR-02 | Timeouts are best-effort; a timed-out thread cannot be stopped | `test_timed_out_target_is_recorded_and_the_run_continues`; `test_timed_out_thread_is_counted_as_possibly_running`; reassessment in PROCESS_ISOLATION_REASSESSMENT | Isolation not in MVP (OD-06 decision needed) | High |
| RR-03 | Regex matching can be very slow | Measured exponential growth (REGEX_REVIEW §2.1); nested-repeat guard added (`test_nested_repeat_patterns_are_refused_at_configuration`) | The guard is partial; overlapping alternations are not caught; no timeout for `re` | Medium |
| RR-04 | Artifacts can be rewritten by a party with write access, including hashes | `test_one_changed_byte_in_cases_is_detected`; `test_rewriting_cases_and_recomputing_the_hash_is_not_detected` (documented miss) | No signing (OD-29 deferred); CI retention outside the project | Medium |
| RR-05 | Redaction is heuristic; exception text may contain sensitive data | Pattern and key redaction (`test_each_listed_credential_prefix_is_replaced_and_counted`); target exception text redacted on disk (`test_planted_secret_in_target_error_is_redacted_on_disk_but_not_in_memory`); documented misses (`test_documented_miss_*`) | Unlisted credential formats and unrecognised keys are not redacted; OD-21 applied | Medium |
| RR-06 | Users may store sensitive data in run artifacts | `io_mode` choices; default export and listings exclude I/O (`test_default_export_has_no_case_input_or_output`); `test_io_none_stores_neither_content_nor_io_hashes` | Depends on user choices; documentation in DATA_HANDLING | Medium |
| RR-07 | Users may overclaim evaluation results | Approved footer on reports (`test_footer_appears_exactly_once`); banned-claims scan of source and README (`test_user_facing_text_contains_no_banned_claims`) | The scan checks listed phrases only; user behaviour is outside the tool | Medium |
| RR-08 | Dependencies may gain vulnerabilities after release | `test_runtime_dependencies_are_empty` (no runtime dependencies); pip-audit run locally with no known vulnerabilities (MILESTONE_13_RECORD) | Audit not yet in CI (M15); development tools and Python itself are outside the runtime set | Medium |

## Acceptance

Each risk needs a decision. Leave a risk open until it is decided.

| ID | Decision (Accept / Reject / Mitigate first) | Accepted by (name) | Date | Notes |
|---|---|---|---|---|
| RR-01 |  |  |  |  |
| RR-02 |  |  |  |  |
| RR-03 |  |  |  |  |
| RR-04 |  |  |  |  |
| RR-05 |  |  |  |  |
| RR-06 |  |  |  |  |
| RR-07 |  |  |  |  |
| RR-08 |  |  |  |  |

Release (Milestone 16) cannot proceed while any row is blank. RR-02 and RR-01 are rated High; the owner should decide
them explicitly.
