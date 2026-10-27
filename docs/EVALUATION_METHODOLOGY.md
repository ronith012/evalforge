# EvalForge — Evaluation Methodology

Status: **Proposed — awaiting approval.**

This document defines what EvalForge measures, how it labels results, and what those
labels do and do not mean. It is the reference for statuses, aggregation, comparison
categories, and the limitations users must understand before trusting a number.

It does not claim that any score demonstrates that an AI system is safe, correct, or
reliable. See §12.

---

## 1. Purpose and principles

1. **Measure what is configured.** EvalForge reports results of the listed cases and
   evaluators only.
2. **Keep failures, errors, and unknowns apart.** A wrong answer, a crashed target, a
   crashed evaluator, and an undecidable case are different facts and are reported
   with different statuses.
3. **Preserve individual results.** Aggregates are derived from case results that
   remain on disk and in reports.
4. **Make comparisons traceable.** Every comparison names both runs and the
   fingerprints of the dataset and evaluators it used.
5. **Refuse meaningless comparisons.** Incompatible runs are not compared unless the
   user explicitly accepts the specific difference, and the output says so.

## 2. Evaluation approaches

| Approach | Description | MVP status | Determinism | Typical cost | Main limitation |
|---|---|---|---|---|---|
| **Deterministic** | Exact, normalized, structural, and rule checks computed by code | In MVP | Deterministic given the same output | Negligible | Cannot judge meaning or quality beyond what the rules encode |
| **Reference-based** | Output compared with `expected` value | In MVP (exact, normalized) | Deterministic | Negligible | Many correct answers differ from the reference; the reference may be wrong |
| **Rule-based** | Required fields, regex, substring, length bounds | In MVP | Deterministic | Negligible | Brittle; checks form, not truth |
| **Latency / performance** | Duration thresholds | In MVP | Environment-dependent | Negligible | Machine-dependent; noisy |
| **Custom code** | User-written Python evaluator | In MVP (trusted) | As deterministic as user code | User-defined | Quality depends on user code |
| **Model-based** | An LLM or classifier judges output | Post-MVP, optional | Non-deterministic unless constrained | Money, time, and data disclosure | Judge bias, drift, privacy (see §13) |
| **Human review** | People grade outputs | Not automated; supported via exported results | Subjective | Human time | Consistency between reviewers must be measured |

## 3. Status semantics

Each **evaluator result** has one of the following statuses. Each **case result** has
one status derived from its target result and its evaluator results (§3.3).

### 3.1 Definitions

| Status | Meaning | Counts as | Typical source |
|---|---|---|---|
| **PASS** | The evaluator ran and the output satisfies its check. | Pass | Evaluator check satisfied |
| **FAIL** | The evaluator ran successfully and the output does not satisfy its check. This is a judgement about the output. | Fail | Wrong value, missing field, rule violation, latency over threshold |
| **ERROR** | The evaluation could not be completed for reasons unrelated to the output's judged quality: target exception or timeout, invalid target output, evaluator exception, evaluator returned an invalid result. | Error (not pass, not fail) | `TARGET_EXCEPTION`, `TARGET_TIMEOUT`, `TARGET_OUTPUT_INVALID`, `EVALUATOR_EXCEPTION`, `EVALUATOR_RESULT_INVALID` |
| **SKIPPED** | The check was intentionally not executed. A reason code is required. | Neither | `NO_EXPECTED`, `USER_FILTER`, `TARGET_ERROR` (evaluators only), `NO_EVALUATORS`, `NOT_APPLICABLE` |
| **INCONCLUSIVE** | The evaluator ran but could not reach a verdict, without an error. Reported separately; never treated as PASS. | Inconclusive | Reserved for custom evaluators that explicitly report uncertainty, and for post-MVP model-based evaluators (for example, an unparseable judge reply). **MVP built-in evaluators never return INCONCLUSIVE.** |

Clarifications:

- **ERROR is not a quality verdict.** A timeout says nothing about whether the answer
  would have been good. Reports must not describe ERROR cases as failures of quality.
- **SKIPPED is not PASS.** A case with only skipped evaluators is not counted as a pass.
- **INCONCLUSIVE is not PASS and not FAIL.** Its handling in comparisons is governed by
  `inconclusive_as_regression` (§5).

