"""Headless subprocess helpers on Windows (no console window)."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Sequence

CREATE_NO_WINDOW = 0x08000000


def _creationflags() -> int:
    if sys.platform == "win32":
        return CREATE_NO_WINDOW
    return 0


def run_hidden(
    args: Sequence[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=_creationflags(),
        stdin=subprocess.DEVNULL,
    )


def popen_hidden(
    args: Sequence[str],
    *,
    cwd: str | None = None,
    stdout: int | None = subprocess.PIPE,
    stderr: int | None = subprocess.PIPE,
    hide_console: bool = True,
) -> subprocess.Popen[str]:
    flags = _creationflags() if hide_console and sys.platform == "win32" else 0
    return subprocess.Popen(
        list(args),
        cwd=cwd,
        stdout=stdout,
        stderr=stderr,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
        text=True,
        env=os.environ.copy(),
    )


def kill_process_tree(pid: int) -> None:
    if sys.platform != "win32":
        try:
            import psutil

            p = psutil.Process(pid)
            for c in p.children(recursive=True):
                c.kill()
            p.kill()
        except Exception:
            pass
        return
    run_hidden(["taskkill", "/PID", str(pid), "/T", "/F"])
