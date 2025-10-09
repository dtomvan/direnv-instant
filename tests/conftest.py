"""Pytest configuration and fixtures for direnv-instant tests."""

from __future__ import annotations

import multiprocessing
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

PROJECT_ROOT = Path(__file__).parent.parent


def _wait_for_sigusr1(queue: multiprocessing.Queue[bool], timeout: int) -> None:
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


class SignalWaiter:
    """Waits for SIGUSR1 signal in a subprocess."""

    def __init__(self) -> None:
        """Initialize signal waiter process."""
        self._queue: multiprocessing.Queue[bool] = multiprocessing.Queue()
        self._process = multiprocessing.Process(
            target=_wait_for_sigusr1, args=(self._queue, 30)
        )
        self._process.start()

        pid = self._process.pid
        assert pid is not None, "Failed to get PID of signal process"
        self.pid = pid

    def wait(self, timeout: float = 30) -> bool:
        """Wait for signal and return whether it was received."""
        self._process.join(timeout=timeout)
        if not self._queue.empty():
            return self._queue.get()
        return False

    def cleanup(self) -> None:
        """Clean up the signal process."""
        if self._process.is_alive():
            self._process.join(timeout=1)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1)


class DirenvInstantRunner:
    """Helper to run direnv-instant binary."""

    def __init__(self, binary_path: str) -> None:
        """Initialize with binary path."""
        self.binary_path = binary_path

    def run(
        self, args: list[str], env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        """Run direnv-instant with given args and environment."""
        return subprocess.run(
            [self.binary_path, *args],
            check=False,
            env=env,
            capture_output=True,
            text=True,
        )


@pytest.fixture(scope="session")
def direnv_instant() -> DirenvInstantRunner:
    """Get direnv-instant runner with pre-resolved binary path."""
    if binary := os.environ.get("DIRENV_INSTANT_BIN"):
        # Resolve relative paths against PROJECT_ROOT
        binary_path = Path(binary)
        if not binary_path.is_absolute():
            binary_path = PROJECT_ROOT / binary_path
        return DirenvInstantRunner(str(binary_path.absolute()))

    # Build binary and return the target path
    subprocess.run(
        ["cargo", "build", "--quiet"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )

    # Find the built binary
    target_dir = PROJECT_ROOT / "target" / "debug"
    binary_name = "direnv-instant.exe" if os.name == "nt" else "direnv-instant"
    binary_path = target_dir / binary_name
    return DirenvInstantRunner(str(binary_path))


@pytest.fixture
def tmux_server() -> Generator[Path]:
    """Set up an isolated tmux server for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        socket_path = Path(tmpdir) / "tmux-socket"

        # Start isolated tmux server
        subprocess.run(
            ["tmux", "-S", str(socket_path), "new-session", "-d"],
            check=True,
            capture_output=True,
        )

        try:
            yield socket_path
        finally:
            # Clean up tmux server
            subprocess.run(
                ["tmux", "-S", str(socket_path), "kill-server"],
                check=False,
                capture_output=True,
            )


@pytest.fixture
def signal_waiter() -> Generator[SignalWaiter]:
    """Set up a process that waits for SIGUSR1 signal."""
    waiter = SignalWaiter()
    try:
        yield waiter
    finally:
        waiter.cleanup()
