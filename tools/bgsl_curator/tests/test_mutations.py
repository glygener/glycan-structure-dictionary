"""Unit tests for the mutation logic (no server needed).

Run:  python -m pytest tools/bgsl_curator/tests/test_mutations.py
 or:  python tools/bgsl_curator/tests/test_mutations.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tools/bgsl_curator
from backend import mutations  # noqa: E402


class FakeStore:
    def __init__(self, nodes, edges, src_index=None):
        self.nodes = nodes
        self.edges = edges
        self.src_index = src_index or {}
        self.reindex()

    def reindex(self):
        self.node_index = {n["term_uuid"]: n for n in self.nodes}

    def get_node(self, u):
        return self.node_index.get(u)

    def edges_for(self, u):
        return [e for e in self.edges if e.get("subj") == u or e.get("obj") == u]


def _src(su, lbl, src="SRC:X"):
    return {"src_lbl": lbl, "src": src, "src_uuid": su}


def fresh():
    nodes = [
        {"term_uuid": "GSD:A", "lbl": "T antigen", "exact_synonyms": [], "abbreviations": [],
         "gtc_id": ["G1"], "sources": [_src("s1", "T antigen")]},
        {"term_uuid": "GSD:B", "lbl": "T or TF antigen", "exact_synonyms": [], "abbreviations": [],
         "gtc_id": [], "sources": [_src("s2", "T or TF antigen")]},
        {"term_uuid": "GSD:C", "lbl": "other", "exact_synonyms": [], "abbreviations": [],
         "gtc_id": [], "sources": [_src("s3", "other")]},
    ]
    edges = [{"subj": "GSD:B", "pred": "related_synonym_of", "obj": "GSD:C", "comment": ""}]
    return FakeStore(nodes, edges)


def test_merge_exact():
    s = fresh()
    entry = mutations.merge(s, "GSD:A", "GSD:B", "exact_synonym")
    assert s.get_node("GSD:B") is None, "absorbed node removed"
    A = s.get_node("GSD:A")
    assert A["term_uuid"] == "GSD:A", "survivor keeps UUID"
    assert "GSD:B" in A["merged_from_term_uuids"], "legacy UUID recorded"
    assert "T or TF antigen" in A["exact_synonyms"], "absorbed label folded into exact"
    assert {x["src_uuid"] for x in A["sources"]} == {"s1", "s2"}, "sources folded"
    # edge B->C repointed to A->C
    assert any(e["subj"] == "GSD:A" and e["obj"] == "GSD:C" for e in s.edges), "edge repointed"
    assert entry["op"] == "merge" and entry["relation"] == "exact_synonym"
    print("ok test_merge_exact")


def test_merge_abbreviation():
    s = fresh()
    mutations.merge(s, "GSD:A", "GSD:B", "abbreviation")
    A = s.get_node("GSD:A")
    assert "T or TF antigen" in A["abbreviations"]
    assert "T or TF antigen" not in A["exact_synonyms"]
    print("ok test_merge_abbreviation")


def test_split():
    s = fresh()
    A = s.get_node("GSD:A")
    A["sources"] = [_src("s1", "6'-sulfo"), _src("s1b", "6-sulfo")]
    A["exact_synonyms"] = ["6'-variant", "6-variant"]
    entry = mutations.split(s, "GSD:A", [
        {"lbl": "6'-sulfo-sialyl Lewis x", "src_uuids": ["s1"], "exact": ["6'-variant"], "abbr": []},
        {"lbl": "6-sulfo-sialyl Lewis x", "src_uuids": ["s1b"], "exact": ["6-variant"], "abbr": []},
    ])
    assert s.get_node("GSD:A") is None, "parent removed"
    kids = entry["children"]
    assert len(kids) == 2
    c0 = s.get_node(kids[0]["uuid"])
    c1 = s.get_node(kids[1]["uuid"])
    assert c0["split_from_term_uuid"] == "GSD:A" and c1["split_from_term_uuid"] == "GSD:A"
    assert c0["term_uuid"].startswith("GSD:") and c0["term_uuid"] != "GSD:A"
    assert {x["src_uuid"] for x in c0["sources"]} == {"s1"}
    assert {x["src_uuid"] for x in c1["sources"]} == {"s1b"}
    assert c0["exact_synonyms"] == ["6'-variant"]
    assert c0["bgsl_curator_meta"]["preferred_label_override"] == "6'-sulfo-sialyl Lewis x"
    print("ok test_split")


def test_relabel():
    s = fresh()
    mutations.relabel(s, "GSD:A", "T-antigen (Tn-related)", "exact")
    A = s.get_node("GSD:A")
    assert A["lbl"] == "T-antigen (Tn-related)"
    assert "T antigen" in A["exact_synonyms"]
    assert A["bgsl_curator_meta"]["preferred_label_override"] == "T-antigen (Tn-related)"
    print("ok test_relabel")


def test_edit_lists_move():
    s = fresh()
    A = s.get_node("GSD:A")
    A["exact_synonyms"] = ["TF antigen"]
    mutations.edit_lists(s, "GSD:A", [{"action": "move", "field": "exact_synonyms", "value": "TF antigen"}])
    assert "TF antigen" not in A["exact_synonyms"]
    assert "TF antigen" in A["abbreviations"]
    print("ok test_edit_lists_move")


def test_edit_lists_rename():
    s = fresh()
    A = s.get_node("GSD:A")
    A["exact_synonyms"] = ["Thomsen-Fridenreich antigen"]
    mutations.edit_lists(s, "GSD:A", [{"action": "rename", "field": "exact_synonyms",
                                       "value": "Thomsen-Fridenreich antigen",
                                       "new_value": "Thomsen-Friedenreich antigen"}])
    assert s.get_node("GSD:A")["exact_synonyms"] == ["Thomsen-Friedenreich antigen"]
    print("ok test_edit_lists_rename")


def test_edges_add_remove():
    s = fresh()
    mutations.edit_edges(s, "add", "GSD:A", "broad_synonym_of", "GSD:C")
    assert any(e["subj"] == "GSD:A" and e["pred"] == "broad_synonym_of" and e["obj"] == "GSD:C" for e in s.edges)
    mutations.edit_edges(s, "remove", "GSD:A", "broad_synonym_of", "GSD:C")
    assert not any(e["subj"] == "GSD:A" and e["pred"] == "broad_synonym_of" and e["obj"] == "GSD:C" for e in s.edges)
    print("ok test_edges_add_remove")


def test_drop():
    s = fresh()
    entry = mutations.drop(s, "GSD:B")
    assert s.get_node("GSD:B") is None
    assert entry["src_uuids"] == ["s2"]
    # incident edge B->C removed
    assert not any(e["subj"] == "GSD:B" or e["obj"] == "GSD:B" for e in s.edges)
    print("ok test_drop")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\nALL UNIT TESTS PASSED")
