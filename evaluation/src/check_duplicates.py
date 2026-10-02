#!/usr/bin/env python3
"""
check_duplicates.py  --  Flag duplicate / near-duplicate samples across one
or more multi-turn evaluation JSONL files.

WHAT IT DOES
------------
Each line of a .jsonl file is one sample, shaped like:

    {
      "dialogue_id": "cca_2",
      "metadata": {...},
      "turns": [
        {"turn_id": 1, "messages": [{"role": "user", "content": "...",
                                      "code_snippet": "..."}, ...]},
        ...
      ],
      "final_ground_truth": {...}
    }

Two samples are treated as duplicates when they share the same *opening
scenario* -- i.e. the first user message of turns[0] is identical or
near-identical. This is the reliable signal because:
  * full-dialogue content is unique for every sample (later turns diverge), and
  * `dialogue_id` collides across genuinely different samples, so it is NOT a
    safe key.
Comparison is done per file (i.e. within a category), using a similarity
ratio on the normalized opening user turn.

USAGE
-----
    # Print a report only (no file changes):
    python check_duplicates.py samples_cca.jsonl samples_ccm.jsonl

    # Also write a "duplicate_flag" field into NEW files
    # (<name>.with_dupflags.jsonl); your originals are never touched:
    python check_duplicates.py samples_cca.jsonl --write

    # Options:
    #   --threshold 0.97   similarity cutoff (1.0 = exact first turn only)
    #   --inplace          write the field into the original file(s) instead of a copy
    #   --out FILE         explicit output path (only valid with a single input file)
    #   --field NAME       name of the field to write (default: "duplicate_flag")

OUTPUT FIELD VALUES
--------------------
    UNIQUE                      no duplicate of this sample exists
    ORIGINAL (dups: L5, L9)     the representative to KEEP (lists duplicate line numbers)
    DUPLICATE -> L3             redundant copy; L3 is the one to keep
=> Your distinct set = every entry NOT marked "DUPLICATE".
"""
import argparse
import difflib
import json
import os
import re
import shutil
import sys


# ----------------------------- helpers --------------------------------------
def norm_text(s):
    """Lowercase, drop punctuation, collapse whitespace."""
    return re.sub(r"[^a-z0-9 ]", " ", re.sub(r"\s+", " ", str(s or "").lower())).strip()


def entry_scenario_key(obj):
    """Extract the normalized opening (first) user turn from a parsed sample.

    Looks at turns[0]'s messages for a role=="user" entry, and includes any
    code_snippet so prompts that differ only in code are kept distinct.
    Falls back to the first message's content if no explicit user role is
    present, matching the original spreadsheet-based logic.
    """
    turns = obj.get("turns") or []
    if not turns:
        return ""
    messages = turns[0].get("messages", []) or []
    for m in messages:
        if m.get("role") == "user":
            parts = [m.get("content") or ""]
            if m.get("code_snippet"):
                parts.append(str(m["code_snippet"]))
            return norm_text(" ".join(parts))
    if messages:
        return norm_text(messages[0].get("content") or "")
    return ""


def read_jsonl(path):
    """Return a list of (line_number, parsed_obj) for a .jsonl file.

    Blank lines are skipped. Lines that fail to parse are skipped with a
    warning (rather than aborting the whole run).
    """
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warning: {path}:{lineno} invalid JSON, skipping ({e})", file=sys.stderr)
                continue
            entries.append((lineno, obj))
    return entries


# ----------------------------- core -----------------------------------------
def compute_dup_flags(entries, threshold):
    """Return (flags, groups) for one file's entries.

    flags:  {line_number -> "UNIQUE" | "ORIGINAL (...)" | "DUPLICATE -> LN"}
    groups: list of duplicate clusters (lists of line numbers, len > 1)
    """
    rows = [(lineno, entry_scenario_key(obj)) for lineno, obj in entries]

    n = len(rows)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if not rows[i][1] or not rows[j][1]:
                continue
            if difflib.SequenceMatcher(None, rows[i][1], rows[j][1]).ratio() >= threshold:
                parent[find(i)] = find(j)

    clusters = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)

    flags, groups = {}, []
    for members in clusters.values():
        ln = sorted(rows[i][0] for i in members)
        if len(ln) == 1:
            flags[ln[0]] = "UNIQUE"
        else:
            groups.append(ln)
            master = ln[0]
            flags[master] = "ORIGINAL (dups: " + ", ".join(f"L{x}" for x in ln[1:]) + ")"
            for x in ln[1:]:
                flags[x] = f"DUPLICATE -> L{master}"
    return flags, groups


