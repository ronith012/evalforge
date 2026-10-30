# Milestone 13 Completion Record: Security Hardening

Status: **Complete locally. Awaiting owner approval. One check (secret scan) is not run.**
Date: 2026-10-30. Python 3.11, 3.12, 3.13 (macOS, arm64). Not committed.

## Scope (IMPLEMENTATION_PLAN §8.10)

| Item | Result | Where |
|---|---|---|
| 1. Verification matrix: each threat maps to a test or an approved residual risk | Done. All 23 threats (THR-001 to THR-023) are mapped. Two are not in MVP (THR-008, THR-017). The matrix's test names are checked by a test. | `docs/SECURITY_VERIFICATION_MATRIX.md`; `tests/test_security.py::test_every_test_named_in_the_matrix_exists` |
| 2. Static checks: `eval`, `exec`, `pickle`, unsafe YAML, `shell=True` | Done. The source tree is parsed with `ast`. Also checked: `os.system`, `subprocess`, and the unsafe-deserialisation modules. | `tests/test_security.py` (TST-SEC-003) |
| 3. Network-isolation test | Done. Static: no network modules in the source. Behavioural: quick start with sockets disabled. | TST-SEC-004 tests |
| 4. Dependency audit: verify the tool, then run | Done. pip-audit 2.10.1 verified on PyPI (Apache Software License classifier; Production/Stable; PyPA). Added as a development dependency only. Run result below. | `pyproject.toml`, `uv.lock` |
| 5. Regex review | Done, with one partial mitigation. Measured exponential growth. Added a nested-repeat guard. | `docs/REGEX_REVIEW.md`; `config.py` |
| 6. Process-isolation reassessment (documentation only) | Done. Recommendation: keep best-effort threads for the MVP and revisit isolation after it. | `docs/PROCESS_ISOLATION_REASSESSMENT.md` |
| 7. Residual risks RR-01 to RR-08 presented for written acceptance | Presented. **Not accepted.** Acceptance fields are blank. | `docs/RESIDUAL_RISK_ACCEPTANCE.md` |

## Defects found and fixed

1. **Run reference could leave the run root (THR-007).** `resolve_run` joined a reference such as
   `../../../outside/victim` onto the run root without a check. Reproduced, then fixed: a run ID must be a plain
   name; a path is accepted only when it is a directory with a manifest. Test:
   `test_run_reference_outside_the_root_is_refused`.
2. **Nested repeats in regex patterns take exponential time (THR-003).** Measured: each +2 characters multiplied the
   time by about 3.5 to 4 (2.4 ms at 14 characters, 380.9 ms at 22). Guard added at configuration time. Partial; see
   the review.
3. **Static check false positive.** `platform.system()` matched a rule for `os.system`. The rule now matches
   `os.system` only.
4. **Banned-claims scan was too loose.** A negation anywhere on a line allowed a banned phrase. Now the negation must
   sit directly before the phrase.

## Checks and exact results

| Check | Command | Result |
|---|---|---|
| Tests | `uv run pytest -q` on 3.11, 3.12, 3.13 | 546 passed on each |
| Lint | `uv run ruff check .` | All checks passed! |
| Format | `uv run ruff format --check .` | 72 files already formatted |
| Types | `uv run mypy --strict` | Success: no issues found in 67 source files |
| Dependency audit | `uv run pip-audit` | No known vulnerabilities found; exit 0. The project itself is skipped because it is not on PyPI. |

## Not run, and why

- **Secret scan with gitleaks.** The download of gitleaks v8.30.1 (MIT licence, verified) was denied by the environment's
  safety policy. I did not try another route to the same binary. The CI job is written, with the release's SHA-256
  checked before the binary runs. A local scan is still needed. **Owner action:** grant permission to download and run
  the verified binary, or run the scan on your own machine.
- **Linux and Windows.** Not run locally (CI is Milestone 15).

## Open items from this milestone

- RR-02 (timeouts) and RR-01 (trust model) are rated High. Both need the owner's written decision.
- RR-03 (regex) remains open; the guard is partial.
- THR-013 and THR-014 remain Partly (see the matrix).

## Requested approval

Approve Milestone 13 with the residual-risk decisions left to the owner. Grant or decline the gitleaks download.

## Partial substitute for the secret scan (2026-10-30)

Without gitleaks, the repository's own credential patterns (`evalforge.redaction.TEXT_PATTERNS`) were run over the 143
tracked and untracked files. Result: 0 hits. This is much narrower than gitleaks: it covers only the listed credential
formats, not history, and not generic high-entropy strings. The full scan remains open.
