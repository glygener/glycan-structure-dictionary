"""Post-process the resolver output to produce postprocessing-compatible edges.

graph.py emits edges_ai-decisions.jsonl with `subj` set to the source-row
`src_uuid` (SRC:...), but the master post-processing expects both `subj` and
`obj` to be `GSD:...`. It also writes an edge for *every* mapping, including
`exact_synonym_of` and `abbreviation_of` — which should be **node merges**,
not edges.

This patch script fixes both issues:

  * For `exact_synonym_of` / `abbreviation_of`: DROP the edge entirely
    (the merge happens via the shared term_uuid in terms_resolved.jsonl).
    The query's original surface form is preserved as a synonym source row.

  * For `related_synonym_of` / `is_a`: KEEP the query as a *separate* node by
    assigning it a fresh GSD UUID (overriding the candidate UUID it was
    merged into) and rewrite the edge with `subj` = that new UUID,
    `obj` = the candidate's UUID.

  * Anything else (unexpected pred): keep as-is and log a warning.

Run after the full sweep, before `build_release.py`.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "data" / "inputs"

# Mappings that just merge — no edge to emit
MERGE_PREDS = {"exact_synonym_of", "abbreviation_of"}

# Mappings that should keep a separate node + edge
SEPARATE_NODE_PREDS = {
    "related_synonym_of",
    "is_a",
    "has_related_synonym",
    "broad_synonym_of",
    "narrow_synonym_of",
}


def patch_source(src_dir: Path) -> dict:
    decisions_f = src_dir / "terms_ai-decisions.jsonl"
    edges_f = src_dir / "edges_ai-decisions.jsonl"
    resolved_f = src_dir / "terms_resolved.jsonl"

    if not (decisions_f.exists() and edges_f.exists() and resolved_f.exists()):
        return {"source": src_dir.name, "skipped": True}

    def _read_jsonl(path: Path) -> list:
        rows = []
        for line in path.open():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # Tolerate a half-written trailing line if a sweep is still in
                # progress against this source.
                break
        return rows

    decisions = _read_jsonl(decisions_f)
    edges = _read_jsonl(edges_f)

    # Build src_uuid -> decision mapping for cross-referencing
    src_to_decision = {d["src_uuid"]: d for d in decisions}

    # Re-read terms_resolved.jsonl (keyed by src_uuid)
    resolved_rows = []
    with resolved_f.open() as f:
        for line in f:
            line = line.strip()
            if line:
                resolved_rows.append(json.loads(line))
    resolved_by_src = {r["src_uuid"]: r for r in resolved_rows}

    # Decide which edges to keep + which terms to re-assign
    kept_edges = []
    reassigned_uuids = {}   # src_uuid -> new_uuid (for separate-node terms)
    counts = {"dropped_merge": 0, "kept_separate": 0, "unknown_pred": 0}

    for edge in edges:
        pred = edge.get("pred", "")
        src_uuid = edge.get("subj", "")
        obj_uuid = edge.get("obj", "")

        if pred in MERGE_PREDS:
            counts["dropped_merge"] += 1
            continue

        if pred in SEPARATE_NODE_PREDS:
            # Idempotency: if subj is already a GSD:... uuid, this file was
            # already patched in a previous run. Keep the edge unchanged.
            if src_uuid.startswith("GSD:"):
                kept_edges.append(edge)
                counts["kept_separate"] += 1
                continue
            # Promote query to its own node with a fresh GSD UUID
            new_uuid = reassigned_uuids.get(src_uuid)
            if new_uuid is None:
                new_uuid = f"GSD:{uuid.uuid4()}"
                reassigned_uuids[src_uuid] = new_uuid

            decision = src_to_decision.get(src_uuid, {})
            query_term = decision.get("source_term", "")
            kept_edges.append({
                "subj": new_uuid,
                "pred": pred,
                "obj": obj_uuid,
                "xref": edge.get("xref", ""),
                "comment": f"{query_term} {pred} {obj_uuid}",
            })
            counts["kept_separate"] += 1
        else:
            counts["unknown_pred"] += 1

    # Update terms_resolved.jsonl: for any term whose src_uuid is in reassigned_uuids,
    # change its term_uuid to the new UUID (so the master gets a separate node).
    for src_uuid, new_uuid in reassigned_uuids.items():
        row = resolved_by_src.get(src_uuid)
        if row:
            row["term_uuid"] = new_uuid

    # Write back
    with resolved_f.open("w", encoding="utf-8") as f:
        for row in resolved_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with edges_f.open("w", encoding="utf-8") as f:
        for edge in kept_edges:
            f.write(json.dumps(edge, ensure_ascii=False) + "\n")

    return {
        "source": src_dir.name,
        "decisions": len(decisions),
        "input_edges": len(edges),
        "kept_edges": len(kept_edges),
        "promoted_terms": len(reassigned_uuids),
        **counts,
    }


def main() -> None:
    reports = []
    print("=" * 70)
    print("Patching resolver edges for postprocessing compatibility")
    print("=" * 70)
    for src in sorted(INPUTS.glob("src_*")):
        if not src.is_dir():
            continue
        r = patch_source(src)
        if r.get("skipped"):
            continue
        print(
            f"  [{r['source']:35s}]  decisions={r['decisions']:>4d}  "
            f"edges_in={r['input_edges']:>4d}  edges_out={r['kept_edges']:>3d}  "
            f"promoted={r['promoted_terms']:>3d}  "
            f"drop_merge={r['dropped_merge']:>4d}  unknown={r['unknown_pred']}"
        )
        reports.append(r)
    print("=" * 70)


if __name__ == "__main__":
    main()
