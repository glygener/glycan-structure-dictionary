# bGSL 2B Re-check (v3.0.0)

Another classifier just labelled the term below as **Class 2B** (single descriptor + optional context noun, e.g. `fucosylated N-glycan`).

**Common 2B false positives** the first pass tends to make:
1. **Canonical named entity (1A)** misread as 2B: `Lewis x`, `sialyl Lewis a`, `dimeric Lewis x`, `core 1`, `GM1`, `globotriaosylceramide`.
2. **Named feature (1B)** misread as 2B: `core fucose`, `high mannose`, `biantennary` (bare), `LacdiNAc`, `bisecting GlcNAc`.
3. **Composite multi-descriptor (2C)** misread as 2B: `core-fucosylated biantennary N-glycan` (two descriptors), `sialylated complex-type N-glycan`.
4. **Linkage-bearing fragment (2A)** misread as 2B: anything with explicit `α1-3`, `β1-4`, `2-6` notation.

## Decide

Read the term carefully. Then choose:

- **`KEEP_2B`** — confirmed; this really is one descriptor with optional generic noun, no canonical-name or named-feature content.
- **`UPGRADE_1A`** — actually a canonical named entity (Lewis/GM/Gb/blood group/Forssman/HNK-1/Tn/sialyl-Tn) or a modification of one.
- **`UPGRADE_1B`** — actually a bare named feature (core fucose / high mannose / biantennary / LacdiNAc) without descriptor adjectives.
- **`UPGRADE_2C`** — actually carries 2+ descriptors (counts: -ylated, terminal/extended, biantennary/triantennary, complex-type each count as ONE descriptor).
- **`UPGRADE_2A`** — contains explicit linkage notation like `α1-3`, `β1-4`, `2-6`.
- **`UPGRADE_2D`** — short alphanumeric glycoform shorthand like `G0`, `G1F`, `FA2G2S2`, `M9`, `A2`, `NGA2`.
- **`UPGRADE_2E`** — composition formula like `Hex5HexNAc4Fuc1NeuAc2` or `H5N4F1S2`.
- **`UPGRADE_3B`** — single monosaccharide or named free disaccharide (e.g. `Gal`, `GlcNAc`, `sialic acid`, `sucrose`, `lactose`).

Examples:
- `fucosylated N-glycan` → KEEP_2B
- `core-fucosylated biantennary N-glycan` → UPGRADE_2C (two descriptors)
- `dimeric Lewis x` → UPGRADE_1A (Lewis x is canonical, dimeric is its modifier)
- `core 1 mucin-type O-glycan` → UPGRADE_1A (core 1 is canonical)
- `biantennary N-glycan` → KEEP_2B (one descriptor + context)
- `biantennary` → UPGRADE_1B (bare feature)
- `Galβ1-4GlcNAc` → UPGRADE_2A
- `G0`, `FA2G2S2`, `M9` → UPGRADE_2D
- `Hex5HexNAc4` → UPGRADE_2E
- `Gal`, `Sucrose` → UPGRADE_3B

## Output

```
{"decision": "<KEEP_2B|UPGRADE_1A|UPGRADE_1B|UPGRADE_2C|UPGRADE_2A|UPGRADE_2D|UPGRADE_2E|UPGRADE_3B>", "reason": "<short>"}
```
