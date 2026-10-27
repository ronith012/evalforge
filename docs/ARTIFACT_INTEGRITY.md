# EvalForge — Artifact Integrity

Status: **Proposed — awaiting approval.** Describes what the hashes in run artifacts
cover, what they do not cover, and the limits of storing hashes next to the data they
protect. Not implemented or tested.

Related: [DATA_HANDLING](DATA_HANDLING.md) §3 (I/O modes), [THREAT_MODEL](THREAT_MODEL.md)
THR-013, [DATA_MODELS](DATA_MODELS.md) §6–§7, [TRD](TRD.md) §4.4 and §7.1.

---

## 1. Summary

- EvalForge stores SHA-256 hashes inside run artifacts. They detect **accidental
  corruption** and **unsophisticated edits** to the files they cover.
- They do **not** provide authenticity. Anyone who can write to a run directory can
  also rewrite the hashes, so a determined or careful modification is not detected.
- Comparisons are blocked by default when the compared runs are incompatible. Overrides
  are explicit and recorded in the output (see §6).

## 2. Hashes that exist

| Hash | Stored in | Computed over | Used for |
|---|---|---|---|
| `dataset.sha256` | `manifest.json` | Exact bytes of the dataset file as read | Traceability; reported in comparisons |
| `dataset.canonical_sha256` | `manifest.json` | Canonical JSON of the parsed case list in file order (TRD §4.4) | Dataset compatibility checks (TRD-132) |
| `case_sha256` | each line of `cases.jsonl` | Canonical JSON of `{id, input, expected?, metadata, tags}` | Detecting changed case content between runs (`changed_input`) |
| `input_sha256` | each case result, when `io_mode` is `full` or `hashes` | Canonical JSON of the input value as passed to the target | Traceability; not used for compatibility |
| `expected_sha256` | each case result, when `io_mode` is `full` or `hashes` and `expected` present | Canonical JSON of `expected` | Traceability |
| `output_sha256` | each case result, when the target produced output and `io_mode` is `full` or `hashes` | Canonical JSON of the output value **as returned by the target, before redaction** | Output-change detection between runs (`output_changed`) |
| `evaluator fingerprint` | `manifest.json` (per evaluator) | Built-in: type and parameters; custom: module, qualname, declared version, SHA-256 of source file (TRD-085) | Evaluator compatibility checks (TRD-133) |
| `cases_sha256` | `manifest.json` | **Exact bytes of `cases.jsonl`** as finalized | Integrity check (§4) |
| `summary_sha256` | `manifest.json` | **Exact bytes of `summary.json`** as finalized | Integrity check (§4) |

Canonical JSON is defined in TRD §4.4. Output hashes are computed before redaction. This
means a stored, redacted output does not match its `output_sha256` if someone recomputes
the hash from the stored text. That is intentional, and it is documented so that no one
assumes stored content can be re-hashed to verify the hash.

## 3. What the file hashes cover precisely

`cases_sha256` covers every byte of `cases.jsonl`: each line's content, line order, the
line terminators (`\n`), and any whitespace. Because the file is written once and never
edited, any byte change makes the hash fail.

`summary_sha256` covers every byte of `summary.json`.

### 3.1 Not covered by any hash

| Item | Why it is not covered | Consequence |
|---|---|---|
| `manifest.json` itself | A file cannot contain a hash of its own final bytes | Edits to the manifest are **not** detected by any in-artifact hash. This includes dataset and evaluator fingerprints, `cases_sha256`, `summary_sha256`, `status`, and `io_mode`. |
| Run directory contents beyond the two hashed files | Not part of the design | Added or removed files outside those two are not detected. |
| File metadata (timestamps, permissions, owner) | Not hashed | Not detected; not relied on. |
| Exported reports (`report export`) and comparison JSON | Generated from the artifacts, not stored as artifacts | Their correctness depends on regenerating them from the run. |
| Per-case hashes (`input_sha256`, `output_sha256`, …) | Only indirectly covered: they are inside `cases.jsonl`, so `cases_sha256` covers them as bytes | Not recomputed from content during verification (§5), because stored content may be redacted. |
| The dataset file | Hashed in the manifest, but the file itself is not in the artifact | Dataset change is detected only if the dataset file is still available and is re-hashed by the user. |

## 4. Verification performed

| Operation | Checks | Failure result |
|---|---|---|
| `inspect` | Recomputes `cases_sha256` and `summary_sha256` from the files and compares them with the manifest. Reports `INTEGRITY_MISMATCH` on failure. | Warning on stderr; exit 4 (CLI §3.4) |
| `compare` | Same checks on both runs before any comparison. | Exit 4 (`INTEGRITY_MISMATCH`), no comparison produced |
| `run.load` (API) | Same checks; `run.integrity_ok` reports the result | `IntegrityError` only when the caller requests strict loading; otherwise `integrity_ok = False` |

Verification does **not**:

- recompute per-case hashes from stored content;
- verify the manifest;
- verify that the run was produced by a particular EvalForge build or by a particular person.

