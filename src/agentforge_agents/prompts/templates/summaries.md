# Summaries Template

Summarize the following content.

## Content
{{ content }}

## Summary style
- Tone: {{ tone | default("neutral, factual") }}
- Length: {{ max_length | default("concise (under 200 words)") }}
- Audience: {{ audience | default("general reader") }}

## Summary rules
1. Preserve key facts, numbers, names, and dates.
2. Preserve the author's claims even if they seem wrong; do not editorialize.
3. Note the source type (article, meeting minutes, code, transcript).
4. For meetings/transcripts include: decisions, action items (with owners),
   and open questions.
5. Never invent details absent from the content.

## Output
Provide the summary, then a one-line `Key takeaway`.