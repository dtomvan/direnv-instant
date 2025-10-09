"""Test that the stop command properly stops the running daemon."""

from __future__ import annotations

import os
import socket as sock_module
import time
from pathlib import Path
from typing import TYPE_CHECKING

from tests.helpers import (
    allow_direnv,
    setup_envrc,
    setup_stub_tmux,
    setup_test_env,
)

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch

    from tests.conftest import DirenvInstantRunner


def test_stop_command_stops_daemon(
    tmp_path: Path, monkeypatch: MonkeyPatch, direnv_instant: DirenvInstantRunner
) -> None:
    """Test that the stop command properly stops the running daemon."""
    setup_envrc(tmp_path, "sleep 3600\n")
    setup_stub_tmux(tmp_path)
    allow_direnv(tmp_path, monkeypatch)

    env = setup_test_env(tmp_path, os.getpid(), tmux_delay="60")

    result = direnv_instant.run(["start"], env)
    assert result.returncode == 0

    # Get socket path from stderr file path (in same directory)
    stderr_file = None
    for line in result.stdout.splitlines():
        if "__DIRENV_INSTANT_STDERR_FILE" in line:
            stderr_file = Path(line.split("=", 1)[1].strip().strip("'\""))
            break
    assert stderr_file, "Could not find stderr file path"
    socket_path = stderr_file.parent / "daemon.sock"

    # Wait for daemon socket
    for _ in range(30):
        if socket_path.exists():
            break
        time.sleep(0.1)
    assert socket_path.exists(), "Daemon socket not created"

    # Run stop command
    env["__DIRENV_INSTANT_CURRENT_DIR"] = str(tmp_path)
    stop_result = direnv_instant.run(["stop"], env)
    assert stop_result.returncode == 0

    # Verify socket is gone or not accepting connections
    time.sleep(1)
    try:
        sock = sock_module.socket(sock_module.AF_UNIX, sock_module.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(str(socket_path))
        sock.close()
    except (OSError, TimeoutError):
        pass  # Expected - daemon stopped
    else:
        msg = "Daemon still running after stop"
        raise AssertionError(msg)
