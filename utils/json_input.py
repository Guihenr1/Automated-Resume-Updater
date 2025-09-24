import json
import sys
from typing import Optional

def read_json_list_of_dicts(prompt: str, allow_single_object: bool = True, allow_empty: bool = True) -> Optional[list[dict]]:
    raw = input(prompt).strip()

    if not raw:
        if allow_empty:
            return None
        print("Input required but empty.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if isinstance(data, dict):
        if not allow_single_object:
            print("Expected a JSON array of objects, got a JSON object.", file=sys.stderr)
            sys.exit(1)
        data = [data]
    elif not isinstance(data, list):
        print("Expected a JSON array or object.", file=sys.stderr)
        sys.exit(1)

    if not all(isinstance(item, dict) for item in data):
        print("Each item must be a JSON object.", file=sys.stderr)
        sys.exit(1)

    return data