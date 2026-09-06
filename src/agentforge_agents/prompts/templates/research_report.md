# Research Report Template

Produce a structured research report for:

## Question
{{ question }}

## Sources consulted
{{ sources | default("to be discovered") }}

## Report structure
1. **Summary** — 3-5 sentences answering the question with overall confidence.
2. **Findings** — each finding with:
   - Claim
   - Evidence (source name, URL, publication date)
   - Confidence (high / medium / low, with reasoning)
3. **Contradictions** — where sources disagree, show both sides.
4. **Limitations** — coverage gaps, timeliness, methodology caveats.
5. **References** — formatted citations for every claim.

## Rules
- Only cite sources actually consulted.
- Never fabricate quotes or statistics.
- Flag anything that could not be verified as `unverified`.
- Target length: {{ max_length | default("800 words") }}.