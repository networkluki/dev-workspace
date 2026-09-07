# clip (Linux)

A Linux port of the Windows [`clip`](https://learn.microsoft.com/windows-server/administration/windows-commands/clip) command.

It reads data from **standard input** and copies it **verbatim** to the system
clipboard. Like `clip.exe`, it is copy-only and takes no text arguments — you
pipe or redirect data into it.

The transfer is binary-safe: no decoding, re-encoding, or newline translation
is performed.

## Features

- Same mental model as Windows `clip` (`command | clip`, `clip < file`).
- Auto-detects the clipboard backend:
  - **Wayland** → [`wl-copy`](https://github.com/bugaevc/wl-clipboard)
  - **X11** → [`xclip`](https://github.com/astrand/xclip) or [`xsel`](https://github.com/kfish/xsel)
- Zero third-party Python dependencies (standard library only).
- Clear, actionable errors on stderr and predictable exit codes.
- Fixed command allowlist — input is only ever delivered on stdin, never
  interpreted as a shell command.

## Requirements

- Python **3.8+**
- A running graphical session and **one** of these clipboard tools:

| Session | Backend | Install (Debian/Ubuntu) |
|---------|---------|-------------------------|
| Wayland | `wl-copy` | `sudo apt install wl-clipboard` |
| X11 | `xclip` | `sudo apt install xclip` |
| X11 | `xsel` | `sudo apt install xsel` |

Backends are selected in the order above, preferring the one that matches the
active session (`WAYLAND_DISPLAY` / `DISPLAY`).

## Installation

From the project root:

```bash
pip install .
```

For development (editable install):

```bash
pip install -e .
```

This installs a `clip` command on your `PATH`.

### Run without installing

```bash
python -m clip < file.txt
```

## Usage

```bash
clip < notes.txt        # Copy a file to the clipboard
ls -la | clip           # Copy command output to the clipboard
echo -n hello | clip    # Copy exact bytes (no trailing newline)
```

When run with no piped input (an interactive terminal), `clip` reads until you
press **Ctrl-D**, mirroring the Windows behaviour of reading until end-of-input.
Press **Ctrl-C** to abort.

### Options

| Option | Description |
|--------|-------------|
| `-V`, `--version` | Print the version and exit. |
| `-h`, `--help` | Show help and exit. |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Data copied successfully. |
| `1` | A backend was found but the copy failed (or input read failed / aborted). |
| `2` | No supported clipboard backend is available. |

## How it works

`clip` reads all of stdin as raw bytes and streams them to the chosen backend
tool over a pipe. The backend takes ownership of the clipboard selection.

Because Wayland (`wl-copy`) and X11 (`xclip`/`xsel`) hold the clipboard in the
copying process, the backend keeps a small helper alive in the background to
serve paste requests — this is standard behaviour for Linux clipboard tools,
not a leak.

## Design notes / limitations

- **Copy-only**, by design, to match Windows `clip`. To *read* the clipboard,
  use your backend's paste tool (`wl-paste`, `xclip -o`, `xsel -o`).
- Sets the **clipboard** selection (Ctrl-C/Ctrl-V), not the X11 primary
  (middle-click) selection.
- No clipboard access exists over pure SSH without X/Wayland forwarding or a
  running display server; `clip` will report that no backend is available.

## License

[MIT](LICENSE)
