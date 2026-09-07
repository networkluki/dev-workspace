# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Lowercase `-v` as an alias for `--version` (alongside `-V`).
- `test_sfc.py`: hermetic pytest suite (35 tests) covering hashing, the dpkg
  backend scan (clean / corrupted / missing / arch-suffix / config-skip /
  targeting), Windows-switch translation including the absolute-path
  regression, backend detection, and the full `main()` flow with a stubbed
  backend.

## [1.0.0] - 2026-09-07

### Added
- Initial release of `sfc`, a Linux System File Checker modeled on Windows
  `sfc /scannow`.
- Auto-detecting package-manager backends:
  - **dpkg** (Debian/Ubuntu): native md5sums verification with a parallel
    hashing thread pool; repair via `apt-get install --reinstall`.
  - **rpm** (RHEL/Fedora/SUSE): verification via `rpm -Va` / `rpm -Vf`; repair
    via `dnf reinstall` or `yum reinstall`.
  - **pacman** (Arch): verification via `pacman -Qkk`; repair via `pacman -S`.
- Operating modes mirroring the Windows switches: `--scannow`, `--verifyonly`,
  `--scanfile PATH`, `--verifyfile PATH`.
- Windows-style switch aliases (`/scannow`, `/verifyonly`, `/scanfile=...`,
  `/verifyfile=...`).
- `--include-config` to optionally verify configuration files (skipped by
  default), `--workers` to tune hashing concurrency, `--yes` for
  non-interactive repair, `--no-progress`, `--version`.
- Root-privilege enforcement for repair operations.
- Defined exit codes (`0` clean/repaired, `1` violations/partial failure,
  `2` usage/environment error, `130` interrupted).
- `README.md` documenting backends, usage, exit codes, and security caveats.

[1.0.0]: https://example.com/sfc/releases/tag/v1.0.0
