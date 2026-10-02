#!/usr/bin/env python3
"""
compare_to_ground_truth.py

Compares the final assistant output ("content") of each dialogue entry
against its own embedded reference text at:

    entry["final_ground_truth"]["expected_nl_output"]

Unlike compare_dialogues.py, there is no separate "master" file set here —
each test entry carries its own ground truth. Entries whose
final_ground_truth.expected_nl_output is missing or null are skipped
(and reported).

Usage:
    python compare_to_ground_truth.py \
        --test test1.jsonl test2.jsonl \
        --details-out details.jsonl \
        --summary-out summary.json \
        [--method embedding|tfidf|difflib] \
        [--model all-MiniLM-L6-v2]

Output:
    1. A JSONL "details" file, one line per test entry that had a usable
       expected_nl_output:
           {
             "dialogue_id": "...",
             "similarity": 0.873,
             "method": "difflib",
             "expected_chars": 1234,
             "actual_chars": 1200
           }

    2. A JSON "summary" file with aggregate statistics across all
       compared entries, plus counts of skipped entries and duplicate
       dialogue_id warnings.
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


def extract_expected_nl_output(entry):
    """Extract entry['final_ground_truth']['expected_nl_output'].

    Returns the string, or None if missing/null/not a string.
    """
    ground_truth = entry.get("final_ground_truth")
    if not isinstance(ground_truth, dict):
        return None
    expected = ground_truth.get("expected_nl_output")
    if isinstance(expected, str) and expected.strip():
        return expected
    return None


# --------------------------------------------------------------------------
# Similarity methods
# --------------------------------------------------------------------------
#
# Three methods are available, in increasing order of how much "meaning"
# vs. surface wording they capture:
#
#   difflib   - character-sequence overlap (no vectorization at all).
#   tfidf     - bag-of-words vectorization; catches shared vocabulary but
#               is blind to synonyms, paraphrase, and word order.
#   embedding - sentence-transformer neural embeddings; two texts that say
#               the same thing in different words score highly. This is
#               the recommended method for comparing *meaning* rather than
#               wording, and is the default.

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


def build_embedding_similarity_fn(model_name):
    """Build a semantic similarity function using sentence-transformer
    embeddings and cosine similarity.

    Requires the `sentence-transformers` package (pip install
    sentence-transformers). The first call downloads the model weights
    from Hugging Face Hub, so it needs network access and may take a
    while the first time; the model is then cached locally.

    Raises ImportError if sentence-transformers is not installed, which
    the caller should catch and fall back to a lighter-weight method.
    """
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.util import cos_sim

    print(f"Loading embedding model '{model_name}' (this may take a moment)...", file=sys.stderr)
    model = SentenceTransformer(model_name)

    def sim_fn(a, b):
        if not a.strip() or not b.strip():
            return 0.0
        embeddings = model.encode([a, b], convert_to_tensor=True, normalize_embeddings=True)
        score = cos_sim(embeddings[0], embeddings[1]).item()
        # Cosine similarity can dip slightly negative for embeddings; clamp
        # to [0, 1] so scores stay in an intuitive "0 = unrelated, 1 =
        # identical meaning" range.
        return max(0.0, min(1.0, score))

    return sim_fn


def get_similarity_fn(method, model_name):
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

    if method == "embedding":
        try:
            return build_embedding_similarity_fn(model_name), f"embedding:{model_name}"
        except ImportError:
            print(
                "WARNING: sentence-transformers not installed "
                "(pip install sentence-transformers). Falling back to 'tfidf'.",
                file=sys.stderr,
            )
        except Exception as e:
            # Covers model-download failures (no network access, bad model
            # name, Hugging Face Hub unreachable, etc.) so a connectivity
            # problem doesn't crash the whole run.
            print(
                f"WARNING: could not load embedding model '{model_name}' ({e}). "
                "Falling back to 'tfidf'.",
                file=sys.stderr,
            )
        try:
            return build_tfidf_similarity_fn(), "tfidf"
        except ImportError:
            print(
                "WARNING: scikit-learn not installed either; falling back to 'difflib'.",
                file=sys.stderr,
            )
            return similarity_difflib, "difflib"

    raise ValueError(f"Unknown method: {method}")


# --------------------------------------------------------------------------
# Main comparison logic
# --------------------------------------------------------------------------

def compare(test_paths, method="embedding", model_name="all-MiniLM-L6-v2"):
    test_entries, test_dupes, test_lines, test_bad = load_jsonl(test_paths)

    sim_fn, method_used = get_similarity_fn(method, model_name)

    details = []
    skipped_no_ground_truth = []
    skipped_no_content = []

    for dialogue_id, entry in test_entries.items():
        expected = extract_expected_nl_output(entry)
        if expected is None:
            skipped_no_ground_truth.append(dialogue_id)
            continue

        actual = extract_final_assistant_content(entry)
        if actual is None:
            skipped_no_content.append(dialogue_id)
            continue

        score = sim_fn(expected, actual)

        details.append(
            {
                "dialogue_id": dialogue_id,
                "similarity": round(score, 6),
                "method": method_used,
                "expected_chars": len(expected),
                "actual_chars": len(actual),
            }
        )

    scores = [d["similarity"] for d in details]

    summary = {
        "method": method_used,
        "test_files": [str(p) for p in test_paths],
        "test_entries_loaded": len(test_entries),
        "test_lines_read": test_lines,
        "test_bad_json_lines": test_bad,
        "test_duplicate_dialogue_ids": sorted(set(test_dupes)),
        "compared_count": len(details),
        "skipped_no_ground_truth_count": len(skipped_no_ground_truth),
        "skipped_no_ground_truth_ids": skipped_no_ground_truth,
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
        description="Compare final assistant output similarity against each entry's own "
                    "final_ground_truth.expected_nl_output."
    )
    parser.add_argument("--test", nargs="+", required=True, help="Path(s) to test JSONL file(s).")
    parser.add_argument(
        "--method",
        choices=["embedding", "tfidf", "difflib"],
        default="embedding",
        help="Similarity method to use (default: embedding — sentence-transformer "
             "cosine similarity, best for comparing meaning rather than wording; "
             "requires 'pip install sentence-transformers'). 'tfidf' uses scikit-learn "
             "bag-of-words cosine similarity. 'difflib' is character-overlap only, "
             "no dependencies. Falls back automatically to a lighter method if the "
             "required package isn't installed.",
    )
    parser.add_argument(
        "--model",
        default="all-MiniLM-L6-v2",
        help="Sentence-transformers model name to use when --method embedding is "
             "selected (default: all-MiniLM-L6-v2, a fast general-purpose model). "
             "Ignored for other methods.",
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

    details, summary = compare(args.test, method=args.method, model_name=args.model)

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