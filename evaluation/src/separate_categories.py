import sys, json, re

from collections import defaultdict

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

def convert_primary_task(*dicts, codes : dict = TASK_TO_CODE) -> list:
    """
    Takes a list of dictionaries with a 'primary_task' key and converts their values
    to the corresponding three-letter code. Returns a new list of dictionaries with the
    converted values.
    """

    outputs = []
    
    for d in dicts:
        if not isinstance(d, dict):
            raise TypeError(f"Expected a dictionary, but got {type(d).__name__}.")
        if "primary_task" not in d["metadata"]:
            raise KeyError("Dictionary does not contain a 'primary_task' key.")
        
        task = str(d["metadata"]["primary_task"])
        
        task = ' '.join(re.split(" |_|-", task.upper()))
        
        for valid_task in TASK_TO_CODE.values():
            if valid_task in task:
                task = valid_task
                break
        
        for long_task, code in TASK_TO_CODE.items():
            if long_task.upper() in task:
                task = code
                break
        
        new_d = {**d}
        new_d["metadata"]["primary_task"] = task
        print(new_d.keys())
        outputs.append(new_d)

    return outputs

def separate_tasks(*dicts) -> dict:
    output = defaultdict(list)
    #print(dicts[0:2])
    for d in dicts:
        if not isinstance(d, dict):
            print(len(dicts))
            print(len(d))
            raise TypeError(f"Expected a dictionary, but got {type(d).__name__}.")
        if "primary_task" not in d["metadata"]:
            raise KeyError("Dictionary does not contain a 'primary_task' key.")
        
        output[d["metadata"]["primary_task"]].append(d)
    return output

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide the path to the input data file.")
        sys.exit(1)
    
    input_files = sys.argv[1:]
    output = []
    
    for input_file in input_files:
        with open(input_file, 'r') as f:
            if input_file.endswith('.jsonl'):
                while raw_data_line := f.readline():
                    raw_data = json.loads(raw_data_line)
                    processed_data = convert_primary_task(raw_data)
                    output += processed_data
            if input_file.endswith('.json'):
                raw_data = json.load(f)
                processed_data = convert_primary_task(raw_data)
                output += processed_data
    
    by_task = separate_tasks(*output)
    
    for task_name, task_group in by_task.items():
        with open(f'processed_{task_name}.jsonl', 'w') as f:
            for item in task_group:
                f.write(json.dumps(item) + '\n')