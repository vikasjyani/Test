#!/usr/bin/env python3
"""Run the Manta backend and frontend together.

Commands and working directories can be overridden either with command-line
options or with the corresponding ``MANTA_*`` environment variables.
"""

from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-command",
        default=os.environ.get("MANTA_BACKEND_COMMAND", "python manage.py runserver"),
        help="backend command (default: %(default)s)",
    )
    parser.add_argument(
        "--frontend-command",
        default=os.environ.get("MANTA_FRONTEND_COMMAND", "npm run dev"),
        help="frontend command (default: %(default)s)",
    )
    parser.add_argument(
        "--backend-dir",
        type=Path,
        default=Path(os.environ.get("MANTA_BACKEND_DIR", "backend")),
        help="backend directory, relative to this file (default: %(default)s)",
    )
    parser.add_argument(
        "--frontend-dir",
        type=Path,
        default=Path(os.environ.get("MANTA_FRONTEND_DIR", "frontend")),
        help="frontend directory, relative to this file (default: %(default)s)",
    )
    return parser.parse_args()


def resolve_directory(directory: Path) -> Path:
    return directory if directory.is_absolute() else ROOT / directory


def start(name: str, command: str, directory: Path) -> subprocess.Popen[bytes]:
    directory = resolve_directory(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"{name} directory does not exist: {directory}")

    argv = shlex.split(command)
    if not argv:
        raise ValueError(f"{name} command cannot be empty")

    print(f"Starting {name}: {shlex.join(argv)} (in {directory})", flush=True)
    return subprocess.Popen(argv, cwd=directory, start_new_session=True)


def stop(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def main() -> int:
    args = parse_args()
    processes: list[subprocess.Popen[bytes]] = []

    try:
        processes.append(start("backend", args.backend_command, args.backend_dir))
        processes.append(start("frontend", args.frontend_command, args.frontend_dir))

        while True:
            for process in processes:
                return_code = process.poll()
                if return_code is not None:
                    return return_code
            time.sleep(0.2)
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    finally:
        stop(processes)


if __name__ == "__main__":
    raise SystemExit(main())
