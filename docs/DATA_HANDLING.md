# EvalForge — Data Handling

Status: **Proposed — awaiting approval.** Describes intended MVP behaviour. Not implemented
or verified. Redaction is heuristic and does not guarantee removal of sensitive information
(§7.4).

Companion documents: [SECURITY](SECURITY.md), [ARTIFACT_INTEGRITY](ARTIFACT_INTEGRITY.md),
[THREAT_MODEL](THREAT_MODEL.md), [DATA_MODELS](DATA_MODELS.md).

---

## 1. Principles

1. **Local by default.** The core processes data on the user's machine and transmits nothing (PRD-NF-001).
2. **Least stored content by user choice.** The user chooses how much case content is persisted (§3).
3. **Redaction is a best-effort safety net, not a guarantee.** It reduces accidental
   exposure of recognisable secrets. It does not identify personal data or proprietary content.
4. **Nothing is collected about the user.** No telemetry. Environment metadata is limited (§6).
5. **Visible defaults.** Every data-handling setting is recorded in the run manifest, so a
   reader can tell what was stored.

## 2. Data classes

| Class | Examples | Origin | Handling |
|---|---|---|---|
| Case content | Input, expected output, metadata, tags | User dataset | Stored per `io_mode` (§3); metadata always stored, see §3.2 |
| Target output | Application response | User target code | Stored per `io_mode`; redacted if redaction enabled |
| Exception data | Exception type, message, traceback | Target or evaluator code | Type and redacted message only (§4) |
| Configuration | Paths, evaluator parameters, target reference | User config file | Snapshot with secret-like values removed (§5) |
| Environment metadata | Python version, OS family, EvalForge version | Runtime | Minimal set (§6) |
| Evaluation results | Statuses, reason codes, messages, scores, details | EvalForge and evaluators | Messages and details redacted when redaction enabled |
| Comparison results | Categories, metrics, findings, hashes, overrides | EvalForge | No case content |
| Logs | Lifecycle events, counts, IDs, durations | EvalForge | No content at any level (TRD-192); redaction applied to any text logged |
| Secrets | Credentials, tokens | Should not be in EvalForge inputs | Not intentionally processed; redaction is a fallback only |

## 3. Input and output persistence

### 3.1 The `io_mode` setting

| Value | Stored in `cases.jsonl` | Stored hashes | `inspect --case` shows | Comparison capability |
|---|---|---|---|---|
| `full` | `input`, `expected` (if present), `output` (redacted if redaction enabled) | `input_sha256`, `expected_sha256`, `output_sha256` (raw values) | Stored content | Full |
| `hashes` | Nothing from input, expected, or output | `input_sha256`, `expected_sha256`, `output_sha256` (raw values) | Hashes only | Output change detected by hash |
| `none` | Nothing | None for input or output | Status and reasons only | Status-level only; `IO_UNAVAILABLE` warning |

In all modes the case identity hash `case_sha256` is stored because it is required for
dataset-change detection. It is derived from the user's own dataset and is therefore not
extra exposure of target output. Evaluator messages and details are stored in all modes,
subject to redaction (§4.3).

Configuration: `[run] io_mode = "full" | "hashes" | "none"` (DATA_MODELS §4). CLI: `--io-mode`.
Default: **open decision OD-12.** Recommended default: `full` for local interactive use;
the example CI workflow sets `hashes`.

### 3.2 Metadata is not I/O

Case `id`, `tags`, and `metadata` are stored in every mode. Users should not place
sensitive data in them. The documentation says so, and the `id` pattern (TRD-041) limits
what can appear in an identifier. `metadata` is free-form, so it is the user's
responsibility. Metadata values are subject to redaction when redaction is enabled, which
applies the same heuristics as for output (§4.3).

### 3.3 Built-in evaluator messages

Built-in evaluators must not place case content in `message` or `details`. Their messages
use fixed text and reason codes, for example "Output differs from expected value." and
`details` contain only structural facts such as `paths` or `max_ms`. A test asserts this
for each built-in evaluator (TST-IO-004). Custom evaluators are not covered by this rule
(§4.3).

### 3.4 Integrity of stored content

Stored content is what the hash-covered file contains. Because output hashes are computed
before redaction, the stored text may differ from its hash (ARTIFACT_INTEGRITY §2).

## 4. Exceptions and tracebacks

| Item | Stored in artifacts | Shown to user | Logged |
|---|---|---|---|
| Exception class name | Yes (`target.error.type`) | Yes | DEBUG |
| Exception message | Yes, truncated to 500 characters, redacted when enabled | Yes, same text | DEBUG, redacted |
| Traceback | **Never** | Only at DEBUG logging level, redacted | DEBUG, redacted |
| Local variable values | **Never captured** | — | — |

Rules:

