## Task Description
This task is called Structural Code Reformatting (SCF). It is part of the Iterative Code Evolution Tier. Some downstream applications include code translation, style normalization, and framework porting.

This task involves the model changing representation in code with modifying the execution logic. In the first turn of this conversation, the user will introduce a code snippet or procedure in one language, whether it be Python or some other language. In their next turn, the user will ask the model to translate the code, either into a different language, a different style (i.e. into functional), or a different framework. This translation turn can repeat up to 3 times. If the task involves translation from one language to another, one of those two languages must be Python, whether it be the initial or the translated code. Avoid doing more than reformat type in a single generation

## Definition

The process of altering the internal representation or syntax of a code artifact without affecting its observable external behavior. This focuses on ``semantic-preserving'' tasks such as source-to-source translation (transpilation), framework porting, and style normalization (linting).

## Guide

- Step 1: User introduces a code snippet or procedure in one language (must be Python or another language, with at least one endpoint being Python)

- Step 2: Assistant acknowledges the code and confirms understanding of its logic and approach without immediately suggesting changes

- Step 3: The user requests the model to translate or reformat the code. Valid requests include: translate to a different programming language, convert to a different paradigm (functional, object-oriented, procedural), adapt to a different framework, or change coding style/conventions. Each translation should preserve the execution logic and behavior while changing the structural representation

- Final Step: Assistant provides the translated/reformatted code that maintains identical functionality and behavior while adapting to the requested language, style, or framework conventions


## Examples
```json
[
  {
    "role": "user",
    "content": "Here is a Python function I use to check whether a string is a palindrome:\n\n```python\ndef is_palindrome(s):\n    cleaned = ''.join(c.lower() for c in s if c.isalnum())\n    return cleaned == cleaned[::-1]\n```\nIt normalizes the string and then compares it to its reverse."
  },
  {
    "role": "assistant",
    "content": "Okay, that function preprocesses the string to remove non-alphanumeric characters and case differences, then performs a reverse comparison."
  },
  {
    "role": "user",
    "content": "Can you express this in Java using a more object-oriented style?"
  },
  {
    "role": "assistant",
    "content": "Here is the same functionality written in Java with an object-oriented approach:\n\n```java\npublic class PalindromeChecker {\n    public static boolean isPalindrome(String s) {\n        StringBuilder cleaned = new StringBuilder();\n        for (char c : s.toCharArray()) {\n            if (Character.isLetterOrDigit(c)) {\n                cleaned.append(Character.toLowerCase(c));\n            }\n        }\n        String normalized = cleaned.toString();\n        return normalized.equals(cleaned.reverse().toString());\n    }\n}\n```\nThis version adapts the structure and style to Java conventions while implementing the same steps."
  }
]

[
  {
    "role": "user",
    "content": "Here’s a small Python function that computes the factorial of a number:\n\n```python\ndef factorial(n):\n    result = 1\n    for i in range(1, n + 1):\n        result *= i\n    return result\n```\nIt uses a simple loop to accumulate the result."
  },
  {
    "role": "assistant",
    "content": "Understood. This function iteratively multiplies values from 1 through `n` to compute the factorial."
  },
  {
    "role": "user",
    "content": "Could you rewrite this using a functional style in Python?"
  },
  {
    "role": "assistant",
    "content": "Here’s a functional-style version using standard library tools:\n\n```python\nfrom functools import reduce\nimport operator\n\ndef factorial(n):\n    return reduce(operator.mul, range(1, n + 1), 1)\n```\nThis expresses the computation declaratively while fitting a functional programming style."
  }
]

```