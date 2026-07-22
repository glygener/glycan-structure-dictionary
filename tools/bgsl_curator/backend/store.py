"""DataStore — the in-memory working copy of the bGSL release plus the
read-only provenance index used by the curator GUI.

Responsibilities
----------------
* Locate the *current* release files (prefer ``*_curated.json`` if a prior
  session saved one, else the newest timestamped ``master_nodes_*.json``).
* Hold ``nodes`` and ``edges`` as the live, mutable working copy the API
  edits in place.
* Build two indexes:
    - ``node_index``  : term_uuid -> node dict
    - ``src_index``   : src_uuid  -> {source_dir, resolved_row, ai_decision}
  The src_index lets the detail view show, per source row, the original
  resolved metadata and the LLM's mapping rationale, and lets the
  write-back layer (propagate.py) find which file to edit.

Seed sources (e.g. src_eog) have only ``terms.jsonl`` — no
``terms_resolved.jsonl`` / ``terms_ai-decisions.jsonl``. Those rows are
still indexed (resolved_row from terms.jsonl, ai_decision = None).
"""

from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]  # backend -> bgsl_curator -> tools -> repo root
RELEASE_DIR = ROOT / "data" / "outputs" / "releases" / "gsd_v2.0.0-draft"
INPUTS = ROOT / "data" / "inputs"


def _latest(glob_pattern: str) -> Path | None:
    matches = sorted(glob.glob(glob_pattern))
    return Path(matches[-1]) if matches else None


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


class DataStore:
    def __init__(self, release_dir: Path = RELEASE_DIR, inputs_dir: Path = INPUTS):
        self.release_dir = release_dir
        self.inputs_dir = inputs_dir

        self.nodes_path = self._resolve_nodes_path()
        self.edges_path = self._resolve_edges_path()

        self.nodes: list[dict] = json.loads(self.nodes_path.read_text()) if self.nodes_path else []
        self.edges: list[dict] = json.loads(self.edges_path.read_text()) if self.edges_path else []

        trace_path = release_dir / "review" / "node_trace_map.json"
        self.trace_map: dict[str, Any] = json.loads(trace_path.read_text()) if trace_path.exists() else {}

        self.node_index: dict[str, dict] = {}
        self.src_index: dict[str, dict] = {}
        self.reindex()
        self._build_src_index()

    # ------------------------------------------------------------------
    # Release-file resolution
    # ------------------------------------------------------------------

    def _resolve_nodes_path(self) -> Path | None:
        curated = self.release_dir / "master_nodes_curated.json"
        if curated.exists():
            return curated
        return _latest(str(self.release_dir / "master_nodes_*.json"))

    def _resolve_edges_path(self) -> Path | None:
        curated = self.release_dir / "master_edges_curated.json"
        if curated.exists():
            return curated
        return _latest(str(self.release_dir / "master_edges_*.json"))

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    def reindex(self) -> None:
        """Rebuild node_index from the live nodes list. Call after any mutation
        that adds/removes nodes."""
        self.node_index = {n["term_uuid"]: n for n in self.nodes if n.get("term_uuid")}

    def _build_src_index(self) -> None:
        """Scan every src_*/ dir once. Map each src_uuid to its source dir, its
        resolved row, and its ai-decision row (if any)."""
        self.src_index = {}
        for src_dir in sorted(self.inputs_dir.glob("src_*")):
            resolved_f = src_dir / "terms_resolved.jsonl"
            terms_f = src_dir / "terms.jsonl"
            # Seeds have only terms.jsonl; sweep sources have terms_resolved.jsonl
            primary = resolved_f if resolved_f.exists() else terms_f
            rows = _read_jsonl(primary)
            decisions = {
                d.get("src_uuid"): d
                for d in _read_jsonl(src_dir / "terms_ai-decisions.jsonl")
                if d.get("src_uuid")
            }
            for row in rows:
                su = row.get("src_uuid")
                if not su:
                    continue
                self.src_index[su] = {
                    "source_dir": src_dir.name,
                    "resolved_file": primary.name,
                    "resolved_row": row,
                    "ai_decision": decisions.get(su),
                }

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_node(self, uuid: str) -> dict | None:
        return self.node_index.get(uuid)

    def edges_for(self, uuid: str) -> list[dict]:
        return [e for e in self.edges if e.get("subj") == uuid or e.get("obj") == uuid]

    def provenance(self, node: dict) -> list[dict]:
        """For each source row of a node, attach its resolved metadata + the
        LLM ai-decision (action / edge_type / rationale)."""
        out: list[dict] = []
        for s in node.get("sources", []):
            su = s.get("src_uuid")
            idx = self.src_index.get(su, {})
            ai = idx.get("ai_decision") or {}
            resolved = idx.get("resolved_row") or {}
            out.append({
                "src": s.get("src"),
                "src_lbl": s.get("src_lbl"),
                "src_uuid": su,
                "source_dir": idx.get("source_dir"),
                "action": ai.get("action"),
                "edge_type": ai.get("edge_type"),
                "rationale": ai.get("rationale"),
                "raw_term": (resolved.get("metadata") or {}).get("raw_term"),
            })
        return out

    # ------------------------------------------------------------------
    # Summaries for the table view
    # ------------------------------------------------------------------

    def node_summary(self, node: dict) -> dict:
        uuid = node.get("term_uuid", "")
        return {
            "term_uuid": uuid,
            "lbl": node.get("lbl", ""),
            "classification": node.get("classification", ""),
            "n_sources": len(node.get("sources", []) or []),
            "n_exact": len(node.get("exact_synonyms", []) or []),
            "n_abbr": len(node.get("abbreviations", []) or []),
            "n_gtc": len(node.get("gtc_id", []) or []),
            "has_edges": bool(self.edges_for(uuid)),
            "merged_from": node.get("merged_from_term_uuids", []) or [],
            "split_from": node.get("split_from_term_uuid"),
        }
