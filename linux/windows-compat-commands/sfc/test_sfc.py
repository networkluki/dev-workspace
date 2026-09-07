# -*- coding: utf-8 -*-
"""Test suite for sfc (System File Checker for Linux).

Run with:  pytest -v

The tests are hermetic: they never touch real system files or invoke a real
package manager. The dpkg backend is exercised against a temporary fake
`/var/lib/dpkg/info` directory, and repair/backend selection is stubbed with
monkeypatching.
"""

from __future__ import annotations

import hashlib
import os

import pytest

import sfc


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def sample_file(tmp_path):
    """A real on-disk file plus its md5 digest."""
    path = tmp_path / "payload.bin"
    data = b"the quick brown fox\n"
    path.write_bytes(data)
    return str(path), hashlib.md5(data).hexdigest()


@pytest.fixture
def dpkg_env(tmp_path, monkeypatch):
    """A fake dpkg info directory; returns a helper to register md5sums entries.

    The helper writes a `<package>.md5sums` file mapping absolute paths to
    expected digests, mirroring dpkg's on-disk format.
    """
    info_dir = tmp_path / "dpkg-info"
    info_dir.mkdir()
    monkeypatch.setattr(sfc, "DPKG_INFO_DIR", str(info_dir))

    def register(package: str, entries, conffiles=None):
        lines = []
        for abs_path, md5 in entries:
            lines.append(f"{md5}  {abs_path.lstrip('/')}")
        (info_dir / f"{package}.md5sums").write_text("\n".join(lines) + "\n")
        if conffiles:
            (info_dir / f"{package}.conffiles").write_text(
                "\n".join(conffiles) + "\n"
            )

    return register


# --------------------------------------------------------------------------- #
# _hash_matches
# --------------------------------------------------------------------------- #
class TestHashMatches:
    def test_ok(self, sample_file):
        path, md5 = sample_file
        assert sfc._hash_matches(path, md5) is sfc.Status.OK

    def test_corrupted(self, sample_file):
        path, _ = sample_file
        assert sfc._hash_matches(path, "0" * 32) is sfc.Status.CORRUPTED

    def test_missing(self, tmp_path):
        ghost = str(tmp_path / "nope.bin")
        assert sfc._hash_matches(ghost, "0" * 32) is sfc.Status.MISSING

    def test_unreadable_directory(self, tmp_path):
        # Hashing a directory raises OSError -> UNREADABLE, never a crash.
        assert sfc._hash_matches(str(tmp_path), "0" * 32) is sfc.Status.UNREADABLE


# --------------------------------------------------------------------------- #
# Windows-style switch translation (incl. the path-mangling regression)
# --------------------------------------------------------------------------- #
class TestSwitchTranslation:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (["/scannow"], ["--scannow"]),
            (["/verifyonly"], ["--verifyonly"]),
            (["/scanfile=/bin/ls"], ["--scanfile=/bin/ls"]),
            (["/verifyfile=/usr/bin/sudo"], ["--verifyfile=/usr/bin/sudo"]),
            (["/SCANNOW"], ["--scannow"]),  # case-insensitive key
        ],
    )
    def test_windows_switches_translated(self, raw, expected):
        assert sfc._translate_windows_switches(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            ["/does/not/exist"],          # absolute path must NOT become a switch
            ["/etc/hostname"],
            ["--verifyfile", "/bin/ls"],  # already Unix-style, untouched
            ["/unknownswitch"],           # not on the allowlist
        ],
    )
    def test_non_switches_preserved(self, raw):
        assert sfc._translate_windows_switches(raw) == raw

    def test_value_with_slash_after_equals_survives(self):
        # The key ("scanfile") is on the allowlist; the value keeps its slashes.
        assert sfc._translate_windows_switches(["/scanfile=/a/b/c"]) == [
            "--scanfile=/a/b/c"
        ]


