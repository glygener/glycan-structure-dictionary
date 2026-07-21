# gsd_v2.0.0-draft — Manual Review Sheet

Generated: 2026-05-20T18:47:01

This folder contains a *pre-deduplication* version of the master node table
along with a TSV for human review.

## Files

| File | Purpose |
|---|---|
| `master_nodes_prededuplication.json` | The 1112 nodes as produced by the resolver, **before** the surface-form dedup pass. No `merged_from_term_uuids` field; each resolver-assigned UUID is its own row. |
| `master_edges_prededuplication.json` | Edge file aligned with the pre-dedup nodes. |
| `dictionary_prededuplication.json`   | Enriched dictionary with `src_content`, also pre-dedup. |
| `node_review.tsv`                    | One row per node with the columns a reviewer needs. Upload to Google Sheets (paste as TSV). |
| `node_trace_map.json`                | UUID → list of `{src, src_lbl, src_uuid}` for every contributing source row. Used to back-track which AI decision caused a wrong merge. |

## Review workflow

1. Open `node_review.tsv` in Google Sheets (File → Import → Upload, separator = Tab).
2. For each node, inspect:
   - `lbl` — primary label,
   - `distinct_src_lbls` — every distinct surface form the resolver mapped to this UUID,
   - `gtc_ids` — every GlyTouCan ID claimed for this node,
   - `exact_synonyms` — bundled synonyms.
3. Fill in:
   - `KEEP` — `TRUE` (default) or `FALSE` to omit the node and all of its source rows from the final release.
   - `REVIEW_ACTION` — one of `keep`, `split`, or `merge_with:<other_uuid>`.
   - `SPLIT_INTO_LABELS` (only when action = `split`) — semicolon-separated labels for the new nodes (e.g. `dimeric Lewis x ; Lewis x`).
   - `NOTES` — free text.

Setting `KEEP=FALSE` propagates to **every** `src_*/terms.jsonl` row that contributes to that node (matched by `src_uuid`), so postprocessing will skip it cleanly.
4. Save the sheet as TSV (File → Download → Tab-separated values) and drop it back into this folder (any name).
5. Run `python scripts/apply_review.py path/to/reviewed.tsv` to rewrite the master nodes/edges and emit `REVIEW_ACTIONS.json` with the audit trail. The output goes to `data/outputs/releases/gsd_v2.0.0-draft/master_nodes_reviewed.json`.

## Reading hints

- A node where `distinct_src_lbls` mixes obviously-different glycans (e.g. "Lewis x", "dimeric Lewis x", "Lewis x triaose [SSEA-1]") is a strong split candidate.
- A node with >10 GTC IDs of mixed series is suspicious — true exact-synonyms usually share 1–3 GTC IDs.
- A node with `exact_synonyms` containing both an abbreviation pattern (e.g. `Le^x`) *and* an extended form (e.g. `Le^x-Le^x`) suggests a dimer/trimer family was conflated with the monomer.

## Worked example — "Lewis x" mis-routed sources

The `Lewis x` node (`GSD:89ba627c-...`) ended up with two source rows whose
`src_lbl` is `Lex_Lex` / `Lex-Lex`. Those are the dimeric form and should live
on the `dimeric Lewis x` node. To fix:

1. On the `Lewis x` row:
   - `REVIEW_ACTION` = `split`
   - `SPLIT_INTO_LABELS` = `Lewis x; dimeric Lewis x`
2. `apply_review.py` will create two fresh nodes and route each source row to
   whichever label its `src_lbl` matches best. The dimeric-style `Lex_Lex`
   rows land on the new `dimeric Lewis x` node.
3. On the original `dimeric Lewis x` row (`GSD:980d0f39-...`) — leave as
   `keep`. After step 2 there will be two `dimeric Lewis x` nodes. In a
   *second* pass through the TSV, mark the newly-created one with
   `REVIEW_ACTION` = `merge_with:GSD:980d0f39-e1ff-430f-bf65-3008c9cc2fd9` so
   it folds into the original. Re-run `apply_review.py`.

This two-pass approach keeps the operations atomic and the audit trail
(`REVIEW_ACTIONS.json`) clean.
