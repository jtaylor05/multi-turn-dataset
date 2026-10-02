"""Evaluation pipeline package.

This package is imported by the top-level entry script in the project root. The
module exports are intentionally lightweight so importing the package does not
trigger side effects beyond the package metadata itself.
"""

__all__ = [
    "add_id",
    "analyze_scores",
    "bleu_eval",
    "check_duplicates",
    "code_eval",
    "combine_jsonl",
    "compare_dialogues",
    "compare_to_ground_truth",
    "convert_csv_jsonl",
    "convert_xlsx_jsonl",
    "evaluation",
    "llm_api",
    "llm_eval",
    "match_id_prefix",
    "model_database",
    "process_data",
    "remove_duplicates",
    "sample_jsonl",
    "separate_categories",
    "tmp_code_execute",
]
