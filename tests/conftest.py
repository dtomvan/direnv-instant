"""Pytest configuration and fixtures for direnv-instant tests."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def tmux_server() -> Generator[Path, None, None]:
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
