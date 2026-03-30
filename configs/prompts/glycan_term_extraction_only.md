# Prompt: Glycan Term Extraction — Terms and Relations Only (v2.0.0)

You will receive one textbook chunk where each sentence is wrapped in sentence index xml tags:

`<S:index>Sentence text. </S:index>`

## Task

Extract **glycan structural terms** and any **relations** (abbreviations and structural formulas) from the chunk.

## Instructions

- Extract glycan terms that appear to refer to named glycan entities, structural features, substructures, descriptors, monosaccharides, or glycan-related vocabulary.
- `surface_form` must match the source text exactly (**case-sensitive**).
- Deduplicate within the chunk by exact `surface_form`.
- For each term, return the integer sentence index for the first appearance of that exact surface form.
- If a term has an abbreviation mentioned in the chunk (e.g., "sialyl-Lewis x" abbreviated as "SLe^x", or "Lewis x (Lex)"), include the abbreviation as a separate entity AND record the relation. Another example: "heparan sulfate" abbreviated as "HS".
- If a term has a condensed IUPAC formula definition in the chunk (e.g., "alpha-gal antigen" defined as "Galα1-3Gal", "LacdiNAc" defined as "GalNAc𝛽1-4GlcNAc"), record the relation.

## Relations

For each entity, optionally include a `relations` array. Each relation has:

- `relation_type`: one of `"has_abbreviation"` or `"has_formula"`
- `target`: the abbreviation text or structural formula string
- `source_sentence_index`: the sentence index where this relation is stated

## Output format

Return strict JSON only:

```json
{
  "entities": [
    {
      "surface_form": "sialyl-Lewis x",
      "first_sentence_index": 27,
      "relations": [
        {
          "relation_type": "has_abbreviation",
          "target": "SLe^x",
          "source_sentence_index": 27
        }
      ]
    },
    {
      "surface_form": "SLe^x",
      "first_sentence_index": 27,
      "relations": []
    }
  ]
}
```

Rules:

- No markdown. No extra keys.
- `first_sentence_index` must come from an existing `<S:n>` tag in the input.
- `relations` is optional per entity; omit or use an empty array if none.
- If there are no entities, return `{"entities": []}`.
