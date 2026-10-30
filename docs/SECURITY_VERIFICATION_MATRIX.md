# Security Verification Matrix

Status: **Milestone 13 working record. Verified by tests on the local machine; not yet verified in CI.**
Every threat in [THREAT_MODEL](THREAT_MODEL.md) §3 appears here. Each row names the tests that check the
control, or states that the threat is not in scope for the MVP, or links to a residual risk
([RESIDUAL_RISK_ACCEPTANCE](RESIDUAL_RISK_ACCEPTANCE.md)). A test that is named here must exist.
`tests/test_security.py::test_every_test_named_in_the_matrix_exists` checks this.

Status values: **Verified** (tests pass locally), **Partly** (control verified, a documented limit remains),
**Pending** (depends on a later milestone), **Not in MVP**.

| ID | Threat | Control (short) | Tests | Status | Residual |
|---|---|---|---|---|---|
| THR-001 | Dataset content executed as code | No `eval`/`exec`/`pickle`/unsafe YAML; JSON only | test_no_code_execution_primitives_in_source, test_no_unsafe_deserialisation_or_process_modules_in_source, test_dataset_strings_are_never_executed, test_yaml_tags_and_pickle_like_text_load_as_plain_strings | Verified | Low |
| THR-002 | Malformed input crashes or is misread | Strict decoding, depth and size limits, error collection | test_seeded_malformed_corpus_raises_only_validation_errors, test_nesting_beyond_the_limit_is_rejected, test_file_size_at_the_limit_is_accepted_and_one_byte_over_is_rejected | Verified | Low |
| THR-003 | Regex denial of service | Pattern length limit; nested-repeat guard; input cap (D-5) | test_regex_pattern_length_is_limited, test_nested_repeat_patterns_are_refused_at_configuration, test_ordinary_patterns_are_accepted, test_rule_based_input_is_capped_before_matching | Partly: the guard is a heuristic; overlapping alternations are not caught | Medium (RR-03) |
| THR-004 | Configuration causes import of module code | `config validate` does not import unless asked; trusted-code documentation | test_config_validate_does_not_import_the_target | Partly: `run` and `--check-imports` import by design | Accepted by design (RR-01) |
| THR-005 | Symlinks cause unintended reads or writes | Symlink warning; reads only | test_symlinked_dataset_warns_and_is_read_only | Verified | Low–Medium |
| THR-006 | Oversized inputs exhaust resources | File, line, case, string, and nesting limits at boundary and boundary+1 | test_file_size_at_the_limit_is_accepted_and_one_byte_over_is_rejected, test_line_length_at_the_limit_is_accepted_and_one_over_is_rejected, test_case_count_at_the_limit_is_accepted_and_one_over_is_rejected, test_string_length_at_the_limit_is_accepted_and_one_over_is_rejected | Verified | Low |
| THR-007 | Path traversal through IDs or references | Case IDs never used as file names; UUID run directories; run references must be plain names or existing run directories | test_case_ids_with_traversal_are_rejected, test_run_directory_is_named_by_a_uuid_under_the_root, test_run_reference_outside_the_root_is_refused | Verified (a defect was found and fixed in `resolve_run` during this milestone) | Low |
| THR-008 | Prompt injection in judges | No model-based evaluator in the MVP | — | Not in MVP | — |
| THR-009 | Terminal escape injection | Sanitisation of control and bidi characters in text output | test_control_and_bidi_characters_are_shown_as_escapes, test_terminal_output_has_no_raw_escape_or_bidi_characters, test_json_report_keeps_hostile_text_as_valid_json_escapes | Verified | Low |
| THR-010 | Timeouts do not isolate targets | Best-effort thread timeout; `threads_possibly_running` counted; per-target timeout | test_timed_out_target_is_recorded_and_the_run_continues, test_timed_out_thread_is_counted_as_possibly_running, test_a_target_timeout_overrides_the_run_timeout | Verified as documented; isolation not in MVP (OD-06) | **High** (RR-02) |
| THR-011 | Secrets captured into snapshots, manifests, logs, messages | Key and pattern redaction; secret-like keys removed from configuration snapshots; unknown config keys do not echo values | test_planted_secret_in_target_output_is_not_stored_in_clear, test_unknown_config_key_does_not_echo_its_value, test_each_listed_credential_prefix_is_replaced_and_counted, test_documented_miss_credential_in_an_unlisted_format_is_not_redacted | Partly: heuristic (DATA_HANDLING §7.4) | Medium (RR-05) |
| THR-012 | Sensitive I/O exposed through artifacts and reports | `io_mode` choices; default export and listing exclude I/O | test_default_export_has_no_case_input_or_output, test_inspect_listing_hides_case_io_without_show_io, test_io_hashes_stores_no_content, test_io_none_stores_neither_content_nor_io_hashes | Verified | Medium (RR-06) |
| THR-013 | Local artifacts modified after the run | Hashes of `cases.jsonl` and `summary.json`, checked on read | test_tampered_cases_file_is_an_integrity_error, test_one_changed_byte_in_cases_is_detected, test_rewriting_cases_and_recomputing_the_hash_is_not_detected | Partly: deliberate rewrite is not detected | Medium (RR-04) |
| THR-014 | Vulnerable dependencies | Zero runtime dependencies; development audit | test_runtime_dependencies_are_empty; audit run recorded in MILESTONE_13_RECORD | Partly: audit run locally; CI audit job pending M15 | Medium (RR-08) |
| THR-015 | Compromised build or release pipeline | Release checklist; name and tooling verification | — | Pending (M15, M16) | Medium |
| THR-016 | Unexpected network requests | No network modules in core; quick start runs with sockets disabled | test_core_source_has_no_network_modules, test_quick_start_completes_with_sockets_disabled | Verified | Low |
| THR-017 | External provider receives case data | No model-based evaluator in the MVP | — | Not in MVP | — |
| THR-018 | Concurrent writers corrupt a run | Exclusive lock; unique run directories | test_second_writer_on_a_locked_run_directory_fails, test_stale_lock_is_reported_and_blocks_a_second_writer, test_a_run_directory_is_never_reused | Verified | Low |
| THR-019 | Overclaiming | Approved footer; banned-claims scan of source and README | test_user_facing_text_contains_no_banned_claims, test_footer_uses_only_negated_forms_of_banned_claims | Partly: the scan checks the listed phrases only | Medium (RR-07) |
| THR-020 | Evaluation gaming | Canonical hash; comparison refuses changed datasets | test_changed_dataset_is_refused_by_default, test_canonical_hash_matches_independent_reference | Partly: intent cannot be detected | Medium |
| THR-021 | Exceptions and tracebacks leak data | No tracebacks stored; type and truncated message only; unexpected faults print the type only | test_cli_never_prints_unexpected_fault_detail, test_target_exception_stores_type_and_message_only, test_planted_secret_in_target_error_is_redacted_on_disk_but_not_in_memory | Verified | Medium (RR-05) |
| THR-022 | Environment metadata identifies the machine | Minimal environment record | test_environment_metadata_is_minimal | Verified | Low |
| THR-023 | Incompatible comparison or hidden override | Refusal by default; overrides recorded and shown; `--strict` | test_changed_dataset_is_refused_by_default, test_compare_allowed_override_is_shown_and_strict_refuses_it, test_strict_refuses_an_overridden_comparison | Verified | Medium (a CI script can still choose not to use `--strict`) |

## Notes

- The threat model's verification column names tests that were planned in TEST_STRATEGY §4.8. Where a planned test
  is covered by a different test with the same intent, this matrix names the test that exists. Planned names that
  do not exist are listed in MILESTONE_13_RECORD.
- Static checks in `tests/test_security.py` read `src/evalforge` only. They do not prove the absence of code paths
  that are never parsed.