### 3.2 Evaluator result precedence

Within one case, evaluator statuses are combined by §3.3. The order below is applied
top to bottom and the first matching rule wins.

### 3.3 Case status aggregation

| Order | Condition | Case status | Reason recorded |
|---|---|---|---|
| 1 | Target result is ERROR | ERROR | Target error code (for example `TARGET_TIMEOUT`); all evaluators recorded SKIPPED with reason `TARGET_ERROR` |
| 2 | No evaluators configured | SKIPPED | `NO_EVALUATORS` (configuration validation normally prevents this) |
| 3 | Any evaluator ERROR | ERROR | First evaluator error code |
| 4 | Any evaluator INCONCLUSIVE | INCONCLUSIVE | First inconclusive reason |
| 5 | Any evaluator FAIL | FAIL | First failing evaluator name |
| 6 | Every evaluator SKIPPED | SKIPPED | Reasons of the evaluators |
| 7 | Otherwise (at least one PASS, the rest PASS or SKIPPED) | PASS | — |

Notes:

- Rule 1 means a target error on one case cannot produce a FAIL.
- Rule 3 precedes rule 5: an evaluator error is never hidden by another evaluator's FAIL.
- Rule 6 with a non-skipped target output means every check was skipped (for example,
  all evaluators require `expected` and the case has none). This is reported
  explicitly rather than as PASS.

### 3.4 Run-level status

Run status (manifest) is separate from case status:

| Run status | Meaning |
|---|---|
| `RUNNING` | Run started; not finalized. |
| `COMPLETED` | Every selected case was attempted and recorded. Case outcomes may include FAIL and ERROR. |
| `ABORTED` | Run stopped by the user (for example Ctrl-C). Recorded cases are valid; remaining cases are absent and listed as not executed. Not comparable. |
| `FAILED` | Engine or storage fault stopped the run. Not comparable. |

A `COMPLETED` run with many ERRORs is still a completed run. The number of ERRORs is
reported; it is not a run-level failure.

### 3.5 Test-table requirement

Every row of §3.3 must have at least one unit test, and the test must assert the
reason recorded (see TEST_STRATEGY §4.5).

## 4. Evaluator limitations (documented per evaluator)

| Evaluator | What it checks | What it does not check | Known pitfalls |
|---|---|---|---|
| `exact_match` | Canonical JSON equality with `expected` | Meaning, paraphrase | A correct answer with extra whitespace or key order differences is handled by canonicalization, but different wording FAILs |
| `normalized_text` | Equality after Unicode NFC, case folding, whitespace collapse | Meaning, locale-specific rules, punctuation (unless configured) | `casefold` is not locale-aware; numbers written differently FAIL |
| `json_structure` | Output parses as JSON; optional top-level type | Field meaning, schema beyond top-level type | Output wrapped in markdown code fences FAILs; that is a real format violation |
| `required_fields` | Dotted-path fields exist and are non-null | Values, types, arrays | Presence ≠ correctness; no array indexing in MVP |
| `rule_based` | Substrings, regex, length | Semantics | Substring checks reward keyword stuffing; regex may be slow on adversarial patterns |
| `latency` | Duration ≤ threshold | Quality | Results vary by hardware and load; compare only on the same machine class |
| `custom` | Whatever the user codes | — | Trusted code; can be wrong |

**Text similarity is not semantic correctness.** Overlap metrics such as ROUGE or
BLEU are excluded from the MVP. If added later, they must be labelled as lexical
overlap and must never be presented as a correctness score.

## 5. Comparison categories

Compared at case level using the baseline status *B* and candidate status *C*.

