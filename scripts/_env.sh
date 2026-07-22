# Shared environment resolution for the bGSL pipeline scripts.
# Not executed directly — source it from a script in scripts/ with:
#     source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
#
# Sets:
#   ROOT  repo root (derived from this file's location, so no absolute paths)
#   PY    a usable Python interpreter
#
# Interpreter priority:
#   1. $BGSL_PY                        (explicit override)
#   2. the gly_env conda env           ($HOME/anaconda3/envs/gly_env)
#   3. the currently-active conda env  ($CONDA_PREFIX)
#   4. python3 / python on PATH
# The picked interpreter still needs the pipeline deps (see requirements.txt);
# the underlying Python scripts report a clear ImportError if it doesn't.

# Repo root = parent of the scripts/ dir this helper lives in.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

_bgsl_pick_python() {
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

if ! PY="$(_bgsl_pick_python)"; then
  echo "[bGSL] No Python interpreter found. Set BGSL_PY=/path/to/python and retry." >&2
  exit 1
fi
