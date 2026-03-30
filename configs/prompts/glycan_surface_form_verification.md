# Prompt: Surface Form Verification (v2.0.0)

You are verifying whether an extracted glycan term (`surface_form`) actually appears in its evidence sentence.

## Task

Given a `surface_form` and the `sentence` it was reportedly extracted from, determine whether the surface form is correct.

## Instructions

Choose one of three actions:

### 1. `accept` — The surface form is correct or needs minor correction

Use when the term genuinely appears in the sentence but has a minor mismatch (e.g., capitalization difference). Return the corrected surface form.

### 2. `split` — The surface form conflates two or more distinct glycan terms

Use **only** when the extracted text clearly combines separate glycan terms that should be individual entries. This typically occurs with the pattern "X and Y Z" where X and Y are independent modifiers of the same base noun Z.

**Example — SPLIT:**
- Surface form: `"linear and branched LN repeats"`
- These are two distinct structural concepts: `"linear LN repeats"` and `"branched LN repeats"`.

**Example — SPLIT with new relation:**
- Surface form: `"sialylated Lewis x (Slex)"`
- Split into: `"sialylated Lewis x"` and `"Slex"`, with a `has_abbreviation` relation from `"sialylated Lewis x"` to `"Slex"`.

**Example — DO NOT SPLIT:**
- Surface form: `"core-fucosylated and terminal-sialylated N-glycan"`
- This is a single composite descriptive phrase describing one class of glycan structure. The "and" joins two modifiers that together describe a specific glycan type. Do NOT split.

**Rule of thumb:** If removing one modifier produces a meaningful but *different* glycan concept from removing the other, and both are simple parallel modifiers of the same noun, split. If the modifiers together define a single composite glycan concept, do not split.

When splitting, return each resulting term with its `first_sentence_index` and any `relations` that arise from the split (e.g., an abbreviation in parentheses that now belongs to one of the split terms).

### 3. `discard` — The surface form does not appear in the sentence

Use when the term was fabricated or hallucinated and cannot be found in the sentence even with minor corrections.

## Output format

Return strict JSON only:

**Accept:**
```json
{"action": "accept", "surface_form": "corrected surface form"}
```

**Split:**
```json
{
  "action": "split",
  "terms": [
    {
      "surface_form": "first term",
      "first_sentence_index": 5,
      "relations": [
        {"relation_type": "has_abbreviation", "target": "abbrev", "source_sentence_index": 5}
      ]
    },
    {
      "surface_form": "second term",
      "first_sentence_index": 5,
      "relations": []
    }
  ]
}
```

**Discard:**
```json
{"action": "discard"}
```
