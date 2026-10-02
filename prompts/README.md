# Prompt Library

This directory contains generation and judging instructions for the dialogue task families. Each task directory has a `PROMPT.md` and an `example_output.json` showing its expected content and format.

- `code-state-awareness/`: preserve and interpret established code context.
- `interaction-analysis/`: assess correctness, guidance, and multi-turn reasoning.
- `iterative-code-evolution/`: evolve or revise code across turns.
- `PROMPT_HEADER.md` and `PROMPT_HEADER_VARIANT.md`: output schema headers.
- `CODER_JUDGE.md`: task definitions and judging instructions.

Review prompt text and example metadata for identifying information before release. The JSON examples are illustrative; use the headers and task-specific prompt as the format contract.