# --------------------------------------------------------------------------- #
# DpkgBackend.scan
# --------------------------------------------------------------------------- #
class TestDpkgScan:
    def test_clean_system_no_violations(self, dpkg_env, sample_file):
        path, md5 = sample_file
        dpkg_env("pkgclean", [(path, md5)])
        assert sfc.DpkgBackend().scan(progress=False) == []

    def test_detects_corrupted_and_missing(self, dpkg_env, sample_file, tmp_path):
        path, md5 = sample_file
        ghost = str(tmp_path / "ghost.bin")
        dpkg_env(
            "demo",
            [
                (path, md5),          # OK
                (path, "0" * 32),     # same file, wrong digest -> CORRUPTED
                (ghost, md5),         # absent -> MISSING
            ],
        )
        violations = sfc.DpkgBackend().scan(progress=False)
        by_status = {v.status for v in violations}
        assert by_status == {sfc.Status.CORRUPTED, sfc.Status.MISSING}
        assert all(v.package == "demo" for v in violations)

    def test_package_name_strips_arch_suffix(self, dpkg_env, tmp_path, monkeypatch):
        # A file named "<package>:<arch>.md5sums" maps to just "<package>".
        info = tmp_path / "dpkg-info"
        f = tmp_path / "x.bin"
        f.write_bytes(b"z")
        (info / "libc6:amd64.md5sums").write_text(
            f"{'0'*32}  {str(f).lstrip('/')}\n"
        )
        violations = sfc.DpkgBackend().scan(progress=False)
        assert violations and violations[0].package == "libc6"

    def test_config_files_skipped_by_default(self, dpkg_env, sample_file):
        path, _ = sample_file
        dpkg_env("cfgpkg", [(path, "0" * 32)], conffiles=[path])
        # Default: conffile with a bad hash is ignored.
        assert sfc.DpkgBackend().scan(progress=False) == []
        # With include_config it surfaces as a violation.
        violations = sfc.DpkgBackend().scan(progress=False, include_config=True)
        assert len(violations) == 1
        assert violations[0].status is sfc.Status.CORRUPTED

    def test_target_not_owned_raises(self, dpkg_env, sample_file, tmp_path):
        path, md5 = sample_file
        dpkg_env("demo", [(path, md5)])
        stranger = tmp_path / "stranger.bin"
        stranger.write_bytes(b"unowned")
        with pytest.raises(sfc.SfcError):
            sfc.DpkgBackend().scan(targets=[str(stranger)], progress=False)

    def test_target_restricts_scan(self, dpkg_env, tmp_path):
        a = tmp_path / "a.bin"
        a.write_bytes(b"a")
        b = tmp_path / "b.bin"
        b.write_bytes(b"b")
        dpkg_env("p", [(str(a), "0" * 32), (str(b), "0" * 32)])
        # Only 'a' is targeted, so only 'a' is reported.
        violations = sfc.DpkgBackend().scan(targets=[str(a)], progress=False)
        assert [v.path for v in violations] == [str(a)]


# --------------------------------------------------------------------------- #
# Backend detection
# --------------------------------------------------------------------------- #
class TestDetectBackend:
    def test_prefers_first_available(self, monkeypatch):
        monkeypatch.setattr(sfc.DpkgBackend, "available", classmethod(lambda cls: True))
        monkeypatch.setattr(sfc.RpmBackend, "available", classmethod(lambda cls: True))
        assert isinstance(sfc.detect_backend(), sfc.DpkgBackend)

    def test_none_available_raises(self, monkeypatch):
        for cls in sfc.BACKENDS:
            monkeypatch.setattr(cls, "available", classmethod(lambda c: False))
        with pytest.raises(sfc.SfcError):
            sfc.detect_backend()


# --------------------------------------------------------------------------- #
# Violation formatting
# --------------------------------------------------------------------------- #
def test_violation_format_includes_path_status_package():
    v = sfc.Violation("/usr/bin/ls", "coreutils", sfc.Status.CORRUPTED, "detail")
    text = v.format()
    assert "/usr/bin/ls" in text
    assert "CORRUPTED" in text
    assert "coreutils" in text
    assert "detail" in text


