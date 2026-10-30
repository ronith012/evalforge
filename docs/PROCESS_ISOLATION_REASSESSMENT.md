# Process Isolation Reassessment (OD-06; THR-010; RR-01, RR-02)

Status: **Milestone 13 written reassessment. Documentation only. No isolation code is added in this milestone.**
Decision requested from the owner: whether the MVP keeps best-effort thread timeouts (recommended) and whether
isolation is planned for a later milestone.

## 1. What the code does now

- Each case runs its target in a daemon thread (`timeouts.Worker`). The runner waits for the configured timeout
  (`run.timeout_seconds` or a target's own `timeout_seconds`). After the timeout the case is recorded as
  `TARGET_TIMEOUT` with status ERROR, and the run continues (test: `test_timed_out_target_is_recorded_and_the_run_continues`).
- A thread that is still running after its timeout cannot be stopped in Python. It keeps running in the background.
  The number of such threads is counted and stored as `threads_possibly_running` in the manifest
  (tests: `test_timed_out_thread_is_counted_as_possibly_running`, `test_finished_threads_are_not_counted`).
- The timeout is therefore best-effort. It bounds how long the **run** waits. It does not bound what the target
  **does**: CPU use, memory, files written, or network calls continue after the timeout.
- Targets and custom evaluators are trusted code and run in the same process with the user's privileges (RR-01,
  THR-004). No sandbox is used.

This design is documented in the user-facing materials (TRD-072, TRD-073, TRD-075) and recorded in OD-06.

## 2. Threat this addresses

THR-010 (impact Medium, likelihood High while targets are slow): a target that loops after a timeout keeps consuming
resources, or a target writes files or makes calls after the run has moved on. A timeout alone is **not** a security
boundary (TRD-073). This is rated **High residual** in the threat model until isolation exists.

## 3. Options

| Option | What it gives | Costs and limits | Fit for MVP |
|---|---|---|---|
| A. Keep threads (current) | Bounds the wait for the run; no extra processes | Does not stop the target; no CPU, memory, or side-effect bound | Yes, as documented |
| B. Subprocess per case | Can terminate a stuck target; memory and CPU can be bounded by the OS | Target must be importable in a child process; results and I/O must be serialised; slower per case; different behaviour on Windows; signal handling differs by platform | No; changes the execution model |
| C. One subprocess per run | Stops the whole run; fewer processes than B | A single hung case still blocks the rest of the run unless the parent restarts the child; state across cases is shared | No |
| D. OS-level sandbox (containers, seccomp, sandbox-exec) | Strongest control over files and network | Platform-specific; not available uniformly; adds operational requirements; outside a zero-dependency library | No; outside the project's scope |
| E. Documented trust boundary only | No extra code; the user runs targets they trust | Relies on the user | Yes, combined with A |

## 4. Reassessment

1. The thread-based timeout is a **wait bound**, not an isolation control. The code and documentation already say so.
2. Options B and C change the execution model, the Windows behaviour, and the data path. Each needs its own design,
   tests on all three platforms, and owner approval. They are not required by the current requirements, which
   accept best-effort timeouts for the MVP (OD-06).
3. Option D is out of scope for a zero-dependency library and is left to users who need it.
4. **Recommendation:** keep option A with option E for the MVP. Record the residual risk RR-02 as High and present it
   for written acceptance (RESIDUAL_RISK_ACCEPTANCE). Revisit process isolation (option B) only after the MVP, with
   a separate design and approval.

## 5. What would change this decision

- A user report or evidence that timed-out targets cause harm in practice, such as stuck threads exhausting memory in CI.
- A requirement to evaluate untrusted targets. The product currently assumes trusted targets (THR-004, RR-01).
- A platform where threads cannot be left running safely.

## 6. Verification of the current design

The behaviours above are tested by the runner tests named in §1, and the documentation statements are checked by
`tests/test_security.py::test_user_facing_text_contains_no_banned_claims` only for overclaiming wording. No automated
test checks that the timeout documentation is complete; that is a documentation review item.
