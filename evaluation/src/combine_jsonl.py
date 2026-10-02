#!/usr/bin/env python3
"""
Merge multiple JSONL files into a single JSONL file.

Usage:
    python merge_jsonl.py file1.jsonl file2.jsonl file3.jsonl -o output.jsonl
    python merge_jsonl.py *.jsonl -o merged.jsonl
"""

import argparse
import json
import sys
from pathlib import Path


def merge_jsonl(input_files: list[str], output_file: str, skip_invalid: bool = False) -> None:
    output_path = Path(output_file)
    total_lines = 0
    skipped_lines = 0

    with output_path.open("w", encoding="utf-8") as out_f:
        for input_file in input_files:
            input_path = Path(input_file)

            if not input_path.exists():
                print(f"Warning: File not found, skipping: {input_file}", file=sys.stderr)
                continue

            file_lines = 0
            with input_path.open("r", encoding="utf-8") as in_f:
                for line_num, line in enumerate(in_f, start=1):
                    line = line.strip()
                    if not line:
                        continue  # skip blank lines

                    try:
                        # Validate that the line is valid JSON
                        json.loads(line)
                        out_f.write(line + "\n")
                        file_lines += 1
                    except json.JSONDecodeError as e:
                        if skip_invalid:
                            print(
                                f"Warning: Skipping invalid JSON on line {line_num} "
                                f"of {input_file}: {e}",
                                file=sys.stderr,
                            )
                            skipped_lines += 1
                        else:
                            print(
                                f"Error: Invalid JSON on line {line_num} of {input_file}: {e}\n"
                                f"Use --skip-invalid to ignore bad lines.",
                                file=sys.stderr,
                            )
                            sys.exit(1)

            print(f"  {input_file}: {file_lines} lines")
            total_lines += file_lines

    print(f"\nDone! Wrote {total_lines} lines to '{output_file}'.")
    if skipped_lines:
        print(f"Skipped {skipped_lines} invalid lines.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge multiple JSONL files into a single JSONL file."
    )
    parser.add_argument(
        "input_files",
        nargs="+",
        metavar="INPUT",
        help="One or more input .jsonl files to merge.",
    )
    parser.add_argument(
        "-o", "--output",
        default="merged.jsonl",
        metavar="OUTPUT",
        help="Path for the merged output file (default: merged.jsonl).",
    )
    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="Skip lines with invalid JSON instead of exiting with an error.",
    )

    args = parser.parse_args()

    print(f"Merging {len(args.input_files)} file(s) into '{args.output}'...")
    merge_jsonl(args.input_files, args.output, skip_invalid=args.skip_invalid)