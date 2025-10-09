"""Test that direnv-instant calls tmux when direnv blocks and Ctrl-C stops daemon."""

from __future__ import annotations

import multiprocessing
import socket as sock_module
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from tests.helpers import (
    allow_direnv,
    setup_envrc,
    setup_test_env,
    wait_for_sigusr1,
)

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch

    from tests.conftest import DirenvInstantRunner


def test_blocking_envrc_calls_tmux(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    tmux_server: Path,
    direnv_instant: DirenvInstantRunner,
) -> None:
    """Test direnv-instant calls tmux when direnv blocks.

    Also verifies that Ctrl-C stops the daemon.
    """
    setup_envrc(tmp_path, "sleep 3600\n")
    allow_direnv(tmp_path, monkeypatch)

    queue: multiprocessing.Queue[bool] = multiprocessing.Queue()
    signal_process = multiprocessing.Process(target=wait_for_sigusr1, args=(queue, 5))
    signal_process.start()

    pid = signal_process.pid
    assert pid is not None, "Failed to get PID of signal process"

    env = setup_test_env(tmp_path, pid)
    # Set TMUX env var to use our isolated server
    env["TMUX"] = f"{tmux_server},0,0"

    # Run direnv-instant start (should not block)
    start_time = time.time()
    result = direnv_instant.run(["start"], env)
    elapsed = time.time() - start_time

    # Should complete quickly (not block forever)
    assert elapsed < 3, f"direnv-instant blocked for {elapsed}s"
    assert result.returncode == 0, f"Failed: {result.stderr}"

    # Check that it exported the env vars
    assert "__DIRENV_INSTANT_ENV_FILE" in result.stdout
    assert "__DIRENV_INSTANT_STDERR_FILE" in result.stdout
    assert "__DIRENV_INSTANT_CURRENT_DIR" in result.stdout

    # Extract socket path
    socket_path = None
    for line in result.stdout.splitlines():
        if "__DIRENV_INSTANT_STDERR_FILE" in line:
            stderr_file = Path(line.split("=", 1)[1].strip().strip("'\""))
            socket_path = stderr_file.parent / "daemon.sock"
            break
    assert socket_path, "Could not find socket path"

    # Poll for watch pane to be created (with timeout)
    watch_pane_id = None
    start = time.time()
    timeout = 5  # Should appear within delay + buffer
    while time.time() - start < timeout:
        list_panes = subprocess.run(
            [
                "tmux",
                "-S",
                str(tmux_server),
                "list-panes",
                "-F",
                "#{pane_id} #{pane_current_command}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        for line in list_panes.stdout.splitlines():
            if "direnv-instant" in line or "watch" in line:
                watch_pane_id = line.split()[0]
                break

        if watch_pane_id:
            break

        time.sleep(0.1)

    assert watch_pane_id, (
        f"Watch pane not found after {timeout}s. Panes: {list_panes.stdout}"
    )

    # Send Ctrl-C to watch pane
    subprocess.run(
        ["tmux", "-S", str(tmux_server), "send-keys", "-t", watch_pane_id, "C-c"],
        check=True,
        capture_output=True,
    )

    # Wait for daemon to stop
    time.sleep(1)

    # Verify daemon socket is no longer accepting connections
    daemon_stopped = False
    try:
        with sock_module.socket(sock_module.AF_UNIX, sock_module.SOCK_STREAM) as sock:
            sock.settimeout(1)
            sock.connect(str(socket_path))
    except (OSError, TimeoutError):
        daemon_stopped = True  # Expected - daemon stopped

    assert daemon_stopped, "Daemon still running after Ctrl-C to watch"

    # Clean up signal process
    signal_process.join(timeout=1)
    signal_process.terminate()
