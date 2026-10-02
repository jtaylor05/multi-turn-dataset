#!/usr/bin/env python3
"""
analyze_scores.py

Analyze a JSONL file of scored entries, grouping by metadata.primary_task,
and produce per-task and global summary statistics (mean, median, stdev,
min, max, quartiles, and pass-rate where a "verdict" field exists).

It auto-discovers every numeric field named "score" anywhere in each JSON
record (handling arbitrarily nested structures such as
scores.evaluate_llm_as_judge[].score), and tracks each distinct "score path"
as its own metric. It also picks up any "verdict" fields the same way.

In addition, for the "evaluate_code_running" judge, it computes pass@k
(the unbiased estimator from the Codex paper) using the boolean "passed"
field on each sample. For a given record, if evaluate_code_running produced
n samples with c of them passing, pass@k is computed for each requested k
(where k <= n) and averaged across records within each task (and globally).

Samples are assumed to be aligned by list index across judges within the
same record (i.e. scores.evaluate_llm_as_judge[i] and
scores.evaluate_code_running[i] refer to the same sample). If a sample's
evaluate_code_running entry has passed=false, that sample's score from
every other judge is forced to 0 before being aggregated, since a judge
score on code that didn't run isn't meaningful. This can be disabled with
--no-zero-failed-code-scores.

Usage:
    python analyze_scores.py input.jsonl \
        [--output-dir OUTPUT_DIR] \
        [--task-key metadata.primary_task] \
        [--pass-at-k 1,5,10]

Outputs (into --output-dir, default: ./analysis_output):
    - report.md          human-readable markdown report
    - summary.csv         flat table of every (task, metric) stat row
    - malformed_lines.txt any lines that failed to parse (if any)
"""

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

CODE_RUNNING_JUDGE = "evaluate_code_running"
PASSED_KEY = "passed"


def get_by_dotpath(obj, dotpath):
    """Fetch a nested value using a dot-separated path, e.g. 'metadata.primary_task'."""
    cur = obj
    for part in dotpath.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def extract_judge_entries(record, scores_key="scores"):
    """
    Extract (judge_name, index, entry_dict) triples from a record's scores
    block. The index is the entry's position within its judge's list, which
    is used elsewhere to align samples across judges (e.g. to match an
    evaluate_llm_as_judge sample with its corresponding
    evaluate_code_running sample).

    Expected shape:
        record["scores"] == {
            "evaluate_llm_as_judge": [ {"score": 6, "verdict": "pass", ...}, ... ],
            "some_other_judge": [ {...}, ... ],   # optional, not always present
        }

    Any judge key may be missing on a given line; that's fine, we just skip it.
    Robust to malformed shapes (non-dict "scores", non-list entries, non-dict
    items within a list) by silently skipping anything that doesn't match.
    """
    scores_block = record.get(scores_key)
    if not isinstance(scores_block, dict):
        return
    for judge_name, entries in scores_block.items():
        if not isinstance(entries, list):
            continue
        for idx, entry in enumerate(entries):
            if isinstance(entry, dict):
                yield judge_name, idx, entry


def get_code_running_entries(record, judge_name=CODE_RUNNING_JUDGE, scores_key="scores"):
    """
    Return the list of sample dicts under scores[judge_name] for a single
    record, or None if that judge isn't present / malformed for this record.

    Each sample dict is expected to look like {"passed": true/false, ...}.
    Robust to malformed shapes the same way extract_judge_entries is.
    """
    scores_block = record.get(scores_key)
    if not isinstance(scores_block, dict):
        return None
    entries = scores_block.get(judge_name)
    if not isinstance(entries, list):
        return None
    cleaned = [e for e in entries if isinstance(e, dict)]
    return cleaned if cleaned else None


def pass_at_k(n, c, k):
    """
    Unbiased pass@k estimator (Codex paper, Chen et al. 2021):
        pass@k = 1 - C(n-c, k) / C(n, k)
    computed via a running product to avoid overflow:
        1 - prod_{i=n-c+1}^{n} (1 - k / i)
    """
    if n - c < k:
        return 1.0
    prod = 1.0
    for i in range(n - c + 1, n + 1):
        prod *= 1.0 - k / i
    return 1.0 - prod


