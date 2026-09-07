# choice

A Linux/Python reimplementation of the Windows `CHOICE` command.

`choice` prompts the user to select one item from a list of single-character
options and returns the **1-based index** of the selection as the process
**exit code** — exactly like the Windows `ERRORLEVEL` convention. This lets
shell scripts branch on the exit code the same way batch files do.

- **Version:** 1.0.0
- **Requirements:** Python 3.8+ (standard library only, no dependencies)
- **Platform:** Linux / macOS / any POSIX terminal (uses `termios`)

---

## What is `choice` on Windows?

`CHOICE` is a built-in Windows command-line utility. It displays a prompt,
waits for the user to press a single key from an allowed set (without pressing
Enter), and sets `ERRORLEVEL` to the position of the pressed key in the list.

### Windows syntax

```
CHOICE [/C choices] [/N] [/CS] [/T timeout /D default] [/M "text"]
```

| Switch        | Meaning                                                             |
|---------------|--------------------------------------------------------------------|
| `/C choices`  | Set of allowed keys. Default is `YN`.                               |
| `/N`          | Hide the choice list in the prompt (keys still work).              |
| `/CS`         | Case-sensitive matching. Default is case-insensitive.              |
| `/T timeout`  | Seconds (0–9999) to wait before choosing the default.             |
| `/D default`  | Default key selected when the timeout expires. Requires `/T`.      |
| `/M "text"`   | Message shown before the prompt.                                   |
| `/?`          | Show help.                                                          |

### Windows exit codes (`ERRORLEVEL`)

| Code    | Meaning                                            |
|---------|----------------------------------------------------|
| `1..N`  | 1-based index of the chosen key in the list.       |
| `0`     | User pressed Ctrl+C / Ctrl+Break.                  |
| `255`   | An error occurred.                                 |

### Windows example

```bat
CHOICE /C YNC /M "Yes, No or Cancel"
IF ERRORLEVEL 3 GOTO cancel
IF ERRORLEVEL 2 GOTO no
IF ERRORLEVEL 1 GOTO yes
```

> Note: In batch, `IF ERRORLEVEL n` means "code is **n or greater**", so the
> checks are written from highest to lowest.

---

## This Linux implementation

The switch semantics are mirrored with POSIX-style options.

| Windows   | This tool                     |
|-----------|-------------------------------|
| `/C`      | `-c`, `--choices`             |
| `/N`      | `-n`, `--no-prompt`           |
| `/CS`     | `-s`, `--case-sensitive`      |
| `/T`      | `-t`, `--timeout`             |
| `/D`      | `-d`, `--default`             |
| `/M`      | `-m`, `--message`             |
| `/?`      | `-h`, `--help`                |
| —         | `-V`, `--version`             |

### Exit codes

| Code    | Meaning                                             |
|---------|-----------------------------------------------------|
| `1..N`  | 1-based index of the chosen key.                    |
| `0`     | User aborted with Ctrl+C or Ctrl+D.                 |
| `255`   | Error (invalid arguments or terminal I/O failure).  |

### Behavior notes

- On a real terminal (TTY), a **single keypress** is read immediately — no
  Enter required, matching Windows.
- When stdin is **piped** (not a TTY), the first character of the first input
  line is used as the selection; if input is empty and a default is set, the
  default is used. This makes the tool scriptable and testable.
- Invalid keys are ignored on a TTY (the prompt keeps waiting).
- Arrow keys, function keys, Home/End and the bare Escape key are recognized as
  ANSI escape sequences, fully consumed, and ignored — they can never
  accidentally select a choice (e.g. the right arrow `ESC [ C` does not pick
  `C`). Raw mode is entered once for the whole prompt so even fast or pasted
  keystrokes are handled consistently.
- Choices must be printable, non-whitespace, and unique (uniqueness honors the
  case-sensitivity setting).

---

## Installation

No dependencies. Copy the script somewhere on your `PATH`:

```bash
sudo install -m 0755 choice.py /usr/local/bin/choice
```

Or run it directly:

```bash
./choice.py --help
```

### Shell completion

Completion scripts for **bash**, **zsh**, and **fish** are provided in
`completions/`. All three complete every option and, for `-d`/`--default`, offer
the individual characters of the `-c`/`--choices` value already on the command
line (defaulting to `YN`).

**bash** (`completions/choice.bash`):

```bash
# System-wide (requires the bash-completion package):
sudo cp completions/choice.bash /usr/share/bash-completion/completions/choice
# Per user:
cp completions/choice.bash ~/.local/share/bash-completion/completions/choice
# Ad hoc for the current shell only:
source completions/choice.bash
```

**zsh** (`completions/_choice`):

```zsh
# System-wide (a directory already on $fpath):
sudo cp completions/_choice /usr/share/zsh/site-functions/_choice
# Per user: place it in a directory added to $fpath before `compinit`, e.g.:
cp completions/_choice ~/.zsh/completions/_choice
#   in ~/.zshrc, before `autoload -Uz compinit && compinit`:
#     fpath=(~/.zsh/completions $fpath)
```

**fish** (`completions/choice.fish`):

```fish
# Per user:
cp completions/choice.fish ~/.config/fish/completions/choice.fish
# System-wide:
sudo cp completions/choice.fish /usr/share/fish/vendor_completions.d/choice.fish
```

If you installed the executable under a different name (e.g. `choice.py`), see
the header of each completion script for how to register the alternate name.

---

## Usage

```
choice [-c LIST] [-n] [-s] [-t SECONDS] [-d CHAR] [-m TEXT]
```

### Examples

Yes/No prompt (default choices):

```bash
choice -m "Continue?"
# -> "Continue? [Y,N]? "
```

Yes/No/Cancel and branch on the result:

```bash
choice -c YNC -m "Yes, No or Cancel"
case $? in
  1) echo "yes" ;;
  2) echo "no" ;;
  3) echo "cancel" ;;
  0) echo "aborted" ;;
  255) echo "error" ;;
esac
```

Auto-select a default after a timeout:

```bash
choice -c YN -t 5 -d N -m "Reboot now? Defaults to No in 5s"
```

Hide the choice list:

```bash
choice -c YN -n -m "Press Y or N"
```

Case-sensitive matching:

```bash
choice -c aAbB -s -m "Pick one"
```

---

## Testing

The piped (non-TTY) path makes the tool easy to test from a shell:

```bash
printf 'Y\n' | choice -c YN;      echo "exit=$?"   # exit=1
printf 'N\n' | choice -c YN;      echo "exit=$?"   # exit=2
printf ''    | choice -t 1 -d N;  echo "exit=$?"   # exit=2 (default)
```

---

## License

Released into the public domain (see project metadata). Use freely.
