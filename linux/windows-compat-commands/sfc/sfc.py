#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sfc - System File Checker for Linux.

A Linux counterpart to the Windows `sfc /scannow` command. Instead of the
Windows component store, it verifies installed system files against the
integrity database maintained by the native package manager:

    * dpkg / apt   -> per-package md5sums (native, no external deps)
    * rpm / dnf    -> `rpm -V` verification database
    * pacman       -> `pacman -Qkk` verification

Corrupted, modified, or missing files are reported and, on request, repaired
by reinstalling the owning packages from the trusted package repositories.

This program is intentionally dependency-free (Python standard library only)
and never invokes a shell; all external commands run with argument vectors.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import enum
import hashlib
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from typing import Iterable, Sequence

__version__ = "1.0.0"
__prog__ = "sfc"

# Directory holding dpkg per-package metadata on Debian/Ubuntu systems.
DPKG_INFO_DIR = "/var/lib/dpkg/info"
# Size of the buffer used while hashing files, in bytes.
HASH_CHUNK_SIZE = 1024 * 1024


# --------------------------------------------------------------------------- #
# Result model
# --------------------------------------------------------------------------- #
class Status(enum.Enum):
    """Outcome of verifying a single file."""

    OK = "OK"
    CORRUPTED = "CORRUPTED"
    MISSING = "MISSING"
    UNREADABLE = "UNREADABLE"


@dataclasses.dataclass(frozen=True)
class Violation:
    """A single file that failed verification."""

    path: str
    package: str
    status: Status
    detail: str = ""

    def format(self) -> str:
        pkg = self.package or "?"
        line = f"  [{self.status.value:<9}] {self.path}  (package: {pkg})"
        if self.detail:
            line += f"  - {self.detail}"
        return line


class SfcError(Exception):
    """Fatal, user-facing error that aborts the run."""


# --------------------------------------------------------------------------- #
# Backend abstraction
# --------------------------------------------------------------------------- #
class Backend:
    """Interface implemented by each package-manager backend."""

    name = "generic"

    @classmethod
    def available(cls) -> bool:
        raise NotImplementedError

    def scan(
        self,
        targets: Sequence[str] | None = None,
        include_config: bool = False,
        workers: int = 4,
        progress: bool = True,
    ) -> list[Violation]:
        """Return the list of files that fail verification.

        `targets`, if given, restricts the scan to those absolute file paths.
        """
        raise NotImplementedError

    def repair(self, packages: Sequence[str], assume_yes: bool) -> bool:
        """Reinstall the given packages. Return True on success."""
        raise NotImplementedError


def _run(cmd: Sequence[str], check: bool = False) -> subprocess.CompletedProcess:
    """Run an external command with an argument vector (never via a shell)."""
    return subprocess.run(
        list(cmd),
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _hash_matches(path: str, expected_md5: str) -> Status:
    """Compare the on-disk md5 of `path` against `expected_md5`."""
    try:
        h = hashlib.md5()  # noqa: S324 - dpkg stores md5; must match its algorithm
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(HASH_CHUNK_SIZE), b""):
                h.update(chunk)
    except FileNotFoundError:
        return Status.MISSING
    except (PermissionError, OSError):
        return Status.UNREADABLE
    return Status.OK if h.hexdigest() == expected_md5 else Status.CORRUPTED


