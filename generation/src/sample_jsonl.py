#!/usr/bin/env python3
"""
sample_jsonl.py

Sample lines from a JSONL file into a new JSONL file, either by an exact
integer count (--int) or by a percentage of the total line count (--percent).

Usage:
    python sample_jsonl.py input.jsonl output.jsonl --int 500
    python sample_jsonl.py input.jsonl output.jsonl --percent 10
    python sample_jsonl.py input.jsonl output.jsonl --percent 2.5 --seed 42
"""

import argparse
import json
import math
import random
import sys


def count_lines(path):
    """Count non-blank lines in a file (streaming, memory-friendly)."""
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def parse_args():
    parser = argparse.ArgumentParser(
        description="Randomly sample lines from a JSONL file into a new JSONL file."
    )
    parser.add_argument("input", help="Path to the input .jsonl file")
    parser.add_argument("output", help="Path to write the sampled .jsonl file")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--percent",
        type=float,
        help="Percentage of total lines to sample (e.g. 10 for 10%%). "
        "Converted to an integer count via rounding.",
    )
    group.add_argument(
        "--int",
        dest="int_count",
        type=int,
        help="Exact number of lines to sample.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (optional).",
    )
    parser.add_argument(
        "--validate-json",
        action="store_true",
        help="Skip/validate that each sampled line is valid JSON (invalid lines are dropped).",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    total_lines = count_lines(args.input)
    if total_lines == 0:
        print("Error: input file has no non-blank lines.", file=sys.stderr)
        sys.exit(1)

    if args.percent is not None:
        if not (0 < args.percent <= 100):
            print("Error: --percent must be between 0 and 100.", file=sys.stderr)
            sys.exit(1)
        n_samples = round(total_lines * (args.percent / 100.0))
    else:
        n_samples = args.int_count
        if n_samples <= 0:
            print("Error: --int must be a positive integer.", file=sys.stderr)
            sys.exit(1)

    n_samples = min(n_samples, total_lines)

    # Reservoir sampling: single pass, O(n_samples) memory, works for huge files.
    reservoir = []
    with open(args.input, "r", encoding="utf-8") as f:
        seen = 0
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue

            if args.validate_json:
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    print(f"Warning: skipping invalid JSON line {seen + 1}", file=sys.stderr)
                    continue

            seen += 1
            if len(reservoir) < n_samples:
                reservoir.append(line)
            else:
                j = random.randint(0, seen - 1)
                if j < n_samples:
                    reservoir[j] = line

    # Shuffle so the selected sample isn't biased toward file order
    random.shuffle(reservoir)

    with open(args.output, "w", encoding="utf-8") as out:
        for line in reservoir:
            out.write(line + "\n")

    print(
        f"Sampled {len(reservoir)} / {total_lines} lines "
        f"({(len(reservoir) / total_lines) * 100:.2f}%) -> {args.output}"
    )


if __name__ == "__main__":
    main()