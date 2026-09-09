# ipconfig (Linux)

A Windows-style `ipconfig` command for Linux, written in Python. It prints
your network configuration in the familiar Windows layout using data from
`iproute2` and the system resolver.

It is **read-only**: it inspects and displays network state, it never changes it.

## Requirements

- Python 3.9 or newer (uses only the standard library)
- `iproute2` (the `ip` command) — standard on virtually all Linux distributions

## Installation

Make the script executable and place it on your `PATH`:

```bash
chmod +x ipconfig.py
sudo install -m 0755 ipconfig.py /usr/local/bin/ipconfig
```

You can now run `ipconfig` from anywhere.

## Usage

| Command                       | Description                                             |
| ----------------------------- | ------------------------------------------------------- |
| `ipconfig`                    | Show basic configuration (IP, mask, gateway) per adapter |
| `ipconfig --all` / `/all`     | Show full configuration (MAC, DHCP status, DNS servers) |
| `ipconfig --version` / `-V`   | Show the program version                                |
| `ipconfig --help` / `-h` / `/?` | Show help                                             |

Both POSIX (`--all`) and Windows-style (`/all`) switches are accepted.

### Example

```text
$ ipconfig

Linux IP Configuration

   Host Name . . . . . . . . . . . . . . : hackwell
   Primary Dns Suffix . . . . . . . . .  : home

Wireless LAN adapter wlo1:

   Connection-specific DNS Suffix . . .  : home
   IPv4 Address . . . . . . . . . . . .  : 192.168.0.19(Preferred)
   Subnet Mask . . . . . . . . . . . . . : 255.255.255.0
   Link-local IPv6 Address . . . . . . . : fe80::d2df:9aff:fe71:af43%wlo1(Preferred)
   Default Gateway . . . . . . . . . . . : 192.168.0.1
```

## Versioning

The version number follows a three-part scheme `MAJOR.MEDIUM.MINOR`:

| Position | Name   | Meaning                          |
| -------- | ------ | -------------------------------- |
| 1st      | MAJOR  | Large / breaking changes         |
| 2nd      | MEDIUM | Medium-sized feature changes     |
| 3rd      | MINOR  | Small changes and fixes          |

Run `ipconfig --version` to see the current version. All notable changes are
recorded in [CHANGELOG.md](CHANGELOG.md).

## Notes and limitations

- **DHCP Enabled** is inferred from the kernel `dynamic` flag on an address
  (set when the address was obtained via DHCP). It is a best-effort indicator,
  not a query of the network manager's configuration.
- **DNS Servers** and the **DNS suffix** are read from `/etc/resolv.conf`.
  On systems using `systemd-resolved` this file may point at a local stub
  resolver (e.g. `127.0.0.53`); use `resolvectl status` for per-link detail.
- Stateful Windows switches (`/release`, `/renew`, `/flushdns`) are **not**
  implemented, because those operations are handled by the specific Linux
  network manager (NetworkManager, systemd-networkd, dhclient) rather than by
  a single portable command.
