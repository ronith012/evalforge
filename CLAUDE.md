# EvalForge — Project Instructions

## Development workflow
- Follow plan → review → approval → implementation → testing.
- Do not implement features before the specifications are approved.
- Work milestone by milestone.
- Do not expand approved scope without explaining the impact.

## Engineering quality
- Use type hints and clear interfaces.
- Write tests for new functionality.
- Validate inputs and handle errors explicitly.
- Keep dependencies minimal.
- Document architectural decisions.
- Never invent test results or claim unverified functionality.

## Evaluation integrity
- Preserve individual evaluation results.
- Distinguish failures, errors, skipped cases, and inconclusive results.
- Make run comparisons traceable.
- Do not describe evaluation scores as proof of safety or correctness.

## Security
- Treat evaluation datasets as untrusted input.
- Do not execute arbitrary code from datasets.
- Keep core evaluation local-first.
- Never expose secrets or sensitive evaluation data in logs.
- Document security limitations.

## Approval requirements
- Planning documents must be reviewed before implementation.
- Run tests after meaningful changes.
- Report exact test results and unresolved issues.
- Do not publish or push releases without explicit approval.
