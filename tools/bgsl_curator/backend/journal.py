"""Append-only curation journal + transactional in-memory undo.

Every mutating API call follows:

    snap = journal.begin(store)        # deep-copy nodes+edges
    try:
        entry = mutations.<op>(...)    # mutate the live working copy
    except Exception:
        journal.rollback(store, snap)  # restore, discard
        raise
    stamped = journal.commit(store, snap, entry)  # push undo + append log

``commit`` writes one stamped line to ``sessions/<id>/curation_log.jsonl``
(the canonical, replayable audit record). ``undo`` pops the last snapshot,
restores the store, and appends an ``{op:"undo"}`` marker (the log stays
append-only).
"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"


class Journal:
    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = SESSIONS_DIR / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.session_dir / "curation_log.jsonl"
        self.log_path.touch(exist_ok=True)
        self._seq = self._last_seq()
        # undo stack: list of (seq, nodes_snapshot, edges_snapshot)
        self._undo: list[tuple[int, list, list]] = []

    def _last_seq(self) -> int:
        seq = 0
        if self.log_path.exists():
            for line in self.log_path.open(encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                try:
                    seq = max(seq, json.loads(line).get("seq", 0))
                except json.JSONDecodeError:
                    pass
        return seq

    # ------------------------------------------------------------------

    def begin(self, store) -> dict:
        return {
            "nodes": copy.deepcopy(store.nodes),
            "edges": copy.deepcopy(store.edges),
        }

    def rollback(self, store, snap: dict) -> None:
        store.nodes = snap["nodes"]
        store.edges = snap["edges"]
        store.reindex()

    def commit(self, store, snap: dict, entry: dict) -> dict:
        self._seq += 1
        stamped = {"seq": self._seq, "ts": datetime.now().isoformat(timespec="seconds"), **entry}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(stamped, ensure_ascii=False) + "\n")
        self._undo.append((self._seq, snap["nodes"], snap["edges"]))
        return stamped

    def undo(self, store) -> dict | None:
        if not self._undo:
            return None
        seq, nodes, edges = self._undo.pop()
        store.nodes = nodes
        store.edges = edges
        store.reindex()
        self._seq += 1
        marker = {"seq": self._seq, "ts": datetime.now().isoformat(timespec="seconds"),
                  "op": "undo", "undoes_seq": seq}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(marker, ensure_ascii=False) + "\n")
        return marker

    def entries(self) -> list[dict]:
        out: list[dict] = []
        for line in self.log_path.open(encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return out

    def effective_entries(self) -> list[dict]:
        """Entries with undone ops removed (for replay / propagation)."""
        all_e = self.entries()
        undone = {e["undoes_seq"] for e in all_e if e.get("op") == "undo"}
        return [e for e in all_e if e.get("op") != "undo" and e.get("seq") not in undone]
