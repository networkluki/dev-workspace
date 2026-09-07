# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-09-07

### Added
- Shell completion for bash, zsh, and fish (`completions/choice.bash`,
  `completions/_choice`, `completions/choice.fish`). All three complete every
  short and long option and offer the individual characters of the current
  `-c`/`--choices` value (space or `=` form) as candidates for `-d`/`--default`,
  defaulting to the `YN` set when no choices are given.

[1.1.0]: https://example.com/choice/releases/tag/v1.1.0

## [1.0.1] - 2026-09-07

### Fixed
- Arrow keys and other ANSI escape sequences (function keys, Home/End, etc.) are
  now fully consumed and ignored on a terminal. Previously only the leading ESC
  byte was read, so the trailing bytes (e.g. the `A`/`B`/`C`/`D` of an arrow
  key) could be misread as separate keypresses and accidentally match a valid
  choice. The Escape key alone is also ignored.

### Changed
- The terminal is now put into raw mode once for the whole prompt instead of
  per keystroke. This closes a race where a keystroke arriving immediately after
  the prompt (very fast typing or pasted input) could be echoed and
  line-buffered by the terminal in canonical mode. Accepted keys are echoed with
  an explicit CR+LF since output post-processing is disabled in raw mode.

### Added
- `test_arrows.py`: a PTY-based test covering arrow keys, `Ctrl`+arrow, the bare
  Escape key, a plain key selection, and `Ctrl+C` abort.

[1.0.1]: https://example.com/choice/releases/tag/v1.0.1

## [1.0.0] - 2026-09-07

### Added
- Initial release of `choice`, a Linux/Python reimplementation of the Windows
  `CHOICE` command.
- Single-key selection on a real terminal (TTY) with no Enter required, using
  `termios`/`tty` raw mode.
- Non-interactive (piped stdin) mode: uses the first character of input, or the
  configured default when input is empty.
- Windows-compatible exit codes: `1..N` for the 1-based selection index, `0` on
  abort (Ctrl+C / Ctrl+D), `255` on error.
- Options mirroring the Windows switches:
  - `-c/--choices` (default `YN`)
  - `-n/--no-prompt` to hide the choice list
  - `-s/--case-sensitive` matching (default is case-insensitive)
  - `-t/--timeout` (0–9999 seconds) with `-d/--default`
  - `-m/--message` prompt text
  - `-V/--version` and `-h/--help`
- Argument validation with `255` exit code: empty choices, non-printable or
  whitespace choices, duplicate choices, `--timeout`/`--default` used
  independently, out-of-range timeout, and default not in the choices list.

[Unreleased]: https://example.com/choice/compare/v1.0.0...HEAD
[1.0.0]: https://example.com/choice/releases/tag/v1.0.0
