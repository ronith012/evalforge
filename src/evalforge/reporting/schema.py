# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Access to the published JSON Schema files (PRD-F-025; TRD §10)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

SCHEMA_DIR: Final = Path(__file__).resolve().parent / "schemas"


def schema_path(name: str) -> Path:
    """Path of a published schema file. Names are plain file names; no directories are allowed."""
    if "/" in name or "\\" in name or name in ("", ".", ".."):
        raise ValueError(f"not a schema file name: {name!r}")
    return SCHEMA_DIR / name


def load_schema(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads(schema_path(name).read_text(encoding="utf-8"))
    return data
