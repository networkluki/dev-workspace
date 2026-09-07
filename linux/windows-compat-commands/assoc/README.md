# assoc

A Linux clone of the Windows [`assoc`](https://learn.microsoft.com/windows-server/administration/windows-commands/assoc)
command, written in Python (standard library only).

On Windows, `assoc` maps a file **extension** (`.txt`) to a **file type**
stored in the registry. The Linux equivalent of that "file type" is a **MIME
type** (`text/plain`) resolved through the freedesktop.org
[shared-mime-info](https://specifications.freedesktop.org/shared-mime-info-spec/latest/)
database. `assoc` therefore maps extensions to MIME types using the same
command-line syntax as Windows.

## Requirements

- Python 3.9+ (no third-party packages)
- `update-mime-database` (from `shared-mime-info`) — required only for
  modifying associations. Reading works without it.

`update-mime-database` is present on essentially every desktop Linux install.
On a headless server: `apt install shared-mime-info` /
`dnf install shared-mime-info`.

## Usage

```
assoc                       List every known .ext=MIMETYPE association
assoc .txt                  Show the MIME type associated with .txt
assoc .txt=text/plain       Associate .txt with text/plain
assoc .txt=                 Remove the .txt association (user overrides only)
assoc --version             Print the version
assoc --help                Show help
```

### Examples

```console
$ assoc .txt
.txt=text/plain

$ assoc .log=text/plain
.log=text/plain

$ assoc .log
.log=text/plain

$ assoc .log=
$ assoc .log
File association not found for extension .log
```

Exit codes mirror the Windows tool: `0` on success, `1` when an association is
not found or an operation fails, `2` on a command-line usage error.

## How it works

- **Reading** (`assoc`, `assoc .ext`) parses the merged `globs2` files from
  every directory in `$XDG_DATA_DIRS` plus `$XDG_DATA_HOME` — the same database
  the desktop uses. When several MIME types claim one extension, the entry with
  the highest weight wins; on a tie the user's database wins, matching the
  freedesktop resolution order.
- **Writing** (`assoc .ext=type`, `assoc .ext=`) edits only the current user's
  MIME package at `$XDG_DATA_HOME/mime/packages/assoc.xml`
  (default `~/.local/share/mime/packages/assoc.xml`) and then runs
  `update-mime-database` on `~/.local/share/mime`. This never requires root and
  never modifies system files.

## Important caveat: removal is user-scoped

`assoc .ext=` removes an association **only if this tool created it** at the
user level. An extension defined by the *system* database
(`/usr/share/mime`, e.g. `.html`) cannot be removed without editing system
files as root, so `assoc` refuses and tells you why:

```console
$ assoc .html=
assoc: error: .html is defined by the system MIME database and cannot be
removed at the user level (needs root to edit /usr/share/mime)
```

You *can*, however, override such an extension to a different MIME type at the
user level (`assoc .html=text/plain`), and later revert to the system default
with `assoc .html=`.

## Differences from Windows `assoc`

| Aspect | Windows | This tool |
| --- | --- | --- |
| "File type" | Registry ProgID (`txtfile`) | MIME type (`text/plain`) |
| Scope of writes | System-wide (needs admin) | Current user only (no root) |
| Backing store | Registry `HKEY_CLASSES_ROOT` | freedesktop shared-mime-info |
| Remove system default | Yes (as admin) | No (user scope only) — see caveat |

`assoc` maps extensions to MIME types. It does **not** set the *default
application* that opens a file — that is a separate concept on Linux
(`xdg-mime default <app>.desktop <mimetype>`).

## Installation

Run it directly:

```bash
python3 assoc.py .txt
```

Or install the `assoc` command:

```bash
pip install .
assoc .txt
```

## Security notes

- All user input is validated against strict allowlists before use: extensions
  must match `^\.[A-Za-z0-9][A-Za-z0-9._+-]*$` and MIME types must match the
  RFC 6838 token grammar. This prevents injection into the MIME package XML.
- The user MIME package is built with `xml.etree.ElementTree`, which never
  fetches external entities. On read-back, any file containing a `DOCTYPE`
  declaration is rejected before parsing, closing XXE and internal-entity
  ("billion laughs") expansion.
- Writes are confined to `$XDG_DATA_HOME`; the tool runs with the invoking
  user's privileges and never escalates.

## License

MIT — see below or add a `LICENSE` file as needed.