# --------------------------------------------------------------------------- #
# main() end-to-end with a stubbed backend
# --------------------------------------------------------------------------- #
class FakeBackend(sfc.Backend):
    name = "fake"

    def __init__(self, violations, repair_ok=True):
        self._violations = violations
        self._repair_ok = repair_ok
        self.repaired = None

    def scan(self, targets=None, include_config=False, workers=4, progress=True):
        return list(self._violations)

    def repair(self, packages, assume_yes):
        self.repaired = list(packages)
        return self._repair_ok


@pytest.fixture
def use_fake_backend(monkeypatch):
    def install(violations, repair_ok=True):
        backend = FakeBackend(violations, repair_ok)
        monkeypatch.setattr(sfc, "detect_backend", lambda: backend)
        return backend

    return install


class TestMain:
    def test_no_args_prints_help_and_returns_2(self, use_fake_backend, capsys):
        use_fake_backend([])
        assert sfc.main([]) == 2

    def test_verifyonly_clean_returns_0(self, use_fake_backend, capsys):
        use_fake_backend([])
        assert sfc.main(["--verifyonly"]) == 0
        assert "did not find any integrity violations" in capsys.readouterr().out

    def test_verifyonly_with_violations_returns_1(self, use_fake_backend, capsys):
        v = sfc.Violation("/usr/bin/ls", "coreutils", sfc.Status.CORRUPTED)
        use_fake_backend([v])
        assert sfc.main(["--verifyonly"]) == 1
        assert "found 1 integrity violation" in capsys.readouterr().out

    def test_scannow_requires_root_when_violations(
        self, use_fake_backend, monkeypatch, capsys
    ):
        v = sfc.Violation("/usr/bin/ls", "coreutils", sfc.Status.CORRUPTED)
        use_fake_backend([v])
        monkeypatch.setattr(os, "geteuid", lambda: 1000, raising=False)
        assert sfc.main(["--scannow"]) == 2
        assert "requires root" in capsys.readouterr().err

    def test_scannow_repairs_as_root(self, use_fake_backend, monkeypatch, capsys):
        v = sfc.Violation("/usr/bin/ls", "coreutils", sfc.Status.CORRUPTED)
        backend = use_fake_backend([v], repair_ok=True)
        monkeypatch.setattr(os, "geteuid", lambda: 0, raising=False)
        assert sfc.main(["--scannow", "--yes"]) == 0
        assert backend.repaired == ["coreutils"]
        assert "successfully" in capsys.readouterr().out

    def test_scannow_repair_failure_returns_1(self, use_fake_backend, monkeypatch):
        v = sfc.Violation("/usr/bin/ls", "coreutils", sfc.Status.CORRUPTED)
        use_fake_backend([v], repair_ok=False)
        monkeypatch.setattr(os, "geteuid", lambda: 0, raising=False)
        assert sfc.main(["--scannow", "--yes"]) == 1

    def test_scanfile_missing_target_returns_2(self, use_fake_backend, capsys):
        use_fake_backend([])
        assert sfc.main(["--verifyfile", "/definitely/not/here"]) == 2
        assert "does not exist" in capsys.readouterr().err

    def test_no_backend_returns_2(self, monkeypatch, capsys):
        def boom():
            raise sfc.SfcError("no supported package manager found")

        monkeypatch.setattr(sfc, "detect_backend", boom)
        assert sfc.main(["--verifyonly"]) == 2
        assert "no supported package manager" in capsys.readouterr().err

    def test_windows_switch_reaches_main(self, use_fake_backend, capsys):
        use_fake_backend([])
        assert sfc.main(["/verifyonly"]) == 0


class TestVersionFlag:
    @pytest.mark.parametrize("flag", ["--version", "-V", "-v"])
    def test_version_flags(self, flag, capsys):
        with pytest.raises(SystemExit) as exc:
            sfc.main([flag])
        assert exc.value.code == 0
        assert sfc.__version__ in capsys.readouterr().out
