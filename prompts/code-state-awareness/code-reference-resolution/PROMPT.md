## Task Description
This task is called Code Reference Resolution (CRR). It is part of the Code State Awareness Tier. Some downstream applications include symbol reference, diff reference, error-log reference

This task involves the model resolving vague implicit references to earlier code or fixes (i.e. using pronouns such as "this" or "it"). This could look like the user introducing an initial code snippet that includes a few different functions from their code base. In the final turn the user will ask the assistant to complete a task related to one of the first mentioned functions (fix, rewrite, edit, etc.) by implicit and vague reference, using only pronouns. Avoid mentioning or explaining the functions in too much detail during the distractor task or the final evaluation turn.

## Definition

The capacity to resolve anaphoric and symbolic pointers (e.g., pronouns like ``it,'' or definite descriptions like ``the previous helper'') to specific nodes in the project’s Abstract Syntax Tree (AST). It evaluates the accuracy of symbolic binding within a stateful execution context, especially when multiple structurally similar entities are present in the history.

## Guide

- Step 1: User introduces multiple related code snippets or functions (typically 2-3 functions), providing brief descriptions of what each does and how they relate to each other
- Step 2: Assistant acknowledges the code structure and confirms understanding of the relationships between the functions, using the actual function names
- Final Step: User requests a modification, fix, or update to one of the originally introduced functions using only vague pronouns ("it", "this", "that one", "the other one") without naming the specific function, and the assistant must correctly identify which function is being referenced and provide the appropriate solution while preserving the behavior of related functions

## Examples
```json
[
  {
    "role": "user",
    "content": "I have a couple of utility functions in my codebase:\n\n```python\ndef normalize_name(name):\n    return name.strip().lower()\n\n\ndef format_user(name, age):\n    clean = normalize_name(name)\n    return f\"{clean}:{age}\"\n```\nThe first one cleans up a string, and the second one builds a display value using it."
  },
  {
    "role": "assistant",
    "content": "Got it. So `normalize_name` handles string cleanup, and `format_user` depends on it to produce a combined name/age representation."
  },
  {
    "role": "user",
    "content": "Separately, I'm also experimenting with decorators for timing function calls:\n\n```python\nimport time\n\ndef timing(fn):\n    def wrapper(*args, **kwargs):\n        start = time.time()\n        result = fn(*args, **kwargs)\n        end = time.time()\n        print(f\"Elapsed: {end - start}\")\n        return result\n    return wrapper\n```\nThis is not wired into the other code yet."
  },
  {
    "role": "assistant",
    "content": "That decorator measures execution time and prints it, but as you said, it’s independent from the name formatting utilities you showed earlier."
  },
  {
    "role": "user",
    "content": "Right now it fails when the input name is None. Can you adjust it so that this case is handled gracefully without changing how the other one works?"
  },
  {
    "role": "assistant",
    "content": "Yes. You can update `normalize_name` to safely handle `None` by returning an empty string (or another default), while leaving `format_user` unchanged:\n\n```python\ndef normalize_name(name):\n    if name is None:\n        return \"\"\n    return name.strip().lower()\n```\nThis way the downstream formatting logic continues to work, but malformed input won’t raise an exception."
  }
]

[
  {
    "role": "user",
    "content": "I have two related helper functions:\n\n```python\ndef slugify(title):\n    return title.strip().lower().replace(\" \", \"-\")\n\n\ndef build_url(base, title):\n    slug = slugify(title)\n    return f\"{base}/{slug}\"\n```\nThe first one normalizes a string, and the second one uses it to construct a URL."
  },
  {
    "role": "assistant",
    "content": "Okay, so `slugify` is responsible for turning the title into a URL-friendly form, and `build_url` relies on it to assemble the final URL."
  },
  {
    "role": "user",
    "content": "Separately, I also wrote this retry utility for network calls:\n\n```python\nimport time\n\ndef retry(fn, attempts=3):\n    for i in range(attempts):\n        try:\n            return fn()\n        except Exception:\n            time.sleep(1)\n    raise RuntimeError(\"All attempts failed\")\n```\nThis is used in a different part of the codebase."
  },
  {
    "role": "assistant",
    "content": "That function just retries a callable a fixed number of times and isn’t connected to the URL or slug logic you showed earlier."
  },
  {
    "role": "user",
    "content": "When the title is an empty string or None, it ends up producing an odd URL. Can you update it to handle that more gracefully without changing how the other one works?"
  },
  {
    "role": "assistant",
    "content": "You can make `slugify` handle empty or `None` values safely, while keeping `build_url` the same:\n\n```python\ndef slugify(title):\n    if not title:\n        return \"untitled\"\n    return title.strip().lower().replace(\" \", \"-\")\n```\nThis way the URL builder continues to behave as before, but malformed input won’t result in awkward URLs."
  }
]
```