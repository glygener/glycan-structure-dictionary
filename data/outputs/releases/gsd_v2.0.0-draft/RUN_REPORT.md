# GSD v2.0.0-draft — Run Report

Generated: 2026-05-27T00:12:37

## Summary
- Total nodes:      **1329**
- Nodes with GTC ID: **633** (47%)
- Nodes without GTC: 696
- Total edges:       **220**
- QC-dropped terms (synthetic glycans):  0

## Source coverage (count of nodes referencing each source)
- `SRC:PUBDICT_GLYCAN_MOTIF`: 439
- `SRC:EOG_VARKI_4E`: 323
- `SRC:BIOOLIGO`: 238
- `SRC:PUBDICT_GLYCONAVI_NAME`: 235
- `SRC:PUBDICTIONARIES-GLYCAN-IMAGE`: 222
- `SRC:PUBDICT_GLYCOSMOS`: 218
- `SRC:GSD_GLYGEN_V0`: 182
- `SRC:GLYCOEPITOPE`: 173
- `SRC:GLYCOMOTIF_GGM`: 172
- `SRC:SUGARBIND`: 155
- `SRC:GLYCOMOTIF_GDV`: 119
- `SRC:CUMMINGS`: 116
- `SRC:GLYCOMOTIF_CCRC`: 105
- `SRC:PUBDICT_GLYCONAVI_ABBREV`: 98
- `SRC:GLYGEN_CURATORS_NCOMPO`: 92
- `SRC:PUBDICT_MOTIF_GTC`: 65
- `SRC:TERMS_GLYGEN_CURATORS`: 1

## Edge predicates
- `related_synonym_of`: 94
- `broad_synonym_of`: 51
- `narrow_synonym_of`: 43
- `has_related_synonym`: 32

## Files
- master nodes:  `master_nodes_20260527_001227.json`
- master edges:  `master_edges_20260527_001227.json`
- dictionary:    `dictionary_20260527_001227.json`
- qc report:     `qc_report.json`

## Pipeline changes vs. previous release
- Replaced `search_pubmed` lookup tool with `query_textbook` (RAG over Essentials of Glycobiology 4e).
- Pre-split `src_gsdv1` synonyms based on `edges.jsonl` `has_related_synonym` relations (e.g. `CA19-9` is now a separate node from `sialyl Lewis a`).
- Seed vector store from src_gsdv1 + curated src_eog/src_n-compo/src_pubdictionaries-glycan-image (623 unique terms).
- New sources scraped and normalised:
  - GlycoMotif GGM (185), GDV (126), CCRC (116)
  - Pubdictionaries glyconavi-name (468 raw / 232 unique), glyconavi-abbrev (104 raw / 95 unique)
- New sources promoted from `some_other_resouces/`:
  - GlycoEpitope (173), BioOligo (254), SugarBind (204), Cummings (117)
  - Pubdict glycan-motif (504), glycosmos (218), motifglytoucan (67)
- Resolver fast-paths added: shared GlyTouCan ID, normalised surface-form match.
- Drop filter: regex flags fluorinated/synthetic/labelled glycans (6 dropped from glyconavi).
- **`keep` flag**: every row in `src_*/terms.jsonl` carries a top-level `keep: true` boolean. Reviewer flips it to `false` on rows they want omitted from the final release; postprocessing filters them out before building master nodes/edges and drops any orphan edges that referenced them.
- **GlycoMotif Name/Keyword separation**: the GlycoMotif scrape originally merged `Name(s)` and `Keyword(s)` into a single `aliases` column, polluting `exact_synonyms` with classification keywords (e.g. 'Glycolipid', 'Trisialylated ganglioside'). The v2 scrape keeps them as separate columns, and `scripts/patch_glycomotif_synonyms.py` updates `terms.jsonl` in place — preserving `term_uuid`/`src_uuid` so the sweep does NOT need to re-run.
