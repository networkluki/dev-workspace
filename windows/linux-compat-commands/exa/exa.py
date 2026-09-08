#!/usr/bin/env python3
"""En liten exa-inspirerad fillistare för Python 3.9 och senare."""

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

VERSION = "1.3.2"
CONFIG_PATH = Path(__file__).with_name("config.json")
CONFIG_LIMIT = 64 * 1024
GIT_TIMEOUT = 10
Entry = Tuple[Path, os.stat_result]

CONFIG_TYPES = {
    "all": bool, "long": bool, "oneline": bool, "directory": bool,
    "reverse": bool, "classify": bool, "group_directories_first": bool,
    "tree": bool, "git": bool, "only_dirs": bool, "summary": bool,
    "sort": str, "icons": str, "color": str, "ext": str, "depth": int,
}
CONFIG_CHOICES = {
    "sort": ("name", "size", "modified", "extension"),
    "icons": ("always", "auto", "never"),
    "color": ("always", "auto", "never"),
}
FILE_COLORS = {
    "33": {".py", ".js", ".ts", ".tsx", ".jsx", ".lua", ".c", ".cpp", ".rs", ".go"},
    "35": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".mp4", ".mkv"},
    "31": {".zip", ".7z", ".gz", ".rar", ".tar", ".bz2", ".xz"},
    "32": {".exe", ".cmd", ".bat", ".ps1", ".sh", ".msi"},
    "36": {".json", ".toml", ".yaml", ".yml", ".ini", ".xml"},
    "95": {".mp3", ".wav", ".ogg", ".flac"},
}

ICONS = {
    ".py": "🐍", ".js": "📜", ".ts": "📜", ".lua": "📜",
    ".ps1": "📜", ".cmd": "📜", ".bat": "📜", ".json": "⚙",
    ".toml": "⚙", ".yaml": "⚙", ".yml": "⚙", ".ini": "⚙",
    ".png": "🖼", ".jpg": "🖼", ".jpeg": "🖼", ".gif": "🖼",
    ".svg": "🖼", ".mp3": "🎵", ".wav": "🎵", ".mp4": "🎬",
    ".mkv": "🎬", ".zip": "📦", ".7z": "📦", ".gz": "📦",
    ".rar": "📦", ".exe": "⚡", ".pdf": "📕", ".md": "📝", ".txt": "📝",
}


