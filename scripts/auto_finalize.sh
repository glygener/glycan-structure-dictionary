#!/usr/bin/env bash
# Wait for resolver sweep to finish, then run the patch + postprocess + audit.
# Safe to invoke at any time — it short-circuits if the sweep is still running.

set -e

ROOT=/Users/cyrusay/Desktop/github_repo/gsd_v3
PY=/Users/cyrusay/anaconda3/envs/gly_env/bin/python

if pgrep -f "run_full_sweep" > /dev/null; then
  echo "[wait] resolver sweep is still running — exiting (rerun me when done)"
  $PY $ROOT/scripts/sweep_status.py
  exit 0
fi

cd $ROOT
echo "==> Sweep complete. Finalising release."

# 1. Patch edges
echo ""
echo "------- patch_resolver_edges -------"
$PY scripts/patch_resolver_edges.py

# 2. Dedupe (idempotent)
echo ""
echo "------- dedup_terms -------"
/Users/cyrusay/anaconda3/bin/python3 scripts/dedup_terms.py

# 3. Postprocessing + report
echo ""
echo "------- build_release -------"
$PY scripts/build_release.py

# 4. Dedupe master nodes (catch surface-form duplicates the resolver missed)
echo ""
echo "------- dedup_master_nodes -------"
/Users/cyrusay/anaconda3/bin/python3 scripts/dedup_master_nodes.py

# 5. Audit
echo ""
echo "------- audit -------"
/Users/cyrusay/anaconda3/bin/python3 scripts/audit_release.py
