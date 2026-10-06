"""Shared helpers for tool modules."""
import json
from typing import Any


def to_json(result: Any) -> str:
    """Serialise an API result to pretty JSON.

    Error strings returned by the client (``"ERROR: ..."``) are passed
    through unchanged so tools never raise on API failures.
    """
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2, ensure_ascii=False)