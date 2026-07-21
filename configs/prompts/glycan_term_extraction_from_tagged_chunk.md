# Prompt: Glycan Term Extraction from Tagged Chunk (v1.3.3)

You will receive one textbook chunk where each sentence is wrapped in sentence index xml tags:

`<S:index>Sentence text. </S:index>`

## Task

Extract **glycan structural terms** from the chunk, using the provided classification scheme as criteria.

## Instructions

- From the textbook chunk, extract glycan terms that fits the classification criteria.
- Assign exactly one class code per extracted term (e.g., `1A`, `1B`).
- If a term cannot be confidently assigned to one valid class code, discard it.
- `surface_form` must match the source text exactly (**case-sensitive**).
- Deduplicate within the chunk by exact `surface_form`.
- If a term has an abbreviation in the chunk, include the abbreviation as a separate term.
- For each term, return the integer sentence index for the first appearance of that exact surface form.

## Output format

Return strict JSON only, in this format:

```json
{
  "entities": [
    {
      "surface_form": "sialyl Lewis X",
      "first_sentence_index": 27,
      "classification": "1A",
      "reason": "<justification of classification, in one concise sentence>"
    }
  ]
}
```

Rules:

- No markdown. No extra keys.
- `first_sentence_index` must come from an existing `<S:n>` tag in the input.
- `classification` must be one of: `1A`, `1B`, `2A`, `2B`, `2C`, `2D`, `2E`, `3A`, `3B`, `3C`.
- If there are not any entities, return empty entities list.
