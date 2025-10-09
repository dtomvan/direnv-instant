"""Test that direnv-instant runs direnv synchronously when not in tmux."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

from tests.helpers import allow_direnv, setup_envrc

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch

    from tests.conftest import DirenvInstantRunner


def test_no_tmux_runs_direnv_synchronously(
    tmp_path: Path, monkeypatch: MonkeyPatch, direnv_instant: DirenvInstantRunner
) -> None:
    """Test that direnv-instant runs direnv synchronously when not in tmux."""
    setup_envrc(
        tmp_path,
        """#!/bin/bash
sleep 1
export SYNC_TEST=success
""",
    )

    allow_direnv(tmp_path, monkeypatch)

    # Prepare environment WITHOUT TMUX
    env = os.environ.copy()
    env.pop("TMUX", None)  # Ensure TMUX is not set

    # Run direnv-instant start (should block until direnv completes)
    start_time = time.time()
    result = direnv_instant.run(["start"], env)
    elapsed = time.time() - start_time

    # Should block for at least the sleep duration
    assert elapsed >= 1, f"direnv-instant returned too quickly: {elapsed}s"
    assert result.returncode == 0, f"Failed: {result.stderr}"

    # Should output direnv's export statements directly
    assert "SYNC_TEST" in result.stdout or "SYNC_TEST" in result.stderr

    # Should not set daemon-related env vars
    assert "__DIRENV_INSTANT_ENV_FILE" not in result.stdout
    assert "__DIRENV_INSTANT_STDERR_FILE" not in result.stdout
    assert "__DIRENV_INSTANT_CURRENT_DIR" in result.stdout  # This is always set