def safe_text(value: str) -> str:
    """Escape terminal controls in filenames and errors."""
    return "".join(
        char if not unicodedata.category(char).startswith("C") else ascii(char)[1:-1]
        for char in value
    )


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if value < 1024 or unit == "PiB":
            return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def hidden(path: Path, info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return path.name.startswith(".") or bool(attributes & stat.FILE_ATTRIBUTE_HIDDEN)


def icon_for(path: Path, info: os.stat_result) -> str:
    if stat.S_ISLNK(info.st_mode):
        return "🔗"
    if stat.S_ISDIR(info.st_mode):
        return "📁"
    return ICONS.get(path.suffix.lower(), "📄")


def color_for(path: Path, info: os.stat_result) -> str:
    if stat.S_ISLNK(info.st_mode):
        return "36"
    if stat.S_ISDIR(info.st_mode):
        return "1;34"
    extension = path.suffix.lower()
    return next((code for code, extensions in FILE_COLORS.items() if extension in extensions), "0")


def is_link(info: os.stat_result) -> bool:
    # Windows junctions also need to stop traversal, even if lstat reports a directory.
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def display_width(value: str) -> int:
    width = 0
    for char in value:
        if not unicodedata.combining(char):
            width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return width


def render_entry(
    path: Path, info: os.stat_result, args: argparse.Namespace, color: bool, icons: bool
) -> Tuple[str, int]:
    name = safe_text(path.name or str(path))
    is_dir = stat.S_ISDIR(info.st_mode)
    is_link = stat.S_ISLNK(info.st_mode)
    if args.classify:
        name += "/" if is_dir else "@" if is_link else ""
    plain = (icon_for(path, info) + " " if icons else "") + name
    text = plain
    if color:
        code = color_for(path, info)
        text = f"\033[{code}m{plain}\033[0m"
    if args.long:
        size = "-" if is_dir else human_size(info.st_size)
        modified = datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M")
        prefix = f"{stat.filemode(info.st_mode)} {size:>10} {modified} "
        text = prefix + text
        plain = prefix + plain
    return text, display_width(plain)


def output_rows(rows: List[Tuple[str, int]], one_line: bool) -> None:
    if not rows:
        return
    if one_line:
        for text, _ in rows:
            print(text)
        return
    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    cell_width = max(length for _, length in rows) + 2
    columns = max(1, width // cell_width)
    for start in range(0, len(rows), columns):
        chunk = rows[start : start + columns]
        print("".join(
            text + (" " * (cell_width - length) if index < len(chunk) - 1 else "")
            for index, (text, length) in enumerate(chunk)
        ))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="exa", description="Lista filer med ikoner och färger.",
        epilog="Exempel: exa | exa -la | exa -l -s size | exa C:\\Windows",
    )
    result.add_argument("paths", nargs="*", default=["."], metavar="SÖKVÄG")
    boolean = argparse.BooleanOptionalAction
    result.add_argument("-a", "--all", action=boolean, default=False, help="visa dolda filer")
    result.add_argument("-l", "--long", action=boolean, default=False, help="visa detaljer och storlek")
    result.add_argument("-1", "--oneline", action=boolean, default=False, help="en post per rad")
    result.add_argument("-d", "--directory", action=boolean, default=False, help="visa själva katalogen")
    result.add_argument("-r", "--reverse", action=boolean, default=False, help="omvänd sortering")
    result.add_argument("-F", "--classify", action=boolean, default=False, help="markera kataloger med /")
    result.add_argument(
        "-s", "--sort", choices=("name", "size", "modified", "extension"),
        default="name", help="sortera efter fält (stigande)",
    )
    result.add_argument(
        "--group-directories-first", action=boolean, default=False, help="visa kataloger först",
    )
    result.add_argument(
        "--icons", nargs="?", const="always", default="always",
        choices=("always", "auto", "never"), help="ikoner (standard: always)",
    )
    result.add_argument(
        "--color", "--colour", choices=("always", "auto", "never"), default="auto",
        help="färger (standard: auto)",
    )
    result.add_argument("-T", "--tree", action=boolean, default=False, help="visa ett katalogträd")
    result.add_argument("--depth", type=int, default=None, help="trädets maxdjup; 0 visar bara roten")
    result.add_argument("--git", action=boolean, default=False, help="visa Git-status, även ignorerat")
    result.add_argument("--ext", default="", help="filändelser separerade med komma, t.ex. py,lua")
    result.add_argument("--only-dirs", action=boolean, default=False, help="visa endast kataloger")
    result.add_argument("--summary", action=boolean, default=False, help="summera visade poster")
    result.add_argument("--config", metavar="FIL", help=f"inställningsfil (standard: {CONFIG_PATH})")
    result.add_argument("--no-config", action="store_true", help="ignorera sparade inställningar")
    result.add_argument("-v", "--version", action="version", version=f"exa-python {VERSION}")
    return result


def read_config(path: Path, required: bool) -> dict:
    try:
        with path.open("rb") as handle:
            data = handle.read(CONFIG_LIMIT + 1)
    except FileNotFoundError:
        if required:
            raise ValueError(f"Inställningsfilen finns inte: {path}")
        return {}
    if len(data) > CONFIG_LIMIT:
        raise ValueError("Inställningsfilen får vara högst 64 KiB.")
    settings = json.loads(data.decode("utf-8-sig"))
    if not isinstance(settings, dict):
        raise ValueError("Inställningsfilen måste innehålla ett JSON-objekt.")
    for key, value in settings.items():
        if key not in CONFIG_TYPES:
            raise ValueError(f"Okänd inställning: {key}")
        if type(value) is not CONFIG_TYPES[key]:
            raise ValueError(f"Fel datatyp för inställningen {key}.")
        if key in CONFIG_CHOICES and value not in CONFIG_CHOICES[key]:
            raise ValueError(f"Ogiltigt värde för {key}: {value}")
        if key == "depth" and value < 0:
            raise ValueError("depth får inte vara negativt.")
    return settings


def parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    arguments = list(sys.argv[1:] if argv is None else argv)
    result = parser()
    # First parse identifies config flags; help/version still work with a broken config.
    initial = result.parse_args(arguments)
    if not initial.no_config:
        try:
            path = Path(initial.config).expanduser() if initial.config else CONFIG_PATH
            result.set_defaults(**read_config(path, required=initial.config is not None))
        except (OSError, ValueError, RuntimeError) as error:
            result.error(safe_text(str(error)) + " Rätta filen eller använd --no-config.")
    args = result.parse_args(arguments)
    if args.depth is not None and args.depth < 0:
        result.error("--depth måste vara 0 eller större.")
    if args.tree and args.directory:
        result.error("--tree och --directory kan inte användas tillsammans.")
    args.extensions = tuple(part.strip().lower().lstrip(".") for part in args.ext.split(",")) if args.ext else ()
    if any(not part or "/" in part or "\\" in part for part in args.extensions):
        result.error("--ext kräver filändelser, exempelvis py,lua.")
    return args


def report_error(path: Path, error: Exception) -> None:
    print(f"exa: {safe_text(str(path))}: {safe_text(str(error))}", file=sys.stderr)


def matches(path: Path, info: os.stat_result, args: argparse.Namespace) -> bool:
    if stat.S_ISDIR(info.st_mode):
        return args.tree or args.only_dirs or not args.extensions
    if args.only_dirs:
        return False
    return not args.extensions or path.name.lower().endswith(tuple("." + ext for ext in args.extensions))


def read_entries(path: Path, args: argparse.Namespace) -> Tuple[List[Entry], bool]:
    entries = []
    failed = False
    try:
        for candidate in path.iterdir():
            try:
                info = candidate.lstat()
            except OSError as error:
                report_error(candidate, error)
                failed = True
                continue
            if not args.all and hidden(candidate, info):
                continue
            if matches(candidate, info, args):
                entries.append((candidate, info))
    except OSError as error:
        report_error(path, error)
        failed = True

    def sort_key(entry: Entry) -> tuple:
        item, info = entry
        name = item.name.casefold()
        if args.sort == "size":
            return info.st_size, name
        if args.sort == "modified":
            return info.st_mtime, name
        if args.sort == "extension":
            return item.suffix.casefold(), name
        return (name,)

    entries.sort(key=sort_key, reverse=args.reverse)
    if args.group_directories_first:
        entries.sort(key=lambda entry: not stat.S_ISDIR(entry[1].st_mode))
    return entries, failed


def path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


class GitStatus:
    """Read one status snapshot per repository; never lock or write the Git index."""

    def __init__(self) -> None:
        self.cache: Dict[str, Dict[str, Set[str]]] = {}
        self.ignored: Set[str] = set()

    def run(self, path: Path, *arguments: str) -> bytes:
        environment = os.environ.copy()
        environment.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
        try:
            process = subprocess.run(
                ["git", "-c", "core.fsmonitor=false", "-C", str(path), *arguments],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=GIT_TIMEOUT,
                env=environment, check=False,
            )
        except FileNotFoundError as error:
            raise OSError("Git hittades inte. Installera Git eller använd --no-git.") from error
        except subprocess.TimeoutExpired as error:
            raise OSError(f"Git tog mer än {GIT_TIMEOUT} sekunder. Prova --no-git.") from error
        if process.returncode:
            detail = process.stderr.decode("utf-8", errors="replace").strip()
            raise OSError(f"Git misslyckades: {detail}. Prova --no-git.")
        return process.stdout

    def load(self, path: Path) -> Tuple[Path, Dict[str, Set[str]]]:
        directory = path if path.is_dir() else path.parent
        root = Path(os.fsdecode(self.run(directory, "rev-parse", "--show-toplevel")).rstrip("\r\n"))
        key = path_key(root)
        if key not in self.cache:
            data = self.run(
                root, "status", "--porcelain=v1", "-z", "--ignored",
                "--untracked-files=all", "--no-renames",
            )
            statuses: Dict[str, Set[str]] = {}
            for record in data.split(b"\0"):
                if not record:
                    continue
                if len(record) < 4 or record[2:3] != b" ":
                    raise OSError("Git returnerade ett oväntat statusformat.")
                status = record[:2].decode("ascii")
                item = root / os.fsdecode(record[3:]).rstrip("/")
                if status == "!!":
                    self.ignored.add(path_key(item))
                # Aggregate child changes so collapsed directories show their status too.
                while True:
                    statuses.setdefault(path_key(item), set()).add(status)
                    if path_key(item) == key:
                        break
                    if item.parent == item:
                        raise OSError("Git returnerade en sökväg utanför arbetskatalogen.")
                    item = item.parent
            self.cache[key] = statuses
        return root, self.cache[key]

    def label(self, path: Path, snapshot: Tuple[Path, Dict[str, Set[str]]]) -> str:
        root, statuses = snapshot
        values = statuses.get(path_key(path), set())
        if values:
            return next(iter(values)) if len(values) == 1 else "**"
        item = Path(os.path.abspath(path))
        while True:
            if path_key(item) in self.ignored:
                return "!!"
            if path_key(item) == path_key(root) or item.parent == item:
                return "--"
            item = item.parent


@dataclass
class Summary:
    files: int = 0
    directories: int = 0
    links: int = 0
    other: int = 0
    size: int = 0

    def add(self, info: os.stat_result) -> None:
        if is_link(info):
            self.links += 1
        elif stat.S_ISDIR(info.st_mode):
            self.directories += 1
        elif stat.S_ISREG(info.st_mode):
            self.files += 1
            self.size += info.st_size
        else:
            self.other += 1

    def text(self, failed: bool) -> str:
        result = f"{self.files} filer, {self.directories} mappar"
        if self.links:
            result += f", {self.links} länkar"
        if self.other:
            result += f", {self.other} övriga poster"
        result += f" · {human_size(self.size)} totalt (visade filer)"
        if failed:
            result += " · ofullständig listning"
        return result


def list_path(
    path: Path, args: argparse.Namespace, color: bool, icons: bool, git: Optional[GitStatus]
) -> bool:
    try:
        info = path.lstat()
        listing = not args.directory and path.is_dir()
        if args.tree and is_link(info):
            listing = False
    except OSError as error:
        report_error(path, error)
        return True
    failed = False
    snapshot = None
    if git is not None:
        try:
            snapshot = git.load(path)
        except OSError as error:
            report_error(path, error)
            failed = True

    def render(item: Path, metadata: os.stat_result) -> Tuple[str, int]:
        text, width = render_entry(item, metadata, args, color, icons)
        if git is not None:
            label = git.label(item, snapshot) if snapshot is not None else "!!"
            # A failed Git query is distinct from an ignored file.
            prefix = f"[{label}] " if snapshot is not None else "[ER] "
            return prefix + text, width + len(prefix)
        return text, width

    summary = Summary()
    if not listing:
        if matches(path, info, args):
            output_rows([render(path, info)], True)
            summary.add(info)
    elif args.tree:
        print(render(path, info)[0])
        # An explicit stack avoids Python recursion limits on deep directory trees.
        stack: List[Tuple[Path, os.stat_result, str, int, bool]] = []

        def push_children(parent: Path, prefix: str, depth: int) -> None:
            nonlocal failed
            children, errors = read_entries(parent, args)
            failed = failed or errors
            for index in range(len(children) - 1, -1, -1):
                child, metadata = children[index]
                stack.append((child, metadata, prefix, depth, index == len(children) - 1))

        if args.depth is None or args.depth > 0:
            push_children(path, "", 1)
        while stack:
            item, metadata, prefix, depth, last = stack.pop()
            print(prefix + ("└── " if last else "├── ") + render(item, metadata)[0])
            summary.add(metadata)
            if stat.S_ISDIR(metadata.st_mode) and not is_link(metadata):
                if args.depth is None or depth < args.depth:
                    push_children(item, prefix + ("    " if last else "│   "), depth + 1)
    else:
        entries, errors = read_entries(path, args)
        failed = failed or errors
        for _, metadata in entries:
            summary.add(metadata)
        output_rows([render(item, metadata) for item, metadata in entries], args.long or args.oneline or not sys.stdout.isatty())
    if args.summary:
        print(summary.text(failed))
    return failed


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    terminal = sys.stdout.isatty()
    color = args.color == "always" or (
        args.color == "auto" and terminal and "NO_COLOR" not in os.environ
    )
    icons = args.icons == "always" or (args.icons == "auto" and terminal)
    failed = False
    git = GitStatus() if args.git else None
    for index, raw_path in enumerate(args.paths):
        try:
            path = Path(raw_path).expanduser()
        except RuntimeError as error:
            report_error(Path(raw_path), error)
            failed = True
            continue
        if len(args.paths) > 1:
            if index:
                print()
            print(safe_text(str(path)) + ":")
        errors = list_path(path, args, color, icons, git)
        failed = failed or errors
    return int(failed)


if __name__ == "__main__":
    # Preserve icons and Swedish filenames when output is redirected.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.stdout = open(os.devnull, "w")
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
