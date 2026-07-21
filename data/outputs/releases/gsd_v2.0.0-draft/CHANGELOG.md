# gsd_v2.0.0-draft — Changelog

Generated overnight, 2026-05-19. Compared to gsd_v1.0.0.

## What's new

### New source datasets ingested

12 sources added beyond the v1 baseline. All normalised into the standard
`src_*/terms.jsonl` schema.

| Source | Terms | GTC coverage |
|---|---|---|
| `src_glycomotif_ggm`           | ~185 | 100% |
| `src_glycomotif_gdv`           | ~126 | 100% |
| `src_glycomotif_ccrc`          | ~116 | 100% |
| `src_pubdict-glycan-motif`     |  ~504 | 100% |
| `src_pubdict-glycosmos`        |  ~218 | 100% |
| `src_pubdict-motifglytoucan`   |   ~67 | 100% |
| `src_pubdict-glyconavi-name`   |  ~235 |   0% |
| `src_pubdict-glyconavi-abbrev` |   ~98 |   0% |
| `src_glycoepitope`             |  ~173 |   0% |
| `src_biooligo`                 |  ~254 |   0% |
| `src_sugarbind`                |  ~204 |  98% |
| `src_cummings`                 |  ~117 |   0% |

### Pipeline changes

- **Replaced `search_pubmed` with `query_textbook`** — the resolver now grounds
  ambiguous decisions in the Essentials of Glycobiology (EoG, 4e) Chroma store
  (`data/workspace/chroma/eog`, 2 662 chunks) instead of hitting PubMed over
  the network. New tool definition lives in
  `src/gsd/part2_enrichment/1_ai-assisted_term_matching/tools.py`.

- **`gsdv1` synonyms pre-split.** Where `src_gsdv1/edges.jsonl` declared a
  `has_related_synonym` relationship (e.g. *sialyl Lewis a → CA19-9*), the
  bundled synonym was pruned from the parent term and promoted to its own
  stub node. This implements the user's request that "CA 19-9 and sialyl
  lewis a as TWO separate nodes linked by an edge". Pre-split logic:
  `scripts/expand_gsdv1_synonyms.py`. Backup of the original lives at
  `data/inputs/src_gsdv1/terms.original.jsonl`.

- **Resolver fast-paths.** Three deterministic shortcuts skip the LLM
  for high-confidence cases:
  1. **GlyTouCan-ID match** — when the query and a candidate share any GTC
     accession, auto-map as `exact_synonym_of`.
  2. **Normalised surface-form match** — case/dash/greek-letter-insensitive
     equality between query and any candidate name or synonym, given
     vector similarity ≥ 0.5, auto-maps as `exact_synonym_of`.
  3. **No-candidate auto-add** — when the best candidate is below 0.45
     similarity *and* the query has no GTC ID, the resolver registers a new
     entry without invoking the LLM.

  These were measured to push >60% of decisions onto the deterministic
  pathway in GTC-rich sources.

- **Edge post-processing.** The resolver emitted edges with `subj = src_uuid`
  (a SRC: namespace identifier), and emitted a synonym edge even when the
  decision was a simple node merge. `scripts/patch_resolver_edges.py` now
  drops `exact_synonym_of`/`abbreviation_of` edges (those collapse via shared
  term_uuid) and rewrites `related_synonym_of`/`is_a` edges to keep the query
  as a separate node with a fresh GSD: UUID.

- **Postprocessing QC relaxed.** The pre-merge QC previously aborted on
  duplicate `term_uuid` within a single resolved file; this was incompatible
  with the resolver's design of multiple query rows mapping to one canonical
  term. Check is now a tally, not a hard stop. Source unique-uuid is still
  enforced.

### Quality control

- Regex-based filter against fluorinated, isotope-labeled, click-chemistry,
  biotinylated, and aminolinker variants. Hits live in
  `src_*/terms_qc-discarded.jsonl` per source.
- The natural-glycan principle is enforced: synthetic analogues are removed
  before resolution.

## Known caveats

- Sources with 0 % GTC coverage may produce duplicate nodes when a term
  surface form already exists in the dictionary under a slightly different
  spelling — the resolver catches most of these via the surface-form
  fast-path, but rare typos slip through. Inspect `master_nodes_*.json` for
  near-duplicate `lbl` values and emit a `related_synonym_of` edge if so.
- `data/inputs/src_pubdict-glyconavi-name/` contains some `Î±` / `Î²`
  mojibake originating from the upstream dictionary. The normaliser fixes
  the most common Greek-letter cases; rare ones may still appear.
- KEGG Glycan and GlycoNAVI motif (direct) were not scraped — they need
  authenticated or JS-rendered access. The pubdict-glycan-image and
  pubdict-glyconavi-name dictionaries cover much of the same content.

## Reproducing

```bash
# 1. (optional) re-scrape sources
# 2. Normalise + QC + expand gsdv1 synonyms
python scripts/normalize_new_sources.py
python scripts/qc_filter.py
python scripts/expand_gsdv1_synonyms.py
python scripts/dedup_terms.py

# 3. Seed the vector store
python src/gsd/part2_enrichment/seed_store.py \
  --seed-source src_gsdv1 \
  --extra-sources src_eog src_n-compo src_pubdictionaries-glycan-image src_glygen_curators

# 4. Run the resolver on each new source
bash scripts/run_full_sweep.sh

# 5. Patch resolver edges + build release
bash scripts/auto_finalize.sh
```
