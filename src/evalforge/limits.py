# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Size and count limits (TRD §4.2, §5.6; DATA_MODELS §4.1).

These are the proposed defaults from the planning documents. They are not yet confirmed by the
owner as final values.
"""

from typing import Final

MAX_DATASET_BYTES: Final = 50 * 1024 * 1024
MAX_CASES: Final = 100_000
MAX_LINE_BYTES: Final = 1024 * 1024
MAX_JSON_DEPTH: Final = 64
MAX_STRING_BYTES: Final = 1024 * 1024
MAX_TAGS: Final = 32
MAX_TAG_CHARS: Final = 64
MAX_CASE_ID_CHARS: Final = 128
MAX_VALIDATION_ERRORS: Final = 100

MAX_EVALUATOR_NAME_CHARS: Final = 64
MAX_EVALUATOR_MESSAGE_CHARS: Final = 500
MAX_EVALUATOR_DETAILS_BYTES: Final = 16 * 1024
MAX_REGEX_CHARS: Final = 512
MAX_REQUIRED_PATHS: Final = 32
MAX_PATH_CHARS: Final = 256

MAX_ERROR_MESSAGE_CHARS: Final = 500
MAX_TARGET_NAME_CHARS: Final = 128
MAX_TIMEOUT_SECONDS: Final = 3600