def main():
    ap = argparse.ArgumentParser(description="Flag duplicate samples by opening scenario, across JSONL files.")
    ap.add_argument("jsonl", nargs="+", help="Path(s) to .jsonl file(s), one sample per line")
    ap.add_argument("--threshold", type=float, default=0.97,
                    help="Similarity cutoff on the opening user turn (default 0.97; 1.0 = exact only)")
    ap.add_argument("--write", action="store_true",
                    help="Write a duplicate-flag field (to a copy unless --inplace)")
    ap.add_argument("--inplace", action="store_true",
                    help="With --write, modify the original file(s) instead of writing copies")
    ap.add_argument("--out", default=None,
                    help="Output path when writing. With a single input file, this is treated "
                         "as an explicit output file path. With multiple input files, this is "
                         "treated as an output DIRECTORY (created if needed); each file is "
                         "written there under its original basename.")
    ap.add_argument("--field", default="duplicate_flag",
                    help="Name of the field to write into each JSON object (default: duplicate_flag)")
    args = ap.parse_args()

    if args.out and args.inplace:
        sys.exit("--out and --inplace cannot be used together")

    multi = len(args.jsonl) > 1
    if args.out and multi:
        os.makedirs(args.out, exist_ok=True)

    for path in args.jsonl:
        if not os.path.exists(path):
            sys.exit(f"File not found: {path}")

    grand = {"UNIQUE": 0, "ORIGINAL": 0, "DUPLICATE": 0}
    per_file = {}
    for path in args.jsonl:
        entries = read_jsonl(path)
        if not entries:
            continue
        flags, groups = compute_dup_flags(entries, args.threshold)
        per_file[path] = (entries, flags, groups)
        for v in flags.values():
            key = "DUPLICATE" if v.startswith("DUPLICATE") else ("ORIGINAL" if v.startswith("ORIGINAL") else "UNIQUE")
            grand[key] += 1

    # ---- report ----
    print(f"\nDuplicate report (threshold={args.threshold})")
    print("=" * 72)
    for path, (entries, flags, groups) in per_file.items():
        ndup = sum(len(g) - 1 for g in groups)
        print(f"\n{path}: {len(flags)} samples, {len(groups)} dup-group(s), {ndup} redundant")
        for g in groups:
            print(f"    keep L{g[0]}  ->  drop {', '.join('L' + str(x) for x in g[1:])}")
    distinct = grand["UNIQUE"] + grand["ORIGINAL"]
    total = sum(grand.values())
    print("\n" + "=" * 72)
    print(f"TOTAL: {total} samples | UNIQUE={grand['UNIQUE']} "
          f"ORIGINAL={grand['ORIGINAL']} DUPLICATE={grand['DUPLICATE']}")
    print(f"Distinct samples after dedup: {distinct}  (drop {grand['DUPLICATE']})")

    # ---- write field ----
    if args.write:
        for path, (entries, flags, _) in per_file.items():
            if args.inplace:
                out = path
                backup = os.path.splitext(path)[0] + ".backup.jsonl"
                if not os.path.exists(backup):
                    shutil.copyfile(path, backup)
                    print(f"\nBackup saved: {backup}")
            elif args.out:
                out = os.path.join(args.out, os.path.basename(path)) if multi else args.out
            else:
                out = os.path.splitext(path)[0] + ".with_dupflags.jsonl"

            with open(out, "w", encoding="utf-8") as f:
                for lineno, obj in entries:
                    obj[args.field] = flags.get(lineno, "UNIQUE")
                    f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            print(f"Wrote '{args.field}' field -> {out}")


if __name__ == "__main__":
    main()