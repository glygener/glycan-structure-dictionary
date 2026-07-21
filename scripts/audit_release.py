"""Quick audit of the gsd_v2.0.0-draft release."""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path("/Users/cyrusay/Desktop/github_repo/gsd_v3")
RELEASE_DIR = ROOT / "data" / "outputs" / "releases" / "gsd_v2.0.0-draft"


def main() -> None:
    nodes_files = sorted(RELEASE_DIR.glob("master_nodes_*.json"))
    edges_files = sorted(RELEASE_DIR.glob("master_edges_*.json"))
    dict_files = sorted(RELEASE_DIR.glob("dictionary_*.json"))
    if not nodes_files:
        print("[ERR] No master_nodes file in release dir.")
        return

    nodes = json.loads(nodes_files[-1].read_text())
    edges = json.loads(edges_files[-1].read_text()) if edges_files else []

    n_total = len(nodes)
    with_gtc = sum(1 for n in nodes if n.get("gtc_id"))
    n_sources_per_node = [len(n.get("sources", [])) for n in nodes]
    multi_source = sum(1 for c in n_sources_per_node if c > 1)

    print("=" * 60)
    print(f"Release: gsd_v2.0.0-draft")
    print(f"  master_nodes  : {nodes_files[-1].name} ({n_total} nodes)")
    print(f"  master_edges  : {edges_files[-1].name if edges_files else '-'} ({len(edges)} edges)")
    print(f"  dictionary    : {dict_files[-1].name if dict_files else '-'}")
    print("-" * 60)
    print(f"  Nodes with gtc_id   : {with_gtc} ({with_gtc * 100 // max(1, n_total)}%)")
    print(f"  Nodes with >=2 srcs : {multi_source}")
    print(f"  Avg sources/node    : {sum(n_sources_per_node)/max(1,n_total):.2f}")
    print("-" * 60)

    # Random 10 sample
    sample = random.sample(nodes, min(10, n_total))
    print("\nRandom sample (10 nodes):")
    for n in sample:
        gtc = n.get("gtc_id") or []
        sources = [s.get("src", "?") for s in n.get("sources", [])]
        print(
            f"  - {n.get('lbl', '?'):40s}  "
            f"gtc={','.join(gtc) or '-':14s}  "
            f"sources=({len(sources)}) {','.join(sources[:3])}"
            + ("..." if len(sources) > 3 else "")
        )

    # CA19-9 / sialyl Lewis a sanity check
    print("\nSeparation check (CA19-9 vs sialyl Lewis a):")
    for n in nodes:
        lbl = n.get("lbl", "").lower()
        if "ca19" in lbl.replace("-", "").replace(" ", "") or "sialyl lewis a" in lbl:
            print(f"  - {n.get('lbl')}  ({n.get('term_uuid')})  gtc={n.get('gtc_id') or '-'}")

    print("=" * 60)


if __name__ == "__main__":
    main()
