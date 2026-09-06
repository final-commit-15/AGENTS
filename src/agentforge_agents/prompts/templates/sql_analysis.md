# SQL Analysis Template

Analyze the database and answer the question with SQL.

## Schema
{{ schema | default("describe tables and columns before querying") }}

## Question
{{ question }}

## Tasks
1. Write a **read-only** query that answers the question.
2. Explain the query in plain language.
3. Execute it if allowed and report the row counts and head rows.
4. Interpret the results (trends, outliers, caveats).

## Query constraints
- Only SELECT / PRAGMA / EXPLAIN / WITH.
- Add explicit WHERE filters; avoid full-table scans when indexing exists.
- Name join keys explicitly; never assume column existence.

## Output format
- `Query`: the SQL.
- `Explanation`: why this query is correct and efficient.
- `Results`: summarized output.
- `Interpretation`: the answer in plain language with confidence.