# Changelog

All notable changes to this project are documented in this file.

The version scheme is `MAJOR.MEDIUM.MINOR`:

- **MAJOR** — large / breaking changes
- **MEDIUM** — medium-sized feature changes
- **MINOR** — small changes and fixes

## [1.0.0] - 2026-09-09

### Added

- Windows-style `ipconfig` output for Linux, built on `iproute2` (`ip -j`).
- Default view: per-adapter IPv4 address, subnet mask, IPv6 addresses and
  default gateway, plus host name and primary DNS suffix.
- `--all` / `/all`: full view adding physical (MAC) address, inferred DHCP
  status and DNS servers.
- `--version` / `-V`: prints the program version.
- `--help` / `-h` / `/?`: usage help.
- Acceptance of both POSIX (`--all`) and Windows-style (`/all`) switches.
- Adapter classification (Ethernet, Wireless LAN, Loopback, Tunnel, Virtual).
- Media-disconnected detection for adapters without a global address.
