"""Pure mutation operations on the in-memory nodes/edges working copy.

Each function mutates ``store.nodes`` / ``store.edges`` in place, calls
``store.reindex()`` when node membership changes, and returns a *journal
entry payload* (dict, without timestamp — journal.py stamps that).

UUID bookkeeping (per the curator's rules):
  * MERGE  — survivor UUID kept; absorbed UUID recorded in
             ``survivor.merged_from_term_uuids``.
  * SPLIT  — each child gets a fresh ``GSD:{uuid4()}`` and records the
             parent UUID in ``split_from_term_uuid``.

Helpers ``_normalise`` / ``_similarity`` / ``_new_uuid`` mirror
scripts/apply_review.py (kept local to avoid sys.path coupling).
"""

from __future__ import annotations

import re
import uuid as _uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import DataStore

VALID_RELATIONS = {"exact_synonym", "abbreviation"}
EDGE_PREDS = {
    "broad_synonym_of",
    "narrow_synonym_of",
    "related_synonym_of",
    "has_related_synonym",
    "exact_synonym_of",
    "abbreviation_of",
    "is_a",
}


# ---------------------------------------------------------------------------
# Shared helpers (mirror scripts/apply_review.py)
# ---------------------------------------------------------------------------

def _new_uuid() -> str:
    return f"GSD:{_uuid.uuid4()}"


def _normalise(s: str) -> str:
    # Case-sensitive carve-out: `i-antigen` vs `I-antigen` are different glycans.
    if not s:
        return ""
    first_was_upper = s.lstrip()[:1] == "I"
    t = s.lower()
    for a, b in (("α", "a"), ("β", "b"), ("γ", "g"), ("δ", "d")):
        t = t.replace(a, b)
    t = re.sub(r"[\s\-_'`^()\[\]\.\,/]+", "", t)
    if t == "iantigen":
        t = "Iantigen_uc" if first_was_upper else "iantigen_lc"
    return t


def _dedupe_keep_order(items: list[str], *, drop: set[str] | None = None) -> list[str]:
    drop = drop or set()
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in (None, ""):
            continue
        if x in drop:
            continue
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _union(dst: list, src: list) -> list:
    out = list(dst or [])
    for x in src or []:
        if x not in out:
            out.append(x)
    return out


# ---------------------------------------------------------------------------
# MERGE
# ---------------------------------------------------------------------------

def merge(store: "DataStore", survivor_uuid: str, absorbed_uuid: str, relation: str) -> dict:
    if relation not in VALID_RELATIONS:
        raise ValueError(f"relation must be one of {VALID_RELATIONS}, got {relation!r}")
    if survivor_uuid == absorbed_uuid:
        raise ValueError("survivor and absorbed must differ")
    B = store.get_node(survivor_uuid)
    A = store.get_node(absorbed_uuid)
    if not B:
        raise ValueError(f"survivor node not found: {survivor_uuid}")
    if not A:
        raise ValueError(f"absorbed node not found: {absorbed_uuid}")

    absorbed_lbl = A.get("lbl", "")
    absorbed_src_uuids = [s.get("src_uuid") for s in A.get("sources", []) if s.get("src_uuid")]

    # Fold sources (dedupe by src_uuid)
    existing = {s.get("src_uuid") for s in B.get("sources", [])}
    for s in A.get("sources", []):
        if s.get("src_uuid") not in existing:
            B.setdefault("sources", []).append(s)

    # Union scalar-list provenance fields
    B["gtc_id"] = _union(B.get("gtc_id"), A.get("gtc_id"))
    if A.get("db_xref") or B.get("db_xref"):
        B["db_xref"] = _union(B.get("db_xref"), A.get("db_xref"))

    # Fold the absorbed label + its lists into the chosen relation bucket
    add_to_exact = [absorbed_lbl] + (A.get("exact_synonyms") or []) if relation == "exact_synonym" else (A.get("exact_synonyms") or [])
    add_to_abbr = [absorbed_lbl] + (A.get("abbreviations") or []) if relation == "abbreviation" else (A.get("abbreviations") or [])
    B["exact_synonyms"] = _dedupe_keep_order((B.get("exact_synonyms") or []) + add_to_exact, drop={B.get("lbl", "")})
    B["abbreviations"] = _dedupe_keep_order((B.get("abbreviations") or []) + add_to_abbr, drop={B.get("lbl", "")})

    # Legacy-UUID metadata (carry A's own merge chain too)
    chain = [absorbed_uuid] + (A.get("merged_from_term_uuids") or [])
    B["merged_from_term_uuids"] = _union(B.get("merged_from_term_uuids"), chain)

    # Rewrite edges A -> B; drop self-edges and exact duplicates
    _rewrite_edge_endpoint(store, absorbed_uuid, survivor_uuid)

    # Remove A
    store.nodes = [n for n in store.nodes if n.get("term_uuid") != absorbed_uuid]
    store.reindex()

    return {
        "op": "merge",
        "survivor": survivor_uuid,
        "absorbed": absorbed_uuid,
        "relation": relation,
        "absorbed_lbl": absorbed_lbl,
        "absorbed_src_uuids": absorbed_src_uuids,
    }


