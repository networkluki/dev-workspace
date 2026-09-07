"""Command-line interface for ``clip``.

Behaviour mirrors the Windows ``clip`` command: data supplied on standard
input is copied verbatim to the system clipboard. The transfer is binary-safe;
no text decoding, re-encoding, or newline translation is performed.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Sequence

from . import __version__

# Seconds to wait for a backend to accept the data before giving up. Well-behaved
# clipboard tools read stdin and daemonize almost instantly; a stuck backend
# should fail loudly instead of hanging the pipeline.
_BACKEND_TIMEOUT = 10.0


@dataclass(frozen=True)
class Backend:
    """A known-good clipboard tool invoked to write the system clipboard.

    ``argv`` is a fixed argument vector (never passed through a shell), so the
    set of executables that can run is a strict allowlist and untrusted input is
    only ever delivered on stdin, never interpreted as a command.
    """

    name: str
    argv: tuple[str, ...]
    server: str  # "wayland", "x11", or "any"
    install_hint: str


# Ordered by preference. Wayland first when a Wayland session is present, then
# the common X11 tools. Only these fixed commands are ever executed.
_BACKENDS: tuple[Backend, ...] = (
    Backend(
        name="wl-copy",
        argv=("wl-copy",),
        server="wayland",
        install_hint="wl-clipboard (e.g. 'sudo apt install wl-clipboard')",
    ),
    Backend(
        name="xclip",
        argv=("xclip", "-selection", "clipboard", "-in"),
        server="x11",
        install_hint="xclip (e.g. 'sudo apt install xclip')",
    ),
    Backend(
        name="xsel",
        argv=("xsel", "--clipboard", "--input"),
        server="x11",
        install_hint="xsel (e.g. 'sudo apt install xsel')",
    ),
)


def _has_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def _has_x11() -> bool:
    return bool(os.environ.get("DISPLAY"))


def _server_available(backend: Backend) -> bool:
    """Report whether the display server this backend needs is present."""
    if backend.server == "wayland":
        return _has_wayland()
    if backend.server == "x11":
        return _has_x11()
    return True


def _select_backend() -> Backend | None:
    """Pick the first installed backend whose display server is available.

    Falls back to any installed backend if no session hint matches, which keeps
    the tool working under unusual setups (e.g. XWayland with only ``xclip``).
    """
    candidates = [b for b in _BACKENDS if shutil.which(b.argv[0])]
    for backend in candidates:
        if _server_available(backend):
            return backend
    return candidates[0] if candidates else None


def _no_backend_message() -> str:
    hints = "\n".join(f"  - {b.name}: {b.install_hint}" for b in _BACKENDS)
    return (
        "clip: no supported clipboard backend found.\n"
        "Install one of the following and ensure a graphical session is running:\n"
        f"{hints}"
    )


def _read_stdin_bytes() -> bytes:
    """Read all of standard input as raw bytes (binary-safe)."""
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is not None:
        return buffer.read()
    # Fallback for unusual stdin replacements without a binary buffer.
    return sys.stdin.read().encode(errors="surrogateescape")


def _copy(backend: Backend, data: bytes) -> int:
    # X11/Wayland clipboard tools fork a background helper that inherits open
    # file descriptors and holds the selection. If we captured stderr via a
    # pipe, that helper would keep the pipe's write end open and block us until
    # end-of-file. Capturing to a temporary file instead lets us wait only on
    # the short-lived foreground process while still reading any error output.
    with tempfile.TemporaryFile() as stderr_file:
        try:
            result = subprocess.run(
                backend.argv,
                input=data,
                stdout=subprocess.DEVNULL,
                stderr=stderr_file,
                timeout=_BACKEND_TIMEOUT,
                check=False,
            )
        except FileNotFoundError:
            print(
                f"clip: backend '{backend.name}' disappeared before it "
                "could run.",
                file=sys.stderr,
            )
            return 1
        except subprocess.TimeoutExpired:
            print(
                f"clip: backend '{backend.name}' timed out after "
                f"{_BACKEND_TIMEOUT:g}s.",
                file=sys.stderr,
            )
            return 1

        if result.returncode != 0:
            stderr_file.seek(0)
            detail = stderr_file.read().decode(errors="replace").strip()
            suffix = f": {detail}" if detail else ""
            print(
                f"clip: backend '{backend.name}' failed "
                f"(exit {result.returncode}){suffix}",
                file=sys.stderr,
            )
            return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clip",
        description=(
            "Copy standard input to the system clipboard "
            "(a Linux port of the Windows 'clip' command)."
        ),
        epilog=(
            "Examples:\n"
            "  clip < notes.txt        Copy a file to the clipboard\n"
            "  ls -la | clip           Copy command output to the clipboard\n"
            "  echo -n hello | clip    Copy exact bytes (no trailing newline)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns a process exit code.

    Exit codes:
      0  data copied successfully
      1  a backend was found but the copy failed
      2  no supported clipboard backend is available
    """
    parser = _build_parser()
    parser.parse_args(argv)

    backend = _select_backend()
    if backend is None:
        print(_no_backend_message(), file=sys.stderr)
        return 2

    # Interactive hint: when stdin is a terminal, tell the user how to finish,
    # matching the Windows behaviour of reading until end-of-input.
    if sys.stdin.isatty():
        print(
            "clip: reading from terminal; type input then press Ctrl-D to copy "
            "(Ctrl-C to abort).",
            file=sys.stderr,
        )

    try:
        data = _read_stdin_bytes()
    except KeyboardInterrupt:
        print("\nclip: aborted.", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"clip: failed to read standard input: {exc}", file=sys.stderr)
        return 1

    return _copy(backend, data)


if __name__ == "__main__":
    sys.exit(main())
