"""Helper functions for direnv-instant integration tests."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import multiprocessing
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch


def wait_for_sigusr1(queue: multiprocessing.Queue, timeout: int) -> None:
    """Subprocess that waits for SIGUSR1 and reports back."""
    received = False

    def handler(_signum: int, _frame: object) -> None:
        nonlocal received
        received = True

    signal.signal(signal.SIGUSR1, handler)

    # Wait for signal
    start = time.time()
    while not received and (time.time() - start) < timeout:
        time.sleep(0.1)

    queue.put(received)


def setup_envrc(tmp_path: Path, content: str) -> Path:
    """Create and configure .envrc file."""
    envrc = tmp_path / ".envrc"
    envrc.write_text(content)
    envrc.chmod(0o755)
    return envrc


def setup_stub_tmux(tmp_path: Path, script_content: str | None = None) -> Path:
    """Create stub tmux script."""
    stub_tmux = tmp_path / "tmux"
    if script_content is None:
        script_content = "#!/bin/bash\nexit 0\n"
    stub_tmux.write_text(script_content)
    stub_tmux.chmod(0o755)
    return stub_tmux


def setup_test_env(
    tmp_path: Path, shell_pid: int, tmux_delay: str = "1"
) -> dict[str, str]:
    """Prepare environment for direnv-instant tests."""
    env = os.environ.copy()
    env["TMUX"] = "test"
    env["DIRENV_INSTANT_SHELL_PID"] = str(shell_pid)
    env["DIRENV_INSTANT_TMUX_DELAY"] = tmux_delay
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    return env


def allow_direnv(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Change to test directory and allow direnv."""
    monkeypatch.chdir(tmp_path)
    subprocess.run(["direnv", "allow"], check=True, capture_output=True)
