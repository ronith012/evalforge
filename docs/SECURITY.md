# EvalForge — Security Policy and Secure-Use Guidance

Status: **Proposed — awaiting approval.** No security behaviour in this document is
implemented or tested yet. Limitations are stated explicitly.

Companion documents: [THREAT_MODEL](THREAT_MODEL.md), [DATA_HANDLING](DATA_HANDLING.md).

---

## 1. Purpose

This document defines how EvalForge handles security-relevant behaviour for users
and contributors. It covers the design rules, controls, limitations, and the vulnerability
reporting process.

## 2. Supported versions

No version has been released. This section will list supported versions at first release
(RELEASE_CHECKLIST §6).

## 3. Reporting a vulnerability

**Reporting channel: to be defined (OD-20).** No contact address is published in this
planning phase. Do not report vulnerabilities in public issues until a private channel
is defined. The approved channel will be added here and in the README.

Expected handling once a channel exists (proposed):

1. Acknowledge receipt.
2. Reproduce and assess severity using the threat register (THREAT_MODEL §3).
3. Prepare a fix and a test that would have caught it.
4. Coordinate disclosure timing with the reporter.
5. Record the advisory in CHANGELOG.

No response-time commitment is made in this planning document.

## 4. Sensitive data controls

Full data-handling rules are in [DATA_HANDLING](DATA_HANDLING.md). This section states
the security-relevant controls. Redaction is **heuristic and incomplete**; it is not a
guarantee that sensitive information is removed (DATA_HANDLING §7.4).

### 4.1 What counts as a secret

For EvalForge, a secret is any value that grants access to a system or identifies a
private credential: API keys, tokens, passwords, session identifiers, private keys, and
connection strings with embedded credentials. EvalForge does not know which values are
secrets. It relies on the rules below, which are best effort.

### 4.2 Exceptions and tracebacks

- Stored: exception type, and the message truncated to 500 characters (DATA_HANDLING §4).
- Never stored: tracebacks and local variable values.
- Logged: tracebacks only at DEBUG, after redaction.
- Residual risk: an exception message can contain sensitive data that the heuristics miss
  (RR-05, OD-21).

### 4.3 Configuration values

- The manifest stores the configuration with values removed for keys matching the secret-key
  pattern. Removed values are replaced by `[REDACTED]`, and the count of removed fields is recorded.
- Secret-key pattern (case-insensitive):
  `api[_-]?key|token|secret|password|passwd|credential|auth|private[_-]?key|session`.
- Paths are stored relative to the configuration file directory (TRD-184).
- Secrets placed under non-matching keys are stored. Users are told not to put secrets in the
  configuration file at all (§11).

### 4.4 Environment variables and environment metadata

- EvalForge does not read environment variables for configuration (TRD-183).
- EvalForge does not store environment variable values, hostnames, usernames, home
  directories, or absolute working directories. The stored environment metadata is limited
  to EvalForge version, Python version, OS family, and machine architecture
  (DATA_HANDLING §6).

### 4.5 Logs

- Logs never contain case inputs, outputs, expected values, or evaluator details (TRD-192).
- Any text that is logged passes through the same redaction as stored text (TRD-194).

### 4.6 Redaction: method and limits

When redaction is enabled (default), the following is applied to stored strings, evaluator
messages and details, exception messages, and logged text.

- **Key-based:** values under object keys matching the secret-key pattern are replaced.
- **Pattern-based:** substrings matching known credential prefixes are replaced. The initial
  list is a starting point and includes prefixes such as `sk-`, `sk_live_`, `ghp_`,
  `github_pat_`, `AKIA`, and `xox[baprs]-`. It is incomplete by design.
- Replacements are shown as `[REDACTED:<category>]`, so removal is visible.

Known misses (must appear in user documentation):

- credential formats not in the list;
- secrets under unrecognised key names;
- personal data, health or financial information, and proprietary text, which are not detected;
- secrets split across fields or encoded;
- text the user's own code writes outside EvalForge.

Known false positives: non-secret text that matches a pattern is replaced, which alters
stored content.

Disabling redaction (`--no-redaction`, config `redaction = false`) is an explicit opt-out. The
manifest and outputs record it (DATA_HANDLING §7.5). Whether configuration may set it is
OD-27.

## 5. Sensitive input and output exposure

| Surface | Default | How to change |
|---|---|---|
| Run directory `cases.jsonl`, `io_mode = full` | Stores input, expected, output (redacted if enabled) | `--io-mode hashes` or `none`; config `[run] io_mode` |
| Run directory `cases.jsonl`, `io_mode = hashes` | Stores hashes only | Default for the example CI workflow (OD-12) |
| `inspect` case list | Hides input and output | `--show-io` (only meaningful with `io_mode = full`) |
| `inspect --case` | Shows stored input and output | Intentional detail view |
| `report export` | Excludes input and output | `--include-io` (requires `io_mode = full`) |
| Terminal progress | Never shows input or output | Not configurable |
| Comparison JSON | Excludes content; includes hashes and overrides | Not configurable |

Guidance:

- Add `.evalforge/` to `.gitignore` (the project template includes this).
- Do not commit run directories with `io_mode = full` to public repositories. Committed
  content remains in history after deletion.
- Use `io_mode = "hashes"` or `"none"` in CI when artifacts are shared more widely than the
  evaluation data.
- Treat exported reports with `--include-io` as sensitive.

## 6. Output sanitization

Applies to all text output (terminal and text reports) and to any field displayed
to users.

