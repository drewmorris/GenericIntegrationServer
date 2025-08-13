from __future__ import annotations

from typing import Any, Mapping
import re

_SECRET_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"token$",
        r"secret$",
        r"password$",
        r"api[_-]?key$",
        r"access[_-]?token$",
        r"refresh[_-]?token$",
        r"client[_-]?secret$",
    ]
]


def _is_secret_key(key: str) -> bool:
    return any(p.search(key) for p in _SECRET_PATTERNS)


def mask_secrets(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {k: ("***" if _is_secret_key(str(k)) else mask_secrets(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask_secrets(v) for v in obj]
    return obj 