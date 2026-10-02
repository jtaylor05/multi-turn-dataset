## Task Description
This task is called Semantic Code Rewriting (SCR). It is part of the Iterative Code Evolution Tier. Some downstream applications include refactoring, performance optimization, Library/API migration, test case generation.

This task involves the model modifying code behaviour or extend logic while preserving core intent. On the initial turn, the user will introduce a code snippet or artefact. After the assistant's turn, the user will then ask the model to improve the artefact, whether by improving efficiency, refactoring to different dependencies or migrating APIs. The user can request multiple of these improvements over the course of multiple turns. The user should avoid being vague, and request specific changes, rather than just requesting for a 'better' function.

## Definition

The execution of code transformations that modify or extend the functional behavior of a program while preserving its core intentionality. This evaluates the model's ability to implement complex enhancements such as performance optimizations, security hardening, or API migrations that require deep logic re-engineering.

## Guide

- Step 1: User introduces a code snippet or artifact that works but may need improvement in some way (efficiency, dependencies, API version, structure, etc.)

- Step 2: Assistant acknowledges the code and confirms understanding of what it does and how it works, without immediately suggesting changes

- Step 3+: Over 1-3 additional turns, user requests specific modifications to improve the code while preserving its core intent and behavior. Requests should be concrete and specific, such as: migrate to a different library/API version, refactor to use different dependencies, optimize for performance (time or space), change implementation approach (iterative to recursive, synchronous to async), add caching/memoization, or rewrite to use different language features/patterns

- Final Step: Assistant rewrites the code according to the requested changes while preserving the original function signature, return format, and core behavior so that calling code doesn't need modifications. The explanation should clarify what changed internally while emphasizing that external behavior remains the same


## Examples
```json
[
  {
    "role": "user",
    "content": "I have this function that fetches user data from our old internal API:\n\n```python\nimport requests\n\ndef get_user_profile(user_id):\n    response = requests.get(f'http://api.internal.com/v1/users/{user_id}')\n    data = response.json()\n    return {\n        'id': data['userId'],\n        'name': data['fullName'],\n        'email': data['emailAddress'],\n        'created': data['registrationDate']\n    }\n```\nIt works but we're migrating to a new API endpoint with a different response structure."
  },
  {
    "role": "assistant",
    "content": "Got it. Your function calls the v1 API and transforms the response fields into a standardized format for your application."
  },
  {
    "role": "user",
    "content": "The new API is at `/v2/users/{user_id}` and returns fields like `user_id`, `display_name`, `primary_email`, and `created_at`. Can you rewrite this to use the new endpoint while keeping the same return format?"
  },
  {
    "role": "assistant",
    "content": "Here's the rewritten function for the v2 API:\n\n```python\nimport requests\n\ndef get_user_profile(user_id):\n    response = requests.get(f'http://api.internal.com/v2/users/{user_id}')\n    data = response.json()\n    return {\n        'id': data['user_id'],\n        'name': data['display_name'],\n        'email': data['primary_email'],\n        'created': data['created_at']\n    }\n```\n\nThis maintains the exact same function signature and return structure, so callers won't need any changes. Only the endpoint URL and field mappings have been updated to match the v2 API schema."
  }
]
[
  {
    "role": "user",
    "content": "I have this function that searches for repositories using the GitHub API v3:\n\n```python\nimport requests\n\ndef search_repositories(query, max_results=10):\n    url = 'https://api.github.com/search/repositories'\n    params = {'q': query, 'per_page': max_results}\n    headers = {'Accept': 'application/vnd.github.v3+json'}\n    \n    response = requests.get(url, params=params, headers=headers)\n    data = response.json()\n    \n    results = []\n    for repo in data['items']:\n        results.append({\n            'name': repo['name'],\n            'owner': repo['owner']['login'],\n            'stars': repo['stargazers_count'],\n            'url': repo['html_url']\n        })\n    \n    return results\n```\nIt returns a clean list of repository info."
  },
  {
    "role": "assistant",
    "content": "I see. Your function queries GitHub's search API and extracts key repository details into a simplified format."
  },
  {
    "role": "user",
    "content": "We're moving to use PyGithub library instead of raw requests. Can you rewrite this to use PyGithub while keeping the same return format?"
  },
  {
    "role": "assistant",
    "content": "Here's the rewritten function using PyGithub:\n\n```python\nfrom github import Github\n\ndef search_repositories(query, max_results=10):\n    g = Github()  # Anonymous access\n    repos = g.search_repositories(query=query)\n    \n    results = []\n    for repo in repos[:max_results]:\n        results.append({\n            'name': repo.name,\n            'owner': repo.owner.login,\n            'stars': repo.stargazers_count,\n            'url': repo.html_url\n        })\n    \n    return results\n```\n\n**Installation:**\n```bash\npip install PyGithub\n```\n\nThis maintains the exact same function signature and return structure. The PyGithub library handles authentication, rate limiting, and pagination more elegantly than raw requests, while your calling code remains unchanged."
  }
]
```