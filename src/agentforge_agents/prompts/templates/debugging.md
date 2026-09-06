# Debugging Template

Diagnose and fix the reported problem.

## Symptom
{{ symptom }}

## Reproduced context
{{ context | default("none provided") }}

## Expected behavior
{{ expected | default("the operation should complete successfully") }}

## Procedure
1. Reproduce the failure in a minimal example.
2. Identify the root cause (not merely the surface symptom).
3. Propose the minimal fix that does not change unrelated behavior.
4. Verify the fix with the failing case plus a regression check.

## Output format
- `Root cause`: one paragraph.
- `Fix`: the exact code change (full diff or before/after).
- `Verification`: commands run and their results.
- `Risks`: side effects of the change, if any.