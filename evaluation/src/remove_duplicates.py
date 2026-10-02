#!/usr/bin/env python3
"""
remove_duplicates.py  --  Drop entries flagged as duplicates from JSONL
files already processed by check_duplicates.py --write.

USAGE
-----
    # Write cleaned copies (<name>.deduped.jsonl); originals untouched:
    python remove_duplicates.py samples_cca.jsonl samples_ccm.jsonl

    # Overwrite the originals (a .backup.jsonl is kept):
    python remove_duplicates.py samples_cca.jsonl --inplace

    # Options:
    #   --field NAME   name of the flag field to check (default: "duplicate_flag")
    #   --out PATH     single file -> explicit output path; multiple files -> output directory
"""
import argparse
import json
import os
import shutil
import sys


def main():
    ap = argparse.ArgumentParser(description="Remove DUPLICATE-flagged entries from processed JSONL files.")
    ap.add_argument("jsonl", nargs="+", help="Path(s) to .jsonl file(s) already flagged by check_duplicates.py")
    ap.add_argument("--field", default="duplicate_flag", help="Flag field to check (default: duplicate_flag)")
    ap.add_argument("--inplace", action="store_true", help="Overwrite originals (keeps a .backup.jsonl)")
    ap.add_argument("--out", default=None,
                    help="Single input file -> explicit output file path. "
                         "Multiple input files -> output directory (created if needed).")
    args = ap.parse_args()

    if args.out and args.inplace:
        sys.exit("--out and --inplace cannot be used together")

    multi = len(args.jsonl) > 1
    if args.out and multi:
        os.makedirs(args.out, exist_ok=True)

    for path in args.jsonl:
        if not os.path.exists(path):
            sys.exit(f"File not found: {path}")

        kept, dropped = [], 0
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Warning: {path}:{lineno} invalid JSON, keeping as-is ({e})", file=sys.stderr)
                    kept.append(line)
                    continue
                flag = str(obj.get(args.field, ""))
                if flag.startswith("DUPLICATE"):
                    dropped += 1
                else:
                    kept.append(json.dumps(obj, ensure_ascii=False))

        if args.inplace:
            out = path
            backup = os.path.splitext(path)[0] + ".backup.jsonl"
            if not os.path.exists(backup):
                shutil.copyfile(path, backup)
                print(f"Backup saved: {backup}")
        elif args.out:
            out = os.path.join(args.out, os.path.basename(path)) if multi else args.out
        else:
            out = os.path.splitext(path)[0] + ".deduped.jsonl"

        with open(out, "w", encoding="utf-8") as f:
            for line in kept:
                f.write(line + "\n")

        print(f"{path}: kept {len(kept)}, dropped {dropped} duplicate(s) -> {out}")


if __name__ == "__main__":
    main()