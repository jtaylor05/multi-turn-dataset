## Task Description
This task is called Code Context Memory (CCM). It is part of the Code State Awareness Tier. Some downstream applications include function recall, variable persistence, and architectural constraints.

This task involves the model recalling or reusing previously introduced code artefacts or constraints across turns. This could look like the user introducing an initial code snippet or context which is not mentioned until a later turn. In the final turn, the user will ask for a task that utilizes the seeded knowledge, without specifically mentioning that the context is required. Avoid using phrases like, "we will come back to this later," as you should avoid indicating that the model should remember this context specifically.

## Definition

The ability of a model to maintain a persistent, stateful representation of the software environment across a dialogue. It measures the retention of ``global'' project laws, such as architectural patterns, variable semantics, and technical debt decisions, ensuring that subsequent code generations adhere to constraints established in earlier turns without explicit re-statement.

## Guide

- Step 1: Generate user-introduced code snippet or artefact
- Step 2: Generate response acknowledging the user's code
- Final Step: Generate user request relating to the initial task introduced in Step 1, without reiterating the context brought up in that step. 

## Examples
```json
[
  {
    "role": "user",
    "content": "I'm setting up a small Python client library. Initial context:\n\n- Constant: API_VERSION = \"v1\"\n- Default params: DEFAULT_PARAMS = {\"lang\": \"en\"}\n- Helper function:\n\n```python\ndef build_endpoint(resource):\n    return f\"/api/{API_VERSION}/{resource}\"\n```\n\nWe’ll build on this later."
  },
  {
    "role": "assistant",
    "content": "Understood.\n\nYou currently have a versioned API scheme, shared default parameters, and a helper for constructing endpoints. I’ll keep that structure in mind."
  },
  {
    "role": "user",
    "content": "While we're at it, could you add a small utility that converts a dictionary into a URL query string?"
  },
  {
    "role": "assistant",
    "content": "Sure, here’s a simple helper:\n\n```python\nfrom urllib.parse import urlencode\n\ndef to_query_string(params):\n    return urlencode(params)\n```"
  },
  {
    "role": "user",
    "content": "Now add a function that prepares the full request path for a given resource, including any default settings."
  },
  {
    "role": "assistant",
    "content": "Here’s one way to do that using the existing project helpers and defaults:\n\n```python\ndef prepare_request(resource):\n    endpoint = build_endpoint(resource)\n    query = to_query_string(DEFAULT_PARAMS)\n    return f\"{endpoint}?{query}\"\n```\n\nThis builds on the established API structure and shared configuration without duplicating that logic."
  }
]

[
  {
    "role": "user",
    "content": "I'm prototyping a data processing module. Initial setup:\n\n- Constant: BATCH_SIZE = 100\n- Global flag: STRICT_MODE = True\n- Existing function:\n\n```python\ndef process_record(record):\n    if STRICT_MODE and \"id\" not in record:\n        raise ValueError(\"Missing id\")\n    return record[\"id\"], record.get(\"value\")\n```\n\nWe’ll add more functionality later."
  },
  {
    "role": "assistant",
    "content": "Got it.\n\nSo far the module defines batch sizing, a strict validation mode, and a per-record processing helper. I’ll keep this context in mind."
  },
  {
    "role": "user",
    "content": "Separate task for now: I also need a quick function that chunks a list into fixed-size pieces."
  },
  {
    "role": "assistant",
    "content": "Here’s a simple utility for that:\n\n```python\ndef chunk_list(items, size):\n    for i in range(0, len(items), size):\n        yield items[i:i + size]\n```"
  },
  {
    "role": "user",
    "content": "Please add a function that processes a collection of records efficiently and returns the results."
  },
  {
    "role": "assistant",
    "content": "You can implement it like this, building on the existing helpers and constraints:\n\n```python\ndef process_records(records):\n    results = []\n    for batch in chunk_list(records, BATCH_SIZE):\n        for record in batch:\n            results.append(process_record(record))\n    return results\n```\n\nThis approach respects the established batch size and validation behavior without re-encoding those rules."
  }
]
```