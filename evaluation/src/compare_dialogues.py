#!/usr/bin/env python3
"""
compare_dialogues.py

Compares the final assistant output ("content") of matching dialogue
entries between a set of "master" JSONL files and a set of "test" JSONL
files. Entries are matched by their "dialogue_id" field.

For each test entry with a matching dialogue_id in the master set, a
textual similarity score is computed between the final assistant message
content in the test entry and the final assistant message content in the
master entry. Test entries with no matching dialogue_id are skipped (but
counted and reported in the summary).

Usage:
    python compare_dialogues.py \
        --master master1.jsonl master2.jsonl \
        --test test1.jsonl test2.jsonl \
        --details-out details.jsonl \
        --summary-out summary.json \
        [--method difflib|tfidf]

Output:
    1. A JSONL "details" file, one line per test entry that had a
       matching master entry:
           {
             "dialogue_id": "...",
             "similarity": 0.873,
             "method": "difflib",
             "master_chars": 1234,
             "test_chars": 1200
           }

    2. A JSON "summary" file with aggregate statistics across all
       compared entries, plus counts of matched/skipped/unmatched
       entries and duplicate dialogue_id warnings.
"""

import argparse
import difflib
import json
import statistics
import sys
from pathlib import Path


# --------------------------------------------------------------------------
# Loading / extraction helpers
# --------------------------------------------------------------------------

def load_jsonl(paths):
    """Load JSON objects from one or more JSONL files.

    Returns a dict mapping dialogue_id -> entry (last one wins on
    duplicates, but duplicates are tracked and returned separately).
    """
    entries_by_id = {}
    duplicate_ids = []
    total_lines = 0
    bad_lines = 0

    for path in paths:
        p = Path(path)
        if not p.exists():
            print(f"WARNING: file not found, skipping: {path}", file=sys.stderr)
            continue
        with p.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                total_lines += 1
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    bad_lines += 1
                    print(
                        f"WARNING: could not parse JSON at {path}:{line_num}: {e}",
                        file=sys.stderr,
                    )
                    continue

                dialogue_id = obj.get("dialogue_id")
                if dialogue_id is None:
                    print(
                        f"WARNING: entry missing 'dialogue_id' at {path}:{line_num}, skipping",
                        file=sys.stderr,
                    )
                    continue

                if dialogue_id in entries_by_id:
                    duplicate_ids.append(dialogue_id)
                entries_by_id[dialogue_id] = obj

    return entries_by_id, duplicate_ids, total_lines, bad_lines


def extract_final_assistant_content(entry):
    """Extract the content of the last assistant message in the last turn.

    Expects the dialogue entry shape:
        {
          "dialogue_id": ...,
          "turns": [
            {"turn_id": ..., "messages": [{"role": ..., "content": ...}, ...]},
            ...
          ]
        }

    Returns the string content, or None if it can't be found.
    """
    turns = entry.get("turns")
    if not turns or not isinstance(turns, list):
        return None

    last_turn = turns[-1]
    messages = last_turn.get("messages")
    if not messages or not isinstance(messages, list):
        return None

    for message in reversed(messages):
        if message.get("role") == "assistant":
            content = message.get("content")
            if isinstance(content, str):
                return content
            return None

    return None


# --------------------------------------------------------------------------
# Similarity methods
# --------------------------------------------------------------------------

