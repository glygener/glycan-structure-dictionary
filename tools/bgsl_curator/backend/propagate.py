"""Write-back layer: make the curated working copy durable so a future
``build_release.py`` run reproduces it.

Two artefacts are produced (derived from the FINAL store state, not by
replaying ops — the final state is the source of truth):

3a. Resolved-layer grouping (per-source files, the "AI node mapping"):
    For every source row, rewrite ``terms_resolved.term_uuid`` and
    ``terms_ai-decisions.mapped_to_uuid`` to its current owning node. Rows
    whose src_uuid is no longer owned by any node (orphaned by a DROP) get
    ``keep=false``. This makes build_release reproduce the curated node
    GROUPING (merges/splits) and drops. Seed sources (only terms.jsonl) are
    edited in place there.

3b. Authoritative presentation override (``data/inputs/curator_overrides.json``):
    Per current node: lbl, exact_synonyms, abbreviations, classification,
    legacy-UUID metadata; plus the authoritative edge list and dropped
    src_uuids. Applied by ``scripts/apply_curator_overrides.py`` after a
    rebuild to reproduce labels/lists/edges byte-for-byte.

Curator edge ADD operations are additionally appended to the subject
source's ``edges_ai-decisions.jsonl`` as a decisions paper-trail.

Every touched file is backed up to ``<file>.bak`` on first write per run.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .store import INPUTS, _read_jsonl

OVERRIDES_PATH = INPUTS / "curator_overrides.json"

_OVERRIDE_NODE_FIELDS = [
    "lbl", "exact_synonyms", "abbreviations", "classification",
    "merged_from_term_uuids", "split_from_term_uuid",
]


def _backup_once(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak")
    if path.exists() and not bak.exists():
        shutil.copyfile(path, bak)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def sync_to_sources(store, journal_entries: list[dict]) -> dict:
    # ---- owner map: src_uuid -> owning node uuid ----------------------
    owner: dict[str, str] = {}
    for n in store.nodes:
        for s in n.get("sources", []):
            su = s.get("src_uuid")
            if su:
                owner[su] = n["term_uuid"]

    stats = {"files_touched": 0, "rows_regrouped": 0, "rows_dropped": 0, "edge_decisions_added": 0}

    # ---- 3a. rewrite per-source resolved + ai-decision files ----------
    for src_dir in sorted(INPUTS.glob("src_*")):
        resolved_f = src_dir / "terms_resolved.jsonl"
        terms_f = src_dir / "terms.jsonl"
        primary = resolved_f if resolved_f.exists() else terms_f
        if not primary.exists():
            continue

        rows = _read_jsonl(primary)
        changed = False
        for row in rows:
            su = row.get("src_uuid")
            if not su:
                continue
            if su in owner:
                if row.get("term_uuid") != owner[su]:
                    row["term_uuid"] = owner[su]
                    stats["rows_regrouped"] += 1
                    changed = True
                if row.get("keep") is False:
                    row["keep"] = True
                    changed = True
            else:
                # orphaned -> dropped node
                if row.get("keep") is not False:
                    row["keep"] = False
                    stats["rows_dropped"] += 1
                    changed = True
        if changed:
            _backup_once(primary)
            _write_jsonl(primary, rows)
            stats["files_touched"] += 1

        # ai-decisions: realign mapped_to_uuid
        ai_f = src_dir / "terms_ai-decisions.jsonl"
        if ai_f.exists():
            ai_rows = _read_jsonl(ai_f)
            ai_changed = False
            for row in ai_rows:
                su = row.get("src_uuid")
                if su in owner and row.get("mapped_to_uuid") != owner[su]:
                    row["mapped_to_uuid"] = owner[su]
                    if not row.get("rationale", "").startswith("curator"):
                        row["rationale"] = f"curator-curated; {row.get('rationale', '')}".strip()
                    ai_changed = True
            if ai_changed:
                _backup_once(ai_f)
                _write_jsonl(ai_f, ai_rows)
                stats["files_touched"] += 1

    # ---- edge-add paper trail -> edges_ai-decisions -------------------
    for entry in journal_entries:
        if entry.get("op") == "edge" and entry.get("action") == "add":
            subj = entry.get("subj")
            node = store.get_node(subj)
            if not node or not node.get("sources"):
                continue
            su0 = node["sources"][0].get("src_uuid")
            src_dir_name = store.src_index.get(su0, {}).get("source_dir")
            if not src_dir_name:
                continue
            ai_edges_f = INPUTS / src_dir_name / "edges_ai-decisions.jsonl"
            existing = _read_jsonl(ai_edges_f)
            key = (entry.get("subj"), entry.get("pred"), entry.get("obj"))
            if any((e.get("subj"), e.get("pred"), e.get("obj")) == key for e in existing):
                continue
            existing.append({
                "subj": entry["subj"], "pred": entry["pred"], "obj": entry["obj"],
                "xref": f"SRC:{src_dir_name.replace('src_', '').upper()}",
                "comment": f"curator: {entry['subj']} {entry['pred']} {entry['obj']}",
            })
            _backup_once(ai_edges_f)
            _write_jsonl(ai_edges_f, existing)
            stats["edge_decisions_added"] += 1

    # ---- 3b. authoritative override file ------------------------------
    dropped_src_uuids: list[str] = [su for su in store.src_index if su not in owner]
    overrides = {
        "generated_by": "bgsl_curator",
        "note": "Applied by scripts/apply_curator_overrides.py after build_release.",
        "nodes": {
            n["term_uuid"]: {k: n.get(k) for k in _OVERRIDE_NODE_FIELDS if n.get(k) is not None}
            for n in store.nodes
        },
        "edges": store.edges,
        "dropped_src_uuids": dropped_src_uuids,
    }
    OVERRIDES_PATH.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    stats["overrides_path"] = str(OVERRIDES_PATH)
    stats["override_nodes"] = len(overrides["nodes"])
    stats["override_edges"] = len(overrides["edges"])
    return stats