| Category | Condition | Meaning |
|---|---|---|
| `regressed` | *B* = PASS and *C* ∈ {FAIL, ERROR, INCONCLUSIVE} | Previously passing case no longer passes. Sub-type recorded: `to_fail`, `to_error`, `to_inconclusive`. |
| `recovered` | *B* ∈ {FAIL, ERROR, INCONCLUSIVE} and *C* = PASS | Previously not passing case now passes. |
| `unchanged` | *B* = *C* | Same status. Output may still differ; output hash is reported. |
| `changed` | *B* ≠ *C* and not `regressed` or `recovered` | For example FAIL → ERROR, SKIPPED → PASS, or ERROR → FAIL. Reported, not counted as regression by default. |
| `missing_in_candidate` | Case ID in baseline only | Coverage reduction. Governed by `missing_case_policy`. |
| `new_in_candidate` | Case ID in candidate only | Coverage increase. Reported as info or warning. |
| `changed_input` | Same ID, different canonical case content, only with `--allow-dataset-change` | Not compared for status; reported. |

Decisions:

- **FAIL → ERROR is `changed`, not `regressed`.** It is a change in the failure mode,
  which may matter, so it appears in the report. Users who want it to gate CI can set
  thresholds (`max_newly_errored` applies only to PASS → ERROR under the current rules;
  see OD-13 for the alternative). *Open decision.*
- **Output-level categories depend on `io_mode`.** With `io_mode = none` in either run, only status-level categories are computed and `IO_UNAVAILABLE` is reported. With `io_mode = hashes`, output change is determined from `output_sha256` only (DATA_HANDLING §3.1).
- **PASS → ERROR is `regressed` with sub-type `to_error`.** It is a regression of
  availability, not of quality, and is reported as such.

## 6. Threshold selection

Thresholds in `[regression]` (TRD §9.1) are policy choices, not statistical results.

Guidance for users (documented, not enforced):

1. For deterministic targets, one newly failing case is a real change. The default
   `max_newly_failing = 0` expresses "no previously passing case may fail."
2. For non-deterministic targets, a pass-rate drop of a few percentage points may
   be noise. Set `max_pass_rate_drop` from observed variance across repeated baseline
   runs, not from intuition.
3. Set `min_executed_for_rate_check` high enough that the interval in §7 is narrow
   relative to the threshold. Small suites produce wide intervals.
4. Record why each threshold was chosen in the project's own documentation.

Proposed defaults are open decision OD-08.

## 7. Statistical uncertainty

### 7.1 Pass-rate interval

For `n` executed cases with `k` PASS, the reported pass rate is `p = k/n`. EvalForge
reports a 95% Wilson score interval:

```
center = (p + z²/(2n)) / (1 + z²/n)
half   = z · sqrt( p(1−p)/n + z²/(4n²) ) / (1 + z²/n)
interval = [center − half, center + half],  z = 1.959963984540054
```

Clipped to [0, 1]. Computed with the standard library `math` module. Test vectors are
hand-computed (TEST_STRATEGY §4.6).

### 7.2 What the interval does not mean

- It describes sampling uncertainty over the **chosen cases** only.
- It does not account for dataset bias, evaluator error, or target variance across runs.
- It is not a significance test. EvalForge does not claim that a difference is
  statistically significant in the MVP.

### 7.3 Two-run comparison

Two pass rates with overlapping intervals are not evidence of a difference. The
report displays both intervals when `PASS_RATE_DROP` is evaluated. A significance
test is post-MVP and would be an approved addition.

## 8. Variance and reproducibility

| Source of variance | EvalForge handling |
|---|---|
| Target non-determinism (sampling, network, time) | Not controlled. Recorded if the target exposes a seed. Users should repeat baseline runs to estimate variance. |
| Dataset order | Fixed: dataset order is preserved and recorded. |
| Timing (latency) | Measured per case; percentiles reported; environment recorded. |
| Evaluator code changes | Fingerprinted; comparison refused by default when changed (TRD-133). |
| Dataset changes | Canonical hash compared; refusal by default (TRD-132). |
| Python / OS differences | Recorded in manifest. Not normalized. |

Reproducibility claim (PRD-NF-002): for a deterministic target with identical dataset
and configuration, two runs produce identical case statuses, evaluator results, and
output hashes. The claim is verified by test, not assumed.

## 9. False positives and false negatives

Deterministic checks make both kinds of error:

| Evaluator | False positive (passes a bad output) | False negative (fails a good output) |
|---|---|---|
| `exact_match` | Rare; only if expected is itself wrong | Common: equivalent answers with different wording |
| `normalized_text` | Output that differs only in case or spacing from an incorrect expected value | Equivalent answers with different punctuation or numerals |
| `json_structure` | Well-formed JSON with wrong content | Valid JSON wrapped in prose or fences if format rules are strict |
| `required_fields` | Required fields present but with wrong values | Correct output that encodes the field at a different path |
| `rule_based` | Output containing the expected keyword while being wrong | Correct output that paraphrases the keyword |
| `latency` | None for quality | Slow machines fail fast cases |

Users should inspect a sample of PASS and FAIL cases (`evalforge inspect`) when adopting
a new evaluator. EvalForge provides no automatic false-positive estimate in the MVP.

## 10. Dataset quality, leakage, and overfitting

| Risk | Description | Mitigation in EvalForge | Mitigation for users |
|---|---|---|---|
| Low-quality cases | Ambiguous or wrong expected values | None automatic | Peer review of expected values; version datasets |
| Duplicates | Same case repeated, inflating counts | Duplicate ID detection (PRD-F-003) | Also check for duplicate inputs with different IDs (post-MVP check; not in MVP scope) |
| Leakage | Cases used to tune prompts then reported as held-out | None; EvalForge cannot know intent | Keep a held-out split; record which split each run used in metadata |
| Overfitting to the suite | Changes made to pass specific cases | Regression findings name cases, making overfitting visible | Add new cases rather than editing expected values to match outputs; track expected-value changes in version control |
| Contamination | Test inputs that appear in training data of a model under test | None | Documented as an external limitation |

Editing an `expected` value is a change to the dataset and changes its canonical hash.
EvalForge therefore makes such edits visible in comparisons.

## 11. Human review

- EvalForge does not provide a review workflow in the MVP.
- Users are encouraged to export case results (`report export`) and review a sample
  of PASS and FAIL cases.
- If human review is used to label cases, inter-rater agreement should be measured
  before its labels are used as ground truth. Measurement method: out of scope for the
  MVP; documented as a recommendation only.

## 12. Limitations of aggregate scores

- A pass rate is a count over the chosen cases, weighted equally. It does not reflect
  severity. Users who need severity weighting must add it in their own tooling or in
  a future approved feature.
- Averaging across evaluators is not performed in the MVP. Each evaluator's results
  are kept separately, which avoids hiding a failing check behind a passing aggregate.
- A high pass rate does not show that unseen inputs behave well.
- A regression report shows what changed on the chosen cases, not the cause.
- Reports must include the sentence in the report footer: "EvalForge reports results
  of the configured evaluators on the provided cases. These results do not establish
  that the system is safe, correct, or reliable in general." *(Exact wording to be
  approved; OD-18.)*

## 13. Model-based evaluation (post-MVP design constraints)

Not implemented in the MVP. If approved later, the following must be documented and
designed before implementation:

| Aspect | Requirement |
|---|---|
| Opt-in | Disabled by default. Enabled explicitly per evaluator in configuration. |
| Data disclosure | Case inputs and outputs sent to a judge are external data disclosure. The manifest must record the judge provider, model identifier, and that disclosure occurred. |
| Reproducibility | Judge model versions change over time. Record the exact identifier, parameters (temperature, seed where available), and prompt template hash. Results are non-deterministic unless the provider guarantees otherwise. |
| Cost | Record token counts and estimated cost when the provider reports them. Enforce a configurable maximum spend or call count. |
| Reliability | Measure judge agreement with a human-labelled sample before use. Report the measurement. Unparseable replies are INCONCLUSIVE, not PASS or FAIL. |
| Prompt injection | Case content can contain instructions aimed at the judge. Judge prompts must treat case content as data; this does not eliminate the risk (THREAT_MODEL THR-008). |
| Bias | Judges can favour verbose or stylistically similar outputs. Document; test with controlled examples. |
| Local option | Where feasible, a local model may be supported. Its quality and cost trade-offs must be documented. |

## 14. Glossary

- **Case:** One input, optional expected output, and metadata.
- **Target:** The application function under evaluation.
- **Evaluator:** A check that produces an evaluator result for a case.
- **Executed count:** PASS + FAIL + ERROR + INCONCLUSIVE.
- **Regression:** A case category or metric change that breaches a configured
  threshold. Not a claim about the cause.
