# Seeded regression pair (synthetic example)

All data is **synthetic**. The baseline and candidate targets are identical except for one fixture behaviour: the
candidate answers the case `greet-003` with a different greeting, so that case regresses from PASS to FAIL.

`expected_findings.json` lists the findings the comparison must produce, exactly. The test
`tests/test_e2e.py::test_seeded_regression_pair_produces_the_expected_findings` checks it.
