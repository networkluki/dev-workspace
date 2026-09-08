# Changelog

All notable changes to `dev-workspace` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.0.0] - 2026-09-08

First tagged release. Establishes the top-level directory scaffolding and
bundles the first working commands for Linux, Windows, and Android/Termux.

### Added
- Repository scaffolding: `bash/`, `python/`, `powershell/`, `go/`, `linux/`,
  `windows/`, `android/`, `docker/`, `git/`, `snippets/`, `docs/`, `experiments/`.
- `linux/windows-compat-commands/` — Linux CLI tools inspired by Windows
  commands: `assoc`, `choice`, `clip`, `pause`, `sfc`, `systeminfo`.
- `windows/linux-compat-commands/exa/` — Linux-inspired file listing for
  Windows with icons, colors, tree view, and Git status (Python 3).
- `android/termux-commands/exa/` — modern `ls` replacement for Termux on
  Android (Python 3): icons, colors, tree view, Git status.
- `android/termux-commands/sysinfo/` — `systeminfo` utility that collects OS,
  hardware, and network information (Python 3).
- Root `README.md` documenting the repository structure and intended use.
- `LICENSE` (MIT).

### Notes
- Each tool ships its own `README.md` and `CHANGELOG.md` with platform
  requirements, usage, and version history.
- Directories without implementations yet contain a `.gitkeep` placeholder;
  their intended scope is described in the root `README.md`.

[v1.0.0]: https://github.com/networkluki/dev-workspace/releases/tag/v1.0.0
