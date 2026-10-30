# Quick start (synthetic example)

All data in this example is **synthetic**. The cases are invented, the target returns fixed answers, and no real
customer or model output is involved. Every case carries the tag `synthetic`.

Run it from this directory. The test suite copies the directory to a temporary location first, so the repository is
never written to.

```
evalforge config validate
evalforge dataset validate dataset.jsonl
evalforge run
evalforge run --format json
evalforge compare <baseline-run-id> <candidate-run-id> --format json
```

`support_bot.py` is the target. It is trusted code: EvalForge imports it when a run starts.
