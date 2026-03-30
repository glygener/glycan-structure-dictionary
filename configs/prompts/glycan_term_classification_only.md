# Prompt: Glycan Term Classification (v2.0.0)

You are classifying a single glycan structural term into one of the classes defined in the reference classification scheme below.

## Task

Given a `surface_form` and its evidence `sentence`, assign exactly one class code.

## Instructions

- Read the classification scheme carefully before assigning a class.
- Assign the class that best fits the term based on its **Definition**, **Types**, and **Notes and special handling** sections.
- Pay close attention to the "Notes and special handling" — they contain critical boundary rules about what belongs and what does NOT belong in each class.
- If the term matches the **Excluded Tier** criteria, classify it as `"DISCARD"`.
- If the term cannot be confidently assigned to any class, classify it as `"DISCARD"`.

## Output format

Return strict JSON only:

```json
{"classification": "1A", "reason": "Justification in one concise sentence."}
```

- `classification` must be one of: `1A`, `1B`, `2A`, `2B`, `2C`, `2D`, `2E`, `3A`, `3B`, `3C`, or `DISCARD`.
