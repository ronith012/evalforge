# Security Policy

Status: **Pre-alpha. The private reporting channel is not yet set (OD-20).**

## Reporting a vulnerability

Do **not** open a public issue for a security problem. Report it privately to the project owner.
The address or channel for private reports has not been set yet. Until it is set, report privately
through a channel the owner has confirmed to you directly, and do not publish details.

When you report, include:

- the EvalForge version (`evalforge --version`) and your Python version;
- the smallest dataset, configuration, or command that shows the problem, with synthetic data;
- what you expected and what happened.

Do not include real evaluation data, credentials, or run directories from a private project.

## What EvalForge does and does not protect against

The threat model and its residual risks are in [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md),
[`docs/SECURITY.md`](docs/SECURITY.md), and [`docs/RESIDUAL_RISK_ACCEPTANCE.md`](docs/RESIDUAL_RISK_ACCEPTANCE.md).
In summary:

- Targets and custom evaluators are trusted code. They run with your privileges and are not sandboxed.
- Timeouts are best-effort. A timed-out target is not stopped.
- Redaction is heuristic. It does not guarantee that sensitive text is removed.
- Stored run artifacts can be rewritten by anyone with write access to them.

## Supported versions

No release has been published. Only the development branch is maintained.
