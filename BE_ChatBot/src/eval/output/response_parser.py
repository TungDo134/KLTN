from __future__ import annotations

import json
import re
from typing import Any


FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL)


def _find_balanced_json_object(text: str) -> str | None:
    end = text.rfind("}")
    if end == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(end, -1, -1):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "}":
            depth += 1
        elif char == "{":
            depth -= 1
            if depth == 0:
                return text[index : end + 1]

    return None


def extract_json_block(text: str) -> str | None:
    matches = FENCED_JSON_RE.findall(text or "")
    if matches:
        return matches[-1].strip()
    return _find_balanced_json_object(text or "")


def parse_response_plan(text: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    block = extract_json_block(text)
    if not block:
        return False, None, "No JSON object found in response."

    try:
        parsed = json.loads(block)
    except json.JSONDecodeError as exc:
        return False, None, f"Invalid JSON: {exc}"

    if not isinstance(parsed, dict):
        return False, None, "JSON root is not an object."
    return True, parsed, None
