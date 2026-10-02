# Multi-Turn Code Interaction Dataset

This repository contains prompt templates and command-line tools for generating and evaluating multi-turn coding dialogues. Generation and evaluation can run directly with Python or in separate Docker images.

## Requirements

- Python 3.11 or later for local use
- Docker for container use
- Provider API credentials for model generation and LLM-as-judge evaluation

Install dependencies from the relevant `requirements.txt`. Generation and evaluation have separate environments because their dependencies differ.

## Quick Start

Create a local data directory and a private environment file from the example:

```sh
mkdir -p data
cp generation/.env.example generation/.env
```

Edit `generation/.env` locally and set credentials for the model provider you use (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `DASHSCOPE_API_KEY`). Ollama can be configured with `OLLAMA_BASE_URL`. Do not commit credentials or private dataset content.

Build and open the generation container with the host data directory mounted at `/app/data`:

```sh
docker build -t multi-turn-generation ./generation
docker run --rm -it --env-file generation/.env \
  -v "$PWD/data:/app/data" multi-turn-generation
```

Inside the container, use:

```sh
python /app/main.py /app/data/input.jsonl --models claude-haiku-4-5
```

Generated JSONL and resumable batch state files are written to the current working directory. Run `cd /app/data` first to keep those outputs on the mounted host directory.

To evaluate JSON or JSONL input, build the evaluation image and mount the same directory:

```sh
cp evaluation/.env.example evaluation/.env
docker build -t multi-turn-evaluation ./evaluation
docker run --rm -it --env-file evaluation/.env \
  -v "$PWD/data:/app/data" multi-turn-evaluation
```

Then run:

```sh
python /app/main.py /app/data/input.jsonl --output /app/data/evaluated.jsonl
```

Use `python /app/main.py --help` in either container for available options. If a provider does not need credentials for a chosen task or model, omit `--env-file` or use a local environment file containing only the required keys.

## Repository Map

- [`generation/`](generation/README.md): batch generation and model API adapters.
- [`evaluation/`](evaluation/README.md): dialogue processing, code execution checks, and model-based scoring.
- [`prompts/`](prompts/README.md): task instructions, format headers, and sample outputs.
- [`bash/`](bash/README.md): container and analysis helper scripts.

## Data Format

Inputs are JSONL files with one dialogue object per line, or JSON files accepted by the evaluation command. Generation expects `dialogue_id` and `turns`; evaluation also uses `metadata.primary_task` and `final_ground_truth`. See the prompt headers and task examples for the full schemas.

## Anonymized Submission Checklist

- Keep API keys in ignored `.env` files; use the `.env.example` files as templates.
- Keep private datasets, model outputs, logs, and local runs outside version control.
- Review prompts, examples, and metadata for author names, affiliations, private paths, acknowledgements, and identifying comments before submission.
- Check all submission files and repository metadata for identifying information. This repository does not add author or affiliation details.

Evaluation may execute code supplied in dataset entries. Run it only in an isolated environment with appropriate resource and network restrictions.