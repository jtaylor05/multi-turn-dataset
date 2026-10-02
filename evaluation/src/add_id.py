#!/usr/bin/env python3
"""Add sequential IDs to lines in a JSONL file."""

import argparse
import json
import os
import tempfile


def set_nested(obj: dict, json_path: str, value) -> None:
    """Set a value in a nested dict using a dot-separated path."""
    keys = json_path.split(".")
    for key in keys[:-1]:
        obj = obj.setdefault(key, {})
    obj[keys[-1]] = value


def add_ids(input_path: str, output_path: str, json_path: str, prefix: str | None) -> None:
    lines = []
    with open(input_path, "r") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                lines.append(line)
                continue

            obj = json.loads(line)
            id_value = f"{prefix}_{i}" if prefix else str(i)
            set_nested(obj, json_path, id_value)
            lines.append(json.dumps(obj))

    # Write to a temp file first to safely handle in-place replacement
    dir_name = os.path.dirname(output_path) or "."
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp") as tmp:
        tmp.write("\n".join(lines))
        if lines:
            tmp.write("\n")
        tmp_path = tmp.name

    os.replace(tmp_path, output_path)
    print(f"Wrote {len([l for l in lines if l])} records to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add sequential IDs to a JSONL file.")
    parser.add_argument("input", help="Path to the input JSONL file")
    parser.add_argument(
        "--json-path",
        default="id",
        help="Dot-separated JSON path for the ID field (default: 'id')",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="Prefix for the ID value. ID will be '<prefix>_<i>' or just '<i>' if omitted.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path. Defaults to overwriting the input file.",
    )
    args = parser.parse_args()

    output_path = args.output or args.input
    add_ids(args.input, output_path, args.json_path, args.prefix)