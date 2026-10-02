## Task Description
This task is called Incremental Specification Refinement (ISR). It is part of the Iterative Code Evolution Tier. Some downstream applications include code generation, IaC generation, requirement ambiguity, and deferred inputs.

This task involves the model resolving ambiguity and localising requirements incrementally that are provided incrementally. This multi-turn conversation might begin with the user making an ambiguous or simple request for a function, code-snippet, or algorithm. In each later turn, the user will provide additional specification to modify the initial request. You should avoid having the user request too much in one go, keeping the increments small, but meaningful.

## Definition

The ability to manage ``requirements volatility'' by aggregating and integrating underspecified or deferred constraints provided across multiple turns. It measures how effectively a model updates its internal task representation as new requirements arrive, preventing premature commitment to incorrect assumptions.

## Guide

- Step 1: User makes an initial, ambiguous, or simple request for a function, code snippet, or algorithm without providing full specifications

- Step 2: Assistant provides a reasonable basic implementation based on the underspecified request, potentially asking if additional features are needed

- Step 3+: Over 2-4 additional turns, user incrementally adds new requirements, constraints, or specifications that refine or modify the original request. Each refinement should be small but meaningful (e.g., adding error handling, changing performance requirements, adding output format changes, handling edge cases, supporting additional input types)

- Final Step: Assistant updates the implementation to incorporate all cumulative specifications, building on previous iterations rather than rewriting from scratch when possible

## Examples
```json
[
  {
    "role": "user",
    "content": "I need a function to validate email addresses."
  },
  {
    "role": "assistant",
    "content": "I can help you create an email validation function in Python. Here's a basic implementation:\n\n```python\nimport re\n\ndef validate_email(email):\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return bool(re.match(pattern, email))\n\n# Example usage\nprint(validate_email(\"user@example.com\"))  # True\nprint(validate_email(\"invalid.email\"))      # False\n```\n\nThis function uses a regular expression to check for a valid email format. Would you like me to add any additional validation rules or features?"
  },
  {
    "role": "user",
    "content": "It should also check that the domain has an MX record, and return a detailed result explaining why an email is invalid."
  },
  {
    "role": "assistant",
    "content": "I'll update the function to check MX records and provide detailed validation results:\n\n```python\nimport re\nimport dns.resolver\n\ndef validate_email(email):\n    result = {\n        'valid': True,\n        'email': email,\n        'errors': []\n    }\n    \n    # Check basic format\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    if not re.match(pattern, email):\n        result['valid'] = False\n        result['errors'].append('Invalid email format')\n        return result\n    \n    # Extract domain\n    domain = email.split('@')[1]\n    \n    # Check MX record\n    try:\n        mx_records = dns.resolver.resolve(domain, 'MX')\n        if not mx_records:\n            result['valid'] = False\n            result['errors'].append('No MX records found for domain')\n    except dns.resolver.NXDOMAIN:\n        result['valid'] = False\n        result['errors'].append('Domain does not exist')\n    except dns.resolver.NoAnswer:\n        result['valid'] = False\n        result['errors'].append('No MX records found for domain')\n    except Exception as e:\n        result['valid'] = False\n        result['errors'].append(f'DNS lookup failed: {str(e)}')\n    \n    return result\n\n# Example usage\nprint(validate_email(\"user@example.com\"))\nprint(validate_email(\"invalid@nonexistentdomain12345.com\"))\n```\n\nNote: You'll need to install the `dnspython` package: `pip install dnspython`"
  }
]
[
  {
    "role": "user",
    "content": "Write a function to find the longest common subsequence between two strings."
  },
  {
    "role": "assistant",
    "content": "I'll create a function to find the longest common subsequence (LCS) using dynamic programming:\n\n```python\ndef longest_common_subsequence(str1, str2):\n    m, n = len(str1), len(str2)\n    dp = [[0] * (n + 1) for _ in range(m + 1)]\n    \n    # Fill the dp table\n    for i in range(1, m + 1):\n        for j in range(1, n + 1):\n            if str1[i-1] == str2[j-1]:\n                dp[i][j] = dp[i-1][j-1] + 1\n            else:\n                dp[i][j] = max(dp[i-1][j], dp[i][j-1])\n    \n    # Backtrack to find the actual subsequence\n    lcs = []\n    i, j = m, n\n    while i > 0 and j > 0:\n        if str1[i-1] == str2[j-1]:\n            lcs.append(str1[i-1])\n            i -= 1\n            j -= 1\n        elif dp[i-1][j] > dp[i][j-1]:\n            i -= 1\n        else:\n            j -= 1\n    \n    return ''.join(reversed(lcs))\n\n# Example usage\nprint(longest_common_subsequence(\"ABCDGH\", \"AEDFHR\"))  # \"ADH\"\nprint(longest_common_subsequence(\"AGGTAB\", \"GXTXAYB\"))  # \"GTAB\"\n```\n\nThis returns the actual LCS string with O(m*n) time and space complexity."
  },
  {
    "role": "user",
    "content": "The space complexity needs to be O(n) instead. I'm working with very long strings and can't afford the O(m*n) space."
  },
  {
    "role": "assistant",
    "content": "I'll optimize the function to use O(n) space. Since we only need the previous row to compute the current row, we can use just two arrays:\n\n```python\ndef longest_common_subsequence(str1, str2):\n    m, n = len(str1), len(str2)\n    \n    # Use only two rows instead of full m x n table\n    prev = [0] * (n + 1)\n    curr = [0] * (n + 1)\n    \n    # Fill the dp table row by row\n    for i in range(1, m + 1):\n        for j in range(1, n + 1):\n            if str1[i-1] == str2[j-1]:\n                curr[j] = prev[j-1] + 1\n            else:\n                curr[j] = max(prev[j], curr[j-1])\n        # Swap rows\n        prev, curr = curr, prev\n        curr = [0] * (n + 1)\n    \n    # The length is in prev[n]\n    lcs_length = prev[n]\n    \n    # Note: To reconstruct the actual LCS string with O(n) space,\n    # we'd need to run the algorithm again or use a different approach.\n    # For now, returning just the length:\n    return lcs_length\n\n# Example usage\nprint(longest_common_subsequence(\"ABCDGH\", \"AEDFHR\"))  # 3\nprint(longest_common_subsequence(\"AGGTAB\", \"GXTXAYB\"))  # 4\n```\n\nThis now uses O(n) space instead of O(m*n). Note that reconstructing the actual LCS string with O(n) space requires either running the algorithm again or using Hirschberg's algorithm, which is more complex. Would you like me to implement that as well?"
  }
]
```