## 5. Threat analysis for stored hashes

| Scenario | Detected by stored hashes? | Notes |
|---|---|---|
| Accidental corruption of `cases.jsonl` (disk error, truncated write) | **Yes** | Hash mismatch |
| Editor or script changes one case's status in `cases.jsonl`, manifest left unchanged | **Yes** | Hash mismatch |
| Same edit, and `cases_sha256` in the manifest recomputed and rewritten | **No** | Anyone who can rewrite the manifest defeats the check |
| Changing `dataset.canonical_sha256` in the manifest to hide a dataset change | **No** | The manifest is not hashed |
| Replacing a whole run directory with an older copy (rollback) | **No** | The older copy is internally consistent |
| Removing failing case lines and recomputing hashes | **No** | Same as above |
| Changing `io_mode` or `redaction` in the manifest to hide what was stored | **No** | Manifest not hashed |
| Hash collision in SHA-256 | Not expected | Assumed infeasible for this purpose; no claim beyond that |

Conclusion: the stored hashes are a **consistency check**, not a **tamper-evidence
mechanism**. They must not be presented to users as proof that results are authentic.

## 6. Comparison blocking and overrides

### 6.1 Default behaviour

A comparison is refused (exit 5) when any of these holds:

| Condition | Reason code | Override flag |
|---|---|---|
| Either run's status is not `COMPLETED` | `RUN_INCOMPLETE` | None (not overridable) |
| Schema major versions differ | `SCHEMA_VERSION_UNSUPPORTED` (exit 4) | None |
| Integrity check fails | `INTEGRITY_MISMATCH` (exit 4) | None |
| Canonical dataset hashes differ | `DATASET_CHANGED` | `--allow-dataset-change` |
| Evaluator names or fingerprints differ | `EVALUATOR_CHANGED` | `--allow-evaluator-change` |

Target name differences are expected in regression testing and do not block a comparison
(TRD-134).

### 6.2 Override rules

1. Overrides exist only as command-line flags or explicit API arguments. They cannot be
   set in the configuration file, environment, or artifact content.
2. Each override is recorded in `compatibility.overrides` of the comparison output, with
   the flag name, the scope, and the observed difference (for example both canonical
   hashes).
3. Text output begins with a banner that names each override and the observed difference.
   The banner appears before any findings.
4. An overridden comparison always produces a finding `COMPARISON_OVERRIDDEN` with
   severity `warning`.
5. `--strict` (API: `strict=True`) turns any override into a refusal (exit 5). Teams that
   want overrides never to affect CI can set it. *Decision: OD-28.*
6. An overridden comparison is never presented as equivalent to a clean comparison. The
   summary line in text output states whether it was overridden.

### 6.3 What a comparison does with partial information

| Situation | Behaviour |
|---|---|
| `io_mode` is `none` in one run | Output-level comparison is unavailable. Categories are computed from statuses only. Finding `IO_UNAVAILABLE` (warning). |
| `io_mode` is `hashes` in both runs | Output change is determined from `output_sha256`. Content-level inspection is unavailable. |
| Dataset changed and `--allow-dataset-change` given | Cases whose `case_sha256` differs are categorized `changed_input` and not status-compared. |

## 7. Limits of this approach, stated for users

- Integrity hashes do not protect against a party who controls the run directory.
- A baseline stored only on the local disk has no independent record. Its provenance
  is whatever the user can demonstrate.
- Hashes of low-entropy outputs (for example a yes/no answer) can be guessed by someone who
  knows the candidate output space. This applies to `io_mode = "hashes"` and to the
  hashes kept in `io_mode = "full"`.

## 8. Stronger options (not in MVP)

| Option | What it adds | Cost or limit |
|---|---|---|
| Commit baseline run directories to version control and review changes | Tamper evidence through the repository history, if history is protected | Requires repository controls; sensitive data in history (DATA_HANDLING §9) |
| Record `manifest.json` SHA-256 in CI logs or a release record | An external anchor independent of the run directory | Manual or CI discipline; not automatic |
| Sign manifests with a user key (for example detached signatures) | Authenticity against parties without the key | Key management; new dependency or external tool; decision OD-29 |
| Keyed hashes (HMAC) for output hashes | Prevents guessing of low-entropy outputs without the key | Key management; prevents cross-party comparison unless keys are shared |

Recommended for MVP: documentation of the stronger options, and no new mechanism.

## 9. Requirements and tests

| ID | Requirement | Test |
|---|---|---|
| TRD-114 | Manifest stores `cases_sha256` and `summary_sha256` | TST-IN-001 |
| TRD-119 | Integrity documentation states what is and is not covered (§3.1) | TST-DOC-007 (text check against this document's §3.1 table) |
| PRD-NF-015 (new) | Comparison blocked by default; overrides explicit and visible | TST-CM-019 … TST-CM-022 |
| THR-013 | Accidental corruption and casual edits detected | TST-SEC-012, TST-IN-002 |
| THR-013 | Manifest-level tampering is documented as undetected | TST-IN-003 (asserts the documented outcome: undetected) |
