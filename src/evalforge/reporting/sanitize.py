# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Terminal sanitisation (SECURITY §6; THREAT_MODEL THR-009).

Text output shows control characters and bidirectional overrides as ``\\uXXXX`` escapes, so a
reader sees that something was there and the terminal cannot be steered by it. TAB and LF are
kept. CR is escaped.
JSON output is not sanitised: JSON escaping already makes the data safe, and the JSON is data.
"""

from __future__ import annotations

import re
from typing import Final

_UNSAFE: Final = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f‪-‮⁦-⁩]")


def sanitize_text(text: str) -> str:
    """Return ``text`` with every control or bidirectional-override character escaped."""
    return _UNSAFE.sub(lambda match: f"\\u{ord(match.group()):04x}", text)
