# Requirements Traceability Register

Status: **Milestone 14 register. Generated from the PRD and TRD; checked by `tests/test_traceability.py`.**

Every requirement ID in [PRD](PRD.md) and [TRD](TRD.md) is either cited by a test file (its ID appears in
`tests/`) or has a row below. The check fails for any ID with neither, for any status outside the list, and for
any test name in a *Verified* or *Partly* row that does not exist. A *Verified* or *Partly* row must name at least one test.

Requirements: 224. Cited by a test file: 34. Listed below: 190.

| Status | Count | Meaning |
|---|---|---|
| Verified | 118 | A named test checks the requirement. The test passes locally. |
| Partly | 14 | Some of the requirement is tested. The row says what is not. |
| Open | 19 | Not verified. No test exists. Each needs a test or an owner decision before release. |
| Deferred | 14 | Belongs to a later milestone (CI, packaging, release, or gate G-2). Not claimed as done. |
| Documented | 7 | Verified by a document or review, not by a test. |
| Not in MVP | 7 | Post-MVP feature. Not built. |
| Non-goal | 10 | Stated as out of scope. No test is required. |
| Not applicable | 1 | Nothing in the MVP falls under the requirement. |

## Register

Requirements already cited by a test file are not repeated here. Evidence lists test names; each is checked.

