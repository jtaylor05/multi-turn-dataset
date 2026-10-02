#!/usr/bin/env python3
"""
rewrap.py

Combines "simple" JSONL files (containing only dialogue_id + a flat list of
turns like {"role": ..., "content": ...}) with "detailed" JSONL files
(containing dialogue_id, metadata, and a richer turns structure like
{"turn_id": ..., "messages": [...]}).

For each record in a detailed file, the script looks up the matching
dialogue_id across ALL provided simple files, rewraps the simple file's flat
turns into the detailed format's turn/messages shape (best effort - it does
not try to reconstruct code_snippet, reasoning_chain, etc.), and replaces the
detailed record's "turns" field with that rewrapped version. All other
top-level fields/metadata from the detailed record are left untouched.

If a dialogue_id in a detailed file has no match in any simple file, that
record is skipped entirely.

Output files are written to the given output directory (created if it
doesn't exist) using the same filenames as the input detailed files.

Usage:
    python rewrap.py \
        --simple simple1.jsonl simple2.jsonl \
        --detailed detailed1.jsonl detailed2.jsonl \
        --output-dir ./combined
"""

import argparse
import json
import os
import sys
import re

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")


def _strip_code_fence(s):
    """Strip a leading ```json / ``` and trailing ``` from a string, if present."""
    return _CODE_FENCE_RE.sub("", s.strip())


def load_jsonl(path):
    """Yield parsed JSON objects from a JSONL file, one per line."""
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(
                    f"Warning: skipping malformed JSON in {path} line {line_num}: {e}",
                    file=sys.stderr,
                )


def build_simple_turns_index(simple_files):
    """
    Build a dict mapping dialogue_id -> flat list of turns
    (e.g. [{"role": "user", "content": "..."}, ...])
    by reading all provided simple files.
    """
    index = {}
    for path in simple_files:
        for record in load_jsonl(path):
            dialogue_id = record.get("dialogue_id")
            turns = record.get("turns")
            if dialogue_id is None or turns is None:
                print(
                    f"Warning: record missing 'dialogue_id' or 'turns' in {path}, skipping",
                    file=sys.stderr,
                )
                continue
            if dialogue_id in index:
                print(
                    f"Warning: duplicate dialogue_id '{dialogue_id}' found in simple "
                    f"files; overwriting previous entry with the one from {path}",
                    file=sys.stderr,
                )
            index[dialogue_id] = turns
    return index


def expand_message_payload(msg):
    """Return one or more message dicts for a flat turn entry.

    The function first tries to parse the message's content as JSON. If the
    parsed payload is a dict containing "content" and/or "code_snippet",
    those values are emitted as messages with the original role. Otherwise,
    the original content is preserved as a single message.
    """
    if not isinstance(msg, dict):
        return []

    role = msg.get("role")
    raw_content = msg.get("content")

    if isinstance(raw_content, str):
        try:
            parsed = json.loads(_strip_code_fence(raw_content))
        except (TypeError, ValueError):
            parsed = None
    else:
        parsed = raw_content

    if isinstance(parsed, dict):
        expanded_messages = {"role" : role}
        if "content" in parsed and parsed.get("content") is not None:
            expanded_messages["content"] = parsed.get("content")
        if "code_snippet" in parsed and parsed.get("code_snippet") is not None:
            expanded_messages["code_snippet"] = parsed.get("code_snippet")
        if expanded_messages:
            return [expanded_messages]
        
    return [{"role": role, "content": raw_content}]


def rewrap_turns(flat_turns):
    """
    Best-effort conversion of a flat turns list
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
    into the detailed format's turn structure:
        [{"turn_id": 1, "messages": [{"role": "user", "content": "..."}, ...]}, ...]

    A new turn group starts every time a message with role "user" is
    encountered. This naturally groups a user message together with any
    assistant message(s) that follow it, mirroring the shape seen in the
    detailed files (one turn_id per user/assistant exchange).
    """
    wrapped_turns = []
    current_messages = []
    turn_id = 0

    for msg in flat_turns:
        if not isinstance(msg, dict):
            print(f"Found non-dict entry: {msg:10}")
            continue
        role = msg.get("role")
        if role == "user" and current_messages:
            # Close out the previous turn group before starting a new one.
            turn_id += 1
            wrapped_turns.append({"turn_id": turn_id, "messages": current_messages})
            current_messages = []

        for expanded_msg in expand_message_payload(msg):
            current_messages.append(expanded_msg)

    if current_messages:
        turn_id += 1
        wrapped_turns.append({"turn_id": turn_id, "messages": current_messages})

    return wrapped_turns


def combine(simple_files, detailed_files, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    simple_index = build_simple_turns_index(simple_files)

    for detailed_path in detailed_files:
        out_path = os.path.join(output_dir, os.path.basename(detailed_path))
        written = 0
        skipped = 0

        with open(out_path, "w", encoding="utf-8") as out_f:
            for record in load_jsonl(detailed_path):
                dialogue_id = record.get("dialogue_id")
                if dialogue_id is None:
                    print(
                        f"Warning: record missing 'dialogue_id' in {detailed_path}, skipping",
                        file=sys.stderr,
                    )
                    skipped += 1
                    continue

                flat_turns = simple_index.get(dialogue_id)
                if flat_turns is None:
                    # No matching simple-file entry; skip this record.
                    skipped += 1
                    continue

                combined_record = dict(record)  # shallow copy, preserves all metadata
                combined_record["turns"] = rewrap_turns(flat_turns)

                out_f.write(json.dumps(combined_record, ensure_ascii=False) + "\n")
                written += 1

        print(
            f"{detailed_path} -> {out_path}: wrote {written} record(s), "
            f"skipped {skipped} unmatched/invalid record(s)"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Combine simple turn-only JSONL files into detailed JSONL files by dialogue_id."
    )
    parser.add_argument(
        "--simple",
        nargs="+",
        required=True,
        help="Paths to simple JSONL files (dialogue_id + flat 'turns' list).",
    )
    parser.add_argument(
        "--detailed",
        nargs="+",
        required=True,
        help="Paths to detailed JSONL files (dialogue_id + metadata + structured 'turns').",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write the combined output files to (created if missing).",
    )
    args = parser.parse_args()

    combine(args.simple, args.detailed, args.output_dir)


if __name__ == "__main__":
    main()