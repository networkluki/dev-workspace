# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-09-07

### Added

- Initial release: a Linux port of the Windows `clip` command that copies
  standard input to the system clipboard.
- Binary-safe stdin-to-clipboard transfer (no decoding or newline translation).
- Automatic backend detection with session-aware ordering:
  - Wayland: `wl-copy`
  - X11: `xclip`, then `xsel`
- `-V` / `--version` and `-h` / `--help` options.
- Interactive hint when stdin is a terminal (read until Ctrl-D).
- Predictable exit codes: `0` success, `1` copy/read failure, `2` no backend.
- Backend timeout to fail loudly instead of hanging a pipeline.
- Packaging via `pyproject.toml` exposing the `clip` console script and
  `python -m clip` module execution.
- README and MIT license.

[Unreleased]: https://github.com/luki/clip-linux/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/luki/clip-linux/releases/tag/v1.0.0
