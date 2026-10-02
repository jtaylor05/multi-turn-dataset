from .bleu_eval import calculate_codebleu_scores
from .llm_eval import llm_judge
from .code_eval import evaluate_functional_correctness_batch, _is_pytest_style

import json

### This module will implement a few basic methods of evaluation, including code bleu, code-running-evaluation, and llm-as-judge evaluation. The goal is to have a single module that can be used to evaluate the outputs of the evaluation pipeline in a consistent way. This module will be imported by the main evaluation script and used to evaluate the outputs of the evaluation pipeline.

def evaluate_code_bleu(reference : str, *inputs) -> dict:
    """
    The evaluate_code_bleu function takes a list of inputs and returns a dictionary containing the code bleu score for each input.
    """
    # Here we would have the actual logic to compute the code bleu score for each input
    bleus = calculate_codebleu_scores(list(inputs), reference)
    scores = []
    for bleu_score in bleus:
        scores.append([bleu_score["code_bleu"]])
    return scores

def evaluate_llm_as_judge(*inputs, guideline : str = "", model="claude-haiku-4-5") -> dict:
    """
    The evaluate_llm_as_judge function takes a list of inputs and returns a dictionary containing the llm-as-judge score for each input.
    """
    # Here we would have the actual logic to compute the llm-as-judge score for each input
    
    references = [str(input["final_ground_truth"]) for input in inputs]
    candidates = [str(input["turns"][-1]) for input in inputs]
    
    print(f"Evaluating {len(candidates)} candidate(s) with LLM-as-judge...")
    
    scores = []
    for idx, ref, cand in zip(range(len(references)), references, candidates):
        llm_scores = llm_judge(guideline, ref, cand, model=model)
        for llm_score in llm_scores:
            scores.append(llm_score.to_dict())
    
    return scores

def evaluate_code_running(*inputs) -> list:
    """
    Runs each input's final code_snippet against its own test_cases_to_pass,
    concurrently, sharing one Manager/ThreadPoolExecutor across the whole
    batch. Also picks up pytest-style test suites and entry-point aliasing
    automatically via evaluate_functional_correctness_batch.
    """
    problems = []
    for entry in inputs:
        code_snippet = entry["turns"][-1]["messages"][-1].get("code_snippet")
        raw_test_cases = entry["final_ground_truth"].get("test_cases_to_pass")
        constraints_to_check = entry["final_ground_truth"].get("constraints_to_check")

        if raw_test_cases is not None and _is_pytest_style(raw_test_cases):
            test_cases = raw_test_cases
        elif raw_test_cases is not None:
            test_cases = "def check():\n    " + "\n    ".join(raw_test_cases.split("\n"))
        else:
            test_cases = None

        problems.append({
            "code": code_snippet,
            "test_cases": test_cases,
            "entry_point": "check",
            "constraints_to_check": constraints_to_check,
            "applicable": raw_test_cases is not None,
        })

    return evaluate_functional_correctness_batch(problems, timeout=3.0)