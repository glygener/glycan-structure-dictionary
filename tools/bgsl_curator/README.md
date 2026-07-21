# bGSL Curator

An interactive, fully-traceable GUI for hand-correcting the bGSL dictionary:
**merge**, **split**, **relabel**, **edit synonym/abbreviation lists**,
**edit relationship edges**, and **drop** nodes — with UUID bookkeeping and
write-back to the resolved layer so a rebuild reproduces every edit.

## Launch

```bash
bash tools/bgsl_curator/run.sh
# then open http://localhost:8765
```

(First time only: `pip install -r tools/bgsl_curator/requirements.txt` into the
`gly_env` environment.)

On startup the server loads the current release: it prefers
`master_nodes_curated.json` (a prior saved session) if present, otherwise the
newest `master_nodes_*.json` in `data/outputs/releases/gsd_v2.0.0-draft/`.

## What each operation does

| Operation | Effect | UUID rule |
|---|---|---|
| **Merge into…** | Folds the current node into a chosen survivor as an *exact synonym* or *abbreviation*; survivor absorbs sources, GTC/db_xref, lists; edges repoint. | Survivor UUID kept; absorbed UUID recorded in `merged_from_term_uuids`. |
| **Split** | Splits one node into ≥2 children; you route every source row, synonym, abbreviation, and edge into a bucket; gtc/db_xref are reconstructed per child from routed sources. | Each child gets a fresh `GSD:` UUID citing the parent in `split_from_term_uuid`. |
| **Relabel** | Sets a new canonical label; the old label can become an exact synonym, an abbreviation, or be discarded. | UUID unchanged. |
| **Edit lists** | Add / remove / move (exact↔abbr) / rename a synonym or abbreviation. | UUID unchanged. |
| **Edit edges** | Add / remove broad/narrow/related/is_a relationships between nodes. | — |
| **Drop** | Excludes the node from the release. | Source rows flagged `keep=false` on sync. |

## Three-layer traceability

1. **Journal** — every operation is appended to
   `tools/bgsl_curator/sessions/<session_id>/curation_log.jsonl` (timestamp,
   op, before/after UUIDs+labels, routed src_uuids). **Undo** reverts the last
   op. This is the canonical audit trail.

2. **Curated deliverable** — **Save** writes `master_nodes_curated.json`,
   `master_edges_curated.json`, `dictionary_curated.json` into the release dir.
   These reflect all edits exactly and never clobber the timestamped release.
   This is what you share with collaborators.

3. **Resolved-layer write-back** — **Sync→sources** rewrites each source row's
   `terms_resolved.term_uuid` and `terms_ai-decisions.mapped_to_uuid` to its
   current owning node (drops → `keep=false`), and writes the authoritative
   presentation override to `data/inputs/curator_overrides.json`. `.bak`
   backups are made on first touch. This makes a future `build_release.py` run
   reproduce the curated state.

**Publish** writes a fresh timestamped release from the curated state and
rebuilds `bGSL_v2.0.0_review.tsv`.

### EoG sentences are preserved, never re-fetched

`build_bgsl_tsv.py` keeps the `eog_sentence` column **exactly as-is** by
default — it makes **no OpenAI calls** and assigns **no new sentences**.
Sentences are cached per node in `bGSL_eog_cache.json` keyed by `term_uuid`,
so a sentence survives a relabel or merge (same UUID) and is never borrowed by
a different node. Split children get fresh UUIDs and therefore start with a
blank sentence rather than an invented one. To deliberately fetch sentences
for nodes that don't have one yet, run `python scripts/build_bgsl_tsv.py
--refresh-eog` (or POST `/api/publish?refresh_eog=true`).

## Reproducing the curated state from scratch

```bash
PY=/Users/cyrusay/anaconda3/envs/gly_env/bin/python
$PY scripts/build_release.py            # reproduces grouping/drops from resolved term_uuids
$PY scripts/apply_curator_overrides.py  # applies labels/lists/edges from curator_overrides.json
$PY scripts/build_bgsl_tsv.py           # refresh reviewer TSV
```

## Layout

```
backend/   store.py · mutations.py · journal.py · propagate.py · models.py · app.py
frontend/  index.html · app.js · style.css   (vanilla JS, no build step)
sessions/  per-session curation_log.jsonl
```
