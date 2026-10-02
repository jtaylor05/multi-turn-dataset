# Generation Source

This package implements the generation pipeline used by [`../main.py`](../main.py):

- `llm_api.py` contains provider API adapters.
- `model_database.py` selects an adapter for a model identifier.
- `llm_statemachine.py` tracks dialogue progress and serializes resumable state.
- `batch_poll.py` submits, polls, and saves batches.
- `sample_jsonl.py`, `rewrap.py`, and `extract_code_snippets.py` are data utilities.

The package is internal to the generation command-line tool; start with its CLI rather than calling state-machine methods directly.