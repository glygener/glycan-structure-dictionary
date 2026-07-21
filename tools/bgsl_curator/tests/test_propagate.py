"""Isolated durability test: sync_to_sources + apply_curator_overrides in a
temp sandbox (real data untouched). Proves the resolved-layer write-back +
override application reproduce a curated merge.

Run:  python tools/bgsl_curator/tests/test_propagate.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1]
ROOT = TOOL.parents[1]
sys.path.insert(0, str(TOOL))

from backend import propagate  # noqa: E402


class MiniStore:
    def __init__(self, nodes, edges, src_index):
        self.nodes = nodes
        self.edges = edges
        self.src_index = src_index
        self.node_index = {n["term_uuid"]: n for n in nodes}

    def get_node(self, u):
        return self.node_index.get(u)


def _write_jsonl(p: Path, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="curator_test_"))
    inputs = tmp / "data" / "inputs"
    release = tmp / "release"
    release.mkdir(parents=True)

    # --- fake sources: two rows, originally separate nodes A and B ---------
    src_dir = inputs / "src_demo"
    _write_jsonl(src_dir / "terms_resolved.jsonl", [
        {"term": "T antigen", "xref": "SRC:DEMO", "term_uuid": "GSD:A", "src_uuid": "s1",
         "metadata": {"exact_synonyms": [], "gtc_id": ["G1"], "raw_term": "T antigen"}},
        {"term": "T or TF antigen", "xref": "SRC:DEMO", "term_uuid": "GSD:B", "src_uuid": "s2",
         "metadata": {"exact_synonyms": [], "gtc_id": [], "raw_term": "T or TF antigen"}},
    ])
    _write_jsonl(src_dir / "terms_ai-decisions.jsonl", [
        {"source_term": "T antigen", "src_uuid": "s1", "xref": "SRC:DEMO", "mapped_to_uuid": "GSD:A", "action": "add", "edge_type": "", "rationale": "seed"},
        {"source_term": "T or TF antigen", "src_uuid": "s2", "xref": "SRC:DEMO", "mapped_to_uuid": "GSD:B", "action": "add", "edge_type": "", "rationale": "added"},
    ])

    # --- store AFTER an in-GUI merge B->A (exact) --------------------------
    survivor = {
        "term_uuid": "GSD:A", "lbl": "T antigen",
        "exact_synonyms": ["T or TF antigen"], "abbreviations": [],
        "classification": "1A", "gtc_id": ["G1"],
        "merged_from_term_uuids": ["GSD:B"],
        "sources": [
            {"src_lbl": "T antigen", "src": "SRC:DEMO", "src_uuid": "s1"},
            {"src_lbl": "T or TF antigen", "src": "SRC:DEMO", "src_uuid": "s2"},
        ],
    }
    store = MiniStore(
        nodes=[survivor], edges=[],
        src_index={
            "s1": {"source_dir": "src_demo", "resolved_row": {}, "ai_decision": {}},
            "s2": {"source_dir": "src_demo", "resolved_row": {}, "ai_decision": {}},
        },
    )

    # --- redirect propagate to the sandbox + run sync ----------------------
    propagate.INPUTS = inputs
    propagate.OVERRIDES_PATH = inputs / "curator_overrides.json"
    stats = propagate.sync_to_sources(store, journal_entries=[])

    # assert: s2 regrouped to survivor in resolved file
    resolved = [json.loads(l) for l in (src_dir / "terms_resolved.jsonl").read_text().splitlines() if l.strip()]
    by_su = {r["src_uuid"]: r for r in resolved}
    assert by_su["s2"]["term_uuid"] == "GSD:A", "s2 regrouped to survivor"
    assert by_su["s1"]["term_uuid"] == "GSD:A", "s1 unchanged"
    assert (src_dir / "terms_resolved.jsonl.bak").exists(), ".bak made"
    # ai-decisions realigned
    ai = {json.loads(l)["src_uuid"]: json.loads(l) for l in (src_dir / "terms_ai-decisions.jsonl").read_text().splitlines() if l.strip()}
    assert ai["s2"]["mapped_to_uuid"] == "GSD:A", "ai-decision realigned"
    # overrides file written
    ov = json.loads((inputs / "curator_overrides.json").read_text())
    assert "GSD:A" in ov["nodes"] and "T or TF antigen" in ov["nodes"]["GSD:A"]["exact_synonyms"]
    assert ov["nodes"]["GSD:A"]["merged_from_term_uuids"] == ["GSD:B"]
    print(f"  ✓ sync_to_sources: {stats['rows_regrouped']} regrouped, override has survivor w/ folded synonym")

    # --- simulate a fresh build (regroup only, NO presentation) ------------
    # build_release would group s1+s2 under GSD:A but lbl from first row, and
    # exact_synonyms would NOT contain the absorbed label (that's the override's job).
    fresh_nodes = [{
        "term_uuid": "GSD:A", "lbl": "T antigen",
        "exact_synonyms": [], "abbreviations": [], "classification": "",
        "gtc_id": ["G1"],
        "sources": [{"src_lbl": "T antigen", "src": "SRC:DEMO", "src_uuid": "s1"},
                    {"src_lbl": "T or TF antigen", "src": "SRC:DEMO", "src_uuid": "s2"}],
    }]
    (release / "master_nodes_20990101_000000.json").write_text(json.dumps(fresh_nodes), encoding="utf-8")
    (release / "master_edges_20990101_000000.json").write_text("[]", encoding="utf-8")
    (release / "dictionary_20990101_000000.json").write_text(json.dumps({"nodes": fresh_nodes, "edges": []}), encoding="utf-8")

    # --- run apply_curator_overrides against the sandbox -------------------
    spec = importlib.util.spec_from_file_location("aco", ROOT / "scripts" / "apply_curator_overrides.py")
    aco = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aco)
    aco.RELEASE_DIR = release
    aco.OVERRIDES = inputs / "curator_overrides.json"
    aco.main()

    rebuilt = json.loads((release / "master_nodes_20990101_000000.json").read_text())
    a = [n for n in rebuilt if n["term_uuid"] == "GSD:A"][0]
    assert "T or TF antigen" in a["exact_synonyms"], "override re-applied the folded synonym"
    assert a["classification"] == "1A", "override re-applied classification"
    assert a["merged_from_term_uuids"] == ["GSD:B"], "override re-applied legacy UUID"
    print("  ✓ apply_curator_overrides: fresh build + override reproduces the curated node")

    print("\nDURABILITY TEST PASSED (sandboxed; real data untouched)")


if __name__ == "__main__":
    main()
