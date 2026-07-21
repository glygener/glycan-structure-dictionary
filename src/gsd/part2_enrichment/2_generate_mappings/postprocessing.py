"""Post-processing: merge resolved source JSONL files into master node/edge registries.

Pipeline:
  1. Back up existing output files.
  2. Build ordered processing queue from source directories.
  3. Pre-merge quality checks (mandatory fields, UUID formats, duplicates).
  4. Merge terms into master_nodes.json (sequential, source-order priority).
  5. Post-merge quality check.
  6. Merge edges into master_edges.json (supports expanded edge types).
  7. Build final dictionary.json with enriched source metadata.

Usage:
    python postprocessing.py [--inputs-dir PATH] [--output-dir PATH] [--qc-only]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

_PKG_DIR = Path(__file__).resolve().parent
SRC_ROOT = _PKG_DIR.parents[2]  # src/
for _p in (str(SRC_ROOT), str(_PKG_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gsd.config import load_paths_config

from postprocessing_utils import backup_existing_file
from postprocessing_utils import create_processing_queue
from postprocessing_utils import quality_check_jsonl_files
from postprocessing_utils import update_master_registered_terms_file
from postprocessing_utils import post_merge_quality_check
from postprocessing_utils import update_master_registered_edges_file
from postprocessing_utils import build_ontology


# src_eog is the ONLY seed (merged directly from terms.jsonl). All other
# sources go through the resolver and produce terms_resolved.jsonl, which
# postprocessing prefers over terms.jsonl when present.
PROCESSING_ORDER = [
    "src_eog",                         # ONLY seed
    # Tier 1: GSDv1 — rich metadata, first through the resolver
    "src_gsdv1",
    # Tier 2: Other former seeds + well-curated
    "src_n-compo",
    "src_glygen_curators",
    "src_pubdictionaries-glycan-image",
    "src_sugarbind",
    "src_glycoepitope",
    "src_biooligo",
    "src_cummings",
    # Tier 3: Moderate curation
    "src_glycomotif_ggm",
    "src_glycomotif_gdv",
    "src_glycomotif_ccrc",
    "src_pubdict-glycan-motif",
    "src_pubdict-glycosmos",
    "src_pubdict-motifglytoucan",
    # Tier 4: Abbreviation-heavy, lowest priority
    "src_pubdict-glyconavi-name",
    "src_pubdict-glyconavi-abbrev",
]

MANDATORY_FIELDS_TERMS = ["term", "xref", "term_uuid", "src_uuid"]
MANDATORY_FIELDS_EDGES = ["subj", "pred", "obj", "xref"]

# Expanded set of valid edge predicates
VALID_EDGE_PREDICATES = {
    "exact_synonym_of",
    "related_synonym_of",
    "abbreviation_of",
    "is_a",
    "has_related_synonym",  # legacy predicate, still accepted
}


def run_postprocessing(
    inputs_dir: Path | None = None,
    output_dir: Path | None = None,
    qc_only: bool = False,
) -> None:
    """Execute the full post-processing pipeline."""
    paths_cfg = load_paths_config()

    if inputs_dir is None:
        inputs_dir = Path(paths_cfg["data"]["inputs"])
    if output_dir is None:
        output_dir = Path(paths_cfg["outputs"]["releases"]) / "gsd_latest"

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("_%Y%m%d_%H%M%S")

    outf_name_nodes = f"master_nodes{timestamp}.json"
    outf_name_edges = f"master_edges{timestamp}.json"
    outf_name_gsd = f"dictionary{timestamp}.json"

    # Backup existing outputs
    bck_dir = output_dir / "backup" / f"backup{timestamp}"
    bck_dir.mkdir(parents=True, exist_ok=True)

    json_files = list(output_dir.glob("*.json"))
    if json_files:
        for json_file in json_files:
            backup_path = bck_dir / json_file.name
            json_file.rename(backup_path)
            print(f"- Backed up {json_file.name} to {bck_dir.name}/{json_file.name}")

    outf_path_nodes = output_dir / outf_name_nodes
    outf_path_nodes.touch(exist_ok=True)
    outf_path_edges = output_dir / outf_name_edges
    outf_path_edges.touch(exist_ok=True)
    outf_path_gsd = output_dir / outf_name_gsd
    outf_path_gsd.touch(exist_ok=True)

    print("=" * 80 + "\nRunning post-processing pipeline...")
    print(f"Inputs:  {inputs_dir}")
    print(f"Outputs: {output_dir}")

    # Create processing queue
    # Look for both terms.jsonl and terms_resolved.jsonl (from graph.py output)
    processing_queue_terms, processing_queue_edges = create_processing_queue(
        PROCESSING_ORDER, inputs_dir
    )

    # Pre-merge quality checks
    quality_check_jsonl_files(
        processing_queue_terms,
        processing_queue_edges,
        MANDATORY_FIELDS_TERMS,
        MANDATORY_FIELDS_EDGES,
    )

    if qc_only:
        print("\n[QC-ONLY] Quality checks complete. Skipping merge.")
        return

    # Merge terms
    for term_file in processing_queue_terms:
        update_master_registered_terms_file(term_file, outf_path_nodes)

    # Post-merge quality check
    post_merge_quality_check(outf_path_nodes)

    # Merge edges (includes AI-generated edges from resolver + manual edges)
    for edge_file in processing_queue_edges:
        update_master_registered_edges_file(edge_file, outf_path_edges)

    # Build final dictionary
    build_ontology(outf_path_nodes, outf_path_edges, outf_path_gsd, processing_queue_terms)

    print(f"\n{'='*80}")
    print("Post-processing complete.")
    print(f"  Nodes: {outf_path_nodes}")
    print(f"  Edges: {outf_path_edges}")
    print(f"  Dictionary: {outf_path_gsd}")
    print("=" * 80)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge resolved source JSONL files into master node/edge registries."
    )
    parser.add_argument(
        "--inputs-dir",
        type=Path,
        default=None,
        help="Directory containing source subdirectories (default: from paths.yaml).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for master files (default: data/outputs/releases/gsd_latest).",
    )
    parser.add_argument(
        "--qc-only",
        action="store_true",
        help="Run quality checks only, skip merge.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_postprocessing(
        inputs_dir=args.inputs_dir,
        output_dir=args.output_dir,
        qc_only=args.qc_only,
    )