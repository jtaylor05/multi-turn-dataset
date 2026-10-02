"""
Batch-transforms JSONL files of conversation entries.

Each input JSONL file contains one whole entry per line, e.g.:
    {"id": ..., "metadata": {...}, "conversation": [ {role, content}, ... ], ...}
or (older nested format):
    {"id": ..., "metadata": {...}, "turns": [ {"turn_id": ..., "messages": [...]}, ... ], ...}

For every message found in an entry (however many there are), this script
replaces the message's raw "content" string with the flat schema:

    {"role": ..., "content": ..., "code_snippet": ..., "metadata": {"contains_code": ..., "intent": ""}}

All other top-level fields on the entry (id, metadata, additional data, etc.)
are left untouched. Each output file has the same number of lines as its
input file (one line per entry) and the same filename, written into the
given output directory.

Usage:
    python3 extract_code_snippets.py <input_dir> <output_dir>
"""

import json
import os
import re
import sys


# Matches fenced code blocks: ```lang\ncode\n```
CODE_FENCE_RE = re.compile(r"```([a-zA-Z0-9_+\-]*)\n(.*?)```", re.DOTALL)

# Heuristic markers for the start of an *unfenced* code block pasted inline with prose
CODE_START_RE = re.compile(
    r"^\s*(import\s+\w|from\s+\w+\s+import|def\s+\w|class\s+\w|@\w)"
)


def extract_text_and_code(content):
    """
    Given a raw message content string (prose possibly interleaved with
    ```fenced``` or unfenced code), return (text, code_snippet) where:
      - text is all prose concatenated (fences/code removed), whitespace-trimmed
      - code_snippet is all code concatenated (joined by blank lines), or ""
        if no code was found
    """
    if not isinstance(content, str):
        # Already-structured content (e.g. previously transformed) - leave as-is
        return content, ""

    text_parts = []
    code_parts = []

    pos = 0
    for m in CODE_FENCE_RE.finditer(content):
        start, end = m.span()

        if start > pos:
            pre_text, pre_code = _split_embedded_code(content[pos:start])
            if pre_text:
                text_parts.append(pre_text)
            if pre_code:
                code_parts.append(pre_code)

        code = m.group(2)
        if code.endswith("\n"):
            code = code[:-1]
        if code.strip():
            code_parts.append(code.strip("\n"))

        pos = end

    if pos < len(content):
        tail_text, tail_code = _split_embedded_code(content[pos:])
        if tail_text:
            text_parts.append(tail_text)
        if tail_code:
            code_parts.append(tail_code)

    text = "\n\n".join(p.strip() for p in text_parts if p.strip()).strip()
    code_snippet = "\n\n".join(p.strip("\n") for p in code_parts if p.strip()).strip()

    return text, code_snippet


def _split_embedded_code(text):
    """
    Handle a chunk of text (outside any ``` fence) that may itself contain an
    unfenced block of pasted code (e.g. a user pastes a function directly
    after a sentence, with no markdown fences at all).
    Returns (prose_part, code_part).
    """
    lines = text.split("\n")
    start_idx = None
    for i, line in enumerate(lines):
        if CODE_START_RE.match(line):
            start_idx = i
            break

    if start_idx is None:
        return text.strip("\n"), ""

    prose_part = "\n".join(lines[:start_idx]).strip("\n")
    code_part = "\n".join(lines[start_idx:]).strip("\n")
    return prose_part, code_part


def transform_message(message):
    role = message.get("role", "")
    raw_content = message.get("content", "")

    text, code_snippet = extract_text_and_code(raw_content)

    return {
        "role": role,
        "content": text,
        "code_snippet": code_snippet,
        "metadata": {
            "contains_code": bool(code_snippet),
            "intent": "",
        },
    }


def find_and_transform_messages(entry):
    """
    Locate the message list(s) inside an entry and transform each message
    in place. Supports:
      - entry["conversation"]: a flat list of message dicts
      - entry["messages"]: a flat list of message dicts
      - entry["turns"]: a list of {"turn_id": ..., "messages": [...]}
    Whichever of these keys is present is used; the entry is modified and
    returned (same top-level structure, transformed messages in place).
    """
    if "conversation" in entry and isinstance(entry["conversation"], list):
        entry["conversation"] = [transform_message(m) for m in entry["conversation"]]

    elif "messages" in entry and isinstance(entry["messages"], list):
        entry["messages"] = [transform_message(m) for m in entry["messages"]]

    elif "turns" in entry and isinstance(entry["turns"], list):
        for turn in entry["turns"]:
            if isinstance(turn.get("messages"), list):
                turn["messages"] = [transform_message(m) for m in turn["messages"]]

    return entry


def process_file(input_path, output_path):
    count_entries = 0
    with open(input_path, "r", encoding="utf-8") as in_f, \
         open(output_path, "w", encoding="utf-8") as out_f:
        for line in in_f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            entry = find_and_transform_messages(entry)
            out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            count_entries += 1
    return count_entries


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 transform_messages.py <input_dir> <output_dir>")
        sys.exit(1)

    input_dir, output_dir = sys.argv[1], sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)

    jsonl_files = [f for f in os.listdir(input_dir) if f.endswith(".jsonl")]
    if not jsonl_files:
        print(f"No .jsonl files found in {input_dir}")
        return

    total_entries = 0
    for filename in jsonl_files:
        in_path = os.path.join(input_dir, filename)
        out_path = os.path.join(output_dir, filename)
        n = process_file(in_path, out_path)
        total_entries += n
        print(f"{filename}: transformed {n} entries -> {out_path}")

    print(f"Done. {len(jsonl_files)} files, {total_entries} entries total.")


if __name__ == "__main__":
    main()