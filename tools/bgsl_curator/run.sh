#!/usr/bin/env bash
# Launch the bGSL Curator GUI, then open http://localhost:8765
#
# Picks a Python interpreter in priority order:
#   1. $BGSL_PY                        (explicit override)
#   2. the gly_env conda env           ($HOME/anaconda3/envs/gly_env)
#   3. the currently-active conda env  ($CONDA_PREFIX)
#   4. python3 / python on PATH
# and fails with a clear message if the chosen interpreter lacks the deps.
#
# Env overrides: BGSL_PY, BGSL_HOST (default 127.0.0.1), BGSL_PORT (default 8765).
# Extra args are passed through to uvicorn, e.g.  bash run.sh --reload
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

HOST="${BGSL_HOST:-127.0.0.1}"
PORT="${BGSL_PORT:-8765}"

pick_python() {
  local candidates=() py
  [ -n "${BGSL_PY:-}" ]      && candidates+=("$BGSL_PY")
  candidates+=("$HOME/anaconda3/envs/gly_env/bin/python")
  [ -n "${CONDA_PREFIX:-}" ] && candidates+=("$CONDA_PREFIX/bin/python")
  candidates+=("$(command -v python3 || true)" "$(command -v python || true)")
  for py in "${candidates[@]}"; do
    [ -n "$py" ] && [ -x "$py" ] && { printf '%s\n' "$py"; return 0; }
  done
  return 1
}

if ! PY="$(pick_python)"; then
  echo "[bGSL] No Python interpreter found. Set BGSL_PY=/path/to/python and retry." >&2
  exit 1
fi

# The chosen interpreter must have the curator's runtime deps.
if ! "$PY" -c 'import uvicorn, fastapi, pydantic' >/dev/null 2>&1; then
  echo "[bGSL] '$PY' is missing the curator dependencies (fastapi, uvicorn, pydantic)." >&2
  echo "       Install them into that environment with:" >&2
  echo "         \"$PY\" -m pip install -r \"$HERE/requirements.txt\"" >&2
  echo "       Or point BGSL_PY at an environment that already has them." >&2
  exit 1
fi

echo "[bGSL] Using interpreter: $PY"
echo "[bGSL] Serving on http://$HOST:$PORT  (Ctrl+C to stop)"
exec "$PY" -m uvicorn backend.app:app --host "$HOST" --port "$PORT" "$@"
