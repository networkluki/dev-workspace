# systeminfo

A dependency-free Linux system information CLI written in pure Python 3.

Reads `/proc`, `/sys`, and `utmp` directly, degrades gracefully when a data
source is unavailable, and never crashes on a single failed metric.

## Requirements

- Linux
- Python **3.10+** (uses PEP 604 `X | None` type syntax)
- No third-party packages — standard library only

## Installation

The script is self-contained. Make it executable and symlink it into a
directory on your `PATH`.

**Per-user (no sudo)** — recommended if `~/.local/bin` is on your `PATH`:

```bash
chmod +x systeminfo
ln -sf "$(pwd)/systeminfo" ~/.local/bin/systeminfo
```

**System-wide (requires sudo):**

```bash
chmod +x systeminfo
sudo ln -s "$(pwd)/systeminfo" /usr/local/bin/systeminfo
```

The symlink always points at the script in this repository, so future edits
take effect with no reinstall.

> If your current shell still reports `command not found` right after linking,
> it has cached the old lookup. Run `hash -r` or open a new terminal.

## Usage

```bash
systeminfo            # formatted, human-readable output
systeminfo --json     # machine-readable JSON (for automation / monitoring)
systeminfo --version  # print version and exit
systeminfo --help     # usage
```

### Example (text)

```
Hostname     : server01
OS           : Ubuntu 26.04.1 LTS
Kernel       : Linux 7.0.0-31-generic
Architecture : x86_64
Uptime       : 3d 4h 12m
CPU          : Intel(R) Core(TM) i5-2450M CPU @ 2.50GHz (4 cores)
Load avg     : 0.72, 0.66, 0.73
Memory       : 6.1 GiB / 11.0 GiB (55.7%)
Disk (/)     : 85.8 GiB / 3.6 TiB (2.3%)
Interfaces   :
  eth0         up      de:ad:be:ef:00:01 10.0.0.10, fe80::1
  lo           unknown 00:00:00:00:00:00 127.0.0.1, ::1
Logged in    :
  alice  (pts/0)  since 2026-09-07 15:04 from 10.0.0.20
```

## Reported fields

| Field          | Source                       | Notes                                    |
|----------------|------------------------------|------------------------------------------|
| Hostname       | `socket.gethostname()`       |                                          |
| OS             | `/etc/os-release`            | `PRETTY_NAME`, falls back to `NAME`      |
| Kernel         | `platform`                   |                                          |
| Architecture   | `platform.machine()`         |                                          |
| Uptime         | `/proc/uptime`               |                                          |
| CPU            | `/proc/cpuinfo`, `os.getloadavg()` | Model, logical core count, load avg |
| Memory         | `/proc/meminfo`              | Used = total − available (bytes)         |
| Disk (`/`)     | `os.statvfs("/")`            | Root filesystem usage (bytes)            |
| Interfaces     | `/sys/class/net`, ioctl, `/proc/net/if_inet6` | Name, MAC, state, IPv4, IPv6 |
| Logged in      | `/var/run/utmp`              | Active `USER_PROCESS` sessions           |

## JSON output

`--json` emits the full structure plus a `collected_at` ISO-8601 timestamp.
Byte-valued fields (memory, disk) are raw integers; format them downstream.

```json
{
  "hostname": "server01",
  "os": { "name": "Ubuntu 26.04.1 LTS", "version": "26.04" },
  "kernel": "Linux 7.0.0-31-generic",
  "architecture": "x86_64",
  "uptime_seconds": 274320.0,
  "cpu": { "model": "...", "cores": 4, "load": [0.72, 0.66, 0.73] },
  "memory": { "total": 11847208960, "available": 5245698048, "used": 6601510912 },
  "disk": { "total": 3934684045312, "used": 92171399168, "free": 3642565144576 },
  "network": [
    { "name": "eth0", "mac": "de:ad:be:ef:00:01", "state": "up",
      "ipv4": "10.0.0.10", "ipv6": ["fe80::1"] }
  ],
  "users": [
    { "user": "alice", "tty": "pts/0", "host": "10.0.0.20", "login_time": 1757250240 }
  ],
  "collected_at": "2026-09-07T16:41:33+0200"
}
```

## Versioning

Semantic versioning — `MAJOR.MINOR.PATCH`:

- **MAJOR** — large / breaking changes
- **MINOR** — medium changes (new features, backward compatible)
- **PATCH** — small changes (bug fixes)

| Version | Change                                                        |
|---------|---------------------------------------------------------------|
| 1.4.0   | Add bump-version helper and development docs                  |
| 1.3.0   | Added network interfaces and logged-in users                  |
| 1.2.0   | Initial release: host, OS, kernel, uptime, CPU, memory, disk  |

## Development

### Bumping the version

The version is stored in `__version__` in the `systeminfo` script and mirrored
in the changelog table above. Use the `bump-version` helper to update both in
one step:

```bash
./bump-version <level> ["changelog message"]
```

`<level>` selects which part of `MAJOR.MINOR.PATCH` to increment and accepts
three equivalent spellings:

| Level             | Effect          | Example         |
|-------------------|-----------------|-----------------|
| `major` `1` `stora` | `X+1.0.0`     | 1.3.0 → 2.0.0   |
| `minor` `2` `medel` | `X.Y+1.0`     | 1.3.0 → 1.4.0   |
| `patch` `3` `sma`   | `X.Y.Z+1`     | 1.3.0 → 1.3.1   |

Examples:

```bash
./bump-version minor "Add swap usage"   # bumps code version + adds changelog row
./bump-version 3 "Fix IPv6 parsing"     # patch bump via numeric alias
./bump-version patch                     # code version only, no changelog row
```

The helper validates the current version before changing anything and writes
atomically (temp file + `mv`), so an interrupted run leaves files intact. It
does not create a git commit — review with `git diff`, then commit yourself.

## Limitations

These are deliberate trade-offs to keep the tool at zero dependencies:

- **One IPv4 per interface.** `ioctl(SIOCGIFADDR)` returns only the primary
  IPv4; secondary aliases are not listed. Use `ip addr` for the full set.
- **utmp is assumed little-endian.** Correct on x86-64 / ARM64; records would
  be misread on big-endian platforms (e.g. s390x).
- **musl / Alpine** often does not populate `utmp`, so `Logged in` may be empty
  even with active sessions (matches `who` behavior there).
- **Root filesystem only.** Disk usage covers `/`, not every mounted volume.
