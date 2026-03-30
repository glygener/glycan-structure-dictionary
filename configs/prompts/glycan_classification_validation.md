# Prompt: Classification Validation (v2.0.0)

You are validating whether a glycan term has been correctly classified.

## Task

Given a `surface_form`, its assigned `classification`, the **class definition** for that classification, and the **excluded tier** criteria, determine whether the term correctly belongs to the assigned class.

## Instructions

- Read the class definition, types, and **notes and special handling** carefully.
- Check whether the term fits the definition AND does not violate any of the notes/special handling rules.
- Also check whether the term should have been discarded under the excluded tier criteria.
- Answer `true` if the classification is correct, `false` if the term belongs elsewhere or should be discarded.
- Provide a brief reason explaining your decision.

## Output format

Return strict JSON only:

```json
{"valid": true, "reason": "Brief explanation."}
```
