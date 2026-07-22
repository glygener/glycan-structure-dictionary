"""De-duplicate each src_*/terms.jsonl by term_uuid.

When two rows share the same term_uuid (a true duplicate or a normaliser
collision), merge them into one: union of `exact_synonyms`, `gtc_id`, and
`db_xref`; first non-empty value of everything else; keep the FIRST src_uuid.

After this pass every terms.jsonl has unique term_uuids, which is required by
the postprocessing QC.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import OrderedDict

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "data" / "inputs"

LIST_FIELDS = {"exact_synonyms", "gtc_id", "db_xref", "publication"}


def merge_metadata(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        if v in (None, "", []):
            continue
        cur = out.get(k)
        if cur in (None, ""):
            out[k] = v
            continue
        if k in LIST_FIELDS:
            cur_list = list(cur) if isinstance(cur, list) else [cur]
            new_list = list(v) if isinstance(v, list) else [v]
            for nv in new_list:
                if nv not in cur_list:
                    cur_list.append(nv)
            out[k] = cur_list
    return out


def dedupe(path: Path) -> dict:
    rows = []
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))

    merged: dict[str, dict] = OrderedDict()
    for row in rows:
        uid = row["term_uuid"]
        if uid not in merged:
            merged[uid] = row
            continue
        existing = merged[uid]
        # union metadata
        existing["metadata"] = merge_metadata(
            existing.get("metadata") or {}, row.get("metadata") or {}
        )

    with path.open("w", encoding="utf-8") as f:
        for r in merged.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return {"path": path.parent.name, "rows_in": len(rows), "rows_out": len(merged)}


def main() -> None:
    print("=" * 70)
    print("De-duplicating terms.jsonl by term_uuid")
    print("=" * 70)
    for src in sorted(INPUTS.glob("src_*")):
        f = src / "terms.jsonl"
        if not f.exists():
            continue
        # Skip files that the resolver owns (terms_resolved.jsonl will be merged into master)
        r = dedupe(f)
        if r["rows_in"] != r["rows_out"]:
            print(f"  [{r['path']:35s}]  {r['rows_in']:>4d} -> {r['rows_out']:>4d}  (-{r['rows_in']-r['rows_out']})")
    print("=" * 70)


if __name__ == "__main__":
    main()
