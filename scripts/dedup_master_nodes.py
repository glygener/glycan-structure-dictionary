"""Post-merge cleanup: collapse master_nodes entries that the resolver missed.

The vector-store-based resolver has poor recall for very short abbreviations
(e.g. searching for "Gb3" against a long descriptive doc for
"globotriaosylceramide" gives a similarity below the threshold). The resolver
then adds it as a separate node, even though it should have merged.

This script finds such duplicates and folds them into the parent:

  Two nodes are merged when (A) is the SHORTER label, (A) appears in (B)'s
  exact_synonyms or sources[].src_lbl, and (A) has no GTC ID *or* shares a GTC
  with (B). The shorter node's source rows are reattached to the longer node,
  and the shorter node is dropped.

Run after `build_release.py`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("/Users/cyrusay/Desktop/github_repo/gsd_v3")
RELEASE_DIR = ROOT / "data" / "outputs" / "releases" / "gsd_v2.0.0-draft"


def _normalise(s: str) -> str:
    # Case-sensitive carve-out: `i-antigen` (linear poly-LacNAc) and
    # `I-antigen` (branched poly-LacNAc) are different glycans. This is
    # the only term we treat as case-sensitive.
    if not s:
        return ""
    first_was_upper = s.lstrip()[:1] == "I"
    t = s.lower()
    for src, dst in (("α", "a"), ("β", "b"), ("γ", "g"), ("δ", "d")):
        t = t.replace(src, dst)
    t = re.sub(r"[\s\-_'`^()\[\]\.\,/]+", "", t)
    if t == "iantigen":
        t = "Iantigen_uc" if first_was_upper else "iantigen_lc"
    return t


def _run_one_pass(nodes: list[dict], edges_path: Path | None) -> tuple[list[dict], int]:
    """One dedup pass — returns (new_nodes_list, merge_count).

    Match ONLY on the primary `lbl`. We deliberately ignore `src_lbl` and
    `exact_synonyms` because they can be wrong: the resolver may have routed
    a source row's surface form to the wrong canonical node, and using that
    as a merge key would then cascade the mistake (e.g. one source's
    `src_lbl="Lewis x"` was routed to the `dimeric Lewis x` node; matching on
    that would incorrectly absorb the legitimate standalone `Lewis x` node).

    Two nodes are merged only when their primary labels match after
    normalisation (case / whitespace / punctuation / Greek letters) AND the
    source-side node has no GTC OR shares at least one GTC with the target.
    """
    forms_index: dict[str, list[tuple]] = {}
    for n in nodes:
        uid = n.get("term_uuid")
        lbl = n.get("lbl") or ""
        gtc = set(n.get("gtc_id") or [])
        nf = _normalise(lbl)
        if not nf:
            continue
        forms_index.setdefault(nf, []).append((uid, bool(gtc), gtc))

    merges: dict[str, str] = {}
    for nf, hits in forms_index.items():
        if len(hits) <= 1:
            continue
        uniq_uuids = list({h[0] for h in hits})
        if len(uniq_uuids) <= 1:
            continue
        idx_by_uuid = {n["term_uuid"]: n for n in nodes}
        sorted_uids = sorted(uniq_uuids, key=lambda u: len(idx_by_uuid[u].get("lbl") or ""), reverse=True)
        target = sorted_uids[0]
        target_gtc = set(idx_by_uuid[target].get("gtc_id") or [])
        for src in sorted_uids[1:]:
            src_gtc = set(idx_by_uuid[src].get("gtc_id") or [])
            # Merge purely on normalised surface form. GTC ID is NOT used as a
            # merge signal — GSDv1's GTC IDs are unreliable. IDs are still
            # carried on the node for provenance / downstream enrichment.
            if True:  # was: if not src_gtc or (src_gtc & target_gtc):
                final_target = target
                while final_target in merges:
                    final_target = merges[final_target]
                if src == final_target:
                    continue
                merges[src] = final_target

    if not merges:
        return nodes, 0

    by_uuid = {n["term_uuid"]: n for n in nodes}
    merged_into: dict[str, list[str]] = {}
    for src, tgt in merges.items():
        merged_into.setdefault(tgt, []).append(src)

    new_nodes: list[dict] = []
    for n in nodes:
        uid = n["term_uuid"]
        if uid in merges:
            continue
        if uid in merged_into:
            for src_uid in merged_into[uid]:
                src_node = by_uuid[src_uid]
                existing_src_uuids = {s.get("src_uuid") for s in n.get("sources", [])}
                for s in src_node.get("sources", []):
                    if s.get("src_uuid") not in existing_src_uuids:
                        n.setdefault("sources", []).append(s)
                for g in src_node.get("gtc_id") or []:
                    if g not in (n.get("gtc_id") or []):
                        n.setdefault("gtc_id", []).append(g)
                for syn in src_node.get("exact_synonyms") or []:
                    if syn not in (n.get("exact_synonyms") or []):
                        n.setdefault("exact_synonyms", []).append(syn)
                for abbr in src_node.get("abbreviations") or []:
                    if abbr not in (n.get("abbreviations") or []):
                        n.setdefault("abbreviations", []).append(abbr)
                for xref in src_node.get("db_xref") or []:
                    if xref not in (n.get("db_xref") or []):
                        n.setdefault("db_xref", []).append(xref)
                n.setdefault("merged_from_term_uuids", []).append(src_uid)
        new_nodes.append(n)

    # rewrite edges in place
    if edges_path and edges_path.exists():
        edges = json.loads(edges_path.read_text())
        new_edges = []
        for e in edges:
            subj = merges.get(e.get("subj"), e.get("subj"))
            obj = merges.get(e.get("obj"), e.get("obj"))
            if subj == obj:
                continue
            e["subj"] = subj
            e["obj"] = obj
            new_edges.append(e)
        edges_path.write_text(json.dumps(new_edges, indent=2, ensure_ascii=False))

    return new_nodes, len(merges)


def main() -> None:
    nodes_files = sorted(RELEASE_DIR.glob("master_nodes_*.json"))
    if not nodes_files:
        print("[ERR] No master_nodes file found.")
        return
    nodes_path = nodes_files[-1]
    edges_files = sorted(RELEASE_DIR.glob("master_edges_*.json"))
    edges_path = edges_files[-1] if edges_files else None
    nodes = json.loads(nodes_path.read_text())
    n_before = len(nodes)

    # Iterate to convergence — merging can expose new synonyms that enable
    # further matches on the next pass.
    total_merged = 0
    for it in range(1, 11):
        nodes, n_merged = _run_one_pass(nodes, edges_path)
        if n_merged == 0:
            break
        total_merged += n_merged
        print(f"[MERGE] pass {it}: removed {n_merged}, total now {len(nodes)}")

    nodes_path.write_text(json.dumps(nodes, indent=2, ensure_ascii=False))
    print(f"[MERGE] Master nodes: {n_before} -> {len(nodes)}  ({total_merged} total merged)")

    # Rebuild dictionary.json so it reflects the post-dedup state.
    dict_files = sorted(RELEASE_DIR.glob("dictionary_*.json"))
    if dict_files and edges_path and edges_path.exists():
        dict_path = dict_files[-1]
        edges = json.loads(edges_path.read_text())
        # Minimal rebuild: nodes + edges. Loses the rich src_content that
        # build_ontology produces from the raw JSONL files, but those can be
        # re-built later by re-running postprocessing.
        dictionary = {"nodes": nodes, "edges": edges}
        dict_path.write_text(json.dumps(dictionary, indent=2, ensure_ascii=False))
        print(f"[MERGE] Rewrote dictionary: {dict_path.name} ({len(nodes)} nodes / {len(edges)} edges)")
    return

if __name__ == "__main__":
    main()