# ---------------------------------------------------------------------------
# SPLIT
# ---------------------------------------------------------------------------

def split(store: "DataStore", parent_uuid: str, children: list[dict], edge_routing: dict | None = None) -> dict:
    """children: list of {lbl, src_uuids[], exact[], abbr[], gtc[]?, classification?}.

    edge_routing: {edge_id -> child_index | "drop"} where edge_id is the
    index of the edge within store.edges_for(parent). Unrouted edges default
    to child 0.
    """
    A = store.get_node(parent_uuid)
    if not A:
        raise ValueError(f"parent node not found: {parent_uuid}")
    if len(children) < 2:
        raise ValueError("split requires at least 2 children")

    sources_by_su = {s.get("src_uuid"): s for s in A.get("sources", [])}
    edge_routing = edge_routing or {}

    new_nodes: list[dict] = []
    child_records: list[dict] = []
    for spec in children:
        lbl = (spec.get("lbl") or "").strip()
        if not lbl:
            raise ValueError("each split child needs a non-empty label")
        new_uid = _new_uuid()
        routed_su = [su for su in (spec.get("src_uuids") or []) if su in sources_by_su]
        routed_sources = [sources_by_su[su] for su in routed_su]

        # Reconstruct gtc_id / db_xref from routed sources' resolved metadata,
        # unless explicitly provided by the UI.
        gtc = spec.get("gtc")
        if gtc is None:
            gtc = []
            for su in routed_su:
                meta = (store.src_index.get(su, {}).get("resolved_row") or {}).get("metadata") or {}
                gtc = _union(gtc, meta.get("gtc_id") or [])
        db_xref: list[str] = []
        for su in routed_su:
            meta = (store.src_index.get(su, {}).get("resolved_row") or {}).get("metadata") or {}
            db_xref = _union(db_xref, meta.get("db_xref") or [])

        meta_block = dict(A.get("bgsl_curator_meta") or {})
        meta_block["preferred_label_override"] = lbl
        meta_block.setdefault("keep", True)

        node = {
            "lbl": lbl,
            "term_uuid": new_uid,
            "gtc_id": gtc,
            "sources": routed_sources,
            "exact_synonyms": _dedupe_keep_order(spec.get("exact") or [], drop={lbl}),
            "abbreviations": _dedupe_keep_order(spec.get("abbr") or [], drop={lbl}),
            "classification": spec.get("classification") or A.get("classification", ""),
            "bgsl_curator_meta": meta_block,
            "is_class": A.get("is_class", False),
            "raw_term": lbl,
            "split_from_term_uuid": parent_uuid,
        }
        if db_xref:
            node["db_xref"] = db_xref
        if A.get("description"):
            node["description"] = A["description"]
        new_nodes.append(node)
        child_records.append({
            "uuid": new_uid, "lbl": lbl, "src_uuids": routed_su,
            "exact": node["exact_synonyms"], "abbr": node["abbreviations"], "gtc": gtc,
        })

    # Route incident edges
    incident = store.edges_for(parent_uuid)
    kept_edges: list[dict] = []
    for e in store.edges:
        if e not in incident:
            kept_edges.append(e)
    for i, e in enumerate(incident):
        target = edge_routing.get(str(i), 0)
        if target == "drop":
            continue
        ci = int(target) if str(target).lstrip("-").isdigit() else 0
        ci = max(0, min(ci, len(new_nodes) - 1))
        child_uid = new_nodes[ci]["term_uuid"]
        ne = dict(e)
        if ne.get("subj") == parent_uuid:
            ne["subj"] = child_uid
        if ne.get("obj") == parent_uuid:
            ne["obj"] = child_uid
        if ne.get("subj") != ne.get("obj"):
            kept_edges.append(ne)
    store.edges = kept_edges

    # Swap parent out, children in
    store.nodes = [n for n in store.nodes if n.get("term_uuid") != parent_uuid] + new_nodes
    store.reindex()

    return {
        "op": "split",
        "parent": parent_uuid,
        "parent_lbl": A.get("lbl", ""),
        "children": child_records,
        "edge_routing": edge_routing,
    }


# ---------------------------------------------------------------------------
# RELABEL
# ---------------------------------------------------------------------------