| Rule | Detail |
|---|---|
| Strip C0 control characters | U+0000–U+001F except TAB (U+0009) and LF (U+000A); CR is removed |
| Strip DEL and C1 controls | U+007F, U+0080–U+009F |
| Strip bidirectional overrides | U+202A–U+202E, U+2066–U+2069 |
| Escape representation | Sanitized strings display `\uXXXX` for removed characters so that users can see that content was altered |
| JSON output | Standard JSON escaping; the sanitization above is not applied to JSON values, which are data |
| Width | Long outputs are truncated in text tables with an explicit marker; full content available via JSON or `--case` |

Tests: ANSI escape sequences, bidi overrides, NUL bytes, and very long lines (TEST_STRATEGY §4.8).

## 7. Regex safety

- Patterns from configuration are compiled with `re` and limited to 512 characters
  (TRD-090).
- Regex matching is applied to output strings no longer than the configured maximum
  (default 1 MiB) (TRD-091).
- Python's `re` has no built-in timeout. Catastrophic backtracking can stall a case;
  the case then runs into the target timeout only if the timeout wraps the evaluator,
  which it does not in the MVP (**known gap; see RR-03**).
- Pattern review checklist for users (documented):
  1. Avoid nested quantifiers such as `(a+)+` and `(a|a)*`.
  2. Prefer anchored, specific patterns.
  3. Test patterns against a long adversarial string before adding them.
  4. Prefer `contains` for literal checks.

## 8. Dependency and supply-chain controls

| Control | Status |
|---|---|
| Minimal runtime dependencies (TRD §3.2) | Proposed |
| Lock file committed (uv, `uv.lock`) | Approved (OD-03); TRD-020 |
| Build and tooling verification before installation | Gate G-1 (OPEN_DECISIONS §3) |
| `pip-audit` in CI | Proposed (TRD-023) |
| Licence review before release | Proposed (RELEASE_CHECKLIST §3) |
| Secret scanning of repository and history before release | Proposed (RELEASE_CHECKLIST §5) |
| Trusted publishing for releases | Proposed |
| Checksums published with artifacts | Proposed |
| Name verification on PyPI | Open; publication blocked until complete (OD-10, G-2) |

## 9. Security testing

Defined in TEST_STRATEGY §4.8. Summary:

- Malicious and malformed dataset corpus (code payloads, pickle bytes, YAML tags,
  NaN/Infinity, deep nesting, huge strings, invalid UTF-8, BOMs).
- Path and ID traversal payloads.
- Symlink fixtures.
- Terminal injection payloads.
- Integrity tampering tests.
- Planted-secret tests across config, logs, manifests, and error messages.
- Network-disabled test of the full quick-start.
- Static checks in CI: no `eval`, `exec`, `pickle`, unsafe YAML, or `shell=True`
  (TRD-216).

Security tests are required to pass before a release. Any failing security test blocks
release unless approved as a documented exception.

## 10. Documented limitations (must appear in user documentation)

1. **Custom evaluators and targets are trusted code.** They run with the user's full process
   privileges and are not sandboxed. No sandbox is implemented or tested in the MVP.
2. **Timeouts are best-effort.** A timed-out target thread cannot be forcibly terminated by
   EvalForge and may keep running, consuming resources and performing side effects. A
   timeout is not execution isolation and does not stop side effects. Process-based
   isolation is not part of the MVP (ARCHITECTURE §11.1; OD-06).
3. **Regex matching has no timeout** in the MVP.
4. **Redaction is heuristic and incomplete.** It does not guarantee removal of sensitive
   information. Exception messages are redacted by the same heuristics and can still leak
   content (DATA_HANDLING §7.4).
5. **Artifact hashes are a consistency check, not tamper evidence.** Anyone who can write to a
   run directory can also rewrite its hashes. The manifest is not hashed (ARTIFACT_INTEGRITY §3–§5).
6. **No sandbox for model-generated code.** EvalForge does not execute code generated by
   models or contained in datasets.
7. **Scores are not safety certifications.** See EVALUATION_METHODOLOGY §12.
8. **Dependencies can contain vulnerabilities** despite audits. The MVP runtime has no third-party
   dependencies as approved under OD-03 and OD-15 (TRD §3.2).
9. **Input size limits are defaults.** Users who raise them accept the associated resource use.

## 11. Secure-use guidance for users

- Review custom evaluator and target code before running it, as you would any code.
- Keep configuration files under version control and review changes to them.
- Do not put secrets in `evalforge.toml`. Pass them to your target code through your own
  secret management.
- Do not run `evalforge config validate --check-imports` on untrusted projects, because it
  imports modules.
- Do not share run directories containing sensitive data. Prefer `io_mode = "hashes"` or
  `"none"` for shared artifacts.
- Do not treat a clean comparison as proof of anything beyond the configured cases.
- Do not rely on comparison integrity beyond ARTIFACT_INTEGRITY §5; anchor shared baselines
  externally if provenance matters.
- Pin EvalForge and dependency versions in CI.

## 12. Contributor security rules

- No `eval`, `exec`, `pickle`, `marshal`, unsafe YAML loaders, or `shell=True`.
- No network calls in core code. New network-capable features require a design review and an
  approved decision.
- New dependencies require an entry in TRD §3.2 and approval.
- Logging follows TRD-192 and TRD-194.
- Every security-relevant change requires a test (TEST_STRATEGY §4.8 or §4.15).
- External contributions require DCO sign-off, enforced by an automated check before any external contribution is accepted (approved, OD-31; enforcement method OD-32, open).
- Report any suspected vulnerability through the channel in §3, not in a pull request.

## 13. Change control

Changes to this document are reviewed with THREAT_MODEL changes. Residual risks
RR-01 to RR-08 require explicit acceptance before release.
