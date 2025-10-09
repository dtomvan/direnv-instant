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

    def __init__(self, binary_cmd: list[str]) -> None:
        """Initialize with binary command."""
        self.binary_cmd = binary_cmd

    @property
    def cmd_string(self) -> str:
        """Get binary command as a shell string."""
        return " ".join(self.binary_cmd)

    def run(
        self, args: list[str], env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        """Run direnv-instant with given args and environment."""
        cmd = self.binary_cmd + args
        return subprocess.run(
            cmd,
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
        return DirenvInstantRunner([str(binary_path.absolute())])

    # Build binary first to avoid timing issues in tests
    subprocess.run(
        ["cargo", "build", "--quiet"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )

    # Use cargo run
    return DirenvInstantRunner(
        [
            "cargo",
            "run",
            "--quiet",
            "--manifest-path",
            str(PROJECT_ROOT / "Cargo.toml"),
            "--",
        ]
    )


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
