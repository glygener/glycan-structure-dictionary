#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

RUNTIME_DIR = Path.home() / ".cache" / "gsd" / "ollama"
PID_FILE = RUNTIME_DIR / "ollama.pid"
META_FILE = RUNTIME_DIR / "ollama.meta.json"


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main() -> int:
    if not PID_FILE.exists():
        print("Ollama is not running.")
        return 1

    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        print("Invalid PID file.")
        return 1

    if not is_pid_running(pid):
        print(f"Ollama is not running (stale PID {pid}).")
        return 1

    print(f"Ollama is running (PID {pid}).")
    if META_FILE.exists():
        try:
            meta = json.loads(META_FILE.read_text(encoding="utf-8"))
            if "host" in meta:
                print(f"Host: {meta['host']}")
            if "log_file" in meta:
                print(f"Log:  {meta['log_file']}")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())