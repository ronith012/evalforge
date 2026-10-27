# EvalForge — Planning Summary

Status: **Planning revised. Final owner decisions recorded in OPEN_DECISIONS.md. Milestone 1 has not started and requires explicit authorisation.**
No implementation has started. No dependencies were installed. Git has not been initialised.
Nothing has been published or pushed.

Revision date: 2026-10-18. License target: Apache-2.0.

---

## 1. What changed in this revision

| Review item | Change | Where |
|---|---|---|
| 1. Timeouts and isolation | Subprocess feasibility analysed. Isolation **not** in MVP. Timeouts documented as best-effort everywhere. Trusted-code status stated. Milestone 13 produces a decision only; optional M17 if approved. | ARCHITECTURE §11, §11.1; TRD §5.3; SECURITY §10; THREAT_MODEL THR-010, RR-02; IMPLEMENTATION_PLAN M13, M17 |
| 2. Sensitive data | Three I/O modes (`full`, `hashes`, `none`); redaction on by default and recorded when off; tracebacks never stored; exception messages truncated and redacted; minimal environment metadata; paths relative; exports exclude content unless `--include-io` on a full run. Redaction limits stated. | DATA_HANDLING (rewritten); SECURITY §4–§5; DATA_MODELS §4, §6, §7; CLI §3.3–§3.6; THREAT_MODEL THR-011, THR-012, THR-021, THR-022 |
| 3. Artifact integrity | New document. Exact coverage of `cases_sha256` and `summary_sha256`. Manifest not hashed. Limits of stored hashes stated with a threat table. Incompatible comparisons refused by default. Overrides explicit, recorded, banner-visible, warned, and blockable with `--strict`. | ARTIFACT_INTEGRITY (new); TRD §8, TRD-114, TRD-118/119, TRD-136–138; THREAT_MODEL THR-013, THR-023 |
| 4. Open decisions | Full 30-row table produced (in the reply and in OPEN_DECISIONS.md). Four decisions added (OD-27 to OD-30). | OPEN_DECISIONS.md |
| 5. Consistency | Dependency model changed everywhere (see §2). Tests added for each new requirement. Traceability updated. | All documents; TEST_STRATEGY §4.15 and §10 |
| 6. Limits | No code, no installs, no Git, no publishing. | — |

## 2. A conflict found and resolved during the review

**TRD-003 required a pure-Python package, but the plan proposed Pydantic.** Pydantic v2's core
is a compiled extension. The plan now uses **zero third-party runtime dependencies**:

- validation with frozen dataclasses and explicit functions;
- `argparse` for the CLI;
- `tomllib` for configuration (Python 3.11+);
- `hashlib`, `uuid`, `json` from the standard library.

Consequences: more hand-written validation and CLI code in M2 and M11, more tests, and a
larger M2 effort. A fallback (Pydantic with an explicit TRD-003 amendment) is documented.
Approved by the owner as OD-03 and OD-15, recorded as CH-02 and AD-009. No requirement was removed.

## 3. Timeouts and isolation: recommendation

- **MVP:** worker-thread timeouts, best-effort. A timed-out target may keep running. The
  manifest counts such threads, and the summary warns about them.
- **Not claimed:** that arbitrary Python execution can be reliably terminated, or that a timeout
  stops side effects.
- **Isolation feasibility** (ARCHITECTURE §11.1): transferring callables needs picklable or
  importable targets; `spawn` requires an entry-point guard in user scripts; `fork` is unavailable
  on Windows; termination does not reach grandchild processes; resource limits are POSIX-only;
  a subprocess is a fault boundary, not a sandbox.
- **Caveat:** that analysis is based on documented Python behaviour and was **not tested
  empirically** in this phase.
- **Recommendation:** no isolation in MVP. M13 writes the decision. M17 exists only if approved.

## 4. Sensitive data: summary of the rules

| Topic | Rule (default in brackets) |
|---|---|
| Input and output | `io_mode`: full / hashes / none [default OD-12] |
| Expected values | Stored with input, as for input |
| Exceptions | Type and truncated, redacted message. Tracebacks never stored. |
| Configuration | Secret-like keys removed; paths relative; `[REDACTED]` markers counted |
| Environment | EvalForge, Python, OS family, machine architecture only |
| Exports | Excludes content; `--include-io` only from `io_mode = full` runs; never unredacted |
| Redaction | On by default; off is recorded in manifest and outputs |
| Limits | Heuristic and incomplete; no guarantee of removal (DATA_HANDLING §7.4) |

