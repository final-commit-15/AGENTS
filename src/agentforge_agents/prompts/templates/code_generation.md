# Code Generation Template

Generate {{ language }} code for the following specification.

## Specification
{{ specification }}

## Environment / constraints
- Target platform: {{ platform | default("Python 3.12") }}
- Existing libraries in use: {{ libraries | default("none stated") }}
- Code style: {{ style | default("match surrounding code") }}

## Requirements
1. Functionality matching the specification exactly.
2. Idiomatic {{ language | default("Python") }} with clear names.
3. Runtime errors handled gracefully (return errors, do not raise to the caller).
4. No unused imports, dead code, or TODOs.
5. Tests or a runnable example when practical.

## Output
Return the full code block first, then a short section titled `Usage` showing
how to call it, then `Edge cases` listing what was handled.