def compute_stats(values):
    n = len(values)
    if n == 0:
        return None
    values_sorted = sorted(values)
    stats = {
        "n": n,
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if n > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "q1": statistics.quantiles(values, n=4)[0] if n > 1 else values_sorted[0],
        "q3": statistics.quantiles(values, n=4)[2] if n > 1 else values_sorted[0],
    }
    return stats


def load_jsonl(path):
    records = []
    malformed = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append((i, json.loads(line)))
            except json.JSONDecodeError as e:
                malformed.append((i, str(e), line[:200]))
    return records, malformed


def parse_k_values(raw):
    ks = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        k = int(part)
        if k < 1:
            raise argparse.ArgumentTypeError(f"--pass-at-k values must be >= 1, got {k}")
        ks.append(k)
    if not ks:
        raise argparse.ArgumentTypeError("--pass-at-k must contain at least one value")
    return sorted(set(ks))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="Path to the input .jsonl file")
    parser.add_argument("--output-dir", default="analysis_output", help="Directory to write outputs to")
    parser.add_argument("--task-key", default="metadata.primary_task",
                         help="Dot-path to the field used for grouping (default: metadata.primary_task)")
    parser.add_argument("--pass-at-k", default="1",
                         help="Comma-separated list of k values to compute pass@k for, using "
                              "scores.evaluate_code_running[].passed (default: 1)")
    parser.add_argument("--no-zero-failed-code-scores", action="store_true",
                         help="Disable forcing a sample's score to 0 when its aligned "
                              "evaluate_code_running sample has passed=false")
    args = parser.parse_args()

    k_values = parse_k_values(args.pass_at_k)

    in_path = Path(args.input)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records, malformed = load_jsonl(in_path)

    if malformed:
        with open(out_dir / "malformed_lines.txt", "w", encoding="utf-8") as f:
            for lineno, err, snippet in malformed:
                f.write(f"Line {lineno}: {err}\n  snippet: {snippet}\n\n")

    if not records:
        print("No valid JSON records found. Check malformed_lines.txt for details.")
        sys.exit(1)

    # task -> score_metric_name -> list of values
    task_scores = defaultdict(lambda: defaultdict(list))
    # task -> verdict_metric_name -> list of verdict strings
    task_verdicts = defaultdict(lambda: defaultdict(list))
    # global versions
    global_scores = defaultdict(list)
    global_verdicts = defaultdict(list)

    # task -> k -> list of per-record pass@k values
    task_pass_at_k = defaultdict(lambda: defaultdict(list))
    global_pass_at_k = defaultdict(list)
    # how many records actually had usable evaluate_code_running samples,
    # and how many of those were skipped per-k because n < k
    task_code_running_records = defaultdict(int)
    global_code_running_records = 0
    skipped_for_k = defaultdict(int)  # k -> count of records skipped because n < k

    task_counts = defaultdict(int)
    missing_task_count = 0
    zero_out_failed_code = not args.no_zero_failed_code_scores
    zeroed_score_count = 0

    for lineno, rec in records:
        task = get_by_dotpath(rec, args.task_key)
        if task is None:
            task = "UNKNOWN"
            missing_task_count += 1
        task_counts[task] += 1

        code_entries = get_code_running_entries(rec)
        # Index-aligned pass/fail list for this record, used to zero out
        # other judges' scores on samples whose code failed to run.
        code_passed_by_index = (
            [e.get(PASSED_KEY) for e in code_entries] if code_entries else None
        )

        for judge_name, idx, entry in extract_judge_entries(rec):
            val = entry.get("score")
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                if (
                    zero_out_failed_code
                    and judge_name != CODE_RUNNING_JUDGE
                    and code_passed_by_index is not None
                    and idx < len(code_passed_by_index)
                    and code_passed_by_index[idx] is False
                    and val != 0
                ):
                    val = 0
                    zeroed_score_count += 1
                task_scores[task][judge_name].append(val)
                global_scores[judge_name].append(val)

            verdict = entry.get("verdict")
            if isinstance(verdict, str):
                task_verdicts[task][judge_name].append(verdict.lower())
                global_verdicts[judge_name].append(verdict.lower())

        if code_entries:
            n = len(code_entries)
            c = sum(1 for e in code_entries if e.get(PASSED_KEY) is True)
            task_code_running_records[task] += 1
            global_code_running_records += 1
            for k in k_values:
                if n >= k:
                    pk = pass_at_k(n, c, k)
                    task_pass_at_k[task][k].append(pk)
                    global_pass_at_k[k].append(pk)
                else:
                    skipped_for_k[k] += 1

    # ---- Build summary rows for CSV ----
    csv_rows = []

    def add_stat_rows(scope, metric_dict):
        for metric, values in sorted(metric_dict.items()):
            s = compute_stats(values)
            if s:
                csv_rows.append({
                    "scope": scope,
                    "metric": metric,
                    **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()},
                })

    for task in sorted(task_scores.keys()):
        add_stat_rows(f"task:{task}", task_scores[task])
    add_stat_rows("GLOBAL", global_scores)

    def add_pass_at_k_rows(scope, k_dict):
        for k, values in sorted(k_dict.items()):
            s = compute_stats(values)
            if s:
                csv_rows.append({
                    "scope": scope,
                    "metric": f"pass@{k} ({CODE_RUNNING_JUDGE})",
                    **{key: (round(v, 4) if isinstance(v, float) else v) for key, v in s.items()},
                })

    for task in sorted(task_pass_at_k.keys()):
        add_pass_at_k_rows(f"task:{task}", task_pass_at_k[task])
    add_pass_at_k_rows("GLOBAL", global_pass_at_k)

    csv_fields = ["scope", "metric", "n", "mean", "median", "stdev", "min", "max", "q1", "q3"]
    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    # ---- Build markdown report ----
    lines = []
    lines.append(f"# Score Analysis Report\n")
    lines.append(f"- Source file: `{in_path.name}`")
    lines.append(f"- Total records parsed: {len(records)}")
    if malformed:
        lines.append(f"- Malformed lines skipped: {len(malformed)} (see `malformed_lines.txt`)")
    if missing_task_count:
        lines.append(f"- Records missing `{args.task_key}`: {missing_task_count} (grouped as `UNKNOWN`)")
    if global_code_running_records:
        lines.append(f"- Records with `{CODE_RUNNING_JUDGE}` samples: {global_code_running_records} "
                      f"(pass@k computed for k={', '.join(str(k) for k in k_values)})")
        for k in k_values:
            if skipped_for_k[k]:
                lines.append(f"  - Skipped {skipped_for_k[k]} record(s) for pass@{k} (fewer than {k} samples)")
    if zero_out_failed_code:
        lines.append(f"- Scores forced to 0 due to a failed (index-aligned) `{CODE_RUNNING_JUDGE}` sample: "
                      f"{zeroed_score_count}")
    else:
        lines.append("- Score zeroing on failed code samples: disabled (--no-zero-failed-code-scores)")
    lines.append("")

    def fmt_stats_block(values):
        s = compute_stats(values)
        block = []
        block.append(f"  - n={s['n']}, mean={s['mean']:.3f}, median={s['median']:.3f}, "
                      f"stdev={s['stdev']:.3f}, min={s['min']:.3f}, max={s['max']:.3f}, "
                      f"IQR=[{s['q1']:.3f}, {s['q3']:.3f}]")
        return "\n".join(block)

    def fmt_verdict_block(verdict_list):
        n = len(verdict_list)
        counts = defaultdict(int)
        for v in verdict_list:
            counts[v] += 1
        parts = ", ".join(f"{k}={v} ({v/n*100:.1f}%)" for k, v in sorted(counts.items()))
        return f"  - n={n}: {parts}"

    def fmt_pass_at_k_block(k, values, n_records):
        s = compute_stats(values)
        return (f"  - k={k}: mean pass@{k}={s['mean']:.3f} "
                f"(averaged over {s['n']} of {n_records} record(s) with >= {k} samples)")

    lines.append("## Global Summary\n")
    if global_scores:
        for metric in sorted(global_scores.keys()):
            lines.append(f"**Score metric: `{metric}`**")
            lines.append(fmt_stats_block(global_scores[metric]))
    if global_verdicts:
        for metric in sorted(global_verdicts.keys()):
            lines.append(f"**Verdict metric: `{metric}`**")
            lines.append(fmt_verdict_block(global_verdicts[metric]))
    if global_pass_at_k:
        lines.append(f"**Pass@k metric: `{CODE_RUNNING_JUDGE}` (field: `{PASSED_KEY}`)**")
        for k in sorted(global_pass_at_k.keys()):
            lines.append(fmt_pass_at_k_block(k, global_pass_at_k[k], global_code_running_records))
    lines.append("")

    lines.append("## Per-Task Breakdown\n")
    for task in sorted(task_counts.keys(), key=lambda t: -task_counts[t]):
        lines.append(f"### `{task}` (n={task_counts[task]})\n")
        if task_scores.get(task):
            for metric in sorted(task_scores[task].keys()):
                lines.append(f"**Score metric: `{metric}`**")
                lines.append(fmt_stats_block(task_scores[task][metric]))
        if task_verdicts.get(task):
            for metric in sorted(task_verdicts[task].keys()):
                lines.append(f"**Verdict metric: `{metric}`**")
                lines.append(fmt_verdict_block(task_verdicts[task][metric]))
        if task_pass_at_k.get(task):
            lines.append(f"**Pass@k metric: `{CODE_RUNNING_JUDGE}` (field: `{PASSED_KEY}`)**")
            for k in sorted(task_pass_at_k[task].keys()):
                lines.append(fmt_pass_at_k_block(k, task_pass_at_k[task][k], task_code_running_records[task]))
        lines.append("")

    # ---- Ranking: tasks sorted by mean of the primary score metric (if any) ----
    if global_scores:
        primary_metric = sorted(global_scores.keys())[0]
        lines.append(f"## Task Ranking by Mean `{primary_metric}`\n")
        ranked = []
        for task, metrics in task_scores.items():
            if primary_metric in metrics:
                s = compute_stats(metrics[primary_metric])
                ranked.append((task, s["mean"], s["n"]))
        ranked.sort(key=lambda x: -x[1])
        lines.append("| Task | Mean | N |")
        lines.append("|---|---|---|")
        for task, mean, n in ranked:
            lines.append(f"| {task} | {mean:.3f} | {n} |")
        lines.append("")

    # ---- Ranking: tasks sorted by mean pass@k (smallest k) if available ----
    if global_pass_at_k:
        primary_k = sorted(global_pass_at_k.keys())[0]
        lines.append(f"## Task Ranking by Mean pass@{primary_k} (`{CODE_RUNNING_JUDGE}`)\n")
        ranked = []
        for task, k_dict in task_pass_at_k.items():
            if primary_k in k_dict:
                s = compute_stats(k_dict[primary_k])
                ranked.append((task, s["mean"], s["n"]))
        ranked.sort(key=lambda x: -x[1])
        lines.append("| Task | Mean pass@{} | N records |".format(primary_k))
        lines.append("|---|---|---|")
        for task, mean, n in ranked:
            lines.append(f"| {task} | {mean:.3f} | {n} |")
        lines.append("")

    report_text = "\n".join(lines)
    with open(out_dir / "report.md", "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Done. Parsed {len(records)} records across {len(task_counts)} task group(s).")
    print(f"Wrote: {out_dir / 'report.md'}, {out_dir / 'summary.csv'}"
          + (f", {out_dir / 'malformed_lines.txt'}" if malformed else ""))


if __name__ == "__main__":
    main()