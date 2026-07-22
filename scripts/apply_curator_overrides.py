"""Apply curator GUI overrides to a freshly built release.

The bGSL Curator GUI (tools/bgsl_curator) writes two durable artefacts:

  * Resolved-layer rewrites (terms_resolved.term_uuid / ai-decisions) — these
    make `build_release.py` reproduce the curated node GROUPING (merges,
    splits) and DROPS automatically.
  * `data/inputs/curator_overrides.json` — the authoritative *presentation*
    layer: per-node lbl / exact_synonyms / abbreviations / classification /
    legacy-UUID metadata, plus the authoritative edge list.

This script applies that override file onto the newest master_nodes_*.json /
master_edges_*.json (in place) and rewrites the matching dictionary_*.json, so
a full rebuild reproduces the curated state byte-for-byte. Run it AFTER
`build_release.py` and BEFORE `build_bgsl_tsv.py`.

No-op (with a message) if the override file is absent.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "data" / "outputs" / "releases" / "gsd_v2.0.0-draft"
OVERRIDES = ROOT / "data" / "inputs" / "curator_overrides.json"

NODE_FIELDS = ["lbl", "exact_synonyms", "abbreviations", "classification",
               "merged_from_term_uuids", "split_from_term_uuid"]


def _latest(pattern: str) -> Path | None:
    matches = sorted(glob.glob(pattern))
    return Path(matches[-1]) if matches else None


def main() -> None:
    if not OVERRIDES.exists():
        print(f"[skip] no override file at {OVERRIDES}")
        return

    ov = json.loads(OVERRIDES.read_text())
    ov_nodes: dict = ov.get("nodes", {})
    ov_edges: list = ov.get("edges", [])

    nodes_p = _latest(str(RELEASE_DIR / "master_nodes_*.json"))
    edges_p = _latest(str(RELEASE_DIR / "master_edges_*.json"))
    dict_p = _latest(str(RELEASE_DIR / "dictionary_*.json"))
    if not nodes_p:
        print("[err] no master_nodes_*.json found")
        return

    nodes = json.loads(nodes_p.read_text())

    # 1. Apply per-node presentation overrides
    applied = 0
    for n in nodes:
        o = ov_nodes.get(n.get("term_uuid"))
        if not o:
            continue
        for k in NODE_FIELDS:
            if k in o:
                n[k] = o[k]
        applied += 1

    # 2. Authoritative edge list (filtered to surviving nodes)
    node_ids = {n["term_uuid"] for n in nodes}
    edges = [e for e in ov_edges if e.get("subj") in node_ids and e.get("obj") in node_ids]
    dropped_edges = len(ov_edges) - len(edges)

    nodes_p.write_text(json.dumps(nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    if edges_p:
        edges_p.write_text(json.dumps(edges, ensure_ascii=False, indent=2), encoding="utf-8")
    if dict_p:
        dict_p.write_text(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[overrides] applied to {applied}/{len(nodes)} nodes; "
          f"edge list set to {len(edges)} ({dropped_edges} dropped for missing endpoints)")
    print(f"[overrides] wrote {nodes_p.name}" + (f", {edges_p.name}" if edges_p else "")
          + (f", {dict_p.name}" if dict_p else ""))


if __name__ == "__main__":
    main()
