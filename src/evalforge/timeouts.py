# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Best-effort target timeouts (TRD-070 to TRD-075; OD-06).

A target call runs in a daemon worker thread. The caller waits up to the deadline. Python cannot
stop a thread, so a timed-out call may keep running after the run has recorded ``TARGET_TIMEOUT``.
The runner counts such threads (``threads_possibly_running``). Nothing here claims that a timed-out
target has been stopped.
"""

from __future__ import annotations

import threading

from evalforge.canon import JSONValue
from evalforge.targets import Target, TargetInvocation, invoke_target


class Worker:
    """Runs one target call in a daemon thread and keeps its outcome."""

    def __init__(self, target: Target, case_input: JSONValue) -> None:
        self._target = target
        self._input = case_input
        self.invocation: TargetInvocation | None = None
        self.error: BaseException | None = None
        self.thread = threading.Thread(target=self._run, name="evalforge-target", daemon=True)

    def _run(self) -> None:
        try:
            self.invocation = invoke_target(self._target, self._input)
        except BaseException as exc:  # reported to the runner, which decides what it means
            self.error = exc

    def start(self) -> None:
        self.thread.start()


def wait_for(worker: Worker, seconds: float) -> bool:
    """Wait up to ``seconds`` for the worker. Returns True when the worker has finished."""
    worker.thread.join(seconds)
    return not worker.thread.is_alive()
