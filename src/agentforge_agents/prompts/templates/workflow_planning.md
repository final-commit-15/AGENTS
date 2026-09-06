# Workflow Planning Template

Design an executable workflow for the goal below.

## Goal
{{ goal }}

## Available agents and tools
{{ capabilities | default("review the registry before planning") }}

## Workflow design
1. Decompose the goal into steps.
2. Choose the executor for each step: an Agent or a Tool.
3. Declare dependencies and parallel branches (DAG).
4. Define per-step retries and timeouts.
5. Define the workflow state schema (inputs and outputs per step).

## Constraints
- Steps must be idempotent or explicitly documented otherwise.
- Retries must be bounded with backoff.
- No step may depend on unspecified state.
- Destructive operations require a confirmation gate.

## Output format
Return a JSON `WorkflowDefinition` (id, name, steps with id/type/agent|tool_name/
input/output_key/depends_on/max_retries/timeout_seconds, entry_step), plus a
short `steps` narrative explaining the design.