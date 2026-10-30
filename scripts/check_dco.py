#!/usr/bin/env python3
# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Check that every commit in a range carries a Developer Certificate of Origin sign-off.

OD-31 and OD-32 apply.

Usage: python scripts/check_dco.py BASE HEAD

A commit passes when its message has a line of the form ``Signed-off-by: Name <email>``. The check
does not verify the sign-off's content; it enforces that the trailer is present. Exit status 0 means
every commit passed; 1 means at least one commit lacks a sign-off; 2 means the arguments are wrong.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Sequence

SIGNOFF: re.Pattern[str] = re.compile(r"^Signed-off-by: .+ <[^<>\s]+@[^<>\s]+>$", re.MULTILINE)


def has_signoff(message: str) -> bool:
    """True when the commit message contains a sign-off trailer."""
    return SIGNOFF.search(message) is not None


def commits_in_range(base: str, head: str) -> list[str]:
    """Commit IDs reachable from head and not from base, oldest first."""
    output = subprocess.run(
        ["git", "rev-list", "--reverse", f"{base}..{head}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in output.splitlines() if line]


def message_of(commit: str) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%B", commit],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def main(argv: Sequence[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("usage: check_dco.py BASE HEAD\n")
        return 2
    base, head = argv
    commits = commits_in_range(base, head)
    missing = [commit for commit in commits if not has_signoff(message_of(commit))]
    for commit in missing:
        sys.stderr.write(f"error: commit {commit[:12]} has no 'Signed-off-by:' line (DCO)\n")
    if missing:
        return 1
    sys.stdout.write("DCO: every commit in the range is signed off.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
