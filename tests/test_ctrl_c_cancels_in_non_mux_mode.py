"""Test that Ctrl+C cancels direnv export in non-multiplexer mode.

This is a regression test for issue #7:
https://github.com/Mic92/direnv-instant/issues/7

When tmux/zellij isn't running, direnv-instant runs direnv synchronously.
However, there was a bug where pressing Ctrl+C didn't properly cancel the
operation - it would restart instead of canceling.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from typing import TYPE_CHECKING

from tests.helpers import allow_direnv, setup_envrc

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch

    from tests.conftest import DirenvInstantRunner


def test_ctrl_c_cancels_direnv_in_non_mux_mode(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    direnv_instant: DirenvInstantRunner,
    subprocess_runner: list[subprocess.Popen[str]],
) -> None:
    """Test that SIGINT (Ctrl+C) properly cancels direnv export in non-mux mode.

    This test verifies that when direnv-instant is running synchronously
    (without tmux/zellij), sending SIGINT will cancel the operation and
    not restart it.
    """
    # Create a slow .envrc that takes several seconds
    setup_envrc(
        tmp_path,
        """# Slow operation that takes 10 seconds
for i in $(seq 1 10); do
    sleep 1
    echo "Processing step $i..." >&2
done
export SLOW_TEST=completed
""",
    )

    allow_direnv(tmp_path, monkeypatch)

    # Prepare environment WITHOUT multiplexer (no TMUX or ZELLIJ_SESSION_NAME)
    env = os.environ.copy()
    env.pop("TMUX", None)
    env.pop("ZELLIJ_SESSION_NAME", None)
    # Ensure we're in the test directory
    env["PWD"] = str(tmp_path)

    # Start direnv-instant in a subprocess so we can send it SIGINT
    proc = subprocess.Popen(
        [direnv_instant.binary_path, "start"],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    subprocess_runner.append(proc)

    # Wait for direnv to actually start by reading stderr until we see output
    # This confirms the exec happened before we send SIGINT
    stderr_output = []
    start_wait = time.time()
    while time.time() - start_wait < 5:  # 5 second timeout
        line = proc.stderr.readline()
        if line:
            stderr_output.append(line)
            # Once we see the first processing step, we know direnv started
            if "Processing step" in line:
                break
    else:
        # Timeout waiting for direnv to start
        msg = "Timeout waiting for direnv to start"
        raise AssertionError(msg)

    # Send SIGINT (Ctrl+C)
    proc.send_signal(signal.SIGINT)

    # Wait for the process to terminate (with timeout)
    start_time = time.time()
    timeout = 5  # Should terminate quickly after SIGINT

    try:
        stdout, stderr_rest = proc.communicate(timeout=timeout)
        stderr = "".join(stderr_output) + stderr_rest
        elapsed = time.time() - start_time
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr_rest = proc.communicate()
        stderr = "".join(stderr_output) + stderr_rest
        elapsed = time.time() - start_time
        msg = (
            f"Process did not terminate after SIGINT within {timeout}s "
            f"(elapsed: {elapsed:.1f}s)"
        )
        raise AssertionError(msg) from None

    # Verify the process terminated quickly (not restarting)
    # It should terminate in ~2-5 seconds, not continue for the full 10 seconds
    assert elapsed < 8, (
        f"Process took too long to terminate: {elapsed:.1f}s (should be < 8s)"
    )

    # Verify it was interrupted (non-zero exit code or specific signal)
    # SIGINT typically results in exit code 130 (128 + 2) or -2
    assert proc.returncode != 0, (
        f"Process should have non-zero exit code after SIGINT, "
        f"got {proc.returncode}\n"
        f"stdout: {stdout}\nstderr: {stderr}"
    )

    # Verify it didn't complete successfully
    assert "SLOW_TEST" not in stdout, (
        "Process should not have completed the slow operation after SIGINT\n"
        f"stdout: {stdout}\nstderr: {stderr}"
    )
