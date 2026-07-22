#!/usr/bin/env bash
# Run after the full sweep completes. Patches edges, runs postprocessing,
# produces RUN_REPORT.md, and prints a one-line audit summary.

set -e

source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
RELEASE_DIR="$ROOT/data/outputs/releases/gsd_v2.0.0-draft"

echo "=========================================="
echo "  Stage 1: Patch resolver-emitted edges"
echo "=========================================="
"$PY" "$ROOT/scripts/patch_resolver_edges.py"

echo ""
echo "=========================================="
echo "  Stage 2: Build release"
echo "=========================================="
"$PY" "$ROOT/scripts/build_release.py"

echo ""
echo "=========================================="
echo "  Stage 3: Final audit"
echo "=========================================="
"$PY" "$ROOT/scripts/audit_release.py"

echo ""
echo "Release ready at: $RELEASE_DIR"
echo "DONE."
