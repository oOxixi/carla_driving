from __future__ import annotations

import json

from .error_cases import ERROR_CASES



with open(
    "integration/day21/qwen_error_cases.json",
    "w",
    encoding="utf-8"
) as f:


    json.dump(
        ERROR_CASES,
        f,
        indent=2,
        ensure_ascii=False
    )


print(
    "saved qwen_error_cases.json"
)
