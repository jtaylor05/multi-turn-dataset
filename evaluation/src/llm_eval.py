"""
llm_judge.py
============
LLM-as-Judge evaluation, built on top of the LLMAPI abstraction
(model_database.py) instead of a raw anthropic.Anthropic() client.

Two entry points:

    llm_judge(system_prompt, reference, *candidates, ...)
        One reference, N candidates. Useful for "which of these N
        outputs best matches this one gold answer".

    llm_judge_batch(guideline, pairs, ...)
        N independent (reference, candidate) pairs sharing one guideline.
        This is what evaluate_llm_as_judge() uses -- each dataset entry
        has its own reference (final_ground_truth) and candidate (the
        model's actual response), but the grading guideline is constant
        across the whole run.

Both are backed by the same worker (_evaluate_single), run concurrently
across a thread pool, with retries on transient errors and (for Anthropic
models) prompt caching on the shared system content.
"""

from __future__ import annotations

import json
import os
import random
import re
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any

from .llm_api import AnthropicAPI, LLMAPI
from .model_database import get_api

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class EvaluationResult:
    index:      int
    candidate:  str
    score:      int                  # 1-10 (0 if evaluation errored out)
    reasoning:  str
    strengths:  list[str]
    weaknesses: list[str]
    verdict:    str                  # "pass" | "fail" | "error"
    raw:        dict[str, Any] = field(default_factory=dict, repr=False)

    def __str__(self) -> str:
        bar = "█" * self.score + "░" * (10 - self.score)
        lines = [
            f"── Candidate #{self.index} ──────────────────────────────",
            f"  Score   : {self.score}/10  [{bar}]  ({self.verdict.upper()})",
            f"  Reasoning: {textwrap.fill(self.reasoning, width=72, subsequent_indent='             ')}",
        ]
        if self.strengths:
            lines.append("  Strengths:")
            for s in self.strengths:
                lines.append(f"    + {s}")
        if self.weaknesses:
            lines.append("  Weaknesses:")
            for w in self.weaknesses:
                lines.append(f"    - {w}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("raw", None)
        return d


# ---------------------------------------------------------------------------
# Judge prompt construction
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = """\
You are an impartial, expert evaluator.

Your task is to assess a CANDIDATE response against a REFERENCE response,
guided by the TASK DESCRIPTION supplied by the user.

Evaluation criteria (weight each equally unless the task description
says otherwise):
  1. Correctness   - Does the candidate satisfy the task requirements?
  2. Completeness  - Are all aspects of the reference covered?
  3. Quality       - Is the candidate well-structured and idiomatic?
  4. Conciseness   - Does it avoid unnecessary verbosity or duplication?
  5. Faithfulness  - Does it stay true to the intent of the task?

You MUST respond with a single valid JSON object — no markdown fences,
no extra keys — matching EXACTLY this schema:

{
  "score":      <integer 1-10>,
  "reasoning":  "<one concise paragraph explaining the score>",
  "strengths":  ["<strength 1>", ...],
  "weaknesses": ["<weakness 1>", ...]
}

Score guide:
  9-10  Excellent  - matches or surpasses the reference in all criteria
  7-8   Good       - minor gaps, overall high quality
  5-6   Adequate   - meets the core requirement but with notable issues
  3-4   Poor       - significant gaps or errors
  1-2   Failing    - incorrect or deeply incomplete
"""


def _build_system_content(
    judge_prompt: str,
    guideline: str,
    use_cache: bool,
) -> str | list[dict[str, Any]]:
    """
    The judge rubric + guideline/task-description are constant for an
    entire llm_judge()/llm_judge_batch() call, so this is the piece we
    mark cacheable. Reference + candidate vary per call and always stay
    in the per-request user message (see _build_user_message).

    use_cache should only be True when the resolved LLMAPI is
    AnthropicAPI -- cache_control is an Anthropic-specific content block
    field and other providers' request() implementations pass `system`
    straight through as a plain string.
    """
    combined = f"{judge_prompt.strip()}\n\n## Task Description\n{guideline.strip()}"
    if not use_cache:
        return combined
    return [
        {
            "type": "text",
            "text": combined,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def _build_user_message(reference: str, candidate: str, index: int) -> str:
    return textwrap.dedent(f"""\
        ## Reference Response
        ```
        {reference.strip()}
        ```

        ## Candidate #{index}
        ```
        {candidate.strip()}
        ```

        Evaluate Candidate #{index} against the Reference Response using the
        criteria in your instructions. Return only the JSON object.
    """)


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def _is_retryable(exc: Exception) -> bool:
    """Best-effort, provider-agnostic check for transient errors.

    Most SDK exceptions (anthropic, openai) expose .status_code; fall back
    to matching common transient-error class names for providers that don't
    (e.g. the google-genai SDK).
    """
    status = getattr(exc, "status_code", None)
    if status is not None:
        return status == 429 or status >= 500
    name = type(exc).__name__
    return any(
        token in name
        for token in ("RateLimit", "APIConnection", "Timeout", "InternalServerError", "ServiceUnavailable", "Overloaded")
    )


def _call_with_retry(
    api: LLMAPI,
    prompt: str,
    system: str | list[dict[str, Any]],
    max_retries: int,
    base_delay: float = 1.0,
    max_delay: float = 20.0,
) -> str:
    attempt = 0
    while True:
        try:
            _, output = api.request(prompt=prompt, system=system)
            return output
        except Exception as exc:
            attempt += 1
            if attempt > max_retries or not _is_retryable(exc):
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
            print(
                f"  transient error ({type(exc).__name__}): {exc} "
                f"— retry {attempt}/{max_retries} in {delay:.1f}s"
            )
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------


def _evaluate_single(
    api: LLMAPI,
    system: str | list[dict[str, Any]],
    reference: str,
    candidate: str,
    index: int,
    pass_threshold: int,
    max_retries: int,
) -> EvaluationResult:
    """Runs in a worker thread. Never raises -- API and parse failures are
    captured into an EvaluationResult with verdict='error' so one bad
    candidate can't take down the rest of the batch."""

    prompt = _build_user_message(reference, candidate, index)

    try:
        raw_text = _call_with_retry(api, prompt, system, max_retries=max_retries)
    except Exception as exc:
        return EvaluationResult(
            index=index, candidate=candidate, score=0,
            reasoning=f"API error after retries: {exc}",
            strengths=[], weaknesses=[], verdict="error", raw={},
        )

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

    try:
        parsed: dict[str, Any] = json.loads(cleaned)
        score = int(parsed.get("score", 0))
        if not (1 <= score <= 10):
            raise ValueError(f"score {score!r} out of range [1, 10]")
    except (json.JSONDecodeError, ValueError) as exc:
        return EvaluationResult(
            index=index, candidate=candidate, score=0,
            reasoning=f"Judge returned unparseable output ({exc}): {cleaned[:500]!r}",
            strengths=[], weaknesses=[], verdict="error", raw={},
        )

    print(f"Candidate #{index} scored {score}/10 (threshold >= {pass_threshold})")

    return EvaluationResult(
        index=index,
        candidate=candidate,
        score=score,
        reasoning=parsed.get("reasoning", ""),
        strengths=parsed.get("strengths", []),
        weaknesses=parsed.get("weaknesses", []),
        verdict="pass" if score >= pass_threshold else "fail",
        raw=parsed,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def llm_judge_batch(
    guideline: str,
    pairs: list[tuple[str, str]],
    *,
    judge_prompt: str = _JUDGE_SYSTEM,
    pass_threshold: int = 6,
    model: str = "claude-haiku-4-5",
    max_workers: int = 8,
    max_retries: int = 3,
) -> list[EvaluationResult]:
    """
    Evaluate N independent (reference, candidate) pairs against a shared
    guideline, concurrently.

    Parameters
    ----------
    guideline      : Grading guideline / task description, constant across pairs.
    pairs          : List of (reference, candidate) tuples.
    pass_threshold : Minimum score (inclusive) for a "pass" verdict.
    model          : Model name, resolved via model_database.get_api().
    max_workers    : Max concurrent in-flight requests.
    max_retries    : Retries per candidate on transient errors.

    Returns
    -------
    List of EvaluationResult, one per pair, in input order. Individual
    failures show up as verdict="error" rather than raising.
    """
    if not pairs:
        raise ValueError("At least one (reference, candidate) pair must be supplied.")
    if not (1 <= pass_threshold <= 10):
        raise ValueError("pass_threshold must be in [1, 10].")

    api = get_api(model)
    system = _build_system_content(judge_prompt, guideline, use_cache=isinstance(api, AnthropicAPI))

    print(f"Evaluating {len(pairs)} pair(s) with model '{model}' "
          f"(workers={min(max_workers, len(pairs))}, threshold >= {pass_threshold})...")

    results: list[EvaluationResult | None] = [None] * len(pairs)
    with ThreadPoolExecutor(max_workers=min(max_workers, len(pairs))) as pool:
        futures = {
            pool.submit(
                _evaluate_single, api, system, reference, candidate, idx,
                pass_threshold, max_retries,
            ): idx
            for idx, (reference, candidate) in enumerate(pairs)
        }
        for fut in as_completed(futures):
            idx = futures[fut]
            results[idx] = fut.result()

    return results  # type: ignore[return-value]


def llm_judge(
    system_prompt: str,
    reference: str,
    *candidates: str,
    judge_prompt: str = _JUDGE_SYSTEM,
    pass_threshold: int = 6,
    model: str = "claude-haiku-4-5",
    max_workers: int = 8,
    max_retries: int = 3,
) -> list[EvaluationResult]:
    """
    Evaluate each candidate against a single shared reference. Thin
    wrapper around llm_judge_batch() for the "one reference, many
    candidates" shape.
    """
    if not candidates:
        raise ValueError("At least one candidate must be supplied.")
    pairs = [(reference, candidate) for candidate in candidates]
    return llm_judge_batch(
        system_prompt,
        pairs,
        judge_prompt=judge_prompt,
        pass_threshold=pass_threshold,
        model=model,
        max_workers=max_workers,
        max_retries=max_retries,
    )


# ---------------------------------------------------------------------------
# Dataset-entry preprocessing (your extraction logic)
# ---------------------------------------------------------------------------


def evaluate_llm_as_judge(
    *inputs: dict[str, Any],
    guideline: str = "",
    model: str = "claude-haiku-4-5",
    pass_threshold: int = 6,
    max_workers: int = 8,
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    """
    Takes dataset entries (each with "final_ground_truth" and "turns"),
    extracts (reference, candidate) pairs, and scores all of them
    concurrently against the shared guideline.
    """
    pairs = [
        (str(entry["final_ground_truth"]), str(entry["turns"][-1]))
        for entry in inputs
    ]

    results = llm_judge_batch(
        guideline,
        pairs,
        pass_threshold=pass_threshold,
        model=model,
        max_workers=max_workers,
        max_retries=max_retries,
    )

    return [r.to_dict() for r in results]


# ---------------------------------------------------------------------------
# CLI / demo entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="LLM-as-Judge: evaluate candidates against a reference."
    )
    parser.add_argument("--judge", required=False, help="Evaluation Prompt (overrides default system prompt) [filepath]")
    parser.add_argument("--system", required=True, help="Task / evaluation system prompt")
    parser.add_argument("--reference", required=True, help="Reference (gold) string")
    parser.add_argument("--candidates", nargs="+", required=True, help="Candidate strings")
    parser.add_argument("--threshold", type=int, default=6, help="Pass threshold (default 6)")
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    if args.judge:
        if not os.path.isfile(args.judge):
            print(f"Error: Judge prompt file '{args.judge}' not found.", file=sys.stderr)
            sys.exit(1)
        with open(args.judge, "r") as f:
            args.judge = f.read()
    else:
        args.judge = _JUDGE_SYSTEM

    evaluations = llm_judge(
        args.system,
        args.reference,
        *args.candidates,
        judge_prompt=args.judge,
        pass_threshold=args.threshold,
        model=args.model,
        max_workers=args.max_workers,
        max_retries=args.max_retries,
    )

    if args.json:
        print(json.dumps([r.to_dict() for r in evaluations], indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  LLM-AS-JUDGE EVALUATION  ({len(evaluations)} candidate(s))")
        print(f"{'='*60}")
        for r in evaluations:
            print(r)
        passing = sum(1 for r in evaluations if r.verdict == "pass")
        print(f"\n{'='*60}")
        print(f"  Summary: {passing}/{len(evaluations)} passed (threshold ≥ {args.threshold})")
        print(f"{'='*60}\n")