def relabel(store: "DataStore", uuid: str, new_lbl: str, old_lbl_dest: str = "exact") -> dict:
    node = store.get_node(uuid)
    if not node:
        raise ValueError(f"node not found: {uuid}")
    new_lbl = (new_lbl or "").strip()
    if not new_lbl:
        raise ValueError("new label must be non-empty")
    old_lbl = node.get("lbl", "")
    if old_lbl == new_lbl:
        raise ValueError("new label equals current label")

    node["lbl"] = new_lbl
    if old_lbl_dest == "exact":
        node["exact_synonyms"] = _dedupe_keep_order((node.get("exact_synonyms") or []) + [old_lbl], drop={new_lbl})
    elif old_lbl_dest == "abbreviation":
        node["abbreviations"] = _dedupe_keep_order((node.get("abbreviations") or []) + [old_lbl], drop={new_lbl})
    # else discard

    meta = dict(node.get("bgsl_curator_meta") or {})
    meta["preferred_label_override"] = new_lbl
    node["bgsl_curator_meta"] = meta
    # Keep lists clean of the new label
    node["exact_synonyms"] = _dedupe_keep_order(node.get("exact_synonyms") or [], drop={new_lbl})
    node["abbreviations"] = _dedupe_keep_order(node.get("abbreviations") or [], drop={new_lbl})

    return {"op": "relabel", "node": uuid, "old_lbl": old_lbl, "new_lbl": new_lbl, "old_lbl_dest": old_lbl_dest}


# ---------------------------------------------------------------------------
# EDIT LISTS
# ---------------------------------------------------------------------------

_FIELDS = {"exact_synonyms", "abbreviations"}


def edit_lists(store: "DataStore", uuid: str, changes: list[dict]) -> dict:
    node = store.get_node(uuid)
    if not node:
        raise ValueError(f"node not found: {uuid}")
    applied: list[dict] = []
    for ch in changes:
        action = ch.get("action")
        field = ch.get("field")
        value = ch.get("value")
        if field not in _FIELDS:
            raise ValueError(f"field must be one of {_FIELDS}, got {field!r}")
        cur = list(node.get(field) or [])
        if action == "add":
            cur.append(value)
        elif action == "remove":
            cur = [x for x in cur if x != value]
        elif action == "rename":
            new_value = ch.get("new_value")
            cur = [new_value if x == value else x for x in cur]
        elif action == "move":
            other = "abbreviations" if field == "exact_synonyms" else "exact_synonyms"
            cur = [x for x in cur if x != value]
            other_list = list(node.get(other) or [])
            other_list.append(value)
            node[other] = _dedupe_keep_order(other_list, drop={node.get("lbl", "")})
        else:
            raise ValueError(f"unknown list action: {action!r}")
        node[field] = _dedupe_keep_order(cur, drop={node.get("lbl", "")})
        applied.append(ch)
    return {"op": "edit_lists", "node": uuid, "changes": applied}


# ---------------------------------------------------------------------------
# EDIT EDGES
# ---------------------------------------------------------------------------

def edit_edges(store: "DataStore", action: str, subj: str, pred: str, obj: str, comment: str | None = None) -> dict:
    if pred not in EDGE_PREDS:
        raise ValueError(f"pred must be one of {sorted(EDGE_PREDS)}, got {pred!r}")
    if action == "add":
        if not store.get_node(subj) or not store.get_node(obj):
            raise ValueError("both subj and obj must be existing nodes")
        s_lbl = store.get_node(subj).get("lbl", subj)
        o_lbl = store.get_node(obj).get("lbl", obj)
        store.edges.append({
            "subj": subj, "pred": pred, "obj": obj,
            "comment": comment or f"curator: {s_lbl} {pred} {o_lbl}",
        })
    elif action == "remove":
        store.edges = [
            e for e in store.edges
            if not (e.get("subj") == subj and e.get("pred") == pred and e.get("obj") == obj)
        ]
    elif action == "modify":
        for e in store.edges:
            if e.get("subj") == subj and e.get("obj") == obj:
                e["pred"] = pred
                e["comment"] = comment or e.get("comment", "")
    else:
        raise ValueError(f"unknown edge action: {action!r}")
    return {"op": "edge", "action": action, "subj": subj, "pred": pred, "obj": obj}


# ---------------------------------------------------------------------------
# DROP
# ---------------------------------------------------------------------------

def drop(store: "DataStore", uuid: str) -> dict:
    node = store.get_node(uuid)
    if not node:
        raise ValueError(f"node not found: {uuid}")
    src_uuids = [s.get("src_uuid") for s in node.get("sources", []) if s.get("src_uuid")]
    lbl = node.get("lbl", "")
    store.nodes = [n for n in store.nodes if n.get("term_uuid") != uuid]
    store.edges = [e for e in store.edges if e.get("subj") != uuid and e.get("obj") != uuid]
    store.reindex()
    return {"op": "drop", "node": uuid, "lbl": lbl, "src_uuids": src_uuids}


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _rewrite_edge_endpoint(store: "DataStore", old: str, new: str) -> None:
    """Repoint every edge from `old` to `new`; drop self-edges + exact dups."""
    seen: set[tuple] = set()
    out: list[dict] = []
    for e in store.edges:
        subj = new if e.get("subj") == old else e.get("subj")
        obj = new if e.get("obj") == old else e.get("obj")
        if subj == obj:
            continue
        key = (subj, e.get("pred"), obj)
        if key in seen:
            continue
        seen.add(key)
        ne = dict(e)
        ne["subj"] = subj
        ne["obj"] = obj
        out.append(ne)
    store.edges = out
