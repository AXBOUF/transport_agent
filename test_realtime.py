from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

APPS = [
    ("sydneytrains", ROOT / "realtime" / "sydneytrains" / "app.py"),
    ("metro",        ROOT / "realtime" / "metro"        / "app.py"),
]


def init_schema() -> bool:
    print("── Initialising realtime schema ─────────────────────")
    result = subprocess.run(
        [sys.executable, ROOT / "realtime" / "pg_schema.py"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("✗ pg_schema.py failed — check your .env and database connection")
        return False
    print()
    return True


def start_apps() -> list[tuple[str, subprocess.Popen]]:
    print("── Starting realtime schedulers ─────────────────────")
    procs: list[tuple[str, subprocess.Popen]] = []
    for name, path in APPS:
        proc = subprocess.Popen(
            [sys.executable, path],
            cwd=path.parent,
        )
        print(f"  ✓ {name:<16} PID {proc.pid}")
        procs.append((name, proc))
    return procs


def monitor(procs: list[tuple[str, subprocess.Popen]]) -> None:
    print()
    print("── Running — press Ctrl+C to stop all ──────────────")
    try:
        while True:
            for name, proc in procs:
                if proc.poll() is not None:
                    print(f"  ✗ {name} exited unexpectedly (code {proc.returncode})")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n── Shutting down ────────────────────────────────────")
        for name, proc in procs:
            proc.terminate()
            print(f"  stopped {name}")
        for _, proc in procs:
            proc.wait()
        print("Done")


def main() -> None:
    if not init_schema():
        sys.exit(1)
    procs = start_apps()
    monitor(procs)


if __name__ == "__main__":
    main()
