#!/usr/bin/env python3
"""choice - a Linux/Python reimplementation of the Windows CHOICE command.

The program prompts the user to select one item from a list of single-character
choices and returns the 1-based index of the selected choice as the process
exit code (mirroring the Windows ERRORLEVEL convention).

Exit codes:
    1..N  Index (1-based) of the chosen key inside the choices list.
    0     The user aborted with Ctrl+C / Ctrl+D.
    255   An error occurred (invalid arguments or runtime failure).

This behavior intentionally matches Windows CHOICE so scripts can branch on the
exit code in the same way.
"""

from __future__ import annotations

import argparse
import os
import select
import sys

__version__ = "1.1.0"

# Windows CHOICE defaults to the Yes/No set when /C is omitted.
DEFAULT_CHOICES = "YN"

# Windows CHOICE accepts a timeout between 0 and 9999 seconds.
MIN_TIMEOUT = 0
MAX_TIMEOUT = 9999

# Exit codes.
EXIT_ABORT = 0
EXIT_ERROR = 255

# Control characters read in raw terminal mode.
CTRL_C = "\x03"
CTRL_D = "\x04"
ESC = "\x1b"  # Start byte of ANSI escape sequences (arrow keys, function keys).

# Grace period (seconds) to collect the rest of an escape sequence after ESC.
# The bytes of an arrow key arrive as one burst; this small wait tolerates slow
# terminals or SSH latency while still returning promptly on a lone ESC press.
ESC_SEQUENCE_GRACE = 0.02


