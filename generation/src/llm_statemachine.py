
from .llm_api import LLMAPI
from .model_database import get_api

import json
from datetime import datetime

FINAL_PROMPT = """---
FINAL OUTPUT INSTRUCTIONS

You have just completed a multi-turn conversation. Now produce a single, final, wrap-up response following the rules below exactly.

Your response must consist of ONLY a single valid JSON object — nothing before it, nothing after it, no markdown code fences (no ```), no explanatory preamble. The output must be directly parseable by Python's `json.loads()`.

The JSON object must have exactly two top-level keys:

1. "content" (string):
   - Start with a direct, complete answer to the FINAL prompt/request in the conversation.
   - Follow this with a concise summary of the conversation as a whole, covering ONLY the major points, decisions, and conclusions reached. Do not include minor clarifications, small talk, or intermediate steps that were later superseded.
   - Do not include any code in this field — describe code changes in prose only if relevant (e.g., "added input validation, then switched to a recursive approach").
   - Plain text only. Do not use markdown headers, backticks, or code fences inside this string.

2. "code_snippet" (string):
   - The COMPLETE, final, runnable code that reflects the end state of the entire conversation — not a diff, not just what changed in the last turn.
   - If earlier code was modified, rewritten, or replaced over the course of the conversation, include only the final, current version, fully merged and consistent, as if written fresh.
   - The code must be syntactically valid and runnable on its own (including necessary imports/setup).
   - If the conversation did not involve any code, set this field to an empty string "".

FORMATTING REQUIREMENTS (critical — the output must be valid JSON):
- Escape all double quotes, backslashes, and newlines within string values properly (e.g., use \n for line breaks in code, not literal line breaks).
- Do not use trailing commas.
- Do not include comments inside the JSON structure itself.
- Do not wrap the JSON in ``` or ```json fences.
- Output nothing outside the single JSON object — no "Here is the output:" preamble, no closing remarks.

Example of the exact shape expected (structure only, not content):
{"content": "...", "code_snippet": "..."}
---"""

class StateMachine():
    
    current_id = 0
    
    def __init__(self, api : LLMAPI, inputs : list[dict]):
        self.id = self.current_id
        StateMachine.current_id += 1
        
        self.api = api
        self.states = {i["dialogue_id"]:"STARTING" for i in inputs}
        
        self.inputs = inputs
        self.conversations = {d["dialogue_id"] : [] for d in self.inputs}
        
        self._batch_id = None
    
    def _get_prompt(self, entry : dict, index : int) -> str:
        user_prompt = entry["turns"][index]["messages"][0]
        ret = user_prompt["content"] + '\n'
        if user_prompt["metadata"]["contains_code"]:  
            return ret + entry["turns"][index]["messages"][0].get("code_snippet","")
        return ret
    
    def _get_length(self, entry : dict) -> int:
        return len(entry["turns"])
    
    def _get_current_length(self, entry : dict) -> int:
        history = self.conversations[entry["dialogue_id"]]
        return len([d for d in history if d["role"] == "user"])
    
    def poll_status(self) -> bool:
        if self._batch_id is None:
            return False

        poll_results = self.api.poll_batch(self._batch_id)
        match poll_results[0]:
            case "pending":
                return True
            case "failed":
                return False
            case "complete":
                pass
        
        should_continue = False
        for res in poll_results[1]:
            did = res["conv_id"]
            if res.get("output", None) is None:
                self.conversations[did] += [res.get("error", "Unknown Error")]
                self.states[did] = "ERROR"
            else:
                self.conversations[did] += [{"role":"assistant", "content":res["output"]}]
                if self.states[did] == "FINISHING":
                    self.states[did] = "DONE"
                if self.states[did] == "PROCESSING":
                    self.states[did] = "WAITING"
                    should_continue = True
        
        return should_continue
    
    def update(self) -> None:
        batch_requests = []
        for input in self.inputs:
            did = input["dialogue_id"]
            status = self.states[did]
            match status:
                case "STARTING":
                    prompt = self._get_prompt(input, 0)
                    batch_requests += [{"conv_id":did, "prompt":prompt, "history":[]}]
                    self.conversations[did] += [{"role":"user", "content":prompt}]
                    self.states[did] = "PROCESSING"
                case "WAITING":
                    current_index = self._get_current_length(input)
                    prompt = self._get_prompt(input, current_index)
                    #batch_requests += [{"conv_id":did, "prompt":prompt, "history":self.conversations[did]}]
                    self.conversations[did] += [{"role":"user", "content":prompt}]
                    if current_index == self._get_length(input) - 1:
                        batch_requests += [{"conv_id":did, "prompt":prompt + "\n" + FINAL_PROMPT, "history":self.conversations[did]}]
                        self.states[did] = "FINISHING"
                    else:
                        batch_requests += [{"conv_id":did, "prompt":prompt, "history":self.conversations[did]}]
                        self.states[did] = "PROCESSING"
                case "PROCESSING": continue
                case "FINISHING": continue
                case "DONE": continue
                case "ERROR":continue
        if len(batch_requests) > 0:
            self._batch_id = self.api.submit_batch(batch_requests, "")
    
    def complete(self) -> bool:
        return sum([1 for state in self.states.values() if state == "DONE"]) == len(self.inputs)
    
    def model(self) -> str:
        return self.api.model
    
    def results(self) -> list[dict]:
        return [{"dialogue_id": id, "turns":conversation} for id, conversation in self.conversations.items()]

    def save(self) -> None:
        date = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        file_name = f"{date}-{self.id}.jsonl"
        with open(file_name, 'w') as f:
            first_entry = {"api":self.api.model}
            all_lines = [first_entry] + [{"state":self.states[d["dialogue_id"]], 
                                          "entry":d, 
                                          "history": self.conversations[d["dialogue_id"]]} for d in self.inputs]
            for line in all_lines:
                f.write(json.dumps(line) + '\n')
            f.close() 
    
    @classmethod
    def load(cls, file_name : str):
        with open(file_name, 'r') as f:
            lines = [json.loads(s) for s in f.readlines()]
            model = lines[0]["api"]
            
            api = get_api(model)
            sm = cls(api, [])
            sm.states = {d["entry"]["dialogue_id"] : d["state"] for d in lines[1:]}
            sm.inputs = [d["entry"] for d in lines[1:]]
            sm.conversations = {d["entry"]["dialogue_id"] : d["history"] for d in lines[1:]}
            return sm
            
            
            
            