"""FastAPI app for the bGSL Curator.

Launch (from tools/bgsl_curator/):
    uvicorn backend.app:app --reload --port 8765
then open http://localhost:8765
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import mutations
from .journal import Journal
from .models import EdgeReq, ListEditReq, MergeReq, RelabelReq, SplitReq
from .propagate import sync_to_sources
from .store import RELEASE_DIR, ROOT, DataStore

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
GLY_PY = "/Users/cyrusay/anaconda3/envs/gly_env/bin/python"

app = FastAPI(title="bGSL Curator")

STORE = DataStore()
JOURNAL = Journal()
STATE = {"dirty": False}


# ---------------------------------------------------------------------------
# Transactional wrapper
# ---------------------------------------------------------------------------

def _apply(fn, *args, **kwargs):
    snap = JOURNAL.begin(STORE)
    try:
        entry = fn(STORE, *args, **kwargs)
    except ValueError as exc:
        JOURNAL.rollback(STORE, snap)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        JOURNAL.rollback(STORE, snap)
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
    stamped = JOURNAL.commit(STORE, snap, entry)
    STATE["dirty"] = True
    return stamped


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

@app.get("/api/meta")
def meta():
    classes = sorted({(n.get("classification") or "") for n in STORE.nodes})
    return {
        "session_id": JOURNAL.session_id,
        "n_nodes": len(STORE.nodes),
        "n_edges": len(STORE.edges),
        "classifications": [c for c in classes if c],
        "dirty": STATE["dirty"],
        "nodes_path": str(STORE.nodes_path) if STORE.nodes_path else None,
    }


@app.get("/api/nodes")
def list_nodes(query: str = "", klass: str = "", sort: str = "class", page: int = 1, page_size: int = 100):
    q = query.strip().lower()
    rows = []
    for n in STORE.nodes:
        if klass and (n.get("classification") or "") != klass:
            continue
        if q:
            hay = " ".join([
                n.get("lbl", ""),
                " ".join(n.get("exact_synonyms", []) or []),
                " ".join(n.get("abbreviations", []) or []),
                n.get("term_uuid", ""),
            ]).lower()
            if q not in hay:
                continue
        rows.append(STORE.node_summary(n))

    if sort == "lbl":
        rows.sort(key=lambda r: r["lbl"].lower())
    elif sort == "sources":
        rows.sort(key=lambda r: -r["n_sources"])
    else:  # class then lbl
        rows.sort(key=lambda r: ((r["classification"] or "~"), r["lbl"].lower()))

    total = len(rows)
    start = max(0, (page - 1) * page_size)
    return {"total": total, "page": page, "page_size": page_size, "rows": rows[start:start + page_size]}


@app.get("/api/nodes/{uuid:path}")
def get_node(uuid: str):
    node = STORE.get_node(uuid)
    if not node:
        raise HTTPException(status_code=404, detail=f"node not found: {uuid}")
    return {
        "node": node,
        "provenance": STORE.provenance(node),
        "edges": [
            {**e, "subj_lbl": STORE.get_node(e["subj"]).get("lbl") if STORE.get_node(e["subj"]) else e["subj"],
             "obj_lbl": STORE.get_node(e["obj"]).get("lbl") if STORE.get_node(e["obj"]) else e["obj"]}
            for e in STORE.edges_for(uuid)
        ],
    }


# ---------------------------------------------------------------------------
# Mutating endpoints
# ---------------------------------------------------------------------------

@app.post("/api/merge")
def api_merge(req: MergeReq):
    entry = _apply(mutations.merge, req.survivor, req.absorbed, req.relation)
    return {"ok": True, "entry": entry, "node": STORE.get_node(req.survivor)}


@app.post("/api/split")
def api_split(req: SplitReq):
    children = [c.model_dump() for c in req.children]
    entry = _apply(mutations.split, req.parent, children, req.edge_routing)
    return {"ok": True, "entry": entry, "children": [STORE.get_node(c["uuid"]) for c in entry["children"]]}


@app.post("/api/nodes/{uuid:path}/relabel")
def api_relabel(uuid: str, req: RelabelReq):
    entry = _apply(mutations.relabel, uuid, req.new_lbl, req.old_lbl_dest)
    return {"ok": True, "entry": entry, "node": STORE.get_node(uuid)}


@app.post("/api/nodes/{uuid:path}/lists")
def api_lists(uuid: str, req: ListEditReq):
    entry = _apply(mutations.edit_lists, uuid, [c.model_dump() for c in req.changes])
    return {"ok": True, "entry": entry, "node": STORE.get_node(uuid)}


@app.post("/api/edges")
def api_edges(req: EdgeReq):
    entry = _apply(mutations.edit_edges, req.action, req.subj, req.pred, req.obj, req.comment)
    return {"ok": True, "entry": entry}


@app.post("/api/nodes/{uuid:path}/drop")
def api_drop(uuid: str):
    entry = _apply(mutations.drop, uuid)
    return {"ok": True, "entry": entry}


# ---------------------------------------------------------------------------
# Journal / undo
# ---------------------------------------------------------------------------

@app.get("/api/journal")
def get_journal():
    return {"session_id": JOURNAL.session_id, "entries": JOURNAL.entries()}


@app.post("/api/undo")
def undo():
    marker = JOURNAL.undo(STORE)
    if marker is None:
        raise HTTPException(status_code=400, detail="nothing to undo")
    STATE["dirty"] = True
    return {"ok": True, "marker": marker}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

@app.post("/api/save")
def save():
    """Layer 2: write the curated deliverable (non-destructive)."""
    nodes_p = RELEASE_DIR / "master_nodes_curated.json"
    edges_p = RELEASE_DIR / "master_edges_curated.json"
    dict_p = RELEASE_DIR / "dictionary_curated.json"
    nodes_p.write_text(json.dumps(STORE.nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    edges_p.write_text(json.dumps(STORE.edges, ensure_ascii=False, indent=2), encoding="utf-8")
    dict_p.write_text(json.dumps({"nodes": STORE.nodes, "edges": STORE.edges}, ensure_ascii=False, indent=2), encoding="utf-8")
    STATE["dirty"] = False
    return {"ok": True, "nodes": str(nodes_p), "edges": str(edges_p), "dictionary": str(dict_p),
            "n_nodes": len(STORE.nodes), "n_edges": len(STORE.edges)}


@app.post("/api/sync-sources")
def sync():
    """Layer 3: make changes durable in the resolved layer + overrides file."""
    stats = sync_to_sources(STORE, JOURNAL.effective_entries())
    return {"ok": True, "stats": stats}


@app.post("/api/publish")
def publish(run_tsv: bool = True, refresh_eog: bool = False):
    """Write timestamped release files from the curated state, then rebuild the
    reviewer TSV. By default EoG sentences are PRESERVED from the existing TSV
    (no OpenAI calls); pass refresh_eog=true only to fetch sentences for new
    nodes."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (RELEASE_DIR / f"master_nodes_{ts}.json").write_text(json.dumps(STORE.nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    (RELEASE_DIR / f"master_edges_{ts}.json").write_text(json.dumps(STORE.edges, ensure_ascii=False, indent=2), encoding="utf-8")
    (RELEASE_DIR / f"dictionary_{ts}.json").write_text(json.dumps({"nodes": STORE.nodes, "edges": STORE.edges}, ensure_ascii=False, indent=2), encoding="utf-8")
    # Keep the "current" pointer unambiguous: refresh the curated copy too.
    (RELEASE_DIR / "master_nodes_curated.json").write_text(json.dumps(STORE.nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    (RELEASE_DIR / "master_edges_curated.json").write_text(json.dumps(STORE.edges, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {"ok": True, "timestamp": ts}
    if run_tsv:
        cmd = [GLY_PY, "scripts/build_bgsl_tsv.py"]
        if refresh_eog:
            cmd.append("--refresh-eog")
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        result["tsv_returncode"] = proc.returncode
        result["tsv_tail"] = (proc.stdout or proc.stderr or "")[-800:]
    return result


# ---------------------------------------------------------------------------
# Static frontend (mounted last so /api/* wins)
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
