from src.process_data import process_data
import src.evaluation as ev

import argparse
import json

from pathlib import Path

TASK_TO_CODE = {
    "Code Context Memory"                  : "CCM",
    "Code Reference Resolution"            : "CRR",
    "Code Interference Management"         : "CIM",
    "Code Comprehension & Analysis"        : "CCA",
    "Semantic Code Rewriting"              : "SCR",
    "Structural Code Reformatting"         : "SCF",
    "Debugging Reflection & Correction"    : "DRC",
    "Incremental Specification Refinement" : "ISR",
    "Proactive Engineering Guidance"       : "PEG",
    "Correctness Defense"                  : "CD",
    "Multi-Turn Program Reasoning"         : "MPR",
}

TASK_TO_EVAL = {
    "CCM" : [ev.evaluate_llm_as_judge],
    "CRR" : [ev.evaluate_llm_as_judge],
    "CIM" : [ev.evaluate_llm_as_judge],
    "CCA" : [ev.evaluate_llm_as_judge],
    "SCR" : [ev.evaluate_code_running, ev.evaluate_llm_as_judge],
    "SCF" : [ev.evaluate_code_running, ev.evaluate_llm_as_judge],
    "DRC" : [ev.evaluate_code_running, ev.evaluate_llm_as_judge],
    "ISR" : [ev.evaluate_code_running, ev.evaluate_llm_as_judge],
    "PEG" : [ev.evaluate_llm_as_judge],
    "CD"  : [ev.evaluate_llm_as_judge],
    "MPR" : [ev.evaluate_llm_as_judge]
}

CODE_EVAL_TEST = {
    "CCM" : [],
    "CRR" : [],
    "CIM" : [],
    "CCA" : [],
    "SCR" : [ev.evaluate_code_running],
    "SCF" : [ev.evaluate_code_running],
    "DRC" : [ev.evaluate_code_running], 
    "ISR" : [ev.evaluate_code_running], 
    "PEG" : [],
    "CD"  : [],
    "MPR" : []
}

def read(file_path) -> list:
    data = []
    with open(file_path, 'r') as f:
        if file_path.endswith('.jsonl'):
            raw_data_line = f.readline()
            while raw_data_line:
                raw_data = json.loads(raw_data_line)
                data.append(raw_data)
                raw_data_line = f.readline()
            return data
        elif file_path.endswith('.json'):
            raw_data = json.load(f)
            data.append(raw_data)
            return data
        else:
            print(f"Unsupported file format: {file_path}. File ignored.")
            return []

def main():
    parser = argparse.ArgumentParser(
        description="Process input JSON/JSONL files and run evaluations."
    )
    parser.add_argument(
        "input_files", nargs="+", help="Input file(s) (.jsonl or .json)"
    )
    parser.add_argument(
        "--test-code-eval",
        dest="test_code_eval",
        action="store_true",
        help="Use CODE_EVAL_TEST mapping instead of TASK_TO_EVAL",
    )
    parser.add_argument(
        "--output",
        default="evaluated_data.jsonl",
        required=False,
        type=str,
        help="output file name"
    )
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5",
        required=False,
        type=str,
        help="model used in llm-as-judge evaluation"
    )
    args = parser.parse_args()

    eval_map = CODE_EVAL_TEST if args.test_code_eval else TASK_TO_EVAL

    all_input = []
    for file in args.input_files:
        data = read(file)
        if data is not None:
            all_input += data
            
    all_processed = process_data(*all_input)
    print(f"Processed {len(all_processed)} items. Starting evaluation...")
    for processed in all_processed:
        task = processed["metadata"]["primary_task"]
        if task not in eval_map:
            print(f"Unknown task: {task}. Skipping.")
            continue
        eval_functions = eval_map[task]
        scores = {}
        for eval_fn in eval_functions:
            if eval_fn == ev.evaluate_llm_as_judge:
                scores[eval_fn.__name__] = eval_fn(processed, model=args.model)
            else:
                scores[eval_fn.__name__] = eval_fn(processed)
        processed["scores"] = scores
    
    fp = Path(args.output)
    fp.parent.mkdir(parents=True, exist_ok=True)
    
    with open(fp, 'w') as f:
        for item in all_processed:
            f.write(json.dumps(item) + '\n')

    

if __name__ == "__main__":
    main()