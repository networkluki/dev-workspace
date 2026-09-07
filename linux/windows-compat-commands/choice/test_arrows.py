#!/usr/bin/env python3
"""PTY-based test: arrow-key escape sequences must never select a choice."""
import os
import pty
import select
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def run_choice(chunks, args, deadline=5.0):
    """Run choice.py in a PTY, writing each chunk with a gap between them.

    Chunks are written with a delay longer than the escape-sequence grace
    period, mimicking a real user whose next keypress comes well after an
    arrow-key burst. A single logical keystroke (e.g. an arrow's ESC[C) must be
    sent as one chunk so its bytes stay within the grace window.
    """
    if isinstance(chunks, (bytes, bytearray)):
        chunks = [chunks]

    pid, fd = pty.fork()
    if pid == 0:  # child
        os.chdir(HERE)
        os.execvp("python3", ["python3", "choice.py", *args])
        os._exit(127)

    # parent: wait until the prompt is written, proving the child has entered
    # raw mode and is ready to read a key. Feeding input earlier can be lost.
    r, _, _ = select.select([fd], [], [], 3.0)
    if r:
        os.read(fd, 4096)  # consume the prompt

    for i, chunk in enumerate(chunks):
        if i > 0:
            time.sleep(0.1)  # > escape-sequence grace (0.02s)
        os.write(fd, chunk)
    time.sleep(0.3)  # let the child fully process, echo, and exit

    # Drain the echoed output (ignored) so it does not linger in the PTY.
    try:
        while select.select([fd], [], [], 0)[0]:
            if not os.read(fd, 1024):
                break
    except OSError:
        pass  # EIO: slave closed (child exited).

    wpid, status = os.waitpid(pid, os.WNOHANG)
    try:
        os.close(fd)
    except OSError:
        pass
    if wpid == pid:
        return os.waitstatus_to_exitcode(status)

    # Child unexpectedly still running.
    try:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
    except OSError:
        pass
    return None


ESC = b"\x1b"
cases = [
    ("right-arrow then N", [ESC + b"[C", b"N"], ["-c", "YNC"], 2),
    ("up-arrow then Y", [ESC + b"[A", b"Y"], ["-c", "YNC"], 1),
    ("Ctrl+arrow then C", [ESC + b"[1;5C", b"C"], ["-c", "YNC"], 3),
    ("bare ESC then Y", [ESC, b"Y"], ["-c", "YNC"], 1),
    ("plain C", b"C", ["-c", "YNC"], 3),
    ("Ctrl+C abort", b"\x03", ["-c", "YNC"], 0),
]

ok = True
for name, data, args, expected in cases:
    got = run_choice(data, args)
    status = "PASS" if got == expected else "FAIL"
    if got != expected:
        ok = False
    print(f"[{status}] {name:22} expected={expected} got={got}")

sys.exit(0 if ok else 1)
