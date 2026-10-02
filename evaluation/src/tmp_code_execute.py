#!/usr/bin/env python3
"""
run_tests.py — Execute code+test entries from a JSONL file.

Usage:
    python run_tests.py input.jsonl \
        --code_path results.code \
        --test_path results.tests \
        --id_path metadata.submission_id

Output:
    input.out.jsonl — one line per input line:
        { "<last_key_of_id_path>": <id_value>, "result": <execute() return value> }
"""

import argparse
import json
import sys
import multiprocessing
from pathlib import Path

from .code_eval import unsafe_execute

def execute(combined_code: str, timeout: float = 2.0) -> dict:
    manager = multiprocessing.Manager()
    result = manager.list()
 
    p = multiprocessing.Process(
        target=unsafe_execute,
        args=(combined_code, timeout, result, False),
    )
    p.start()
    p.join(timeout=timeout + 1)  # give a little extra for process overhead
 
    if p.is_alive():
        p.kill()
        return {"status": "timed out", "runtime": timeout}
 
    if not result:
        return {"status": "no result", "runtime": -1}
 
    status, runtime = result[0]
    return {"status": status, "runtime": runtime}

# ---------------------------------------------------------------------------
# JSON-path helpers
# ---------------------------------------------------------------------------

def _parse_path(path_str: str) -> list[str]:
    """Split 'a.b.c' into ['a', 'b', 'c']."""
    parts = [p for p in path_str.split(".") if p]
    if not parts:
        raise ValueError(f"Invalid path: {path_str!r}")
    return parts


def _get(obj: dict, parts: list[str], path_str: str):
    """Drill into nested dict using pre-parsed key parts."""
    cur = obj
    for i, key in enumerate(parts):
        if not isinstance(cur, dict):
            traversed = ".".join(parts[:i])
            raise KeyError(
                f"Path '{path_str}': expected a dict at '{traversed}', "
                f"got {type(cur).__name__}"
            )
        if key not in cur:
            traversed = ".".join(parts[: i + 1])
            raise KeyError(f"Path '{path_str}': key '{traversed}' not found")
        cur = cur[key]
    return cur


def _validate_path(first_record: dict, path_str: str, flag_name: str) -> list[str]:
    """Parse and validate a dot-path against the first JSONL record."""
    parts = _parse_path(path_str)
    try:
        _get(first_record, parts, path_str)
    except KeyError as exc:
        sys.exit(f"Error: --{flag_name} {exc}")
    return parts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Execute code+test pairs from a JSONL file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("input", help="Path to the input .jsonl file")
    p.add_argument(
        "--code-path",
        required=True,
        help="Dot-separated path to the code string in each record (e.g. 'results.code')",
    )
    p.add_argument(
        "--test-path",
        required=True,
        help="Dot-separated path to the test-case string in each record (e.g. 'results.tests')",
    )
    p.add_argument(
        "--id-path",
        required=True,
        help="Dot-separated path to the ID value in each record (e.g. 'metadata.submission_id'). "
             "The final key segment is used as the output field name.",
    )
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = build_parser().parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"Error: input file not found: {input_path}")

    # Read all lines up front so we can validate paths on the first record
    # before doing any work.
    lines = [ln for ln in input_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        sys.exit("Error: input file is empty")

    try:
        first_record = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        sys.exit(f"Error: could not parse line 1 as JSON: {exc}")

    # Validate all three paths against the first record.
    code_parts = _validate_path(first_record, args.code_path, "code_path")
    test_parts = _validate_path(first_record, args.test_path, "test_path")
    id_parts   = _validate_path(first_record, args.id_path,   "id_path")

    # The output field name is the last segment of id_path.
    id_field = id_parts[-1]

    output_path = input_path.with_suffix(".out.jsonl")

    processed = 0
    errors = 0

    with output_path.open("w", encoding="utf-8") as out_f:
        for lineno, raw in enumerate(lines, start=1):
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"Warning: skipping line {lineno} (JSON parse error): {exc}", file=sys.stderr)
                errors += 1
                continue

            try:
                code      = _get(record, code_parts, args.code_path)
                test_code = _get(record, test_parts, args.test_path)
                record_id = _get(record, id_parts,   args.id_path)
            except KeyError as exc:
                print(f"Warning: skipping line {lineno}: {exc}", file=sys.stderr)
                errors += 1
                continue

            if not isinstance(code, str):
                print(
                    f"Warning: skipping line {lineno}: --code_path value is "
                    f"{type(code).__name__}, expected str",
                    file=sys.stderr,
                )
                errors += 1
                continue

            if not isinstance(test_code, str):
                print(
                    f"Warning: skipping line {lineno}: --test_path value is "
                    f"{type(test_code).__name__}, expected str",
                    file=sys.stderr,
                )
                errors += 1
                continue

            combined = code + "\n" + test_code

            try:
                result = execute(combined)
            except NotImplementedError:
                sys.exit(
                    "Error: execute() is not implemented. "
                    "Please replace the stub in run_tests.py with your real logic."
                )
            except Exception as exc:  # noqa: BLE001
                print(
                    f"Warning: execute() raised on line {lineno} "
                    f"(id={record_id!r}): {exc}",
                    file=sys.stderr,
                )
                result = {"error": str(exc)}
                errors += 1

            out_record = {id_field: record_id, "result": result}
            out_f.write(json.dumps(out_record, ensure_ascii=False) + "\n")
            processed += 1

    print(
        f"Done. {processed} record(s) written to {output_path}"
        + (f", {errors} warning(s)." if errors else "."),
        file=sys.stderr,
    )