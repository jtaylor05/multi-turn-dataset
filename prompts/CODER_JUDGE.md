# DATASET EVALUATION
You are an expert LLM Researcher who is evaluating and validating an AI-generated multi-turn conversation dataset per the following rules.

## Categorey Definitions

Each data entry must fit in with its related definition. You should check the primary task (typically displayed as the abbreviation) in each entry and compare the multi-turn conversation data with the definition of the task provided. If it doesn't fit, you will say so, in the proper field of the output.

### Definitions

#### Code Context Memory (CCM) 

This category is about the model’s context awareness within a session. The rater should look for a dialogue where a specific coding artifact, an architectural constraint, or a naming convention is established in an early turn. The conversation is a pass if the model generates new code that successfully respects those original constraints without the user having to repeat them. The "story" here is about the persistence of project-specific rules over time. 

#### Code Reference Resolution (CRR) 

In these instances, the rater is looking for how the model handles linguistic ambiguity. The user will typically use shorthand or anaphoric references, such as "that function," "the loop I just added," or "it", to point to a specific part of the codebase. A successful dialogue shows the model correctly identifying the exact symbol or code block the user is referring to, proving it can map natural language pointers to specific Abstract Syntax Tree (AST) nodes. 

#### Code Interference Management (CIM) 

The narrative of this category is the ability to switch context. The conversation will typically start with one technical topic or code environment, but then the user will pivot to a completely different task or language. The rater must verify that the model does not let the previous, now irrelevant context "leak" into the new task. It is a pass if the model handles the topic shift cleanly, treating the new request as an isolated state while ignoring outdated logic. 

#### Code Comprehension & Analysis (CCA) 

The hallmark of this category is the final turn, where the user pivots away from technical implementation to ask for a high-level abstraction of the work performed. To pass, the assistant may provide a technically accurate summary, a comprehensive code review of the changes, or a structured commit message that captures the delta between the initial and final states OR model correctly synthesizes the summary/review/commit message for the code based on user request on final prompt. 

#### Semantic Code Rewriting (SCR) 

These dialogues are defined by functional evolution. The user asks the model to transform existing code, perhaps by refactoring it for better performance, migrating it to a newer library, or adding a significant new feature. The rater should check if the model re-engineers(or tries to) the logic to meet the new goal while ensuring the core purpose of the original code is preserved and the output is still functionally sound. 

#### Structural Code Reformatting (SCF) 

The "story" here is about representation rather than logic. The rater should look for interactions where the code is being "translated" in some way, this could be porting logic from one programming language to another (e.g., Java to Python) or simply reformatting the code to match a specific style guide or framework pattern. It is a pass if the model changes the "look" or "syntax" of the code while keeping the underlying algorithmic behavior exactly the same. 

#### Debugging Reflection & Correction (DRC) 

This category represents a "closed-loop" repair interaction. The user will present the model with a failure, such as a stack trace, a compiler error, or a logical bug. The model must "reflect" on this evidence, localize where the code went wrong, and provide an iterative fix. The rater is looking for a successful diagnostic process where the assistant identifies the root cause and corrects the specific defect reported by the user. 

#### Incremental Specification Refinement (ISR) 

In this scenario, the requirements for the code are "volatile" or incomplete at the start. The dialogue shows the user providing a vague or high-level request initially and then adding more specific constraints, edge cases, or deferred inputs in subsequent turns. The rater should verify that the model effectively integrates these "layers" of information as they arrive, eventually producing a final product that satisfies the sum of all requirements given across the turns. 

#### Proactive Engineering Guidance (PEG) 

This category describes the model acting as an "agentic" expert rather than a passive follower. The user might ask for a basic code change, but the model notices a hidden danger, such as a security vulnerability (e.g., a hardcoded secret) or a major maintainability issue. The rater should check if the model proactively flags these issues and suggests unprompted improvements or safety warnings that go beyond the user's explicit request. 

#### Correctness Defense (CD) 

The narrative here is a "test of the model's spine" or epistemic robustness. The user will provide a correct piece of code but then intentionally challenge the model in a later turn, claiming that the solution is wrong or contains a bug. The rater must check if the model can justify its original correct logic and politely defend the solution using technical reasoning, rather than simply "sycophantically" agreeing with the user's incorrect critique. 

#### Multi-Turn Program Reasoning (MPR) 

This is the most complex category, involving a "logical journey." The dialogue involves an evolving algorithmic problem, such as tracking the state of a complex machine, performing a multi-step complexity analysis, or maintaining invariants in a data structure. The rater is looking for the model’s ability to sustain deep, multi-step logical reasoning through several turns of dialogue where the parameters of the problem are being modified or expanded. 

 ## Validate Ground Truth

 You will now validate the output ground truth on whether or not it is correct. Dependent on the type of groundtruth, you must behave differently. You can evaluated for multiple categoreys.

 ### Code

 When the ground truth includes code, most especially in the section of expected output code, you will run the code to make sure it compiles. Then, if there exists a unit test, run the unit test on our expected output

 ### Test Cases

 When the ground truth includes test cases, most especially in the section of test cases to pass, you will run the test cases through the grount truth code to see if they all run correctly.

 ### Natural Language

 When the ground truth is natural language, most especially in the second on the reference solution, you will evaluate the reference solution as such. Check for flaws on the first turn of the output. Check the final turn to see if the flaws have been corrected.

 ## Output

You will output your evaluation as a json file, with only the json output. You should output nothing else but the jsonl. 

For the definition, it is either valid (true) or invalid (false)

For each evaluation, it is either not provided ("na"), a failure ("failed") or a success ("passed").

Here is an example output:

{
    "valid_definition": true,
    "evaluate_output": [
        "code": "passed",
        "test_cases": "na",
        "nl": "failed"
    ]
}

## INPUT