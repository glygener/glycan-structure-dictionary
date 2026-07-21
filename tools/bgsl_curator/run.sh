#!/usr/bin/env bash
# Launch the bGSL Curator GUI. Open http://localhost:8765 afterwards.
set -e
PY=/Users/cyrusay/anaconda3/envs/gly_env/bin/python
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
exec "$PY" -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 "$@"
