"""Build the gsd_v2.0.0-draft release from all sources.

Wraps the existing postprocessing pipeline, but writes the master files to
`data/outputs/releases/gsd_v2.0.0-draft/` (instead of `gsd_latest`) and emits
a RUN_REPORT.md summarising the run.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/cyrusay/Desktop/github_repo/gsd_v3")
RELEASE_DIR = ROOT / "data" / "outputs" / "releases" / "gsd_v2.0.0-draft"
INPUTS = ROOT / "data" / "inputs"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "gsd" / "part2_enrichment" / "2_generate_mappings"))

from postprocessing import run_postprocessing  # type: ignore


def write_run_report() -> None:
    nodes_files = sorted(RELEASE_DIR.glob("master_nodes_*.json"))
    edges_files = sorted(RELEASE_DIR.glob("master_edges_*.json"))
    dict_files = sorted(RELEASE_DIR.glob("dictionary_*.json"))

    nodes_f = nodes_files[-1] if nodes_files else None
    edges_f = edges_files[-1] if edges_files else None
    dict_f = dict_files[-1] if dict_files else None

    nodes = json.loads(nodes_f.read_text()) if nodes_f else []
    edges = json.loads(edges_f.read_text()) if edges_f else []

    # GTC coverage
    with_gtc = sum(1 for n in nodes if n.get("gtc_id"))
    without_gtc = len(nodes) - with_gtc
    # source counts
    src_counts: dict[str, int] = {}
    for n in nodes:
        for s in n.get("sources", []):
            src = s.get("src", "?")
            src_counts[src] = src_counts.get(src, 0) + 1

    # edge type counts
    edge_types: dict[str, int] = {}
    for e in edges:
        pred = e.get("pred", "?")
        edge_types[pred] = edge_types.get(pred, 0) + 1

    # qc report
    qc_path = RELEASE_DIR / "qc_report.json"
    qc = json.loads(qc_path.read_text()) if qc_path.exists() else []
    total_dropped = sum(r.get("dropped", 0) for r in qc)

    report_lines = [
        "# GSD v2.0.0-draft — Run Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Summary",
        f"- Total nodes:      **{len(nodes)}**",
        f"- Nodes with GTC ID: **{with_gtc}** ({with_gtc*100//max(1,len(nodes))}%)",
        f"- Nodes without GTC: {without_gtc}",
        f"- Total edges:       **{len(edges)}**",
        f"- QC-dropped terms (synthetic glycans):  {total_dropped}",
        "",
        "## Source coverage (count of nodes referencing each source)",
    ]
    for src, c in sorted(src_counts.items(), key=lambda x: -x[1]):
        report_lines.append(f"- `{src}`: {c}")

    report_lines += [
        "",
        "## Edge predicates",
    ]
    for pred, c in sorted(edge_types.items(), key=lambda x: -x[1]):
        report_lines.append(f"- `{pred}`: {c}")

    report_lines += [
        "",
        "## Files",
        f"- master nodes:  `{nodes_f.name if nodes_f else 'MISSING'}`",
        f"- master edges:  `{edges_f.name if edges_f else 'MISSING'}`",
        f"- dictionary:    `{dict_f.name if dict_f else 'MISSING'}`",
        f"- qc report:     `qc_report.json`",
        "",
        "## Pipeline changes vs. previous release",
        "- Replaced `search_pubmed` lookup tool with `query_textbook` (RAG over Essentials of Glycobiology 4e).",
        "- Pre-split `src_gsdv1` synonyms based on `edges.jsonl` `has_related_synonym` relations (e.g. `CA19-9` is now a separate node from `sialyl Lewis a`).",
        "- Seed vector store from src_gsdv1 + curated src_eog/src_n-compo/src_pubdictionaries-glycan-image (623 unique terms).",
        "- New sources scraped and normalised:",
        "  - GlycoMotif GGM (185), GDV (126), CCRC (116)",
        "  - Pubdictionaries glyconavi-name (468 raw / 232 unique), glyconavi-abbrev (104 raw / 95 unique)",
        "- New sources promoted from `some_other_resouces/`:",
        "  - GlycoEpitope (173), BioOligo (254), SugarBind (204), Cummings (117)",
        "  - Pubdict glycan-motif (504), glycosmos (218), motifglytoucan (67)",
        "- Resolver fast-paths added: shared GlyTouCan ID, normalised surface-form match.",
        "- Drop filter: regex flags fluorinated/synthetic/labelled glycans (6 dropped from glyconavi).",
        "- **`keep` flag**: every row in `src_*/terms.jsonl` carries a top-level `keep: true` boolean. Reviewer flips it to `false` on rows they want omitted from the final release; postprocessing filters them out before building master nodes/edges and drops any orphan edges that referenced them.",
        "- **GlycoMotif Name/Keyword separation**: the GlycoMotif scrape originally merged `Name(s)` and `Keyword(s)` into a single `aliases` column, polluting `exact_synonyms` with classification keywords (e.g. 'Glycolipid', 'Trisialylated ganglioside'). The v2 scrape keeps them as separate columns; this correction was applied to `terms.jsonl` in place, preserving `term_uuid`/`src_uuid` so the sweep did NOT need to re-run.",
        "",
    ]
    (RELEASE_DIR / "RUN_REPORT.md").write_text("\n".join(report_lines))
    print(f"\n[REPORT] -> {RELEASE_DIR / 'RUN_REPORT.md'}")


def main() -> None:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    run_postprocessing(inputs_dir=INPUTS, output_dir=RELEASE_DIR, qc_only=False)

    # Iterative dedup of master_nodes (collapses surface-form duplicates that
    # the resolver missed due to short-abbreviation embedding limits).
    import subprocess
    print("\n" + "=" * 80 + "\nIterative deduplication of master_nodes")
    print("=" * 80)
    subprocess.run(
        ["/Users/cyrusay/anaconda3/bin/python3", str(ROOT / "scripts" / "dedup_master_nodes.py")],
        check=False,
    )

    write_run_report()


if __name__ == "__main__":
    main()
