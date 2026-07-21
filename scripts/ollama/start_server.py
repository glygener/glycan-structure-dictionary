#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import yaml

OLLAMA_YAML = Path(__file__).resolve().parents[2] / "configs" / "ollama.yaml"


RUNTIME_DIR = Path.home() / ".cache" / "gsd" / "ollama"
PID_FILE = RUNTIME_DIR / "ollama.pid"
META_FILE = RUNTIME_DIR / "ollama.meta.json"
LOG_FILE = RUNTIME_DIR / "ollama.log"


def load_config() -> dict:
    with OLLAMA_YAML.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def normalize_host(raw_host: str) -> tuple[str, str]:
    host = raw_host.strip()
    host_no_scheme = re.sub(r"^https?://", "", host)
    if ":" not in host_no_scheme:
        raise ValueError(f"Host must include port, got: {raw_host}")
    return host_no_scheme, f"http://{host_no_scheme}"


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_existing_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None
    return pid if pid > 0 else None


def cleanup_stale_pidfile() -> None:
    pid = read_existing_pid()
    if pid is None:
        PID_FILE.unlink(missing_ok=True)
        META_FILE.unlink(missing_ok=True)
        return
    if not is_pid_running(pid):
        PID_FILE.unlink(missing_ok=True)
        META_FILE.unlink(missing_ok=True)


def wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_stale_pidfile()

    existing_pid = read_existing_pid()
    if existing_pid and is_pid_running(existing_pid):
        print(f"Ollama already running (PID {existing_pid})")
        return 0

    cfg = load_config()
    host_env, host_url = normalize_host(cfg.get("host", "http://localhost:11434"))
    bind_host, bind_port_str = host_env.rsplit(":", 1)
    bind_port = int(bind_port_str)

    env = os.environ.copy()
    env["OLLAMA_HOST"] = host_env
    env["OLLAMA_FLASH_ATTENTION"] = "1" if cfg.get("ollama_flash_attention", False) else "0"
    env["OLLAMA_MAX_LOADED_MODELS"] = str(cfg.get("ollama_max_loaded_models", 2))
    env["OLLAMA_KEEP_ALIVE"] = str(cfg.get("ollama_keep_alive", "10m"))
    env["OLLAMA_CONTEXT_LENGTH"] = str(cfg.get("ollama_context_length", 16384))

    with LOG_FILE.open("ab") as log_fh:
        proc = subprocess.Popen(
            ["ollama", "serve"],
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,  # new process group/session
        )

    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    META_FILE.write_text(
        json.dumps(
            {
                "pid": proc.pid,
                "host": host_url,
                "bind_host": bind_host,
                "bind_port": bind_port,
                "log_file": str(LOG_FILE),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if wait_for_port(bind_host, bind_port, timeout=15.0):
        print(f"Ollama started (PID {proc.pid})")
        print(f"Host: {host_url}")
        print(f"Log:  {LOG_FILE}")
        return 0

    if is_pid_running(proc.pid):
        os.killpg(proc.pid, signal.SIGTERM)
        time.sleep(1)
        if is_pid_running(proc.pid):
            os.killpg(proc.pid, signal.SIGKILL)

    PID_FILE.unlink(missing_ok=True)
    META_FILE.unlink(missing_ok=True)
    print("Failed to start Ollama. Check log:", LOG_FILE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())