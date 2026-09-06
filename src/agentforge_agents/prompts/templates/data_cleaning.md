# Data Cleaning Template

Clean the provided dataset and document every change.

## Dataset description
{{ description }}

## Data location
{{ location | default("provided inline or via a tool") }}

## Cleaning procedure
1. Load data and report shape, columns, dtypes, missing counts.
2. Normalize column names and types where needed.
3. Handle missing values (fill with a stated strategy or drop with record).
4. Remove exact duplicates; flag near-duplicates instead of guessing.
5. Reject or quarantine out-of-range values; never silently coerce.
6. Validate the result (dtypes, ranges, referential checks).

## Output format
- `Before`: shape, quality issues found.
- `Changes`: a numbered list of every transformation.
- `After`: shape, remaining issues, and a quality score (0-1).
- `Code`: the cleaning script (pandas) that reproduces the result.