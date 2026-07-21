# bGSL Classification — Lookup Table Report

Generated: $(date)
Source: data/outputs/releases/gsd_v2.0.0-draft/review/master_nodes_prededuplication.json
Output: term_class.tsv (1112 rows)

## Class distribution

| Class | Count | % | Name |
|---|---|---|---|
| `1A` | 289 | 26.0% | Canonical named glycan entity |
| `1B` | 26 | 2.3% | Named recurrent structural feature |
| `1C` | 54 | 4.9% | Non-GAG homo/hetero-polymer |
| `2A` | 96 | 8.6% | Linkage-specified substructure |
| `2B` | 82 | 7.4% | Single descriptor phrase |
| `2C` | 148 | 13.3% | Composite descriptive phrase |
| `2D` | 116 | 10.4% | Glycoform shorthand code |
| `2E` | 8 | 0.7% | Composition formula |
| `3A` | 85 | 7.6% | Umbrella / glycoconjugate class |
| `3B` | 158 | 14.2% | Monosaccharide or named disaccharide |
| `3C` | 26 | 2.3% | Association-defined glycan marker |
| `X` | 24 | 2.2% | Outside scheme |

**Method**: regex (no LLM) = 140 (12.6%); LLM = 972 (87.4%)

## Pipeline

Three-stage cascade per term (configs/prompts/classification/bgsl_classify_v3*.md):

1. **Stage 0 (regex)** — deterministic capture of 2A (linkage), 2D (glycoform), 2E (composition), and 1C (named non-GAG polymers).
2. **Stage 1 (LLM, gpt-oss:20b, reasoning=low)** — decision-tree prompt, JSON-schema constrained output, evaluated in order: 3C → 1A → 1B → 1C → 3B → 3A → 2D → 2E → 2C → 2B → X.
3. **Stage 2 (LLM re-checks)** — when Stage 1 returns 2B, run a 2B-vs-{1A,1B,2A,2C,2D,2E,3B} re-check (the user-reported 2B over-classification failure mode). When Stage 1 returns 3A or X, run a 3C recall check (the missed-3C failure mode).

## Spot-check flags

Heuristic flags (read these before trusting the table):
- `latin_linkage_not_2A`: 16 flagged row(s)
- `blood_group_or_lewis_not_1A`: 8 flagged row(s)
- `glycolipid_id_not_1A`: 7 flagged row(s)
- `ceramide_2B`: 1 flagged row(s)

## Sample flagged rows

| flag | term | class | reason |
|---|---|---|---|
| `latin_linkage_not_2A` | Gal(b1-4)[Fuc(a1-3)]Glc(b1) | X | raw linkage string |
| `latin_linkage_not_2A` | GalNAc(b1-4)[Neu5Ac(a2-3)]Gal(b1) | X | Structural notation not covered by other categories |
| `latin_linkage_not_2A` | GalNAc(b1-4)[Neu5Gc(a2-3)]Gal(b1) | X | linkage notation only |
| `latin_linkage_not_2A` | GlcNAc(b1-3)Gal | 3B | Simple disaccharide noun |
| `latin_linkage_not_2A` | Neu5Ac(a2-6)GalNAc | 3B | Disaccharide structure |
| `latin_linkage_not_2A` | Neu5Ac(a2-8)Neu5Ac(a2-3)Gal(b1-3)GalNAc | 2C | Complex oligomeric sequence |
| `latin_linkage_not_2A` | Neu5Gc(a2-3)Gal | 3B | Disaccharide structure |
| `latin_linkage_not_2A` | Neu5Ac(a2-3)Gal / Monosialoganglioside | 3A | Generic ganglioside category |
| `latin_linkage_not_2A` | Neu5Ac(a2-8)Neu5Ac(a2-3)Gal(b1-4)Glc | 2C | Complex oligomeric sequence |
| `latin_linkage_not_2A` | a2-3 Neu5Ac on Core 1 | 1A | canonical core structure |
| `latin_linkage_not_2A` | deoxy-GlcA b1-3 GalNAc [4S] b1-4 GlcA b1-3 GalNAc [4S] | X | non‑canonical polysaccharide fragment |
| `latin_linkage_not_2A` | di-Lewis x b1-4 Lewis x [di-Lewis x] | 1A | canonical Lewis epitope |
| `latin_linkage_not_2A` | Neu5Ac a2-6 Gal b1-4 GlcNAc b1-4 Gal b1-4 GlcNAc | 2C | Composite glycan sequence |
| `latin_linkage_not_2A` | Sia(a2-8)Sia(a2-3)Gal | 2C | Composite oligosaccharide with linkages |
| `glycolipid_id_not_1A` | GM4 | 3A | generic ganglioside category |
| `glycolipid_id_not_1A` | GQ1c | 3A | generic ganglioside |
| `glycolipid_id_not_1A` | GT2 | 3A | generic ganglioside category |
| `glycolipid_id_not_1A` | GD1 alpha | 3A | generic ganglioside term |
| `glycolipid_id_not_1A` | GQ2 | 2D | upgraded from 2B: Short alphanumeric glycoform shorthand |
| `blood_group_or_lewis_not_1A` | blood group B type 4 | 3C | contains explicit anchor "blood group B" |
| `blood_group_or_lewis_not_1A` | blood group A trisaccharide | 3C | contains explicit anchor "blood group A" |
| `blood_group_or_lewis_not_1A` | 2-6 sialyl i-Lewis x | 2A | Explicit linkage notation present. |
| `blood_group_or_lewis_not_1A` | Blood group A antigen hexaose type 2 | 3C | contains explicit blood group antigen reference |
| `blood_group_or_lewis_not_1A` | Blood group A antigen tetraose type 5 | 3C | contains explicit blood group antigen reference |
| `blood_group_or_lewis_not_1A` | Blood group B antigen hexaose type 1 | 3C | contains explicit anchor "Blood group B antigen" |
| `blood_group_or_lewis_not_1A` | Blood group B antigen hexaose type 2 | 3C | explicit blood group reference |
| `blood_group_or_lewis_not_1A` | 3-Fucosylated Blood group A tetraose | 3C | contains explicit anchor "Blood group A" |
| `ceramide_2B` | galactosylceramide | 2B | single descriptor + noun |