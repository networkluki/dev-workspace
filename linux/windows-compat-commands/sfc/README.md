# sfc — System File Checker for Linux

A Linux counterpart to the Windows **`sfc /scannow`** command, written in Python
(standard library only, no external dependencies).

Windows' `sfc` verifies OS-protected files against a trusted component store and
repairs the corrupted ones. Linux has no single component store, but every
mainstream distribution already ships an authoritative integrity database inside
its **package manager**. `sfc` uses that database to detect files that have been
corrupted, silently modified, or deleted, and repairs them by reinstalling the
owning packages from your trusted repositories.

## How it works

| Distro family | Backend | Verification source | Repair command |
|---|---|---|---|
| Debian / Ubuntu | `dpkg` | native md5sums in `/var/lib/dpkg/info/*.md5sums` | `apt-get install --reinstall` |
| RHEL / Fedora / SUSE | `rpm` | `rpm -Va` verification database | `dnf reinstall` / `yum reinstall` |
| Arch | `pacman` | `pacman -Qkk` | `pacman -S` |

The backend is auto-detected. The dpkg backend hashes files itself (parallelised
with a thread pool) and needs no external helper such as `debsums`.

## Requirements

- Python 3.9+
- One of: `dpkg`, `rpm`, or `pacman`
- **Scanning** works as any user (files must be readable).
- **Repairing** requires **root** (it invokes the package manager), so run repair
  modes under `sudo`.

## Installation

```bash
install -m 0755 sfc.py /usr/local/bin/sfc
```

Or run it directly with `python3 sfc.py ...`.

## Usage

The command mirrors the Windows switches. Both Unix (`--scannow`) and
Windows (`/scannow`) styles are accepted.

```
sfc [--scannow | --verifyonly | --scanfile PATH | --verifyfile PATH]
    [--include-config] [--workers N] [--yes] [--no-progress] [--version]
```

| Mode | Windows equivalent | Root? | Action |
|---|---|---|---|
| `--scannow` | `/scannow` | yes | Scan everything, **repair** problems found |
| `--verifyonly` | `/verifyonly` | no | Scan everything, **report only** |
| `--scanfile PATH` | `/scanfile=PATH` | yes | Scan one file, repair if damaged |
| `--verifyfile PATH` | `/verifyfile=PATH` | no | Verify one file, report only |

Other options:

- `--include-config` — also flag modified configuration files. They are skipped
  by default, since administrators are expected to edit them.
- `--workers N` — number of parallel hashing workers (dpkg backend).
- `--yes` / `-y` — assume "yes" for the package manager's repair prompts.
- `--no-progress` — suppress the progress indicator.
- `--version` / `-V` / `-v`, `--help` / `-h`.

## Examples

```bash
# Report-only full scan (safe, no changes, no root needed)
sfc --verifyonly

# Full scan and repair (Windows-style switch also works: sudo sfc /scannow)
sudo sfc --scannow --yes

# Check a single binary
sfc --verifyfile /usr/bin/sudo

# Repair a single damaged file
sudo sfc --scanfile /usr/bin/ls
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | No integrity violations, or violations found and successfully repaired |
| `1` | Violations found (verify modes) or some repairs failed |
| `2` | Usage error, no supported backend, missing target, or insufficient privileges |
| `130` | Interrupted (Ctrl-C) |

## Notes, limitations, and security

- **Configuration files are skipped by default.** Legitimately edited config
  files would otherwise appear as violations. Use `--include-config` to audit
  them.
- **md5 is used for the dpkg backend** because that is the digest dpkg itself
  stores; it verifies *integrity against the package database*, not
  cryptographic tamper-resistance. A sufficiently privileged attacker can also
  rewrite the md5sums database. For hardened tamper detection use a dedicated
  IDS such as AIDE or dm-verity. Treat `sfc` as an operational integrity/repair
  tool, not a security boundary.
- **Repair trust boundary:** repairs pull packages from whatever repositories
  and GPG keys the host already trusts. `sfc` never adds repositories or keys.
- The tool never invokes a shell; all external commands run as argument vectors.
- A full scan hashes every packaged file and can take several minutes on a large
  install — comparable to Windows `sfc /scannow`.

## Testing

The suite is hermetic — it never touches real system files or a real package
manager (the dpkg backend is driven against a temporary fake info directory,
and repair/detection are monkeypatched).

```bash
pip install pytest
pytest -v
```

## License

MIT
