# Evaluation Source

The command-line entry point in [`../main.py`](../main.py) uses these modules:

- `process_data.py` normalizes dialogue records for evaluation.
- `evaluation.py`, `llm_eval.py`, and `bleu_eval.py` implement scoring paths.
- `code_eval.py` runs functional checks for generated code.
- `model_database.py` and `llm_api.py` provide model API selection.
- `analyze_scores.py` reports aggregate metrics; the remaining modules provide conversion, sampling, comparison, and JSONL utilities.

Run tools from this directory with `python -m src.<module> --help` when the module supports command-line arguments.