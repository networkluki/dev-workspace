#!/usr/bin/env python3
"""assoc - display or modify file extension associations on Linux.

A Linux clone of the Windows ``assoc`` command. On Windows, ``assoc`` maps a
file extension (``.txt``) to a "file type" stored in the registry. The Linux
analog of that "file type" is a MIME type (``text/plain``) resolved through the
freedesktop.org shared-mime-info database.

This tool therefore maps extensions to MIME types:

    assoc                       List every known extension=MIMETYPE
    assoc .txt                  Show the MIME type for .txt
    assoc .txt=text/plain       Associate .txt with text/plain
    assoc .txt=                 Remove the .txt association (user overrides)

Associations are read from every directory in ``$XDG_DATA_DIRS`` plus
``$XDG_DATA_HOME`` (the merged freedesktop MIME database). Modifications are
written only to the current user's MIME database
(``$XDG_DATA_HOME/mime/packages/assoc.xml``), so the command never requires
root and never touches system files. See README.md for the removal caveat.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

__version__ = "1.0.0"

# freedesktop shared-mime-info package namespace.
_NS = "http://www.freedesktop.org/standards/shared-mime-info"
_MIME_INFO = f"{{{_NS}}}mime-info"
_MIME_TYPE = f"{{{_NS}}}mime-type"
_GLOB = f"{{{_NS}}}glob"

# Validation allowlists (server-side / trusted-input hygiene: everything the
# user passes is treated as untrusted and must match before it is used).
#
# Extension: leading dot, then a filename-safe body. Dots are allowed so that
# multi-part extensions such as ".tar.gz" work.
_EXT_RE = re.compile(r"^\.[A-Za-z0-9][A-Za-z0-9._+-]*$")
# MIME type: type/subtype using the RFC 6838 token character set.
_MIME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$")
# A glob we understand: "*.ext". Only these participate in extension mapping.
_STAR_GLOB_RE = re.compile(r"^\*(\.[^/]+)$")


def _eprint(message: str) -> None:
    """Write an error message to stderr."""
    print(message, file=sys.stderr)


@dataclass(frozen=True)
class _Entry:
    """A resolved extension -> MIME type mapping and its source priority."""

    mimetype: str
    weight: int
    priority: int  # 0 = system data dir, 1 = user data dir (wins ties).


def _data_home() -> Path:
    """Return $XDG_DATA_HOME with the freedesktop default fallback."""
    value = os.environ.get("XDG_DATA_HOME", "").strip()
    if value:
        return Path(value)
    return Path.home() / ".local" / "share"


def _data_dirs() -> list[Path]:
    """Return $XDG_DATA_DIRS with the freedesktop default fallback."""
    value = os.environ.get("XDG_DATA_DIRS", "").strip()
    if not value:
        value = "/usr/local/share:/usr/share"
    return [Path(p) for p in value.split(":") if p]


def _mime_dirs() -> list[tuple[Path, int]]:
    """Return (mime dir, priority) pairs, system first then the user dir.

    Later entries (higher priority number) win ties during resolution.
    """
    dirs: list[tuple[Path, int]] = []
    # System directories: reverse so that, per the freedesktop spec, earlier
    # $XDG_DATA_DIRS entries take precedence over later ones.
    for data_dir in reversed(_data_dirs()):
        dirs.append((data_dir / "mime", 0))
    dirs.append((_data_home() / "mime", 1))
    return dirs


def _parse_globs2(path: Path) -> Iterable[tuple[str, str, int]]:
    """Yield (extension, mimetype, weight) triples from a globs2 file.

    globs2 lines look like ``weight:mimetype:glob[:flags]``. Only globs of the
    form ``*.ext`` are relevant to extension association; everything else
    (literal names, ``*`` prefixes with paths, etc.) is ignored.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) < 3:
            continue
        weight_str, mimetype, glob = parts[0], parts[1], parts[2]
        try:
            weight = int(weight_str)
        except ValueError:
            continue
        match = _STAR_GLOB_RE.match(glob)
        if not match:
            continue
        yield match.group(1), mimetype, weight


def _load_associations() -> dict[str, _Entry]:
    """Build the merged extension -> MIME type map across all MIME dirs.

    Resolution mirrors the freedesktop rule: higher weight wins; on equal
    weight the higher-priority directory (the user's) wins.
    """
    result: dict[str, _Entry] = {}
    for mime_dir, priority in _mime_dirs():
        globs2 = mime_dir / "globs2"
        for ext, mimetype, weight in _parse_globs2(globs2):
            current = result.get(ext)
            if current is None or (weight, priority) > (current.weight, current.priority):
                result[ext] = _Entry(mimetype=mimetype, weight=weight, priority=priority)
    return result


def _user_package_path() -> Path:
    """Path to this tool's user-level MIME package file."""
    return _data_home() / "mime" / "packages" / "assoc.xml"


def _load_user_package() -> ET.ElementTree:
    """Load the user MIME package, or create an empty one in memory.

    Defense in depth: stdlib ElementTree never fetches external entities, and
    a DOCTYPE is required for internal-entity ("billion laughs") expansion, so
    we refuse any file containing one before parsing. Our own writer never
    emits a DOCTYPE, so a well-formed assoc package is always accepted.
    """
    path = _user_package_path()
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _eprint(f"assoc: error: cannot read {path}: {exc}")
            raise SystemExit(1)
        if re.search(r"<!DOCTYPE", text, re.IGNORECASE):
            _eprint(f"assoc: error: refusing to parse {path}: it contains a DOCTYPE declaration")
            raise SystemExit(1)
        try:
            root = ET.fromstring(text)
            if root.tag == _MIME_INFO:
                return ET.ElementTree(root)
            _eprint(f"assoc: warning: {path} is not a valid MIME package; recreating it")
        except ET.ParseError:
            _eprint(f"assoc: warning: {path} is malformed; recreating it")
    return ET.ElementTree(ET.Element(_MIME_INFO))