def die(message: str) -> "None":
    """Print an error to stderr and exit with the Windows error code (255)."""
    print(f"choice: error: {message}", file=sys.stderr)
    raise SystemExit(EXIT_ERROR)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser.

    Long options are the primary interface; short options mirror the semantics
    of the original Windows switches (/C, /N, /CS, /T, /D, /M).
    """
    parser = argparse.ArgumentParser(
        prog="choice",
        description=(
            "Prompt the user to choose one of a set of single-character "
            "options and return the 1-based selection index as the exit code."
        ),
        epilog=(
            "Exit codes: 1..N = chosen index, 0 = aborted (Ctrl+C/Ctrl+D), "
            "255 = error."
        ),
    )
    parser.add_argument(
        "-c",
        "--choices",
        default=DEFAULT_CHOICES,
        metavar="LIST",
        help=(
            "Characters allowed as choices, e.g. 'YNC' "
            f"(default: {DEFAULT_CHOICES})."
        ),
    )
    parser.add_argument(
        "-n",
        "--no-prompt",
        action="store_true",
        help="Hide the list of choices; only the message (if any) is shown.",
    )
    parser.add_argument(
        "-s",
        "--case-sensitive",
        action="store_true",
        help="Treat choices as case-sensitive (default: case-insensitive).",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        metavar="SECONDS",
        help=(
            "Seconds to wait before selecting the default choice "
            f"({MIN_TIMEOUT}-{MAX_TIMEOUT}). Requires --default."
        ),
    )
    parser.add_argument(
        "-d",
        "--default",
        metavar="CHAR",
        help="Default choice used when the timeout expires. Requires --timeout.",
    )
    parser.add_argument(
        "-m",
        "--message",
        default="",
        metavar="TEXT",
        help="Message shown before the prompt.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def validate(args: argparse.Namespace) -> "list[str]":
    """Validate parsed arguments and return the normalized list of choices.

    All validation failures exit with code 255 to match Windows CHOICE.
    """
    choices = list(args.choices)

    if not choices:
        die("the choices list must not be empty")

    for char in choices:
        # Windows CHOICE only allows printable characters as choices, and
        # whitespace would make single-key selection ambiguous.
        if not char.isprintable() or char.isspace():
            die(f"invalid choice character: {char!r}")

    # Detect duplicates, honoring case sensitivity.
    seen_key = (lambda c: c) if args.case_sensitive else (lambda c: c.lower())
    seen: set[str] = set()
    for char in choices:
        key = seen_key(char)
        if key in seen:
            die(f"duplicate choice character: {char!r}")
        seen.add(key)

    # /T and /D are only meaningful together, exactly like Windows CHOICE.
    if (args.timeout is None) != (args.default is None):
        die("--timeout and --default must be used together")

    if args.timeout is not None:
        if not MIN_TIMEOUT <= args.timeout <= MAX_TIMEOUT:
            die(
                f"timeout must be between {MIN_TIMEOUT} and {MAX_TIMEOUT} "
                f"seconds"
            )
        if not _matches(args.default, choices, args.case_sensitive):
            die("--default must be one of the choices")

    return choices


def _matches(char: str, choices: "list[str]", case_sensitive: bool) -> bool:
    """Return True if char is present in choices under the case policy."""
    if case_sensitive:
        return char in choices
    return char.lower() in [c.lower() for c in choices]


def _index_of(char: str, choices: "list[str]", case_sensitive: bool) -> int:
    """Return the 1-based index of char within choices, or -1 if absent."""
    if case_sensitive:
        haystack = choices
        needle = char
    else:
        haystack = [c.lower() for c in choices]
        needle = char.lower()
    try:
        return haystack.index(needle) + 1
    except ValueError:
        return -1


def render_prompt(args: argparse.Namespace, choices: "list[str]") -> str:
    """Build the prompt string shown to the user."""
    parts: list[str] = []
    if args.message:
        parts.append(args.message)
    if not args.no_prompt:
        parts.append("[" + ",".join(choices) + "]?")
    return " ".join(parts) + " " if parts else ""


def _drain_escape_sequence(fd: int) -> None:
    """Consume and discard the remainder of an ANSI escape sequence.

    Arrow keys and other special keys send a multi-byte sequence that begins
    with ESC, for example:

        Up arrow     ESC [ A        (\\x1b\\x5b\\x41)
        Down arrow   ESC [ B
        Right arrow  ESC [ C
        Left arrow   ESC [ D
        Home/End     ESC [ H / ESC [ F   (or ESC O H / ESC O F on some terms)
        Ctrl+arrow   ESC [ 1 ; 5 C       (longer, parameterized form)

    We already consumed the leading ESC. The rest of the sequence is buffered
    together, so we read whatever is immediately available and throw it away.
    Without this, the trailing bytes (e.g. the 'A' of an up arrow) would be read
    on the next iterations and could be mistaken for a valid single-key choice.
    """
    while select.select([fd], [], [], ESC_SEQUENCE_GRACE)[0]:
        os.read(fd, 1)


def _read_key(fd: int, timeout: "float | None") -> "str | None":
    """Read one byte as a character from an already-raw terminal.

    Returns the decoded character, CTRL_D on end-of-input, or None on timeout.
    The terminal must already be in raw mode (see prompt_tty).
    """
    ready, _, _ = select.select([fd], [], [], timeout)
    if not ready:
        return None
    data = os.read(fd, 1)
    if not data:
        # EOF on stdin (e.g. Ctrl+D at start of input).
        return CTRL_D
    return data.decode("utf-8", errors="ignore")


def _emit(text: str) -> None:
    """Write text to stdout in raw mode, translating '\\n' to '\\r\\n'.

    In raw mode output post-processing (OPOST/ONLCR) is disabled, so a bare
    '\\n' would not return the cursor to the start of the line.
    """
    sys.stdout.write(text.replace("\n", "\r\n"))
    sys.stdout.flush()


def prompt_tty(args: argparse.Namespace, choices: "list[str]") -> int:
    """Interactive selection loop for a real terminal. Returns the exit code.

    Raw mode is entered once for the entire prompt (not per keystroke). This
    guarantees that from the moment the prompt is shown, every keystroke is
    handled in raw mode, avoiding a race where a very fast or pasted keystroke
    arriving just after the prompt would otherwise be echoed and line-buffered
    by the terminal in canonical mode.
    """
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    timeout = float(args.timeout) if args.timeout is not None else None

    try:
        tty.setraw(fd)
        _emit(render_prompt(args, choices))

        while True:
            key = _read_key(fd, timeout)

            if key is None:
                # Timeout expired: use the configured default choice.
                _emit(args.default + "\n")
                return _index_of(args.default, choices, args.case_sensitive)

            if key in (CTRL_C, CTRL_D):
                _emit("\n")
                return EXIT_ABORT

            if key == ESC:
                # Escape key alone, or an arrow/function-key sequence. Drain any
                # trailing bytes so they are not read as separate keys, then
                # ignore it and keep waiting.
                _drain_escape_sequence(fd)
                continue

            index = _index_of(key, choices, args.case_sensitive)
            if index != -1:
                # Echo the accepted key, matching Windows CHOICE behavior.
                _emit(key + "\n")
                return index
            # Ignore any other key that is not a valid choice and keep waiting.
    finally:
        # Always restore the terminal, even on exceptions.
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def prompt_pipe(args: argparse.Namespace, choices: "list[str]") -> int:
    """Non-interactive selection when stdin is not a TTY (piped input).

    Reads a single line and uses its first character as the selection. If no
    input is available and a default is set, the default is used.
    """
    prompt = render_prompt(args, choices)
    sys.stdout.write(prompt)
    sys.stdout.flush()

    line = sys.stdin.readline()
    if line == "":
        # EOF with no data.
        if args.default is not None:
            return _index_of(args.default, choices, args.case_sensitive)
        return EXIT_ABORT

    stripped = line.strip()
    if not stripped:
        if args.default is not None:
            return _index_of(args.default, choices, args.case_sensitive)
        die("no valid choice provided on stdin")

    index = _index_of(stripped[0], choices, args.case_sensitive)
    if index == -1:
        die(f"invalid choice: {stripped[0]!r}")
    return index


def main(argv: "list[str] | None" = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    choices = validate(args)

    try:
        if sys.stdin.isatty():
            return prompt_tty(args, choices)
        return prompt_pipe(args, choices)
    except KeyboardInterrupt:
        # Reachable on the non-raw (piped) path.
        sys.stdout.write("\n")
        return EXIT_ABORT
    except OSError as exc:
        die(f"terminal I/O failure: {exc}")
        return EXIT_ERROR  # Unreachable; die() raises SystemExit.


if __name__ == "__main__":
    sys.exit(main())
