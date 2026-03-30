#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import time
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


def read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        return pid if pid > 0 else None
    except Exception:
        return None


def main() -> int:
    pid = read_pid()
    if pid is None:
        print("No PID file found. Ollama is likely not running.")
        PID_FILE.unlink(missing_ok=True)
        META_FILE.unlink(missing_ok=True)
        return 0

    if not is_pid_running(pid):
        print(f"Stale PID file found for PID {pid}. Cleaning up.")
        PID_FILE.unlink(missing_ok=True)
        META_FILE.unlink(missing_ok=True)
        return 0

    print(f"Stopping Ollama process group led by PID {pid} ...")
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        META_FILE.unlink(missing_ok=True)
        print("Process group already gone.")
        return 0

    deadline = time.time() + 15
    while time.time() < deadline:
        if not is_pid_running(pid):
            PID_FILE.unlink(missing_ok=True)
            META_FILE.unlink(missing_ok=True)
            print("Ollama stopped.")
            return 0
        time.sleep(0.5)

    print("Graceful stop timed out. Sending SIGKILL ...")
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    deadline = time.time() + 5
    while time.time() < deadline:
        if not is_pid_running(pid):
            PID_FILE.unlink(missing_ok=True)
            META_FILE.unlink(missing_ok=True)
            print("Ollama force-stopped.")
            return 0
        time.sleep(0.25)

    print("Warning: process may still be alive.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())