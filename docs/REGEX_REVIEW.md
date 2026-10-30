# Regex Review (SECURITY §7; THR-003; RR-03)

Status: **Milestone 13 review. Findings and measurements recorded; one partial mitigation added.**

## 1. Scope

Every regular expression in `src/evalforge`, found by a search of `re.` calls:

| Location | Pattern source | Risk |
|---|---|---|
| `evaluators/builtin.py` (`RuleBased`, `regex` rule) | **User configuration** | Can be slow (Python `re` has no timeout) |
| `config.py` (`CALLABLE_RE`, `DOTTED_PATH_RE`, `EVALUATOR_NAME_RE`) | Fixed; applied to configuration strings | Checked below |
| `models.py` (`CASE_ID_RE`, `EVALUATOR_NAME_RE`, `HASH_RE`, `SCHEMA_RE`) | Fixed; applied to stored or input text | Anchored, bounded classes |
| `redaction.py` (credential patterns) | Fixed; applied to stored text | Bounded classes; applied after the text length is already capped |
| `reporting/sanitize.py` | Fixed character class | Single class, no repetition |

## 2. Findings

### 2.1 The user-supplied rule pattern is the risk

A nested repeat such as `(a+)+$` takes exponential time in Python's backtracking engine. The measurement below uses
the threat-model example, a pattern run against `a`×n followed by `b`, on one run per size (Python 3.13.5, macOS arm64):

| n (a's) | Time to return a result |
|---|---|
| 14 | 2.4 ms |
| 16 | 8.5 ms |
| 18 | 27.7 ms |
| 20 | 110.8 ms |
| 22 | 380.9 ms |

Each step of two characters multiplies the time by about 3.5 to 4. At 30 characters the time is in the order of minutes.
A single run did not finish for a 10,000-character input, so no measurement was taken for that size.

**The existing output cap does not prevent this.** The rule evaluator refuses outputs over 1 MiB (decision D-5, an
ERROR, never a quality FAIL). A 30-character input is far below that limit, so the cap does not apply.

### 2.2 Mitigation added in Milestone 13 (partial)

`config._regex_problem` now refuses a pattern in which a repeated group contains a repeat, such as `(a+)+`, `(\w*)*`,
or `(ab+)*`. The check is a single regular expression over the pattern text. Tests:
`test_nested_repeat_patterns_are_refused_at_configuration` (refused) and `test_ordinary_patterns_are_accepted`
(`\d+`, `(ab)+`, `(a|b)+`, `[a-z]+@[a-z]+` accepted).

What the guard does **not** catch:

- overlapping alternations inside a repeat, such as `(a|aa)+`, `(a|a?)+`;
- patterns where the exponential behaviour comes from a backreference or from lookaround;
- nested repeats written with the `{m,n}` quantifier forms only partly covered (`(a+){2,}` is covered; `(?:a|a)+` is not);
- patterns that are slow for reasons other than nesting.

Because it is a heuristic, the guard is a partial mitigation. RR-03 remains open until the owner accepts it or a
complete control is chosen (see §4).

### 2.3 Fixed patterns are linear

Measured on 200,000-character inputs (Python 3.13.5):

| Pattern | Input | Result | Time |
|---|---|---|---|
| `CALLABLE_RE` | `a.` repeated, then `!` | no match | 3.5 ms |
| `CALLABLE_RE` | `a` × 200,000, then `:` | no match | 3.2 ms |
| `DOTTED_PATH_RE` | `a.` repeated, then `!` | no match | 4.1 ms |

Their repeated groups begin with a literal `.`, so each repetition is unambiguous and matching does not backtrack
exponentially.

### 2.4 Inputs to the redaction patterns

The credential patterns are applied to text that has already been capped by the output limits, and each is a
bounded character class with a fixed prefix. They contain no nested repeats.

## 3. Limits that apply

- Pattern length: at most 512 characters (TRD-091; `limits.MAX_REGEX_CHARS`).
- Output length for the regex rule: at most 1 MiB; over that is an ERROR with `input_too_long` (D-5).
- Compilation errors are reported as configuration errors, not run errors.
- Regex matching is not interrupted by a timeout. Python's `re` cannot be stopped from another thread.

## 4. Options for the owner (RR-03)

1. **Accept RR-03** with the partial guard, the documented limits, and this review. Users with untrusted patterns
   must not use `RuleBased` on large outputs.
2. **Run regex matching in a separate process with a deadline.** Complete for the timeout, but adds a process per
   check and is the same design question as OD-06. Deferred to the isolation reassessment.
3. **Replace `re` with a linear-time engine** (a third-party dependency). Conflicts with the zero-runtime-dependency
   rule (OD-15).

Recommendation: option 1 for the MVP, with the warning in the user documentation, and option 2 considered together with
process isolation after the MVP (PROCESS_ISOLATION_REASSESSMENT).

## 5. Tests

- `tests/test_security.py::test_regex_pattern_length_is_limited`
- `tests/test_security.py::test_nested_repeat_patterns_are_refused_at_configuration`
- `tests/test_security.py::test_ordinary_patterns_are_accepted`
- `tests/test_security.py::test_rule_based_input_is_capped_before_matching`
