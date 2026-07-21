"""Quick status of the resolver sweep — count completed sources and decisions."""

import json
from pathlib import Path

ROOT = Path("/Users/cyrusay/Desktop/github_repo/gsd_v3")
INPUTS = ROOT / "data" / "inputs"

NEW_SOURCES = [
    "src_pubdict-motifglytoucan",
    "src_pubdict-glycosmos",
    "src_pubdict-glycan-motif",
    "src_glycomotif_ggm",
    "src_glycomotif_gdv",
    "src_glycomotif_ccrc",
    "src_glycoepitope",
    "src_sugarbind",
    "src_biooligo",
    "src_cummings",
    "src_pubdict-glyconavi-name",
    "src_pubdict-glyconavi-abbrev",
]


def main() -> None:
    print("Resolver sweep status")
    print("=" * 70)
    total_decided = 0
    total_terms = 0
    finished = 0
    for src in NEW_SOURCES:
        d = INPUTS / src
        terms_f = d / "terms.jsonl"
        decisions_f = d / "terms_ai-decisions.jsonl"
        resolved_f = d / "terms_resolved.jsonl"
        n_terms = sum(1 for _ in terms_f.open()) if terms_f.exists() else 0
        n_decisions = sum(1 for _ in decisions_f.open()) if decisions_f.exists() else 0
        n_resolved = sum(1 for _ in resolved_f.open()) if resolved_f.exists() else 0
        complete = "DONE" if n_resolved >= n_terms and n_terms > 0 else f"{n_decisions}/{n_terms}"
        if complete == "DONE":
            finished += 1
        total_decided += n_decisions
        total_terms += n_terms
        print(f"  [{src:35s}]  {complete:>12s}  resolved_rows={n_resolved}")
    print("=" * 70)
    print(f"Finished sources: {finished}/{len(NEW_SOURCES)}")
    print(f"Decisions logged: {total_decided}/{total_terms}")


if __name__ == "__main__":
    main()
