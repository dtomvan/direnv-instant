"""Pytest configuration and fixtures for direnv-instant tests."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

PROJECT_ROOT = Path(__file__).parent.parent


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
