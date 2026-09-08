import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import exa


class ExaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_exa(self, *args, use_config=False):
        stdout, stderr = io.StringIO(), io.StringIO()
        arguments = ["--color=never", "--icons=never", *map(str, args)]
        if not use_config:
            arguments.insert(0, "--no-config")
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = exa.main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_empty_directory(self):
        self.assertEqual(self.run_exa(self.root), (0, "", ""))

    def test_version_flags(self):
        for flag in ("-v", "--version"):
            with self.subTest(flag=flag):
                result = subprocess.run(
                    [sys.executable, str(Path(exa.__file__)), flag],
                    capture_output=True, text=True, timeout=10, check=False,
                )
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, f"exa-python {exa.VERSION}\n")
                self.assertEqual(result.stderr, "")

    def test_names_hidden_unicode_and_spaces(self):
        for name in ("z.txt", "Å ä ö.txt", "a b.py", ".hidden"):
            (self.root / name).touch()
        code, output, error = self.run_exa(self.root)
        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertEqual(output.splitlines(), ["a b.py", "z.txt", "Å ä ö.txt"])
        self.assertIn(".hidden", self.run_exa("-a", self.root)[1])
        self.assertEqual(self.run_exa(self.root / ".hidden")[1], ".hidden\n")

    def test_size_reverse_and_directory_grouping(self):
        (self.root / "small").write_bytes(b"a")
        (self.root / "large").write_bytes(b"abc")
        self.assertEqual(
            self.run_exa("-s", "size", "-r", self.root)[1].splitlines(),
            ["large", "small"],
        )
        (self.root / "folder").mkdir()
        output = self.run_exa("--group-directories-first", "-r", self.root)[1]
        self.assertEqual(output.splitlines(), ["folder", "small", "large"])

    def test_long_icons_classification_and_color(self):
        (self.root / "code.py").write_bytes(b"x" * 1024)
        (self.root / "folder").mkdir()
        code, output, _ = self.run_exa(
            "-lF", "--icons=always", "--color=always", self.root
        )
        self.assertEqual(code, 0)
        self.assertIn("1.0 KiB", output)
        self.assertIn("🐍 code.py", output)
        self.assertIn("📁 folder/", output)
        self.assertIn("\033[1;34m", output)

    def test_missing_path_does_not_stop_other_paths(self):
        code, output, error = self.run_exa(self.root / "missing", self.root)
        self.assertEqual(code, 1)
        self.assertIn("missing", error)
        self.assertIn(str(self.root) + ":", output)

    def test_unreadable_directory(self):
        with patch.object(Path, "iterdir", side_effect=PermissionError("denied")):
            code, output, error = self.run_exa(self.root)
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("denied", error)

    def test_entry_disappears_during_listing(self):
        original = Path.lstat
        missing = self.root / "gone"

        def metadata(path):
            if path == missing:
                raise FileNotFoundError("gone")
            return original(path)

        with patch.object(Path, "iterdir", return_value=iter([missing])):
            with patch.object(Path, "lstat", metadata):
                code, _, error = self.run_exa(self.root)
        self.assertEqual(code, 1)
        self.assertIn("gone", error)

    def test_directory_itself(self):
        (self.root / "child").touch()
        self.assertEqual(self.run_exa("-dF", self.root)[1], self.root.name + "/\n")

    def test_terminal_control_characters_are_escaped(self):
        self.assertEqual(exa.safe_text("a\n\x1b[31m\u202e"), r"a\n\x1b[31m\u202e")

    def test_windows_hidden_attribute(self):
        class Metadata:
            st_file_attributes = stat.FILE_ATTRIBUTE_HIDDEN

        self.assertTrue(exa.hidden(Path("hidden.txt"), Metadata()))

    def test_columns_and_wide_unicode(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with patch.object(exa.shutil, "get_terminal_size", return_value=os.terminal_size((12, 24))):
                exa.output_rows([("ab", 2), ("cd", 2), ("ef", 2), ("gh", 2)], False)
        self.assertEqual(output.getvalue(), "ab  cd  ef\ngh\n")
        self.assertEqual(exa.display_width("📁 a"), 4)

    def test_sizes(self):
        self.assertEqual(exa.human_size(0), "0 B")
        self.assertEqual(exa.human_size(1024), "1.0 KiB")
        self.assertEqual(exa.human_size(1024**5), "1.0 PiB")

    def test_tree_depth_and_hidden_entries(self):
        folder = self.root / "folder"
        folder.mkdir()
        (folder / "child.py").touch()
        (self.root / "last.txt").touch()
        (self.root / ".hidden").touch()
        code, output, error = self.run_exa("-T", "--depth", "2", self.root)
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(output.splitlines(), [
            self.root.name, "├── folder", "│   └── child.py", "└── last.txt",
        ])
        self.assertNotIn("child.py", self.run_exa("-T", "--depth", "1", self.root)[1])
        self.assertEqual(self.run_exa("-T", "--depth", "0", self.root)[1], self.root.name + "\n")
        self.assertIn(".hidden", self.run_exa("-Ta", self.root)[1])

    def test_tree_filters_and_summary_count_only_displayed_files(self):
        folder = self.root / "folder"
        folder.mkdir()
        (folder / "script.PY").write_bytes(b"abc")
        (folder / "ignored.txt").write_bytes(b"x" * 100)
        (self.root / "empty").mkdir()
        code, output, _ = self.run_exa("-T", "--ext", ".py,lua", "--summary", self.root)
        self.assertEqual(code, 0)
        self.assertIn("script.PY", output)
        self.assertNotIn("ignored.txt", output)
        self.assertIn("empty", output)
        self.assertIn("1 filer, 2 mappar · 3 B totalt (visade filer)", output)

    def test_flat_filters_only_dirs_and_compound_extensions(self):
        (self.root / "folder").mkdir()
        (self.root / "a.PY").touch()
        (self.root / "b.lua").touch()
        (self.root / "archive.tar.gz").touch()
        self.assertEqual(self.run_exa("--ext", "py,LUA", self.root)[1], "a.PY\nb.lua\n")
        self.assertEqual(self.run_exa("--ext", "tar.gz", self.root)[1], "archive.tar.gz\n")
        self.assertEqual(self.run_exa("--only-dirs", "--ext", "py", self.root)[1], "folder\n")
        self.assertEqual(self.run_exa("--ext", "txt", self.root)[1], "")
        self.assertEqual(self.run_exa("--ext", "lua", self.root / "a.PY")[1], "")

    def test_summary_empty_depth_zero_and_partial_read_failure(self):
        self.assertIn("0 filer, 0 mappar · 0 B", self.run_exa("--summary", self.root)[1])
        (self.root / "folder").mkdir()
        self.assertIn("0 filer, 0 mappar · 0 B", self.run_exa("-T", "--depth", "0", "--summary", self.root)[1])
        original = Path.iterdir

        def children(path):
            if path.name == "folder":
                raise PermissionError("denied")
            return original(path)

        with patch.object(Path, "iterdir", children):
            code, output, error = self.run_exa("-T", "--summary", self.root)
        self.assertEqual(code, 1)
        self.assertIn("folder", output)
        self.assertIn("ofullständig listning", output)
        self.assertIn("denied", error)

    def test_tree_does_not_follow_reparse_directory(self):
        folder = self.root / "junction"
        folder.mkdir()
        (folder / "do-not-visit").touch()
        original = Path.lstat

        class ReparseMetadata:
            st_mode = stat.S_IFDIR | 0o755
            st_file_attributes = stat.FILE_ATTRIBUTE_REPARSE_POINT

        def metadata(path):
            return ReparseMetadata() if path == folder else original(path)

        with patch.object(Path, "lstat", metadata):
            code, output, _ = self.run_exa("-T", "--summary", self.root)
        self.assertEqual(code, 0)
        self.assertIn("junction", output)
        self.assertNotIn("do-not-visit", output)
        self.assertIn("1 länkar", output)

    def test_tree_does_not_follow_symlink(self):
        target = self.root / "target"
        target.mkdir()
        (target / "child").touch()
        link = self.root / "link"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Symboliska länkar är inte tillgängliga: {error}")
        output = self.run_exa("-T", self.root)[1]
        self.assertEqual(output.count("child"), 1)
        self.assertEqual(self.run_exa("-T", link)[1], "link\n")

    def test_colors_for_file_categories_and_disabled_colors(self):
        for name, code in (("code.py", "33"), ("image.png", "35"), ("archive.zip", "31"), ("run.exe", "32")):
            path = self.root / name
            path.touch()
            self.assertIn(f"\033[{code}m{name}", self.run_exa("--color=always", path)[1])
            self.assertNotIn("\033", self.run_exa(path)[1])
        path = self.root / "code.py"
        class TerminalOutput(io.StringIO):
            def isatty(self):
                return True

        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            with contextlib.redirect_stdout(TerminalOutput()) as output:
                code = exa.main(["--no-config", "--color=auto", str(path)])
        self.assertEqual(code, 0)
        self.assertNotIn("\033", output.getvalue())

    @unittest.skipUnless(os.name == "nt", "Windows-junctions kräver Windows")
    def test_tree_does_not_follow_real_junction_cycle(self):
        link = self.root / "junction"
        result = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", str(link), str(self.root)],
            capture_output=True, timeout=10, check=False,
        )
        if result.returncode:
            self.skipTest("Windows tillät inte att testet skapade en junction.")
        code, output, _ = self.run_exa("-T", "--summary", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(output.count("junction"), 1)
        self.assertIn("1 länkar", output)

    def test_config_defaults_cli_overrides_and_no_config(self):
        config = self.root / "settings.json"
        config.write_text(json.dumps({
            "icons": "never", "tree": True, "depth": 1, "summary": True,
            "sort": "size", "group_directories_first": True,
        }), encoding="utf-8")
        args = exa.parse_args(["--config", str(config)])
        self.assertTrue(args.tree)
        self.assertEqual(args.depth, 1)
        self.assertEqual(args.sort, "size")
        args = exa.parse_args(["--config", str(config), "--no-tree", "--no-summary", "-s", "name"])
        self.assertFalse(args.tree)
        self.assertFalse(args.summary)
        self.assertEqual(args.sort, "name")
        args = exa.parse_args(["--config", str(config), "--no-config"])
        self.assertFalse(args.tree)
        self.assertEqual(args.icons, "always")
        before = config.read_bytes()
        self.assertEqual(self.run_exa("--config", config, self.root, use_config=True)[0], 0)
        self.assertEqual(config.read_bytes(), before)

    def test_config_validation_and_size_limit(self):
        config = self.root / "settings.json"
        for value in ([], {"unknown": 1}, {"tree": "yes"}, {"depth": True}, {"depth": -1}, {"sort": "invalid"}):
            with self.subTest(value=value):
                config.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(ValueError):
                    exa.read_config(config, required=True)
        config.write_bytes(b" " * (exa.CONFIG_LIMIT + 1))
        with self.assertRaisesRegex(ValueError, "64 KiB"):
            exa.read_config(config, required=True)
        config.write_bytes(b"\xff")
        with self.assertRaises(ValueError):
            exa.read_config(config, required=True)
        config.write_text("{ broken", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit) as caught:
                exa.parse_args(["--config", str(config)])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("--no-config", errors.getvalue())
        for flag in ("-v", "--version"):
            with self.subTest(flag=flag):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    with self.assertRaises(SystemExit) as caught:
                        exa.main(["--config", str(config), flag])
                self.assertEqual(caught.exception.code, 0)
                self.assertEqual(output.getvalue(), f"exa-python {exa.VERSION}\n")

    def test_missing_config_optional_and_explicit(self):
        config = self.root / "missing.json"
        self.assertEqual(exa.read_config(config, required=False), {})
        with self.assertRaisesRegex(ValueError, "finns inte"):
            exa.read_config(config, required=True)

    def test_invalid_flags(self):
        for flags in (("--depth", "-1"), ("-T", "-d"), ("--ext", "py,,lua"), ("--ext", "../py")):
            with self.subTest(flags=flags):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        exa.parse_args(["--no-config", *flags])
                self.assertEqual(caught.exception.code, 2)

    def test_git_missing_and_timeout_are_actionable(self):
        for error, expected in (
            (FileNotFoundError(), "Git hittades inte"),
            (subprocess.TimeoutExpired("git", 10), "10 sekunder"),
        ):
            with self.subTest(error=error):
                with patch.object(exa.subprocess, "run", side_effect=error):
                    code, output, stderr = self.run_exa("--git", "--summary", self.root)
                self.assertEqual(code, 1)
                self.assertIn(expected, stderr)
                self.assertIn("ofullständig", output)


@unittest.skipUnless(shutil.which("git"), "Git krävs för integrationstesterna")
class GitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo med mellanslag"
        self.root.mkdir()
        self.environment = os.environ.copy()
        self.environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "--template=")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=Exa Test",
             "-c", "user.email=exa@example.invalid", "-c", "commit.gpgsign=false",
             "-c", f"core.hooksPath={self.root / 'no-hooks'}", *args],
            check=True, capture_output=True, timeout=10, env=self.environment,
        )

    def test_real_git_clean_modified_untracked_ignored_and_staged(self):
        (self.root / ".gitignore").write_text("*.log\ncache/\n", encoding="utf-8")
        (self.root / "clean.txt").write_text("clean", encoding="utf-8")
        (self.root / "changed.txt").write_text("before", encoding="utf-8")
        (self.root / "deleted.txt").touch()
        self.git("add", ".")
        self.git("commit", "-m", "test fixture")
        (self.root / "changed.txt").write_text("after", encoding="utf-8")
        (self.root / "deleted.txt").unlink()
        (self.root / "Å ny.txt").touch()
        (self.root / "ignored.log").touch()
        (self.root / "added.py").touch()
        self.git("add", "added.py")
        (self.root / "cache").mkdir()
        (self.root / "cache" / "child.txt").touch()
        (self.root / "folder").mkdir()
        (self.root / "folder" / "new.lua").touch()
        git = exa.GitStatus()
        with patch.dict(os.environ, self.environment, clear=True):
            snapshot = git.load(self.root)
            self.assertEqual(git.label(self.root / "clean.txt", snapshot), "--")
            self.assertEqual(git.label(self.root / "changed.txt", snapshot), " M")
            self.assertEqual(git.label(self.root / "Å ny.txt", snapshot), "??")
            self.assertEqual(git.label(self.root / "ignored.log", snapshot), "!!")
            self.assertEqual(git.label(self.root / "added.py", snapshot), "A ")
            self.assertEqual(git.label(self.root / "deleted.txt", snapshot), " D")
            self.assertEqual(git.label(self.root / "folder", snapshot), "??")
            self.assertEqual(git.label(self.root / "cache" / "child.txt", snapshot), "!!")
            self.assertEqual(git.label(self.root, snapshot), "**")
            with patch.object(git, "run", wraps=git.run) as run:
                git.load(self.root / "folder")
                self.assertEqual(run.call_count, 1)  # Root discovery only; reuse status snapshot.
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = exa.main(["--no-config", "--icons=never", "--color=never", "--git", "-T", str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("[ M] changed.txt", output.getvalue())
        self.assertIn("[??] Å ny.txt", output.getvalue())
        self.assertIn("[!!] child.txt", output.getvalue())

    def test_git_non_repository_continues_listing(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "file.txt").touch()
        with patch.dict(os.environ, self.environment, clear=True):
            with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()) as error:
                code = exa.main(["--no-config", "--icons=never", "--git", str(outside)])
        self.assertEqual(code, 1)
        self.assertIn("[ER] file.txt", output.getvalue())
        self.assertIn("Git misslyckades", error.getvalue())


if __name__ == "__main__":
    unittest.main()
