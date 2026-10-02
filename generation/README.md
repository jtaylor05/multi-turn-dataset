# Generation

`main.py` accepts one or more input JSONL files and submits their dialogues to the selected model APIs. Results are written as JSONL files in the current working directory. In Docker, mount host data at `/app/data` and run from that directory to persist results.

## Local Use

```sh
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 main.py data/input.jsonl --models claude-haiku-4-5
```

Set the provider key(s) required by the selected model in `.env`, then export them before running locally or use a tool that loads the environment file. The Docker workflow loads `.env` using `--env-file`.

For a local shell session, load the variables with:

```sh
set -a
. ./.env
set +a
```

Useful options:

- `--models` / `-m`: one or more model identifiers; required.
- `--freq` / `-f`: polling interval in seconds.
- `--save` / `-s`: load saved batch state files instead of starting new requests.

Use `python3 main.py --help` for the complete argument list. Local use requires Python 3.11 or later. The `src/` package contains API adapters, model selection, batch polling, and state persistence.