import json
import sys

### This module contains the logic for processing data in the evaluation pipeline.

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

def process_data(*inputs, codes : dict = TASK_TO_CODE) -> list:
    """
    The process_data function takes raw data from anthropic batch response and outputs a jsonl file in the following format:
    {
        "task" : "task_name",
        "content" : "processed_content"
    }
    """
    print(f"Processing {len(inputs)} items...")
    output = []
    for input_data in inputs:
        if "dialogue_id" in input_data:
            output.append(input_data)
            continue
        if check_max_tokens(input_data):
            print(f"Warning: Max tokens reached for dialogue_id {input_data.get('dialogue_id', 'unknown')}. Skipped...")
            continue
        content = get_data(input_data)
        if not content:
            print(f"Couldn't retrieve content. Skipped...")
            continue
        
        # Here we would have the actual processing logic to convert input_data into the desired format
        if "```json" in content:
            content = content.split("```json")[1].rsplit("```", 1)[0].strip() 
         
        try:
            processed_content = json.loads(content)
        except json.JSONDecodeError:
            print(f"Warning: Failed to parse JSON for dialogue_id {input_data.get('dialogue_id', 'unknown')}. Skipped...")
            continue
        output.append(processed_content)
    print(f"Processed {len(output)} items.")
    return output

def check_max_tokens(response) -> bool:
    if check_anthropic(response):
        return response["result"]["message"]["stop_reason"] == "max_tokens"
    if check_openai(response):
        return response["response"]["body"]["choices"][0]["finish_reason"] == "length"
        
def get_data(response) -> str:
    if check_anthropic(response):
        return get_data_anthropic(response)
    if check_openai(response):
        return get_data_openai(response)
    return None

def check_anthropic(response) -> bool:
    if isinstance(response, dict):
        return "result" in response
    return False

def get_data_anthropic(response) -> str:
    return response["result"]["message"]["content"][0]["text"]

def check_openai(response) -> bool:
    if isinstance(response, dict):
        return "response" in response
    return False

def get_data_openai(response) -> str:
    return response["response"]["body"]["choices"][0]["message"]["content"]
    

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
        
        task = d["metadata"]["primary_task"]
        
        for valid_task in TASK_TO_CODE.values():
            if valid_task in task:
                task = valid_task
                break
        
        for long_task, code in TASK_TO_CODE.items():
            if long_task in task:
                task = code
                break
        
        outputs.append({**d, "primary_task": task})

    return outputs

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
                    processed_data = process_data(raw_data)
                    output += processed_data
            if input_file.endswith('.json'):
                raw_data = json.load(f)
                processed_data = process_data(raw_data)
                output.append(processed_data)
    
    with open('processed_data.jsonl', 'w') as f:
        for item in output:
            f.write(json.dumps(item) + '\n')