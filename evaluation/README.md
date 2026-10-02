# Evaluation

`main.py` processes JSON or JSONL dialogue files, runs the configured checks for each task, and writes JSONL output. LLM-as-judge evaluation requires a supported provider key in the environment.

## Local Use

```sh
python3 -m pip install -r requirements.txt
cp .env.example .env
set -a
. ./.env
set +a
python3 main.py data/input.jsonl --output data/evaluated.jsonl
```

The evaluation CLI reads credentials from the process environment; it does not load `.env` automatically. Local use requires Python 3.11 or later.

The Docker image declares `/app/data` as a volume. Mount a host directory there to keep input and output files beyond the container lifetime:

```sh
docker build -t multi-turn-evaluation .
docker run --rm -it --env-file .env -v "$PWD/data:/app/data" \
  multi-turn-evaluation python /app/main.py /app/data/input.jsonl \
  --output /app/data/evaluated.jsonl
```

For options, run `python3 main.py --help`. The `src/` directory contains the evaluation functions and utilities; [`src/analyze_scores.py`](src/analyze_scores.py) summarizes scored JSONL results.

## Safety

The code-evaluation path executes code contained in input records. Treat inputs as untrusted and use an isolated environment with appropriate resource and network restrictions.