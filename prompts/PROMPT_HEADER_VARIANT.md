## TASK

You will be generating a single multi-turn conversation example about a topic discussed in further detail later. Your example output should follow the structure given below (see in-line comments for more detail on each section):

## OUTPUT

The output you will generate will be a JSON file with the structure below

{
  "dialogue_id": "unique_hex_id", // you can keep this a placeholder value
  "metadata": {
    "tier": "placeholder-value", // This will be provided in the topic, write it here
    "primary_task": "ABC", // This will be provided in the topic, write it here
    "downstream_application": "placeholder", // You will provide this, picking from the options in the topic
    "language": "Python", // This will remain relatively static unless the task specifically asks you to change it.
    "complexity_score": 8, // This will be human annotated, no need to put anything here
    "topics": ["placeholder_topic_1", "placeholder_topic_2"] // You will provide these topics, generally relating to the conversation you generate
  },
  "turns": [ // Below are the main turns, there should always be an equal number user and assistant turns
    {
        "turn_id" : 1, // each turn has an id. It should increment every turn
        "messages" : [ // Below are the messages, there should always be 2, one user and one assistant, in that order
            {
                "role": "user", // Should switch back and forth between user and assistant (user on odd and assistant on even ids)
                "content": "natural_language_instruction", // This contains the main natural language content of the user request
                "code_snippet": "initial_code_state", // When the user includes code in their request, place the code here
                "metadata": { "contains_code": true, "intent": "goal_setting" } // metadata shows whether there is code in the code_snippet and the user's main goal with this particular request, provided by you
            },
            {
                "role": "assistant", // Switched from user
                "content": "natural_language_explanation", // Same as above for Turn 1
                "code_snippet": "assistant_generated_code", // Same as above for Turn 1
                "reasoning_chain": "internal_monologue_or_step_by_step_logic", // This should provide the model's hidden thought process that the user does not see
                "ground_truth_valid": true or false based on final_ground_truth // If this is the final turn, provide whether or not the assistants response was correct
            }
        ]
    },
… // This is to indicate that there will be more than 1 turn. Your generation must include 2 to 5 turns
  ],
  "final_ground_truth": {
    "expected_output_code": "final_correct_snippet", // If the final expected answer was code, put the expected answer here
    “expected_nl_output”: “nl output for cases like documentation”, // if the final expected answer is natural language, put expected answer here
    “test_cases_to_pass” : “test case code including comparing input towards output. Entry point should be the same as the method name in the expected output code.”, // Test cases to run to check if the code is correct
    "reference_solution": "### reference solution and explanation on how to judge ###", // Make sure to provide a section on how to judge.
    "constraints_to_check": ["entry function to check"] // code entry point to check correctness for test cases, or whatever other testing is required. Should be dependent on task.
  }
}
