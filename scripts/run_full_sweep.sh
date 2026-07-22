#!/usr/bin/env bash
# Run entity resolution against the seeded GSD vector store for every
# non-seed source. Only src_eog is the seed (merged directly via
# postprocessing). All other sources — including src_gsdv1 — go through
# the resolver and receive fresh UUIDs.
#
# Incremental: each resolved source's new nodes are persisted to Chroma,
# so the next source benefits from all previously-resolved terms.

set -e

source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
cd "$ROOT"

SCRIPT="src/gsd/part2_enrichment/1_ai-assisted_term_matching/graph.py"
LOG_DIR=data/workspace/resolver_runs
mkdir -p "$LOG_DIR"

NEW_SOURCES=(
  # Tier 1: GSDv1 — rich metadata, first through the resolver
  "src_gsdv1"
  # Tier 2: Other former seeds + well-curated
  "src_n-compo"
  "src_glygen_curators"
  "src_pubdictionaries-glycan-image"
  "src_sugarbind"
  "src_glycoepitope"
  "src_biooligo"
  "src_cummings"
  # Tier 3: Moderate curation
  "src_glycomotif_ggm"
  "src_glycomotif_gdv"
  "src_glycomotif_ccrc"
  "src_pubdict-glycan-motif"
  "src_pubdict-glycosmos"
  "src_pubdict-motifglytoucan"
  # Tier 4: Abbreviation-heavy, lowest priority
  "src_pubdict-glyconavi-name"
  "src_pubdict-glyconavi-abbrev"
)

INPUTS=data/inputs

for src in "${NEW_SOURCES[@]}"; do
  # Skip if already fully resolved (terms_resolved.jsonl line count >= terms.jsonl line count)
  if [ -f "$INPUTS/$src/terms_resolved.jsonl" ] && [ -f "$INPUTS/$src/terms.jsonl" ]; then
    r=$(wc -l < "$INPUTS/$src/terms_resolved.jsonl")
    t=$(wc -l < "$INPUTS/$src/terms.jsonl")
    if [ "$r" -ge "$t" ] && [ "$t" -gt 0 ]; then
      echo "[SKIP] $src already resolved ($r/$t rows)"
      continue
    fi
  fi
  echo "=========================================="
  echo "Resolving $src"
  echo "=========================================="
  log="$LOG_DIR/${src}.log"
  "$PY" "$SCRIPT" --source "$src" > "$log" 2>&1 || echo "[WARN] $src exited non-zero"
  tail -8 "$log"
  echo "  -> log: $log"
done

echo "ALL DONE"
