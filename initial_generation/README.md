# Initial Generation

This package creates the first-pass conversational examples from the task prompts. It prepares Anthropic Messages Batch API requests and manages their submission and retrieval. The retrieved files are raw provider batch results; curate or convert those results into the dialogue JSONL schema before passing them to [`generation/`](../generation/README.md), which continues the multi-turn conversations.

## Requirements

- Python 3.11 or later
- An Anthropic API key for submitting or retrieving batches
- Docker for the container workflow

## Local Use

```sh
python3 -m pip install -r initial_generation/requirements.txt
cp initial_generation/.env.example initial_generation/.env
```

Set `ANTHROPIC_API_KEY` in the local environment. For example, in Bash:

```sh
set -a
. initial_generation/.env
set +a
```

Prepare ten requests for each prompt task (110 total by default):

```sh
bash initial_generation/bin/prep -n 10 -m claude-sonnet-4-6
```

The request JSONL files are written to `initial_generation/data/prepped_files/`. Submit one or more prepared files:

```sh
python3 initial_generation/bin/start_batch \
  initial_generation/data/prepped_files/*.jsonl
```

Batch IDs are appended to `initial_generation/data/batch_ids.txt`. Check status and retrieve results with:

```sh
python3 initial_generation/bin/check_batch BATCH_ID
python3 initial_generation/bin/retrieve_batch BATCH_ID
```

Successful responses are written to `initial_generation/data/output/`; failed or expired results go to `initial_generation/data/error/`.

To create requests from prompt lines in JSONL files instead, use `prep_jsonl -h HEADER -o OUTPUT [options] INPUT...`. Use `-n` to cap the total number of requests and `-e` to include the code execution tool. Run any command with `--help` where supported, or inspect its usage message.

## Docker

Build from the repository root so the image can include the shared prompt library:

```sh
docker build -f initial_generation/Dockerfile -t multi-turn-initial-generation .
```

The convenience launcher mounts `initial_generation/data` at `/app/data` and passes `initial_generation/.env` if it exists:

```sh
bash bash/start-initial-generation
```

Inside the container, run `prep -n 10 -m claude-sonnet-4-6`, submit files from `/app/data/prepped_files/` with `start_batch`, then use `check_batch` and `retrieve_batch` with a returned batch ID. The request files, batch ID log, and retrieved results persist on the host.

The data directory can be changed by passing a host path to the launcher or setting `DATA_DIR` for local commands. `PROMPTS_DIR` can override the shared prompt directory for local preparation.

## Safety and Data Handling

Batch submission sends the rendered prompt and task instructions to Anthropic and may incur API costs. Keep API keys in the ignored `.env`, and do not commit generated conversations or private datasets. Review raw provider results before transforming or using them as generation input.