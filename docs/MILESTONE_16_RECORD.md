# Milestone 16 Record: Release Readiness (stopped for approval)

Status: **Prepared. Nothing is published, tagged, pushed, or released.** Stopped at the decision request, as
IMPLEMENTATION_PLAN §8.13 requires. Date: 2026-10-30.

## Checklist evidence

`docs/RELEASE_EVIDENCE.md` records the status of each item in RELEASE_CHECKLIST, with evidence or a blocker.
In summary: several items are done with evidence; the release cannot proceed until the blockers below are resolved.

## Blockers (owner action required)

| # | Item | Why | Owner action |
|---|---|---|---|
| 1 | Gate G-2: package name and trademark checks (OD-10) | The name `evalforge` is already used on PyPI. The trademark check has not been done, and it cannot be verified from this workspace. | Choose a distribution name and complete the checks |
| 2 | Copyright year (OD-01) | The notices must use the year of initial publication. That year is not yet known. | Confirm the placeholder approach and the year at publication |
| 3 | Residual risks RR-01 to RR-08 | Not accepted (`docs/RESIDUAL_RISK_ACCEPTANCE.md`) | Written decision for each |
| 4 | CI on Linux and Windows | No remote; not run | Provide a remote and authority to push |
| 5 | Secret scan | Download denied; not run | Permission, or a local run |
| 6 | Reporting channel (OD-20) and enforcement contact (OD-17) | Placeholders | Provide the channel and the contact |
| 7 | Traceability register: 19 Open rows | Requirements without a test | Test, defer, or accept each |
| 8 | Commit of the uncommitted work | 58 changed files; nothing committed | Ask for a commit when ready |

## Release notes (draft)

**EvalForge 0.0.0.dev0 (pre-alpha, not published).** Local evaluation runs with datasets (JSON and JSONL), targets,
built-in and custom evaluators, stored runs with integrity hashes, text and JSON reports, run comparison with refusals
and explicit overrides, regression findings with configurable thresholds, a command line, and a Python API.

**Known limitations** (RELEASE_CHECKLIST §12):

- Targets and custom evaluators are trusted code. They are not sandboxed (RR-01).
- Timeouts are best-effort. A timed-out target is not stopped, and its resource use may continue (RR-02).
- Regular-expression matching has no timeout. Nested repeats are refused; other slow patterns are not detected (RR-03).
- Stored artifacts can be rewritten by anyone who can write to them. The hashes detect accidental changes only (RR-04).
- Redaction is heuristic. It does not guarantee that sensitive text is removed, and exception text is redacted on
  disk but not in memory (RR-05).
- Users may store sensitive data in artifacts; `io_mode` controls this (RR-06).
- Results are not safety or correctness certifications (RR-07; EVALUATION_METHODOLOGY §12).
- No model-based evaluators.
- Performance targets are not measured. Coverage is not reported.
- Linux and Windows are not verified.
- Dependencies may gain vulnerabilities after release (RR-08).

## Decision request

The release cannot proceed without your decisions on the blockers above. In particular:

1. Choose the distribution name (blocker 1). Without this, nothing can be published.
2. Confirm or decline each residual risk, RR-01 to RR-08, in `docs/RESIDUAL_RISK_ACCEPTANCE.md`.
3. Decide the open items for the packaging milestone: OD-32, the sdist rule, and the CI action versions.
4. Authorise CI on a remote, and the secret-scan download.

**Stop here. No publication step has been taken or is authorised.**
