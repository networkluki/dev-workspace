# windows-compat-commands (Linux)

Linux command-line utilities that provide functionality **inspired by** familiar
Windows commands. These are original Linux implementations, written in pure
Python 3 (standard library only; one Bash helper). They are **not** the Windows
programs, do not run Windows binaries, and do not aim for byte-for-byte
compatibility — they reproduce the *purpose* and, where practical, the
*command-line feel* of their Windows namesakes using native Linux mechanisms.

> Compatibility note: where a tool mirrors a Windows switch or exit-code
> convention, that is stated explicitly and was verified against the source.
> Anything not stated should be assumed to differ. See each command's
> "Differences from Windows" section below.

## Contents

| Command | Inspired by (Windows) | One-line purpose | Version |
|---|---|---|---|
| [`assoc`](#assoc) | `assoc` | Map a file extension to a type (MIME type on Linux) | 1.0.0 |
| [`choice`](#choice) | `CHOICE` | Single-key menu selection returned as the exit code | 1.1.0 |
| [`clip`](#clip) | `clip` | Copy standard input to the system clipboard | 1.0.0 |
| [`ipconfig`](#ipconfig) | `ipconfig` | Show per-adapter TCP/IP configuration | 1.0.0 |
| [`pause`](#pause) | `pause` | Wait for a single keypress | 1.0.0 |
| [`sfc`](#sfc) | `sfc /scannow` | Verify/repair system files via the package manager | 1.0.0 |
| [`systeminfo`](#systeminfo) | `systeminfo` | Report host, OS, hardware, and network information | 1.4.0 |

Each command is self-contained in its own folder with its own `README.md` and
`CHANGELOG.md`. This document is the collection overview; open a folder for the
complete per-command reference.

## Shared design principles

- **Standard library only** for the core tools — no runtime `pip` dependencies.
- **No shell invocation** — every external command runs via an argument vector
  (`subprocess` list form), never a shell string. Input is validated with
  allowlists.
- **Least privilege** — read/scan paths work as a normal user; only operations
  that change the system (e.g. `sfc` repair) require root, and they fail closed
  when not run as root.
- **Predictable POSIX exit codes** and graceful degradation (a single failed
  metric or data source never crashes the tool).

---

## assoc

- **Original Windows command:** `assoc` — maps a file **extension** (`.txt`) to
  a **file type** stored in the Windows registry.
- **Linux implementation:** maps an extension to a **MIME type** (`text/plain`)
  using the freedesktop.org
  [`shared-mime-info`](https://specifications.freedesktop.org/shared-mime-info-spec/latest/)
  database — the Linux analogue of the registry file-type map.
- **Purpose:** query and override which MIME type an extension resolves to.
- **Syntax:**
  ```
  assoc                     List every known .ext=MIMETYPE association
  assoc .ext                Show the MIME type for one extension
  assoc .ext=MIMETYPE       Create/override a user-level association
  assoc .ext=               Remove a user-level association
  assoc --version | --help
  ```
- **Examples:**
  ```console
  $ assoc .txt
  .txt=text/plain
  $ assoc .log=text/plain
  .log=text/plain
  $ assoc .log=
  ```
- **Dependencies:** Python 3.9+. `update-mime-database` (from
  `shared-mime-info`) is required **only for writes**; reading works without it.
- **Privilege requirements:** none. Writes go only to
  `$XDG_DATA_HOME/mime/packages/assoc.xml`; system files are never touched.
- **Limitations:** removing a system-defined association is not possible at the
  user level (would require editing `/usr/share/mime` as root). Only `*.ext`
  globs participate in extension mapping.
- **Differences from Windows:** the target is a **MIME type**, not a registry
  "file type"; there is no `ftype` counterpart and no registry involvement. The
  `.ext=MIMETYPE` / `.ext=` / query syntax and the exit-code scheme
  (`0` success, `1` not found, `2` usage error) match the Windows convention.

## choice

- **Original Windows command:** `CHOICE` — waits for one key from an allowed
  set and sets `ERRORLEVEL` to the 1-based index of the chosen key.
- **Linux implementation:** identical model using `termios` raw-mode terminal
  input; returns the 1-based index as the **process exit code**.
- **Purpose:** let shell scripts branch on a single keystroke the way batch
  files branch on `ERRORLEVEL`.
- **Syntax:**
  ```
  choice [-c LIST] [-n] [-s] [-t SECONDS -d CHAR] [-m TEXT]
  ```
  Short flags mirror the Windows switches (`/C`, `/N`, `/CS`, `/T`, `/D`, `/M`).
- **Examples:**
  ```bash
  choice -c YNC -m "Yes, No or Cancel"
  case $? in 1) echo yes;; 2) echo no;; 3) echo cancel;; esac
  ```
- **Dependencies:** Python 3.8+ (standard library; `termios`).
- **Privilege requirements:** none.
- **Limitations:** requires a POSIX terminal for interactive use; when stdin is
  piped it reads one line and uses its first character. Ships bash/zsh/fish
  completion in `completions/`.
- **Differences from Windows:** exit code `1..N` (chosen index) matches Windows;
  **abort differs** — Ctrl+C/Ctrl+D returns `0` and errors return `255`
  (Windows also uses `0` for Ctrl+C but `255` only for errors). Long options
  are the primary interface; the Windows `/`-style switches are not accepted.

## clip

- **Original Windows command:** `clip` — copies standard input to the clipboard.
- **Linux implementation:** reads stdin as raw bytes and writes them **verbatim**
  (binary-safe, no newline translation) to the system clipboard, auto-detecting
  the backend.
- **Purpose:** `command | clip` / `clip < file` to put data on the clipboard.
- **Syntax:**
  ```
  clip < file          Copy a file
  command | clip       Copy command output
  clip --version | --help
  ```
- **Examples:**
  ```bash
  ls -la | clip
  echo -n hello | clip     # exact bytes, no trailing newline
  ```
- **Dependencies:** Python 3.8+ and **one** clipboard backend:
  `wl-copy` (Wayland), or `xclip` / `xsel` (X11). Backends are a fixed allowlist.
- **Privilege requirements:** none (needs a running graphical session).
- **Limitations:** copy-only, takes no text arguments (like `clip.exe`). Requires
  a display server; no clipboard on a pure headless console.
- **Differences from Windows:** behaviourally equivalent for the copy use case.
  Exit codes: `0` success, `1` backend failure, `2` no backend available.

## ipconfig

- **Original Windows command:** `ipconfig` — displays the TCP/IP network
  configuration per adapter; `ipconfig /all` shows full detail.
- **Linux implementation:** reads the iproute2 JSON interface (`ip -j addr`,
  `ip -j route`) and `/etc/resolv.conf`, then renders the data in the familiar
  Windows layout. **Read-only** — it inspects and prints network state, it never
  changes it.
- **Purpose:** a quick, Windows-style per-adapter view of addresses, masks,
  gateways, and DNS.
- **Syntax:**
  ```
  ipconfig                     Basic per-adapter IPv4/IPv6, subnet mask, gateway
  ipconfig --all               Add MAC address, DHCP status, DNS servers
  ipconfig --version | --help
  ```
  Windows-style switches are also accepted (`/all`, `/version`, `/?`).
- **Examples:**
  ```console
  $ ipconfig
  Wireless LAN adapter wlo1:
     IPv4 Address. . . . . . . . . . . : 192.168.0.19(Preferred)
     Subnet Mask . . . . . . . . . . . : 255.255.255.0
     Default Gateway . . . . . . . . . : 192.168.0.1
  $ ipconfig /all      # adds Physical Address, DHCP Enabled, DNS Servers
  ```
- **Dependencies:** Python 3.9+ and `iproute2` (the `ip` command); no
  third-party packages.
- **Privilege requirements:** none (all data sources are readable by a normal
  user).
- **Limitations:** **DHCP Enabled** is inferred from the kernel `dynamic` flag
  on an address, not queried from the network manager. **DNS Servers/suffix**
  come from `/etc/resolv.conf`, which under `systemd-resolved` may point at the
  local stub (`127.0.0.53`); use `resolvectl status` for per-link detail. The
  stateful switches `/release`, `/renew`, and `/flushdns` are **not**
  implemented (those are handled by the specific Linux network manager).
- **Differences from Windows:** the output layout mirrors Windows, but the data
  sources are Linux-native (iproute2 + resolv.conf) and the tool never mutates
  network state. Exit codes: `0` success, `1` runtime error (e.g. `ip` missing).

## pause

- **Original Windows command:** `pause` — prints a prompt and waits for any key.
- **Linux implementation:** prints the prompt and reads a single keypress from
  the controlling terminal (`/dev/tty`) in raw mode.
- **Purpose:** make a script wait for user acknowledgement.
- **Syntax:**
  ```
  pause [-m MESSAGE]
  pause --version | --help
  ```
- **Examples:**
  ```bash
  pause
  pause -m "Press any key to deploy... "
  ```
- **Dependencies:** Python 3.9+ (standard library; `termios`/`tty`).
- **Privilege requirements:** none.
- **Limitations:** with no controlling terminal it prints the prompt and returns
  immediately (mirrors Windows `pause` under redirected input).
- **Differences from Windows:** default prompt matches
  (`Press any key to continue . . .`); reading from `/dev/tty` means it keeps
  working inside a pipeline. Exit codes: `0` continue, `130` on Ctrl+C.

## sfc

- **Original Windows command:** `sfc /scannow` — verifies OS-protected files
  against a trusted component store and repairs corrupted ones.
- **Linux implementation:** verifies files against the **native package
  manager's** integrity database and repairs by **reinstalling the owning
  packages** from the configured repositories.

  | Distro family | Backend | Verification source | Repair |
  |---|---|---|---|
  | Debian/Ubuntu | `dpkg` | `/var/lib/dpkg/info/*.md5sums` (hashed natively) | `apt-get install --reinstall` |
  | RHEL/Fedora/SUSE | `rpm` | `rpm -Va` | `dnf`/`yum reinstall` |
  | Arch | `pacman` | `pacman -Qkk` | `pacman -S` |
- **Purpose:** detect and repair corrupted, modified, or deleted package-owned
  files.
- **Syntax:**
  ```
  sfc [--scannow | --verifyonly | --scanfile PATH | --verifyfile PATH]
      [--include-config] [--workers N] [--yes] [--no-progress]
  ```
  Windows-style switches are also accepted (`/scannow`, `/scanfile=/usr/bin/ls`).
- **Examples:**
  ```bash
  sfc --verifyonly              # scan, report only (no root)
  sudo sfc --scannow            # scan and repair
  sudo sfc --scanfile /usr/bin/ls
  ```
- **Dependencies:** Python 3.9+ and one of `dpkg`, `rpm`, `pacman`. The dpkg
  backend needs no external helper (no `debsums`).
- **Privilege requirements:** **scanning** (`--verifyonly`, `--verifyfile`) runs
  as any user; **repair** (`--scannow`, `--scanfile`) requires **root** and
  fails closed otherwise.
- **Limitations:** it can only verify/repair files tracked by the package
  manager — not user data, not manually installed software. Configuration files
  are skipped by default (`--include-config` to include them). Repair reinstalls
  whole packages, not individual files.
- **Differences from Windows:** the mechanism is entirely different (package
  database, not a Windows component store/WinSxS). "Repair" means package
  reinstall. Verification hashes are MD5 because that is what dpkg stores; this
  matches dpkg's own records and is not used as a security primitive.

## systeminfo

- **Original Windows command:** `systeminfo` — prints OS, hardware, and network
  configuration.
- **Linux implementation:** reads `/proc`, `/sys`, `os.statvfs`, and `utmp`
  directly to report hostname, OS, kernel, architecture, uptime, CPU, memory,
  disk, network interfaces, and logged-in users.
- **Purpose:** a dependency-free system summary for humans or automation.
- **Syntax:**
  ```
  systeminfo            Formatted, human-readable output
  systeminfo --json     Machine-readable JSON
  systeminfo --version | --help
  ```
- **Examples:** see the folder README for full sample text and JSON output
  (using placeholder host values).
- **Dependencies:** Python 3.10+ (uses `X | None` syntax). No third-party
  packages.
- **Privilege requirements:** none for the reported fields (all sources are
  world-readable on a typical system).
- **Limitations:** Linux-specific data sources; some fields (e.g. per-interface
  IPv4 via `ioctl`) are unavailable on non-Linux POSIX systems and degrade to
  empty rather than failing. Includes a `bump-version` Bash helper that relies
  on **GNU grep** (`grep -Po`).
- **Differences from Windows:** the field set and output format are Linux-native
  and do not match Windows `systeminfo`; it reports MAC/IP/logged-in users from
  `/sys` and `utmp` rather than Windows management APIs.

---

## Installation

**Packaged tools** (`assoc`, `clip` — have a `pyproject.toml`):

```bash
cd clip        # or assoc
pip install .
```

**Single-file scripts** (`choice`, `ipconfig`, `pause`, `sfc`, `systeminfo`):

```bash
install -m 0755 systeminfo/systeminfo ~/.local/bin/systeminfo   # example
```

See each command's own `README.md` for the exact, recommended steps.

## Versioning

The collection and each command follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html); each command keeps a
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/)-style `CHANGELOG.md`.
Command versions are tracked independently; the collection's own history is in
[`CHANGELOG.md`](CHANGELOG.md).
