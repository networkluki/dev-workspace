# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-07

### Added

- Initial release: a Linux clone of the Windows `assoc` command, mapping file
  extensions to MIME types via the freedesktop.org shared-mime-info database.
- `assoc` — list every known `.ext=MIMETYPE` association, sorted by extension.
- `assoc .ext` — query the MIME type for a single extension.
- `assoc .ext=MIMETYPE` — create or override an association at the user level.
- `assoc .ext=` — remove a user-created association (reverting to the system
  default where one exists).
- `--version` / `-V` and `--help` flags.
- Input validation with strict allowlists for extensions and MIME types.
- Hardened XML handling: rejects `DOCTYPE` declarations to prevent XXE and
  entity-expansion attacks; no external entity resolution.
- Windows-compatible exit codes: `0` success, `1` not found / failure,
  `2` usage error.
- `README.md` documenting behavior, the user-scope removal caveat, and
  differences from Windows `assoc`.
- `pyproject.toml` exposing the `assoc` console entry point.

[1.0.0]: https://example.com/assoc/releases/tag/v1.0.0
