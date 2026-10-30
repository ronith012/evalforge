## Summary

<!-- What changes, and why. Link the requirement or decision (PRD, TRD, OPEN_DECISIONS) if one applies. -->

## Checks

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] `uv run mypy --strict` passes
- [ ] New behaviour has tests; traceability register updated if a requirement changed
- [ ] Documentation and CHANGELOG updated where behaviour changed
- [ ] No secrets, real data, or run directories are included

## Sign-off

- [ ] Every commit has a `Signed-off-by:` line (Developer Certificate of Origin; see CONTRIBUTING.md)