1. EvalForge does not use any mechanism that captures local variables.
2. Tracebacks include source lines of user code, which may contain literal secrets. They are
   therefore never written to run artifacts and are shown only at DEBUG, after redaction.
3. An exception message may contain data supplied by the target. It is stored truncated, and
   redacted by the heuristics in §7 when redaction is enabled. Redaction may miss content.
   This is listed as residual risk RR-05 and open decision OD-21.
4. Exceptions raised inside evaluators are recorded in the same way (`EVALUATOR_EXCEPTION`).

## 5. Configuration values

| Rule | Detail |
|---|---|
| Snapshot content | The manifest stores the configuration with values removed for keys matching the secret-key pattern (SECURITY §4.3). Removed values are replaced by `[REDACTED]`, and the count of removed fields is recorded. |
| Non-secret keys | Paths, numeric limits, and evaluator parameters are stored. |
| Paths | Stored relative to the configuration file directory (TRD-184). Absolute paths are not stored because they reveal account names and directory layout. Paths outside the configuration directory are stored as `<external>/<basename>`. |
| Target reference | The `module:attribute` string is stored. It identifies code, not a secret. |
| Environment | Configuration cannot read environment variables (TRD-183), so environment values never enter the snapshot. |
| Allow flags | Override flags (`--allow-*`) are recorded in the comparison output, not in configuration (ARTIFACT_INTEGRITY §6.2). |

Limitation: a secret placed under a non-secret key name is stored. Users are told to keep
secrets out of the configuration file altogether (SECURITY §11).

## 6. Environment-derived metadata

| Field | Stored | Rationale |
|---|---|---|
| EvalForge version | Yes | Reproducibility |
| Python version (major.minor.micro) | Yes | Reproducibility |
| OS family and machine architecture (`sys.platform`, `platform.system()`, `platform.machine()`) | Yes | Reproducibility of performance results |
| Full platform string including kernel build | **No** (proposed) | Adds identifying detail without clear benefit; decision OD-30 |
| Hostname, username, home directory, current working directory (absolute) | **No** | Identifying; not needed |
| Environment variables | **No** | May contain credentials (TRD-106 amended) |
| Installed package list | **No** in MVP | Not captured; post-MVP option with review |
| Wall-clock timestamps | Yes | Needed for ordering and audit |

## 7. Redaction

### 7.1 What redaction applies to

When `redaction = true` (default, see §7.5):

| Surface | Applied |
|---|---|
| Stored input, expected, output values (`io_mode = full`) | Yes, string leaves of JSON values |
| Evaluator `message` and `details` | Yes |
| Exception messages | Yes |
| Logged text at any level | Yes |
| Configuration snapshot | Key-based removal (§5) plus value patterns |
| Exports and reports | Uses the stored (already redacted) values; no unredacted export exists (§8.2) |

### 7.2 Methods

1. **Key-based (structured values).** Object keys matching the secret-key pattern
   (SECURITY §4.3) have their values replaced by `[REDACTED:key]`.
2. **Pattern-based (strings).** Substrings matching known credential formats are replaced by
   `[REDACTED:pattern-name]`. The initial list is a starting point (SECURITY §4.6).
3. **Counting.** Each case result records `redactions` as a count of replacements made to
   its stored values. Counts do not reveal the replaced text.

### 7.3 Replacement is visible

Replacement markers are plain text, so a reader can see that something was removed.
Redaction never silently drops a value.

### 7.4 Limitations (must appear in user documentation)

Redaction is **heuristic** and **incomplete**. It does not guarantee the removal of all
sensitive information. Specifically:

| Limitation | Effect |
|---|---|
| Pattern lists cover only known formats | Credentials in unknown formats are not removed |
| Key-based rules depend on key names | A secret under an unrecognised key name is not removed |
| No semantic understanding | Personal data (names, addresses, identifiers in free text), health information, financial details, and proprietary text are not detected |
| Obfuscation and splitting | Secrets split across fields or encoded (for example base64) are not detected |
| False positives | Non-secret text matching a pattern is replaced, which can alter stored content and the apparent output |
| Ordering | Redaction is applied when text is stored or logged. Text already written by the user's own code (for example in their own logs) is outside EvalForge's control |
| Hashes | Output hashes are computed before redaction. A hash of a low-entropy secret may be guessable (ARTIFACT_INTEGRITY §7) |

Users with sensitive data are told to use `io_mode = "hashes"` or `none`, to keep
credentials out of targets' outputs, and to apply their own review.

### 7.5 Disabling redaction

`redaction = false` (config) or `--no-redaction` (CLI) disables §7.2. This is an explicit
opt-out:

- The manifest records `redaction: false`.
- The text output and the comparison output carry a warning line stating that redaction
  was disabled for the run.