class DpkgBackend(Backend):
    """Debian/Ubuntu backend using native dpkg md5sums (no external deps)."""

    name = "dpkg"

    @classmethod
    def available(cls) -> bool:
        return shutil.which("dpkg") is not None and os.path.isdir(DPKG_INFO_DIR)

    @staticmethod
    def _package_from_md5sums(filename: str) -> str:
        # Files are named "<package>.md5sums" or "<package>:<arch>.md5sums".
        base = filename[: -len(".md5sums")]
        return base.split(":", 1)[0]

    def _conffiles(self) -> set[str]:
        """Return the set of files dpkg tracks as configuration files."""
        conffiles: set[str] = set()
        try:
            entries = os.listdir(DPKG_INFO_DIR)
        except OSError:
            return conffiles
        for entry in entries:
            if not entry.endswith(".conffiles"):
                continue
            try:
                with open(os.path.join(DPKG_INFO_DIR, entry), encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            conffiles.add(line)
            except OSError:
                continue
        return conffiles

    def _load_manifest(
        self, targets: set[str] | None
    ) -> list[tuple[str, str, str]]:
        """Return (absolute_path, expected_md5, package) tuples to verify."""
        try:
            entries = sorted(
                e for e in os.listdir(DPKG_INFO_DIR) if e.endswith(".md5sums")
            )
        except OSError as exc:
            raise SfcError(f"cannot read {DPKG_INFO_DIR}: {exc}") from exc

        manifest: list[tuple[str, str, str]] = []
        for entry in entries:
            package = self._package_from_md5sums(entry)
            full = os.path.join(DPKG_INFO_DIR, entry)
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        line = line.rstrip("\n")
                        if not line:
                            continue
                        # Format: "<md5><two spaces><relative path>"
                        parts = line.split("  ", 1)
                        if len(parts) != 2:
                            continue
                        md5, rel = parts[0].strip(), parts[1]
                        abs_path = "/" + rel.lstrip("/")
                        if targets is not None and abs_path not in targets:
                            continue
                        manifest.append((abs_path, md5, package))
            except OSError:
                continue
        return manifest

    def scan(
        self,
        targets: Sequence[str] | None = None,
        include_config: bool = False,
        workers: int = 4,
        progress: bool = True,
    ) -> list[Violation]:
        target_set = {os.path.realpath(t) for t in targets} if targets else None
        manifest = self._load_manifest(target_set)

        if target_set is not None:
            found = {p for p, _, _ in manifest}
            for missing in sorted(target_set - found):
                raise SfcError(
                    f"{missing} is not owned by any installed package (nothing to verify)"
                )

        skip = set() if include_config else self._conffiles()
        if skip:
            manifest = [row for row in manifest if row[0] not in skip]

        total = len(manifest)
        if total == 0:
            return []

        violations: list[Violation] = []
        done = 0
        started = time.monotonic()

        def check(row: tuple[str, str, str]) -> Violation | None:
            path, md5, package = row
            status = _hash_matches(path, md5)
            if status is Status.OK:
                return None
            return Violation(path=path, package=package, status=status)

        workers = max(1, workers)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for result in pool.map(check, manifest):
                done += 1
                if result is not None:
                    violations.append(result)
                if progress and (done % 500 == 0 or done == total):
                    pct = done * 100 // total
                    print(
                        f"\rVerification {pct}% complete "
                        f"({done}/{total} files)...",
                        end="",
                        file=sys.stderr,
                        flush=True,
                    )
        if progress:
            elapsed = time.monotonic() - started
            print(
                f"\rVerification 100% complete "
                f"({total} files scanned in {elapsed:.1f}s).",
                file=sys.stderr,
                flush=True,
            )
        violations.sort(key=lambda v: v.path)
        return violations

    def repair(self, packages: Sequence[str], assume_yes: bool) -> bool:
        apt = shutil.which("apt-get")
        if apt is None:
            raise SfcError("apt-get not found; cannot reinstall packages")
        cmd = [apt, "install", "--reinstall"]
        if assume_yes:
            cmd.append("-y")
        cmd.extend(sorted(set(packages)))
        proc = _run(cmd)
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode == 0


class RpmBackend(Backend):
    """RHEL/Fedora backend using `rpm -V`."""

    name = "rpm"

    @classmethod
    def available(cls) -> bool:
        return shutil.which("rpm") is not None

    def _owning_package(self, path: str) -> str:
        proc = _run(["rpm", "-qf", "--qf", "%{NAME}", path])
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        return ""

    def _parse(self, output: str, include_config: bool) -> list[Violation]:
        violations: list[Violation] = []
        for raw in output.splitlines():
            if not raw.strip():
                continue
            # `missing     /path` or "SM5DLUGTP  c /path"
            if raw.startswith("missing"):
                path = raw.split(None, 1)[-1].strip()
                violations.append(
                    Violation(path, self._owning_package(path), Status.MISSING)
                )
                continue
            parts = raw.split()
            if len(parts) < 2:
                continue
            flags = parts[0]
            attr = parts[1] if len(parts) == 3 else ""
            path = parts[-1]
            if not include_config and attr == "c":
                continue
            # Content/mode/ownership changes indicate corruption.
            if any(c in flags for c in "SM5DLUGT"):
                detail = f"rpm flags: {flags}"
                violations.append(
                    Violation(path, self._owning_package(path), Status.CORRUPTED, detail)
                )
        return violations

    def scan(
        self,
        targets: Sequence[str] | None = None,
        include_config: bool = False,
        workers: int = 4,
        progress: bool = True,
    ) -> list[Violation]:
        if targets:
            violations: list[Violation] = []
            for path in targets:
                real = os.path.realpath(path)
                proc = _run(["rpm", "-Vf", real])
                # rpm exits 1 when differences are found; that is not an error.
                violations.extend(self._parse(proc.stdout, include_config))
            return violations
        if progress:
            print("Verifying all packages with rpm -Va ...", file=sys.stderr)
        proc = _run(["rpm", "-Va"])
        return self._parse(proc.stdout, include_config)

    def repair(self, packages: Sequence[str], assume_yes: bool) -> bool:
        mgr = shutil.which("dnf") or shutil.which("yum")
        if mgr is None:
            raise SfcError("neither dnf nor yum found; cannot reinstall packages")
        cmd = [mgr, "reinstall"]
        if assume_yes:
            cmd.append("-y")
        cmd.extend(sorted(set(packages)))
        proc = _run(cmd)
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode == 0


class PacmanBackend(Backend):
    """Arch Linux backend using `pacman -Qkk`."""

    name = "pacman"

    @classmethod
    def available(cls) -> bool:
        return shutil.which("pacman") is not None

    def _owning_package(self, path: str) -> str:
        proc = _run(["pacman", "-Qoq", path])
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip().splitlines()[0]
        return ""

    def scan(
        self,
        targets: Sequence[str] | None = None,
        include_config: bool = False,
        workers: int = 4,
        progress: bool = True,
    ) -> list[Violation]:
        if progress and not targets:
            print("Verifying all packages with pacman -Qkk ...", file=sys.stderr)
        proc = _run(["pacman", "-Qkk"])
        target_set = {os.path.realpath(t) for t in targets} if targets else None
        violations: list[Violation] = []
        for raw in proc.stdout.splitlines() + proc.stderr.splitlines():
            line = raw.strip()
            # Problem lines look like: "pkg: /path/to/file (Size mismatch)"
            if ": " not in line or "(" not in line:
                continue
            pkg, rest = line.split(": ", 1)
            path = rest.split(" (", 1)[0].strip()
            if not path.startswith("/"):
                continue
            if target_set is not None and os.path.realpath(path) not in target_set:
                continue
            status = Status.MISSING if "No such file" in rest else Status.CORRUPTED
            detail = rest.split("(", 1)[1].rstrip(")") if "(" in rest else ""
            violations.append(Violation(path, pkg.strip(), status, detail))
        return violations

    def repair(self, packages: Sequence[str], assume_yes: bool) -> bool:
        pacman = shutil.which("pacman")
        if pacman is None:
            raise SfcError("pacman not found")
        cmd = [pacman, "-S"]
        if assume_yes:
            cmd.append("--noconfirm")
        cmd.extend(sorted(set(packages)))
        proc = _run(cmd)
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode == 0


BACKENDS: tuple[type[Backend], ...] = (DpkgBackend, RpmBackend, PacmanBackend)


def detect_backend() -> Backend:
    for cls in BACKENDS:
        if cls.available():
            return cls()
    raise SfcError(
        "no supported package manager found (need one of: dpkg, rpm, pacman)"
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
BANNER = (
    "Linux Resource Protection ({prog} {ver}) using the '{backend}' backend.\n"
)


# Only these keys may be written Windows-style (e.g. /scannow, /scanfile=...).
# Restricting to an allowlist prevents absolute Linux paths such as
# "/does/not/exist" from being mistaken for switches.
_WINDOWS_SWITCH_KEYS = frozenset(
    {
        "scannow",
        "verifyonly",
        "scanfile",
        "verifyfile",
        "include-config",
        "workers",
        "yes",
        "no-progress",
        "version",
        "help",
    }
)


def _translate_windows_switches(argv: Sequence[str]) -> list[str]:
    """Accept Windows-style switches (/scannow) as aliases for --scannow.

    A token is only rewritten when the part before an optional "=" is a known
    switch name; anything else (notably real absolute paths) is left intact.
    """
    out: list[str] = []
    for arg in argv:
        if arg.startswith("/") and len(arg) > 1:
            body = arg[1:]
            key = body.split("=", 1)[0].lower()
            if key in _WINDOWS_SWITCH_KEYS:
                out.append(f"--{body}" if "=" in body else f"--{key}")
                continue
        out.append(arg)
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=__prog__,
        description="System File Checker for Linux "
        "(verifies system files against the package manager's integrity database).",
        epilog="Windows-style switches are also accepted, e.g. /scannow, /verifyonly, "
        "/scanfile=/usr/bin/ls",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--scannow",
        action="store_true",
        help="scan integrity of all protected files and repair problems found",
    )
    mode.add_argument(
        "--verifyonly",
        action="store_true",
        help="scan integrity but do NOT perform any repair",
    )
    mode.add_argument(
        "--scanfile",
        metavar="PATH",
        help="scan integrity of a specific file and repair it if damaged",
    )
    mode.add_argument(
        "--verifyfile",
        metavar="PATH",
        help="verify integrity of a specific file, no repair",
    )
    parser.add_argument(
        "--include-config",
        action="store_true",
        help="also flag modified configuration files "
        "(skipped by default, since admins are expected to edit them)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min(8, (os.cpu_count() or 2) * 2),
        metavar="N",
        help="number of parallel hashing workers (dpkg backend)",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="assume 'yes' for repair prompts (non-interactive)",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="suppress the progress indicator",
    )
    parser.add_argument(
        "--version",
        "-V",
        "-v",
        action="version",
        version=f"{__prog__} {__version__}",
    )
    return parser


def _require_root(action: str) -> None:
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        raise SfcError(
            f"{action} requires root privileges. Re-run with sudo, "
            "or use --verifyonly to scan without repairing."
        )


def main(argv: Sequence[str] | None = None) -> int:
    # Line-buffer stdout so its messages interleave correctly with the
    # stderr progress indicator, even when stdout is a pipe.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass

    raw = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(_translate_windows_switches(raw))

    repair_mode = bool(args.scannow or args.scanfile)
    verify_mode = bool(args.verifyonly or args.verifyfile)
    single_target = args.scanfile or args.verifyfile

    if not (repair_mode or verify_mode):
        parser.print_help()
        return 2

    try:
        backend = detect_backend()
    except SfcError as exc:
        print(f"{__prog__}: error: {exc}", file=sys.stderr)
        return 2

    print(BANNER.format(prog=__prog__, ver=__version__, backend=backend.name))

    targets = None
    if single_target:
        real = os.path.realpath(single_target)
        if not os.path.exists(real):
            print(
                f"{__prog__}: error: {single_target} does not exist.",
                file=sys.stderr,
            )
            return 2
        targets = [real]

    print("Beginning verification phase of the system scan.")
    try:
        violations = backend.scan(
            targets=targets,
            include_config=args.include_config,
            workers=args.workers,
            progress=not args.no_progress,
        )
    except SfcError as exc:
        print(f"{__prog__}: error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        return 130

    if not violations:
        print(
            "\nLinux Resource Protection did not find any integrity violations."
        )
        return 0

    print(f"\nLinux Resource Protection found {len(violations)} integrity violation(s):")
    by_package: dict[str, list[Violation]] = defaultdict(list)
    for v in violations:
        print(v.format())
        if v.package:
            by_package[v.package].append(v)

    unowned = [v for v in violations if not v.package]
    if unowned:
        print(
            f"\nWarning: {len(unowned)} file(s) could not be mapped to a package "
            "and cannot be repaired automatically."
        )

    if verify_mode:
        print(
            "\nVerification finished. Run with --scannow (as root) to repair, "
            "or inspect the files above manually."
        )
        return 1

    # Repair path.
    if not by_package:
        print("\nNo repairable (package-owned) violations found.", file=sys.stderr)
        return 1

    try:
        _require_root("repair")
    except SfcError as exc:
        print(f"\n{__prog__}: error: {exc}", file=sys.stderr)
        return 2

    packages = sorted(by_package)
    print(
        f"\nBeginning repair phase: reinstalling {len(packages)} package(s): "
        f"{', '.join(packages)}"
    )
    try:
        ok = backend.repair(packages, assume_yes=args.yes)
    except SfcError as exc:
        print(f"{__prog__}: error: {exc}", file=sys.stderr)
        return 2

    if not ok:
        print(
            "\nLinux Resource Protection found corrupt files but was UNABLE "
            "to fix some of them. Review the package manager output above.",
            file=sys.stderr,
        )
        return 1

    print(
        "\nLinux Resource Protection found corrupt files and successfully "
        "repaired them by reinstalling the affected packages."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