def similarity_difflib(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def build_tfidf_similarity_fn():
    """Attempt to build a TF-IDF cosine similarity function via sklearn.

    Raises ImportError if sklearn is not available, which the caller
    should catch and fall back to difflib.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    def sim_fn(a, b):
        if not a.strip() or not b.strip():
            return 0.0
        vectorizer = TfidfVectorizer()
        try:
            matrix = vectorizer.fit_transform([a, b])
        except ValueError:
            # e.g. empty vocabulary after tokenization
            return 0.0
        score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return float(score)

    return sim_fn


def get_similarity_fn(method):
    if method == "difflib":
        return similarity_difflib, "difflib"
    if method == "tfidf":
        try:
            return build_tfidf_similarity_fn(), "tfidf"
        except ImportError:
            print(
                "WARNING: scikit-learn not installed; falling back to 'difflib' method.",
                file=sys.stderr,
            )
            return similarity_difflib, "difflib"
    raise ValueError(f"Unknown method: {method}")


# --------------------------------------------------------------------------
# Main comparison logic
# --------------------------------------------------------------------------

def compare(master_paths, test_paths, method="difflib"):
    master_entries, master_dupes, master_lines, master_bad = load_jsonl(master_paths)
    test_entries, test_dupes, test_lines, test_bad = load_jsonl(test_paths)

    sim_fn, method_used = get_similarity_fn(method)

    details = []
    skipped_no_match = []
    skipped_no_content = []

    for dialogue_id, test_entry in test_entries.items():
        master_entry = master_entries.get(dialogue_id)
        if master_entry is None:
            skipped_no_match.append(dialogue_id)
            continue

        test_content = extract_final_assistant_content(test_entry)
        master_content = extract_final_assistant_content(master_entry)

        if test_content is None or master_content is None:
            skipped_no_content.append(dialogue_id)
            continue

        score = sim_fn(master_content, test_content)

        details.append(
            {
                "dialogue_id": dialogue_id,
                "similarity": round(score, 6),
                "method": method_used,
                "master_chars": len(master_content),
                "test_chars": len(test_content),
            }
        )

    scores = [d["similarity"] for d in details]

    summary = {
        "method": method_used,
        "master_files": [str(p) for p in master_paths],
        "test_files": [str(p) for p in test_paths],
        "master_entries_loaded": len(master_entries),
        "test_entries_loaded": len(test_entries),
        "master_lines_read": master_lines,
        "test_lines_read": test_lines,
        "master_bad_json_lines": master_bad,
        "test_bad_json_lines": test_bad,
        "master_duplicate_dialogue_ids": sorted(set(master_dupes)),
        "test_duplicate_dialogue_ids": sorted(set(test_dupes)),
        "compared_count": len(details),
        "skipped_no_master_match_count": len(skipped_no_match),
        "skipped_no_master_match_ids": skipped_no_match,
        "skipped_missing_content_count": len(skipped_no_content),
        "skipped_missing_content_ids": skipped_no_content,
        "similarity_stats": {
            "mean": round(statistics.mean(scores), 6) if scores else None,
            "median": round(statistics.median(scores), 6) if scores else None,
            "min": round(min(scores), 6) if scores else None,
            "max": round(max(scores), 6) if scores else None,
            "stdev": round(statistics.stdev(scores), 6) if len(scores) > 1 else None,
        },
    }

    return details, summary


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare final assistant output similarity between master and test JSONL dialogue files."
    )
    parser.add_argument("--master", nargs="+", required=True, help="Path(s) to master JSONL file(s).")
    parser.add_argument("--test", nargs="+", required=True, help="Path(s) to test JSONL file(s).")
    parser.add_argument(
        "--method",
        choices=["difflib", "tfidf"],
        default="difflib",
        help="Similarity method to use (default: difflib, no extra dependencies). "
             "'tfidf' uses scikit-learn cosine similarity if available.",
    )
    parser.add_argument(
        "--details-out",
        default="details.jsonl",
        help="Path to write the per-entry JSONL details file (default: details.jsonl).",
    )
    parser.add_argument(
        "--summary-out",
        default="summary.json",
        help="Path to write the overall JSON summary file (default: summary.json).",
    )
    args = parser.parse_args()

    details, summary = compare(args.master, args.test, method=args.method)

    details_path = Path(args.details_out)
    with details_path.open("w", encoding="utf-8") as f:
        for row in details:
            f.write(json.dumps(row) + "\n")

    summary_path = Path(args.summary_out)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote {len(details)} comparison rows to {details_path}")
    print(f"Wrote summary to {summary_path}")
    if summary["similarity_stats"]["mean"] is not None:
        print(f"Mean similarity: {summary['similarity_stats']['mean']}")


if __name__ == "__main__":
    main()