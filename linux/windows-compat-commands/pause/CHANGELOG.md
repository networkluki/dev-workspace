# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-09-07

### Added
- Initial release: a Linux/Python replica of the Windows CMD `pause` command.
- Waits for any single keypress using raw terminal mode (`termios`/`tty`).
- Default prompt `Press any key to continue . . .`, matching Windows `pause`.
- Reads the keypress from the controlling terminal (`/dev/tty`), so it works
  even when `stdin`/`stdout` are redirected.
- `-m/--message` option for a custom prompt.
- `-V/--version` and `-h/--help` options.
- POSIX exit codes: `0` on continue, `130` on `Ctrl-C`.
- Graceful fallback that continues immediately when no terminal is available.
- `README.md` with usage, installation, and exit-code documentation.

[Unreleased]: https://example.com/pause/compare/v1.0.0...HEAD
[1.0.0]: https://example.com/pause/releases/tag/v1.0.0
