"""
Pairs Claude Batch API input and output JSONL files.

The custom_id scheme is: "id_0", "id_01", "id_02", ..., "id_0N"
where the suffix (or absence of one) corresponds to the 0-based line index.
"""

import json
import argparse


def parse_custom_id(custom_id: str, prefix: str) -> int:
    """
    Extracts the line index from a custom_id of the form "id_0", "id_01", "id_02", etc.

    "id_0"  → 0
    "id_01" → 1
    "id_02" → 2
    "id_0N" → N
    """
    if not custom_id.startswith(prefix):
        raise ValueError(f"Unexpected custom_id format: '{custom_id}'")

    suffix = custom_id[len(prefix):]  # Everything after "id_0"

    if suffix == "":
        return 0  # "id_0" itself is index 0
    else:
        return int(suffix) + 1  # "id_01" → 1, "id_02" → 2, etc.


def load_jsonl(path: str) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def pair_files(input_path: str, output_path: str, paired_path: str, prefix: str) -> None:
    input_lines = load_jsonl(input_path)
    output_lines = load_jsonl(output_path)

    print(f"Input rows:  {len(input_lines)}")
    print(f"Output rows: {len(output_lines)}")

    # Index output records by their resolved line number
    output_by_index: dict[int, dict] = {}
    for record in output_lines:
        custom_id = record["custom_id"]
        idx = parse_custom_id(custom_id, prefix)
        if idx in output_by_index:
            print(f"WARNING: Duplicate resolved index {idx} for custom_id '{custom_id}'")
        output_by_index[idx] = record

    paired = []
    missing = []

    for i, input_record in enumerate(input_lines):
        if i not in output_by_index:
            missing.append(i)
            print(f"WARNING: No output found for input line {i}")
            continue

        output_record = output_by_index[i]

        # Extract the response text if the result succeeded
        response_text = None
        result = output_record.get("result", {})
        if result.get("type") == "succeeded":
            content_blocks = result.get("message", {}).get("content", [])
            response_text = " ".join(
                block.get("text", "") for block in content_blocks if block.get("type") == "text"
            )

        paired.append({
            "line_index": i,
            "custom_id": output_record["custom_id"],
            "input": input_record,
            "output": output_record,
            "response_text": response_text,
        })

    # Write paired output
    with open(paired_path, "w", encoding="utf-8") as f:
        for record in paired:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nPaired {len(paired)} records → {paired_path}")
    if missing:
        print(f"Missing outputs for {len(missing)} input lines: {missing}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pair Claude Batch API input and output JSONL files.")
    parser.add_argument("input",  help="Path to the input JSONL file")
    parser.add_argument("output", help="Path to the output JSONL file")
    parser.add_argument("-p", "--prefix", required=False, help="Custom ID prefix (default: 'id_0')", default="id_0")
    parser.add_argument("paired", help="Path to write the paired JSONL file")
    args = parser.parse_args()

    pair_files(args.input, args.output, args.paired, args.prefix)