# pause

A Linux/Python replica of the Windows CMD `pause` command.

It prints a prompt and waits for a **single keypress** (any key), then
continues — exactly like `pause` in a Windows batch file. Useful in shell
scripts where you want the user to acknowledge something before the script
moves on.

```console
$ ./pause
Press any key to continue . . .
```

## Features

- Waits for **any key**, not just Enter (raw terminal mode via `termios`/`tty`).
- Reads the keypress from the controlling terminal (`/dev/tty`), so it keeps
  working when `stdin`/`stdout` are redirected in a pipeline.
- Custom prompt with `-m/--message`.
- Correct POSIX exit codes: `0` on continue, `130` on `Ctrl-C`.
- Safe fallback: when no terminal is available, it prints the prompt and
  continues immediately (mirrors Windows `pause` with redirected input).
- No third-party dependencies — standard library only.

## Requirements

- Linux (or any POSIX system with `/dev/tty` and the `termios` module).
- Python 3.9+ (uses `from __future__ import annotations`; tested on 3.14).

## Installation

Clone or copy the `pause` script somewhere on your `PATH`:

```bash
install -m 0755 pause ~/.local/bin/pause
# or system-wide:
sudo install -m 0755 pause /usr/local/bin/pause
```

Then run it as `pause`.

## Usage

```console
$ pause
Press any key to continue . . .

$ pause -m "Press any key to deploy... "
Press any key to deploy...

$ pause --version
pause 1.0.0

$ pause --help
```

### In a shell script

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "About to restart the service."
pause -m "Press any key to continue (Ctrl-C to abort)... "

# Abort the script if the user pressed Ctrl-C at the prompt.
if [[ $? -eq 130 ]]; then
    echo "Aborted." >&2
    exit 130
fi

systemctl restart myservice
```

> Note: `pause` returns `130` on `Ctrl-C` but does not itself terminate the
> shell. Check `$?` (as above) if you want the calling script to abort.

## Exit codes

| Code | Meaning                                             |
|------|-----------------------------------------------------|
| `0`  | A key was pressed (normal continue), or no tty      |
| `130`| Interrupted with `Ctrl-C` (POSIX `128 + SIGINT`)    |
| `2`  | Invalid command-line arguments (from `argparse`)    |

## How it works

The prompt is written to `stdout`. The keypress is read from `/dev/tty` in
raw mode (`tty.setraw`), which disables line buffering and signal generation
so a single byte is returned immediately and `Ctrl-C` arrives as the raw byte
`\x03` instead of raising `SIGINT`. The original terminal attributes are
always restored afterwards, even on error.

## License

MIT