## 5. Artifact integrity: summary

- `cases_sha256` and `summary_sha256` cover the exact bytes of those two files.
- The manifest is **not** hashed, so manifest edits are undetected.
- Detected: accidental corruption and casual edits to `cases.jsonl` or `summary.json`.
- Not detected: a rewrite of the files together with their hashes, manifest tampering, rollback of a whole run directory.
- The hashes are a consistency check, not tamper evidence. Stronger anchors (version-control history,
  external records, signatures) are documented; signing is deferred (OD-29).
- Comparisons refuse incompatible runs by default. Overrides require explicit flags and are shown
  in the banner, the JSON output, and a warning finding. `--strict` refuses instead.

## 6. Decision status

Full record: [OPEN_DECISIONS.md](OPEN_DECISIONS.md).

**Approved by the owner (final confirmation):**

| ID | Decision |
|---|---|
| OD-01 | Copyright holder Bodepudi Ronith; Apache-2.0; `NOTICE`; short headers; year = initial publication year |
| OD-02 | Python 3.11, 3.12, 3.13 initially; all three tested in CI |
| OD-03 | argparse; Hatchling; uv (environment and lock generation) |
| OD-04 | TOML configuration |
| OD-05 | JSON/JSONL run-directory persistence; SQLite deferred |
| OD-06 | Best-effort timeouts in the MVP; reassess process isolation in M13 |
| OD-15 | Zero runtime dependencies; standard-library validation; `mypy --strict` required CI gate |
| OD-31 | DCO sign-off for external contributions; automated enforcement before acceptance |

**Provisional:** OD-10. "EvalForge" may be used as a provisional local name. Publication is blocked until package-index and trademark checks are completed (not yet run).

**Gates:** G-1 (verify Hatchling and uv before installing dependencies; not yet run) and G-2 (publication checks; not yet run).

**Open:** OD-32 (DCO enforcement method) and the open items listed in OPEN_DECISIONS.md §2.

## 7. Remaining risks

| Risk | Status |
|---|---|
| Timed-out target threads continue (THR-010, RR-02) | Accepted as best-effort in MVP; decision M13; documented |
| Custom targets and evaluators are unsandboxed trusted code (RR-01) | Accepted by design; documented |
| Redaction misses secrets or personal data (RR-05, DATA_HANDLING §7.4) | Accepted with documentation; OD-21 |
| Artifact rewritten with its hashes (RR-04) | Accepted; documented; anchors recommended |
| Users store sensitive content in runs (RR-06) | Mitigated by defaults and guidance (OD-12); residual |
| Overrides used in CI without review | Mitigated by visibility and `--strict` (OD-28) |
| Zero-dependency validation is more code (cost of CH-02) | Accepted; M2 and M11 effort increased |
| Package name and trademark unverified (OD-10) | Open; owner check required |
| Performance targets unmeasured (TRD §16) | Open; measure in M2, M7, M10 |
| Research incomplete (RESEARCH_NOTES) | Open; licence checks for two projects outstanding |
| Wilson worked example needs independent re-derivation | Open (TEST_STRATEGY §4.6) |

## 8. Consistency checks

Results of checks run on this revision (see §9 for details):

- Every referenced requirement, threat, safety rule, test, and decision identifier is defined.
- Every MVP requirement (PRD-F-001…030, PRD-NF-001…016) appears in the TEST_STRATEGY traceability table.
- Relative markdown links resolve.
- Section cross-references point at existing sections.
- Terms superseded by this revision (`store_io`, Pydantic and Typer as dependencies) are removed,
  except where a document deliberately records the change.

## 9. Corrections made during this revision

- A missing write step had dropped the new sensitive-data test section (TEST_STRATEGY §4.15). It was reinserted and checked.
- An earlier formatting mismatch stopped a batch edit. The remaining edits were applied in a second pass, and each was checked.
- Dataset `source_path` was previously recorded as an absolute path. It is now relative (DATA_MODELS §3).
- The manifest now records `summary_sha256` as well as `cases_sha256`.
- The CLI now has `--io-mode`, `--no-redaction`, and `--strict`; `--store-io` is removed.

## 10. Next step

Milestone 1 has not started. It needs your explicit authorisation. Before any dependency is
installed, gate G-1 must be completed and recorded. Before publication, gate G-2 must be completed.
Initialising Git needs separate authorisation.

**No implementation will start until you approve it.**