- The default is `true`. Whether the flag may be set in configuration or only on the command
  line is decision OD-27 (recommended: configuration allowed, since it is recorded).

## 8. Exported reports

### 8.1 Default contents

| Export | Includes | Excludes |
|---|---|---|
| Run summary (JSON or text) | Counts, rates, interval, error codes, evaluator failure counts, latency, redaction status | Case content, tracebacks |
| Case list (in `inspect`) | Case ID, status, reason code, evaluator statuses | Input, output, expected |
| Comparison (JSON) | Categories, metrics, findings, compatibility, overrides, hashes | Case content |
| `report export --include-io` | Stored case content (only if `io_mode = full`) | Tracebacks; unstored content |

### 8.2 `--include-io`

- Requires that the source run was stored with `io_mode = full`. Otherwise the command
  fails with a usage error and explains why.
- Exports the stored (already redacted, if redaction was on) values. There is no option to
  export unredacted content, because EvalForge never stored it.
- Prints a warning on stderr that the export contains case content.

### 8.3 Terminal output

Text output never includes case content unless the user runs `inspect --case` or
`inspect --show-io`. Control characters are sanitized (SECURITY §6).

## 9. Storage, retention, deletion, and permissions

| Topic | Rule |
|---|---|
| Location | `.evalforge/runs/<run_id>/` by default (OD-11). Documented as sensitive and gitignored. |
| Retention | Never automatic. Users delete run directories. |
| Deletion | Removes EvalForge-stored data for that run. Copies (exports, CI artifacts, backups, version-control history) remain until the user deletes them. |
| Version control | Committing runs with `io_mode = full` places case content in history. Deleting the file later does not remove it from history. |
| Permissions | Proposed owner-only on POSIX: directories 0700, files 0600 (OD-22). Windows uses default ACLs; documented. |
| Atomic writes | Temporary file in the same directory, then rename (TRD-112). Temporary files are removed on failure. |

## 10. Sharing

| Action | Leaves the machine | Controls |
|---|---|---|
| Committing runs | Whatever the run directory holds | `.gitignore` template; `io_mode` guidance |
| CI artifact upload | Whatever the workflow uploads | Example uploads summary and comparison only (OD-23) |
| Export | Only what the user exports | §8 defaults |
| Sharing a comparison file | Case IDs, hashes, metrics, findings, overrides | Contains no case content |

Integrity limits for shared artifacts are in ARTIFACT_INTEGRITY §5.

## 11. Network and telemetry

- The core makes no network requests (PRD-NF-001, verified by TST-SEC-004).
- EvalForge cannot control network activity inside target code. The manifest records the
  target reference, not outbound traffic.
- No telemetry or update checks.

## 12. Personal data

- EvalForge does not classify or detect personal data.
- Users are responsible for lawful basis, minimisation, and retention under rules that apply to them.
- Case IDs appear in logs at DEBUG, in comparisons, and in findings. Users should not put
  personal identifiers in IDs.
- No compliance certification is claimed for any privacy regulation.

## 13. Synthetic and sample data

- Example datasets are synthetic, written for this project, and labelled as such in their READMEs.
- Real datasets and real outputs are never committed to the repository or used as test fixtures.
- Hostile-input fixtures are labelled as test material.

## 14. Requirements and tests

| ID | Requirement | Test |
|---|---|---|
| PRD-NF-014 (new) | Sensitive-data settings are configurable, recorded in the manifest, and documented | TST-IO-001, TST-IO-002, TST-RD-006 |
| I/O modes | `full`, `hashes`, `none` behave as §3.1 | TST-IO-001 … TST-IO-003 |
| Built-in messages | No case content in built-in messages or details | TST-IO-004 |
| Exceptions | No traceback in artifacts; message truncated and redacted | TST-IO-005, TST-RD-003 |
| Config | Secret-key values removed; paths relative; no environment values | TST-SEC-008, TST-IO-006 |
| Environment | Only the minimal set in §6 is stored | TST-IO-007 |
| Redaction | Pattern and key behaviour; documented misses | TST-RD-001 … TST-RD-006 |
| Exports | Default excludes I/O; `--include-io` requires `full`; no unredacted export | TST-SEC-013, TST-IO-008 |
| Retention | No automatic deletion | TST-IO-009 |

## 15. Open decisions

| ID | Question | Recommended |
|---|---|---|
| OD-12 | Default `io_mode` | `full` locally; `hashes` in the example CI workflow |
| OD-21 | Exception-message redaction | Apply the heuristic and document incompleteness |
| OD-22 | Run-directory permissions | Owner-only on POSIX |
| OD-23 | CI example uploads `cases.jsonl` | No |
| OD-27 (new) | Whether `redaction = false` may be set in configuration | Allowed, because it is recorded in the manifest and in outputs |
| OD-30 (new) | Storing the full platform string | No |
