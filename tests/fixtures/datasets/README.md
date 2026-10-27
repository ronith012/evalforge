# Dataset test fixtures

All files here are **synthetic**. They were written for EvalForge tests and contain no real user,
customer, or proprietary data (DATA_HANDLING §13).

- `support_small.jsonl`: five valid cases covering tags, metadata, a missing `expected`, and `expected: null`.
- `support_small_crlf.jsonl`: the same cases with CRLF line endings.
- `hostile_payloads.jsonl`: strings that look like code or YAML/pickle tags. They must be loaded as
  plain data and never executed (TST-SEC-001, TST-SEC-002).

The same five cases as a JSON array are generated in the tests from `support_small.jsonl`, so no
second copy is stored.
