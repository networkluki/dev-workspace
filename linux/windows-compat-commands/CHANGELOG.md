# Changelog

All notable changes to the `windows-compat-commands` collection are documented
in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file tracks the **collection as a whole**. Each command additionally keeps
its own `CHANGELOG.md`; the versions below are those bundled at each collection
release.

## [Unreleased]

## [1.0.0] - 2026-09-07

### Added

- Initial release of the `windows-compat-commands` collection under
  `linux/`: dependency-free Linux CLI tools that provide functionality inspired
  by familiar Windows commands (pure Python 3 standard library; one Bash
  helper).
- Collection `README.md` documenting, for each command, the Windows command it
  is inspired by, the Linux implementation, purpose, syntax, examples,
  dependencies, limitations, privilege requirements, and differences from the
  Windows implementation.
- Bundled commands at this release:
  - `assoc` **1.0.0** — map file extensions to MIME types via freedesktop
    `shared-mime-info` (inspired by Windows `assoc`).
  - `choice` **1.1.0** — single-key selection returned as the exit code, with
    timeout/default, case sensitivity, and bash/zsh/fish completion (inspired by
    Windows `CHOICE`).
  - `clip` **1.0.0** — copy standard input verbatim to the system clipboard via
    `wl-copy`/`xclip`/`xsel` (inspired by Windows `clip`).
  - `pause` **1.0.0** — wait for a single keypress via `/dev/tty`, redirection
    safe (inspired by Windows CMD `pause`).
  - `sfc` **1.0.0** — verify and repair package-owned files via
    `dpkg`/`rpm`/`pacman` (inspired by Windows `sfc /scannow`).
  - `systeminfo` **1.4.0** — Linux-native host/OS/CPU/memory/disk/network report
    with text and `--json` output (inspired by Windows `systeminfo`).

### Security

- Sanitized example host data in `systeminfo/README.md` (MAC address, private
  IPs, and username replaced with placeholders) prior to publication.
- Replaced a personal contact email in `clip/pyproject.toml` packaging metadata
  with a public project address.

[Unreleased]: https://github.com/networkluki/dev-workspace
[1.0.0]: https://github.com/networkluki/dev-workspace
