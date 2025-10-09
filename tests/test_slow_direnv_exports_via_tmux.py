"""Test that direnv exports variables even when it takes longer than TMUX_DELAY."""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from typing import TYPE_CHECKING

from tests.helpers import (
    allow_direnv,
    setup_envrc,
    setup_stub_tmux,
    setup_test_env,
    wait_for_sigusr1,
)

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch

    from tests.conftest import DirenvInstantRunner


def test_slow_direnv_exports_via_tmux(
    tmp_path: Path, monkeypatch: MonkeyPatch, direnv_instant: DirenvInstantRunner
) -> None:
    """Test direnv exports vars when it takes longer than TMUX_DELAY."""
    setup_envrc(
        tmp_path,
        """#!/bin/bash
echo "Starting build..." >&2
sleep 1
echo "Still building..." >&2
sleep 1
echo "Almost done..." >&2
sleep 1
echo "Build complete!" >&2
export FOO=bar
export BAZ=qux
""",
    )

    tmux_called_file = tmp_path / "tmux_called"
    watch_output_file = tmp_path / "watch_output"
    direnv_instant_cmd = direnv_instant.cmd_string

    setup_stub_tmux(
        tmp_path,
        f"""#!/bin/bash
touch {tmux_called_file}
log_path="${{@: -2:1}}"
socket_path="${{@: -1}}"
{direnv_instant_cmd} watch "$log_path" "$socket_path" > {watch_output_file} 2>&1 &
""",
    )

    allow_direnv(tmp_path, monkeypatch)

    queue: multiprocessing.Queue[bool] = multiprocessing.Queue()
    signal_process = multiprocessing.Process(target=wait_for_sigusr1, args=(queue, 10))
    signal_process.start()

    env = setup_test_env(tmp_path, signal_process.pid)

    # Run direnv-instant start (should not block)
    start_time = time.time()
    result = direnv_instant.run(["start"], env)
    elapsed = time.time() - start_time

    # Should complete quickly (not wait for direnv to finish)
    assert elapsed < 2, f"direnv-instant blocked for {elapsed}s"
    assert result.returncode == 0, f"Failed: {result.stderr}"

    # Parse env file path from output
    env_file_path = None
    for line in result.stdout.splitlines():
        if "__DIRENV_INSTANT_ENV_FILE" in line:
            # Extract path from: export __DIRENV_INSTANT_ENV_FILE='/path/to/file'
            env_file_path = line.split("=", 1)[1].strip().strip("'\"")
            break
    assert env_file_path, "Could not find __DIRENV_INSTANT_ENV_FILE in output"

    # Wait for tmux to be called (after 1s delay)
    time.sleep(2)
    assert tmux_called_file.exists(), "tmux stub was not called"

    # Wait for direnv to complete and write env file (3s execution + processing time)
    timeout_val = 6
    start = time.time()
    env_file = Path(env_file_path)
    while not env_file.exists() and (time.time() - start) < timeout_val:
        time.sleep(0.1)

    assert env_file.exists(), f"Env file not created after {timeout_val}s"

    # Verify environment variables were exported
    env_content = env_file.read_text()
    assert "FOO" in env_content, "FOO not found in env file"
    assert "bar" in env_content, "bar not found in env file"
    assert "BAZ" in env_content, "BAZ not found in env file"
    assert "qux" in env_content, "qux not found in env file"

    # Verify SIGUSR1 was received
    signal_process.join(timeout=1)
    assert not queue.empty(), "SIGUSR1 signal queue is empty"
    signal_received = queue.get()
    assert signal_received, "SIGUSR1 was not received"

    # Wait for watch output to be captured
    timeout_watch = 5
    start = time.time()
    while (time.time() - start) < timeout_watch:
        if watch_output_file.exists() and watch_output_file.stat().st_size > 0:
            break
        time.sleep(0.1)

    # Verify watch command was invoked and captured output
    assert watch_output_file.exists(), "watch output file was not created"
    watch_output = watch_output_file.read_text()
    assert len(watch_output) > 0, "watch command produced no output"
    # Verify we captured direnv output
    assert "Starting build" in watch_output or "direnv" in watch_output.lower()

    # Clean up
    signal_process.terminate()