def _find_mime_type(root: ET.Element, mimetype: str) -> ET.Element | None:
    for element in root.findall(_MIME_TYPE):
        if element.get("type") == mimetype:
            return element
    return None


def _remove_glob_everywhere(root: ET.Element, pattern: str) -> bool:
    """Remove ``pattern`` from every mime-type; drop now-empty mime-types.

    Returns True if anything was removed.
    """
    removed = False
    for mime_type in list(root.findall(_MIME_TYPE)):
        for glob in list(mime_type.findall(_GLOB)):
            if glob.get("pattern") == pattern:
                mime_type.remove(glob)
                removed = True
        if mime_type.find(_GLOB) is None:
            root.remove(mime_type)
    return removed


def _write_and_refresh(tree: ET.ElementTree) -> None:
    """Persist the user package and rebuild the user MIME database."""
    path = _user_package_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.register_namespace("", _NS)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)

    mime_dir = path.parent.parent  # .../mime
    update_bin = shutil.which("update-mime-database")
    if update_bin is None:
        _eprint(
            "assoc: warning: 'update-mime-database' not found; the association "
            "file was written but the MIME database was not refreshed"
        )
        return
    try:
        completed = subprocess.run(
            [update_bin, str(mime_dir)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        _eprint(f"assoc: error: failed to run update-mime-database: {exc}")
        raise SystemExit(1)
    if completed.returncode != 0:
        detail = completed.stderr.strip()
        _eprint(f"assoc: error: update-mime-database failed: {detail or completed.returncode}")
        raise SystemExit(1)


def _validate_extension(ext: str) -> None:
    if not _EXT_RE.match(ext):
        _eprint(f"assoc: error: invalid extension '{ext}' (expected e.g. '.txt')")
        raise SystemExit(1)


def _validate_mimetype(mimetype: str) -> None:
    if not _MIME_RE.match(mimetype):
        _eprint(f"assoc: error: invalid MIME type '{mimetype}' (expected e.g. 'text/plain')")
        raise SystemExit(1)


def cmd_list() -> int:
    """Print every known ``.ext=MIMETYPE`` association, sorted by extension."""
    associations = _load_associations()
    for ext in sorted(associations):
        print(f"{ext}={associations[ext].mimetype}")
    return 0


def cmd_query(ext: str) -> int:
    """Print the association for a single extension, or fail like Windows."""
    _validate_extension(ext)
    entry = _load_associations().get(ext)
    if entry is None:
        _eprint(f"File association not found for extension {ext}")
        return 1
    print(f"{ext}={entry.mimetype}")
    return 0


def cmd_set(ext: str, mimetype: str) -> int:
    """Associate an extension with a MIME type in the user MIME database."""
    _validate_extension(ext)
    _validate_mimetype(mimetype)

    pattern = f"*{ext}"
    tree = _load_user_package()
    root = tree.getroot()

    # An extension maps to exactly one type in our overrides: clear any prior
    # override for this pattern before adding the new one.
    _remove_glob_everywhere(root, pattern)

    mime_type = _find_mime_type(root, mimetype)
    if mime_type is None:
        mime_type = ET.SubElement(root, _MIME_TYPE)
        mime_type.set("type", mimetype)
    glob = ET.SubElement(mime_type, _GLOB)
    glob.set("pattern", pattern)

    _write_and_refresh(tree)
    print(f"{ext}={mimetype}")
    return 0


def cmd_remove(ext: str) -> int:
    """Remove a user-defined association for an extension."""
    _validate_extension(ext)
    pattern = f"*{ext}"
    tree = _load_user_package()
    root = tree.getroot()

    if not _remove_glob_everywhere(root, pattern):
        # Not present in our overrides. It may still be defined by the system
        # database, which we cannot change without root. Be explicit.
        if ext in _load_associations():
            _eprint(
                f"assoc: error: {ext} is defined by the system MIME database and "
                f"cannot be removed at the user level (needs root to edit "
                f"/usr/share/mime)"
            )
        else:
            _eprint(f"File association not found for extension {ext}")
        return 1

    _write_and_refresh(tree)
    return 0


def _build_parser() -> "argparse.ArgumentParser":
    import argparse

    parser = argparse.ArgumentParser(
        prog="assoc",
        description="Display or modify file extension associations (Linux clone of Windows assoc).",
        epilog=(
            "examples:\n"
            "  assoc                     list all extension=MIMETYPE associations\n"
            "  assoc .txt                show the MIME type for .txt\n"
            "  assoc .txt=text/plain     associate .txt with text/plain\n"
            "  assoc .txt=               remove the .txt association (user overrides only)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "spec",
        nargs="?",
        metavar="[.ext[=[MIMETYPE]]]",
        help="extension to query, or '.ext=MIMETYPE' to set, or '.ext=' to remove",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"assoc {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    spec = args.spec
    if spec is None:
        return cmd_list()

    if "=" in spec:
        ext, value = spec.split("=", 1)
        if value == "":
            return cmd_remove(ext)
        return cmd_set(ext, value)

    return cmd_query(spec)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _eprint("assoc: interrupted")
        sys.exit(130)