| ID | Status | Evidence or reason |
|---|---|---|
| PRD-F-001 | Verified | test_json_array_and_jsonl_with_the_same_cases_share_the_canonical_hash; test_case_count_and_order_follow_the_file |
| PRD-F-003 | Verified | test_duplicate_identifier_reports_both_locations |
| PRD-F-004 | Verified | test_metadata_and_tags_are_loaded; test_absent_expected_and_null_expected_are_distinct |
| PRD-F-006 | Verified | test_output_and_duration_are_recorded; test_stored_cases_match_the_in_memory_results |
| PRD-F-007 | Verified | test_target_exception_is_an_error_and_evaluators_are_skipped_with_target_error; test_non_serialisable_output_is_an_output_error; test_timed_out_target_is_recorded_and_the_run_continues |
| PRD-F-008 | Verified | test_exact_match_passes_on_canonically_equal_values |
| PRD-F-009 | Verified | test_normalized_text_ignores_case_and_whitespace_by_default |
| PRD-F-010 | Verified | test_json_structure_checks_the_top_level_type |
| PRD-F-011 | Verified | test_required_fields_reports_every_missing_path |
| PRD-F-012 | Verified | test_rule_contains_missing_names_the_rule |
| PRD-F-013 | Verified | test_latency_just_over_the_maximum_fails_with_details |
| PRD-F-014 | Verified | test_custom_evaluator_loads_by_reference |
| PRD-F-015 | Partly | test_complete_run_is_written_and_loads_with_integrity_ok; test_environment_metadata_is_minimal. The tool version is recorded; the full manifest field list is checked only partly. |
| PRD-F-016 | Verified | test_status_aggregation_table |
| PRD-F-017 | Verified | test_complete_run_is_written_and_loads_with_integrity_ok |
| PRD-F-018 | Verified | test_one_failing_evaluator_does_not_hide_a_later_passing_one; test_exception_is_recorded_for_its_case_and_the_next_case_still_runs |
| PRD-F-019 | Verified | test_each_status_transition_is_classified |
| PRD-F-020 | Verified | test_metrics_report_both_runs_and_the_delta |
| PRD-F-021 | Verified | test_changed_dataset_is_refused_by_default; test_changed_evaluator_definitions_are_refused_by_default |
| PRD-F-023 | Verified | test_exit_codes_match_the_specification |
| PRD-F-026 | Verified | test_inspect_case_detail_and_status_filter |
| PRD-F-027 | Verified | test_run_matches_the_api_in_counts; test_inspect_matches_the_api |
| PRD-F-029 | Verified | test_config_validate_reports_unknown_keys_with_exit_2 |
| PRD-F-030 | Partly | test_quick_start_from_a_clean_environment. The CI example workflow is Milestone 15. |
| PRD-F-101 | Not in MVP | Model-based evaluators (PRD-NG-001). |
| PRD-F-102 | Not in MVP | SQLite persistence is deferred (OD-05; Milestone 12). |
| PRD-F-103 | Not in MVP | Markdown export is post-MVP. |
| PRD-F-104 | Not in MVP | Parallel execution is post-MVP (TRD-100). |
| PRD-F-105 | Not in MVP | Process isolation is post-MVP (OD-06; PROCESS_ISOLATION_REASSESSMENT). |
| PRD-F-106 | Not in MVP | JSON Schema evaluator is not in MVP (OD-07). |
| PRD-F-107 | Not in MVP | Dataset registry is post-MVP. |
| PRD-G-002 | Verified | test_hashes_in_the_manifest_match_the_files; test_the_comparison_record_names_both_runs |
| PRD-G-003 | Verified | test_changed_dataset_is_refused_by_default; test_every_refusal_is_listed_not_only_the_first |
| PRD-G-004 | Verified | test_core_source_has_no_network_modules; test_quick_start_completes_with_sockets_disabled |
| PRD-G-005 | Verified | test_every_name_in_the_api_surface_table_is_exported |
| PRD-NF-002 | Verified | test_output_is_identical_apart_from_the_comparison_id_and_timestamp |
| PRD-NF-003 | Verified | test_dataset_strings_are_never_executed |
| PRD-NF-004 | Open | Linux and Windows have not been run. CI matrix is Milestone 15. |
| PRD-NF-005 | Partly | test_python_versions_match_approved_support checks the declared range. Tests pass locally on 3.11, 3.12 and 3.13; CI is Milestone 15. |
| PRD-NF-007 | Open | Performance targets (TRD-220 to TRD-223) are not measured. |
| PRD-NF-008 | Partly | test_case_result_accepts_a_consistent_record. Run ID and dataset hash in each stored case are not checked by a dedicated test. |
| PRD-NF-009 | Verified | test_unsupported_schema_major_is_refused; test_newer_minor_version_is_accepted |
| PRD-NF-011 | Open | No logging is implemented (TRD-190 to TRD-194 are open). |
| PRD-NF-012 | Deferred | Licence and notice checks in built artifacts are Milestone 15 and 16 (TST-E2E-005). |
| PRD-NF-014 | Verified | test_io_hashes_stores_no_content; test_io_none_stores_neither_content_nor_io_hashes |
| PRD-NF-015 | Verified | test_integrity_scope_table_matches_the_manifest_hash_fields |
| PRD-NF-016 | Documented | docs/PROCESS_ISOLATION_REASSESSMENT.md §1; TRD-072 wording. Overclaim wording is checked by test_user_facing_text_contains_no_banned_claims. |
| PRD-NG-001 | Non-goal | No model-based evaluators (THREAT_MODEL THR-017 not in MVP). |
| PRD-NG-002 | Non-goal | No hosted service or dashboard. |
| PRD-NG-003 | Non-goal | No dataset generation. |
| PRD-NG-004 | Verified | Dataset content is never executed: test_dataset_strings_are_never_executed. |
| PRD-NG-005 | Non-goal | No sandboxing of custom evaluators or targets. Trust model in SECURITY §10.1. |
| PRD-NG-006 | Verified | Overclaim wording: test_user_facing_text_contains_no_banned_claims; footer test_footer_appears_exactly_once. |
| PRD-NG-007 | Non-goal | No significance testing beyond intervals. |
| PRD-NG-008 | Non-goal | No distributed execution. |
| PRD-NG-009 | Non-goal | No semantic similarity metrics. |
| PRD-NG-010 | Non-goal | No provider integrations. |
| PRD-NG-011 | Non-goal | No release automation without approval. |
| PRD-NG-012 | Non-goal | No process isolation in MVP (see OD-06 reassessment). |
| PRD-NG-013 | Verified | Redaction limits: test_documented_miss_credential_in_an_unlisted_format_is_not_redacted. |
| PRD-US-001 | Verified | test_case_count_and_order_follow_the_file |
| PRD-US-002 | Verified | test_error_reports_file_line_and_field |
| PRD-US-003 | Verified | test_reference_resolves_a_function |
| PRD-US-004 | Verified | test_target_exception_is_an_error_and_evaluators_are_skipped_with_target_error |
| PRD-US-005 | Verified | test_exact_match_passes_on_canonically_equal_values; test_rule_contains_missing_names_the_rule |
| PRD-US-006 | Verified | test_complete_run_is_written_and_loads_with_integrity_ok |
| PRD-US-007 | Verified | test_each_status_transition_is_classified |
| PRD-US-008 | Verified | test_compare_regression_exits_1 |
| PRD-US-009 | Verified | test_run_summary_shows_counts_rate_and_integrity |
| PRD-US-010 | Verified | test_custom_evaluator_loads_by_reference |
| TRD-001 | Partly | test_python_versions_match_approved_support; tests pass locally on 3.11, 3.12 and 3.13. CI matrix is Milestone 15. |
| TRD-002 | Open | Linux and Windows have not been run. CI is Milestone 15. |
| TRD-004 | Open | Windows path and newline behaviour has not been tested. |
| TRD-010 | Deferred | Build job (sdist and wheel) is Milestone 15. |
| TRD-011 | Deferred | Licence and notice in built artifacts: Milestones 15 and 16. |
| TRD-012 | Verified | test_package_ships_the_typed_marker (the package is under src/evalforge) |
| TRD-013 | Open | The console script is declared in pyproject.toml and runs (checked by hand: `evalforge --version`). No automated test. |
| TRD-014 | Deferred | Package name check is gate G-2 (OD-10), Milestone 16. |
| TRD-015 | Deferred | Clean-environment install of the wheel: Milestone 15 (TST-E2E-004). |
| TRD-020 | Deferred | uv.lock is committed and used locally. The CI install from the lock file is Milestone 15. |
| TRD-021 | Deferred | CI installs and resolved-version logging: Milestone 15. |
| TRD-022 | Deferred | Licence review before release: Milestone 16 checklist. |
| TRD-023 | Deferred | pip-audit was run locally with no known vulnerabilities (MILESTONE_13_RECORD). The CI audit job is Milestone 15. |
| TRD-024 | Deferred | mypy --strict was run locally and passes. The CI gate is Milestone 15. |
| TRD-025 | Documented | docs/TOOLING_VERIFICATION.md (G-1) records the Hatchling and uv checks. |
| TRD-026 | Deferred | No publication without gate G-2 (Milestone 16). |
| TRD-030 | Verified | test_leading_byte_order_mark_is_accepted_and_changes_only_the_raw_hash; test_utf16_input_is_rejected_as_an_encoding_error |
| TRD-031 | Verified | test_blank_lines_are_ignored |
| TRD-032 | Verified | test_empty_json_array_is_an_empty_valid_dataset; test_top_level_json_object_is_rejected |
| TRD-033 | Verified | test_unsupported_extension_is_rejected |
| TRD-034 | Verified | test_non_finite_numbers_are_rejected |
| TRD-040 | Verified | test_api_run_does_not_execute_an_invalid_dataset |
| TRD-041 | Verified | test_valid_case_ids; test_invalid_case_ids |
| TRD-042 | Verified | test_duplicate_identifier_reports_both_locations |
| TRD-043 | Verified | test_unknown_key_is_rejected_with_its_name |
| TRD-044 | Verified | test_absent_expected_and_null_expected_are_distinct |
| TRD-045 | Verified | test_metadata_that_is_not_an_object_is_rejected |
| TRD-046 | Verified | test_tags_must_be_a_list; test_duplicate_tags_are_rejected |
| TRD-047 | Verified | test_errors_are_collected_in_file_order_and_capped_at_one_hundred |
| TRD-048 | Verified | test_error_reports_file_line_and_field |
| TRD-050 | Verified | test_whitespace_changes_the_raw_hash_but_not_the_canonical_hash |
| TRD-051 | Verified | test_json_array_and_jsonl_with_the_same_cases_share_the_canonical_hash |
| TRD-052 | Verified | test_raw_byte_change_with_identical_cases_is_information_only |
| TRD-060 | Verified | test_callable_is_invoked_with_the_case_input; test_callable_target_type_is_the_adapter |
| TRD-061 | Verified | test_reference_resolves_a_function; test_unknown_module_is_a_load_error |
| TRD-062 | Verified | test_non_serialisable_output_is_an_output_error |
| TRD-064 | Verified | test_target_cannot_change_the_stored_input |
| TRD-070 | Verified | test_timeout_bounds_are_enforced; test_a_target_timeout_overrides_the_run_timeout |
| TRD-071 | Verified | test_timed_out_target_is_recorded_and_the_run_continues |
| TRD-072 | Documented | Wording in PROCESS_ISOLATION_REASSESSMENT §1 and runner docstrings. |
| TRD-073 | Documented | RR-02 in RESIDUAL_RISK_ACCEPTANCE; PROCESS_ISOLATION_REASSESSMENT §2. |
| TRD-074 | Documented | PROCESS_ISOLATION_REASSESSMENT (written decision, Milestone 13). |
| TRD-075 | Partly | test_timed_out_thread_is_counted_as_possibly_running checks the counter. The warning in the terminal summary is not tested. |
| TRD-076 | Documented | SECURITY §10.1; RR-01. |
| TRD-080 | Verified | test_missing_expected_is_skipped_and_evaluate_is_not_called; test_registry_builds_a_custom_evaluator_from_configuration |
| TRD-081 | Partly | test_custom_mutation_does_not_change_the_stored_output. Purity of evaluators is not enforced. |
| TRD-082 | Verified | test_evaluator_pass_must_not_carry_a_reason; test_evaluator_score_must_be_in_unit_interval; test_evaluator_message_is_bounded |
| TRD-083 | Verified | test_missing_expected_is_skipped_and_evaluate_is_not_called |
| TRD-084 | Verified | test_custom_exception_is_an_error_and_is_named; test_custom_non_result_return_is_an_invalid_result |
| TRD-085 | Verified | test_custom_fingerprint_includes_the_source_file_hash; test_builtin_fingerprint_is_stable_and_parameter_sensitive |
| TRD-090 | Verified | test_regex_longer_than_the_limit_is_rejected |
| TRD-091 | Verified | test_regex_over_the_input_cap_is_an_error_not_a_fail |
| TRD-092 | Documented | docs/REGEX_REVIEW.md. |
| TRD-102 | Open | The per-line flush of cases.jsonl is not tested. |
| TRD-103 | Verified | test_interruption_with_grace_completion_records_the_case_and_aborts; test_interruption_without_grace_completion_drops_the_case |
| TRD-105 | Open | Seed recording for targets is not implemented. |
| TRD-106 | Verified | test_environment_metadata_is_minimal |
| TRD-110 | Verified | test_run_directory_is_named_by_a_uuid_under_the_root |
| TRD-112 | Verified | test_replacing_the_manifest_is_atomic_and_leaves_no_partial_files; test_crash_leaves_the_manifest_running_and_is_reported_incomplete |
| TRD-113 | Verified | test_summary_write_failure_keeps_the_cases_and_marks_failed |
| TRD-114 | Verified | test_hashes_in_the_manifest_match_the_files |
| TRD-115 | Verified | test_unsupported_schema_major_is_refused |
| TRD-116 | Verified | test_environment_metadata_is_minimal; test_target_exception_stores_type_and_message_only |
| TRD-117 | Partly | The CLI always persists (test_run_stores_the_run_and_exits_0). The in-memory API flag `persisted: false` in the manifest is not implemented. |
| TRD-118 | Verified | test_io_full_stores_content_and_hashes; test_io_hashes_stores_no_content; test_io_none_stores_neither_content_nor_io_hashes |
| TRD-119 | Verified | test_integrity_scope_table_matches_the_manifest_hash_fields |
| TRD-120 | Verified | test_two_runs_in_one_root_do_not_interfere |
| TRD-121 | Verified | test_second_writer_on_a_locked_run_directory_fails |
| TRD-122 | Verified | test_stale_lock_is_reported_and_blocks_a_second_writer |
| TRD-130 | Verified | test_incomplete_run_is_refused |
| TRD-131 | Partly | The reader rejects unsupported majors (test_unsupported_schema_major_is_refused) before a comparison. No comparison-level test. |
| TRD-132 | Verified | test_changed_dataset_is_refused_by_default; test_allowed_dataset_change_is_an_override_with_a_warning |
| TRD-133 | Verified | test_changed_evaluator_definitions_are_refused_by_default; test_allowed_evaluator_change_is_an_override |
| TRD-135 | Verified | test_every_refusal_is_listed_not_only_the_first |
| TRD-136 | Verified | test_override_flags_cannot_be_set_in_configuration |
| TRD-138 | Verified | test_strict_refuses_an_overridden_comparison |
| TRD-143 | Verified | test_latency_ratio_above_the_maximum_is_a_finding; test_latency_check_is_skipped_when_the_baseline_p95_is_missing_or_zero |
| TRD-150 | Verified | test_footer_appears_exactly_once |
| TRD-151 | Partly | Interval and sample size are reported (test_summary_pass_rate_and_interval_match_the_counts). The threshold guidance is documentation. |
| TRD-160 | Open | Commands accept --help through argparse, which no test checks. --no-color is not implemented. |
| TRD-163 | Verified | test_control_and_bidi_characters_are_shown_as_escapes; test_terminal_output_has_no_raw_escape_or_bidi_characters |
| TRD-164 | Partly | test_config_validate_json_failure_is_one_json_document; diagnostics on stderr are not tested for every command. |
| TRD-165 | Verified | test_no_command_is_a_usage_error |
| TRD-170 | Verified | test_package_exports_the_public_operations |
| TRD-172 | Verified | test_case_metadata_is_read_only |
| TRD-174 | Verified | test_run_matches_the_api_in_counts; test_compare_text_matches_the_shared_renderer |
| TRD-180 | Verified | test_load_config_file_reads_toml_and_records_directory |
| TRD-181 | Verified | test_missing_schema_version_is_an_error |
| TRD-185 | Verified | test_configuration_snapshot_uses_portable_paths; test_configuration_secret_values_become_redacted_and_are_counted |
| TRD-186 | Verified | test_invalid_io_mode_is_rejected; test_redaction_disabled_is_recorded_in_the_manifest |
| TRD-190 | Open | Logging is not implemented. |
| TRD-191 | Open | Logging is not implemented. |
| TRD-192 | Open | Logging is not implemented. No case content appears in any output other than the requested one (test_progress_on_stderr_never_shows_case_inputs). |
| TRD-193 | Open | Logging is not implemented. |
| TRD-194 | Open | Logging is not implemented. |
| TRD-203 | Verified | test_disk_full_during_append_finalises_the_run_as_failed; test_crash_leaves_the_manifest_running_and_is_reported_incomplete |
| TRD-210 | Verified | test_yaml_tags_and_pickle_like_text_load_as_plain_strings |
| TRD-211 | Verified | test_file_size_at_the_limit_is_accepted_and_one_byte_over_is_rejected; test_nesting_beyond_the_limit_is_rejected |
| TRD-213 | Verified | test_case_ids_with_traversal_are_rejected |
| TRD-214 | Verified | test_symlinked_dataset_warns_and_is_read_only |
| TRD-215 | Verified | test_quick_start_completes_with_sockets_disabled; test_core_source_has_no_network_modules |
| TRD-217 | Partly | test_dataset_strings_are_never_executed shows datasets do not import. Custom evaluators and targets are loaded only by configuration or API (code review). |
| TRD-218 | Partly | test_planted_secret_in_target_error_is_redacted_on_disk_but_not_in_memory; evaluator message redaction is not separately tested. |
| TRD-219 | Verified | test_built_in_messages_never_echo_case_content |
| TRD-220 | Open | Performance target not measured. |
| TRD-221 | Open | Performance target not measured. |
| TRD-222 | Open | Performance target not measured. |
| TRD-223 | Open | Memory budget not measured; the dataset streams line by line in the reader. |
| TRD-230 | Verified | test_builtin_fingerprint_is_stable_and_parameter_sensitive; test_rule_length_bounds_are_inclusive |
| TRD-231 | Verified | test_quick_start_from_a_clean_environment; test_seeded_regression_pair_produces_the_expected_findings |
| TRD-232 | Verified | test_quick_start_from_a_clean_environment |
| TRD-233 | Verified | test_run_matches_the_api_in_counts; test_compare_matches_the_api |
| TRD-234 | Verified | test_seeded_malformed_corpus_raises_only_validation_errors; test_dataset_strings_are_never_executed |
| TRD-235 | Partly | test_canonical_hash_matches_independent_reference uses an independent expected value. The rule is applied by review. |
| TRD-236 | Open | Coverage is not measured or reported. |
| TRD-237 | Deferred | Tests on Linux, macOS and Windows in CI: Milestone 15. |
| TRD-240 | Deferred | Versioning policy and CHANGELOG: Milestone 15. |
| TRD-241 | Verified | test_newer_minor_version_is_accepted |
| TRD-242 | Deferred | Stability promise applies from 1.0. |
| TRD-243 | Not applicable | No fields are deprecated yet. |
