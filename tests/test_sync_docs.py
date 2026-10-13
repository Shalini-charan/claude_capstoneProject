"""Verification suite for sync_docs.py — T-09 through T-13."""

import ast
import contextlib
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sync_docs import (
    DocEntry,
    DocstringExtractor,
    ReadmeManager,
    ChangeDetector,
    GitCommitter,
    _build_signature,
    _format_entries,
    main,
    parse_args,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

GOOGLE_STYLE_PY = textwrap.dedent("""\
    def add(a: int, b: int) -> int:
        \"\"\"Add two numbers.

        Args:
            a: First number.
            b: Second number.

        Returns:
            The sum.
        \"\"\"
        return a + b


    class Greeter:
        \"\"\"A simple greeter.

        Attributes:
            name: The name to greet.
        \"\"\"
        pass
""")


def _init_git_repo(directory: Path) -> None:
    """Create a git repo with a single initial commit so HEAD exists."""
    run = lambda *cmd: subprocess.run(
        list(cmd), cwd=directory, capture_output=True, check=False
    )
    run("git", "init")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "user.name", "Test User")
    readme = directory / "README.md"
    readme.write_text("# Test Repo\n", encoding="utf-8")
    run("git", "add", "README.md")
    run("git", "commit", "-m", "init")


# ---------------------------------------------------------------------------
# T-09 — DocstringExtractor
# ---------------------------------------------------------------------------

class TestDocstringExtractor(unittest.TestCase):

    def setUp(self):
        self.ex = DocstringExtractor()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(str(self.tmpdir), ignore_errors=True)

    def _py(self, content: str, name: str = "s.py") -> Path:
        p = self.tmpdir / name
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return p

    # --- happy path ---

    def test_function_with_google_docstring(self):
        entries = self.ex.extract(self._py(GOOGLE_STYLE_PY))
        self.assertEqual(len(entries), 2)
        fn = entries[0]
        self.assertEqual(fn.name, "add")
        self.assertEqual(fn.signature, "a: int, b: int")
        self.assertIn("Add two numbers", fn.docstring)

    def test_class_with_docstring(self):
        entries = self.ex.extract(self._py(GOOGLE_STYLE_PY))
        cls = entries[1]
        self.assertEqual(cls.name, "Greeter")
        self.assertEqual(cls.signature, "")
        self.assertIn("simple greeter", cls.docstring)

    def test_async_function_extracted(self):
        src = 'async def fetch(url: str) -> str:\n    """Fetch a URL."""\n    pass\n'
        entries = self.ex.extract(self._py(src))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "fetch")

    # --- edge / Not Found cases ---

    def test_no_docstrings_returns_empty(self):
        entries = self.ex.extract(self._py("def foo(x):\n    return x\n"))
        self.assertEqual(entries, [])

    def test_empty_file_returns_empty(self):
        entries = self.ex.extract(self._py(""))
        self.assertEqual(entries, [])

    def test_class_extracted_but_nested_method_is_not(self):
        src = '''\
            class MyClass:
                """Class docstring."""
                def method(self, x: int):
                    """Method docstring."""
                    pass
        '''
        entries = self.ex.extract(self._py(src))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "MyClass")

    def test_syntax_error_skips_file_with_warning(self):
        import io
        from contextlib import redirect_stderr
        buf = io.StringIO()
        with redirect_stderr(buf):
            entries = self.ex.extract(self._py("def broken(:\n    pass\n"))
        self.assertEqual(entries, [])
        self.assertIn("parse error", buf.getvalue())

    def test_non_utf8_chars_emit_warning(self):
        p = self.tmpdir / "latin.py"
        p.write_bytes(b'def f():\n    """Doc."""\n    pass\n\xff\xfe')
        import io
        from contextlib import redirect_stderr
        buf = io.StringIO()
        with redirect_stderr(buf):
            entries = self.ex.extract(p)
        self.assertIn("non-UTF-8", buf.getvalue())


# ---------------------------------------------------------------------------
# _build_signature edge cases (code-review gap from Step 6)
# ---------------------------------------------------------------------------

class TestBuildSignature(unittest.TestCase):

    def _sig(self, src: str) -> str:
        return _build_signature(ast.parse(src).body[0])

    def _method_sig(self, src: str) -> str:
        return _build_signature(ast.parse(src).body[0].body[0])

    def test_simple_params(self):
        self.assertEqual(self._sig("def f(a, b): pass"), "a, b")

    def test_annotated_params(self):
        self.assertEqual(self._sig("def f(a: int, b: str): pass"), "a: int, b: str")

    def test_default_value(self):
        sig = self._sig("def f(a, b=1): pass")
        self.assertIn("b", sig)
        self.assertIn("1", sig)

    def test_plain_self_stripped(self):
        self.assertEqual(self._method_sig("class C:\n    def m(self, x: int): pass"), "x: int")

    def test_annotated_self_stripped(self):
        self.assertEqual(
            self._method_sig("class C:\n    def m(self: 'C', x: int): pass"), "x: int"
        )

    def test_cls_stripped(self):
        self.assertEqual(
            self._method_sig("class C:\n    @classmethod\n    def create(cls, x): pass"), "x"
        )

    def test_star_args_and_kwargs(self):
        sig = self._sig("def f(*args, **kwargs): pass")
        self.assertIn("*args", sig)
        self.assertIn("**kwargs", sig)

    def test_positional_only_separator_present(self):
        sig = self._sig("def f(a, b, /, c): pass")
        self.assertIn("/", sig)
        self.assertTrue(sig.startswith("a, b, /"), f"Got: {sig!r}")

    def test_class_node_returns_empty_string(self):
        self.assertEqual(_build_signature(ast.parse("class Foo: pass").body[0]), "")

    def test_no_params_returns_empty(self):
        self.assertEqual(self._sig("def f(): pass"), "")


# ---------------------------------------------------------------------------
# T-10 — ReadmeManager
# ---------------------------------------------------------------------------

class TestReadmeManager(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.readme = self.tmpdir / "README.md"
        self.mgr = ReadmeManager()

    def tearDown(self):
        shutil.rmtree(str(self.tmpdir), ignore_errors=True)

    # --- read_section ---

    def test_read_section_returns_body(self):
        self.readme.write_text(
            "# Title\n\n## API Reference\n### `foo()`\n\nFoo docs.\n",
            encoding="utf-8",
        )
        self.assertIn("foo()", self.mgr.read_section(self.readme))

    def test_read_section_absent_returns_empty(self):
        self.readme.write_text("# Title\nNo section here.\n", encoding="utf-8")
        self.assertEqual(self.mgr.read_section(self.readme), "")

    def test_read_section_missing_file_returns_empty(self):
        self.assertEqual(self.mgr.read_section(self.tmpdir / "ghost.md"), "")

    def test_read_section_stops_at_next_heading(self):
        self.readme.write_text(
            "# Title\n\n## API Reference\n### `f()`\n\nDocs.\n\n## Other\nother\n",
            encoding="utf-8",
        )
        content = self.mgr.read_section(self.readme)
        self.assertIn("Docs.", content)
        self.assertNotIn("other", content)

    # --- write_section ---

    def test_write_section_appends_new_heading(self):
        self.readme.write_text("# Title\n", encoding="utf-8")
        self.mgr.write_section(self.readme, "### `bar()`\n\nBarDoc.\n")
        text = self.readme.read_text(encoding="utf-8")
        self.assertIn("## API Reference", text)
        self.assertIn("BarDoc", text)

    def test_write_section_overwrites_existing(self):
        self.readme.write_text(
            "# Title\n\n## API Reference\n### `old()`\n\nOld.\n", encoding="utf-8"
        )
        self.mgr.write_section(self.readme, "### `new()`\n\nNew.\n")
        text = self.readme.read_text(encoding="utf-8")
        self.assertEqual(text.count("## API Reference"), 1)
        self.assertIn("New.", text)
        self.assertNotIn("Old.", text)

    def test_write_section_no_duplicate_on_repeat(self):
        self.readme.write_text("# Title\n", encoding="utf-8")
        self.mgr.write_section(self.readme, "content A\n")
        self.mgr.write_section(self.readme, "content B\n")
        text = self.readme.read_text(encoding="utf-8")
        self.assertEqual(text.count("## API Reference"), 1)
        self.assertIn("content B", text)
        self.assertNotIn("content A", text)

    def test_write_section_creates_missing_readme(self):
        new_file = self.tmpdir / "new.md"
        self.assertFalse(new_file.exists())
        self.mgr.write_section(new_file, "### `baz()`\n")
        self.assertTrue(new_file.exists())
        self.assertIn("## API Reference", new_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# T-11 — ChangeDetector
# ---------------------------------------------------------------------------

class TestChangeDetector(unittest.TestCase):

    def setUp(self):
        self.cd = ChangeDetector()

    def test_identical_content_no_change(self):
        self.assertFalse(self.cd.has_changed("foo", "foo"))

    def test_trailing_newline_ignored(self):
        self.assertFalse(self.cd.has_changed("foo\n", "foo"))

    def test_leading_and_trailing_whitespace_ignored(self):
        self.assertFalse(self.cd.has_changed("  foo  ", "foo"))

    def test_different_content_is_changed(self):
        self.assertTrue(self.cd.has_changed("foo", "bar"))

    def test_both_empty_no_change(self):
        self.assertFalse(self.cd.has_changed("", ""))

    def test_empty_vs_content_is_changed(self):
        self.assertTrue(self.cd.has_changed("", "something"))

    def test_whitespace_only_vs_empty_no_change(self):
        self.assertFalse(self.cd.has_changed("   \n\n   ", ""))


# ---------------------------------------------------------------------------
# T-12 — GitCommitter
# ---------------------------------------------------------------------------

class TestGitCommitter(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        _init_git_repo(self.tmpdir)
        self.orig_dir = os.getcwd()
        os.chdir(self.tmpdir)
        self.committer = GitCommitter()
        self.readme = self.tmpdir / "README.md"

    def tearDown(self):
        os.chdir(self.orig_dir)
        shutil.rmtree(str(self.tmpdir), ignore_errors=True)

    def _log(self) -> list:
        r = subprocess.run(
            ["git", "log", "--oneline"], cwd=self.tmpdir, capture_output=True, text=True
        )
        return r.stdout.strip().splitlines()

    def test_get_short_hash_non_empty(self):
        h = self.committer.get_short_hash()
        self.assertIsInstance(h, str)
        self.assertGreater(len(h), 0)

    def test_stage_and_commit_creates_commit(self):
        original = self.readme.read_text(encoding="utf-8")
        self.readme.write_text("# Updated content\n", encoding="utf-8")
        commits_before = len(self._log())
        self.committer.stage_and_commit(self.readme, original, "test: sync")
        self.assertEqual(len(self._log()), commits_before + 1)
        self.assertIn("test: sync", self._log()[0])

    def test_rollback_on_commit_failure_restores_file(self):
        original = self.readme.read_text(encoding="utf-8")
        self.readme.write_text("# Changed\n", encoding="utf-8")

        real_run = subprocess.run

        def fail_on_commit(cmd, **kwargs):
            if isinstance(cmd, list) and len(cmd) >= 2 and cmd[1] == "commit":
                return subprocess.CompletedProcess(cmd, 1, "", "commit rejected")
            return real_run(cmd, **kwargs)

        with patch("sync_docs.subprocess.run", side_effect=fail_on_commit):
            with self.assertRaises(SystemExit) as ctx:
                self.committer.stage_and_commit(self.readme, original, "should fail")

        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(self.readme.read_text(encoding="utf-8"), original)

    def test_rollback_on_commit_failure_unstages_file(self):
        original = self.readme.read_text(encoding="utf-8")
        self.readme.write_text("# Changed\n", encoding="utf-8")

        real_run = subprocess.run

        def fail_on_commit(cmd, **kwargs):
            if isinstance(cmd, list) and len(cmd) >= 2 and cmd[1] == "commit":
                return subprocess.CompletedProcess(cmd, 1, "", "commit rejected")
            return real_run(cmd, **kwargs)

        with patch("sync_docs.subprocess.run", side_effect=fail_on_commit):
            with self.assertRaises(SystemExit):
                self.committer.stage_and_commit(self.readme, original, "should fail")

        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=self.tmpdir, capture_output=True, text=True,
        )
        self.assertEqual(staged.stdout.strip(), "", "README.md should not be staged")


# ---------------------------------------------------------------------------
# T-13 — Integration (end-to-end in an isolated temp git repo)
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        _init_git_repo(self.tmpdir)
        self.orig_dir = os.getcwd()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.orig_dir)
        shutil.rmtree(str(self.tmpdir), ignore_errors=True)

    def _log(self) -> list:
        r = subprocess.run(
            ["git", "log", "--oneline"], cwd=self.tmpdir, capture_output=True, text=True
        )
        return r.stdout.strip().splitlines()

    def _commit_py(self, content: str, name: str = "sample.py") -> None:
        f = self.tmpdir / name
        f.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", name], cwd=self.tmpdir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"add {name}"],
            cwd=self.tmpdir, capture_output=True,
        )

    # --- AC-1 + AC-2 + AC-3: first run creates and commits API Reference ---

    def test_first_run_creates_api_reference_section(self):
        self._commit_py(GOOGLE_STYLE_PY)
        commits_before = len(self._log())

        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertEqual(ctx.exception.code, 0)

        readme = (self.tmpdir / "README.md").read_text(encoding="utf-8")
        self.assertIn("## API Reference", readme)
        self.assertIn("add(", readme)
        self.assertIn("Add two numbers", readme)
        self.assertIn("Greeter", readme)

        self.assertEqual(len(self._log()), commits_before + 1)
        self.assertIn("auto-sync", self._log()[0])

    # --- AC-4: second run with no changes makes no commit ---

    def test_second_run_no_change_makes_no_commit(self):
        self._commit_py(GOOGLE_STYLE_PY)
        with self.assertRaises(SystemExit):
            main([])
        commits_after_first = len(self._log())

        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(len(self._log()), commits_after_first)

    # --- Updated docstring triggers new sync commit ---

    def test_updated_docstring_triggers_new_sync_commit(self):
        self._commit_py(GOOGLE_STYLE_PY)
        with self.assertRaises(SystemExit):
            main([])
        commits_after_first_sync = len(self._log())

        updated = GOOGLE_STYLE_PY.replace(
            "Add two numbers.", "Compute the sum of two integers."
        )
        self._commit_py(updated)

        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertEqual(ctx.exception.code, 0)

        # One code commit + one sync commit on top of first sync
        self.assertEqual(len(self._log()), commits_after_first_sync + 2)

        readme = (self.tmpdir / "README.md").read_text(encoding="utf-8")
        self.assertIn("Compute the sum", readme)
        self.assertNotIn("Add two numbers.", readme)

    # --- No .py files: exits cleanly with no commit (DD-05) ---

    def test_no_py_files_exits_0_no_commit(self):
        commits_before = len(self._log())
        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(len(self._log()), commits_before)
        self.assertFalse(any("auto-sync" in l for l in self._log()))

    # --- README created automatically if missing ---

    def test_creates_readme_when_missing(self):
        (self.tmpdir / "README.md").unlink()
        self._commit_py(GOOGLE_STYLE_PY)

        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertEqual(ctx.exception.code, 0)
        self.assertTrue((self.tmpdir / "README.md").exists())
        self.assertIn("## API Reference", (self.tmpdir / "README.md").read_text())


class TestDryRun(unittest.TestCase):
    """CLAUDE-3: --dry-run previews the README update without side effects."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.orig_dir = os.getcwd()
        os.chdir(self.tmpdir)
        self.readme = self.tmpdir / "README.md"
        self.readme.write_text("# Test Repo\n", encoding="utf-8")

    def tearDown(self):
        os.chdir(self.orig_dir)
        shutil.rmtree(str(self.tmpdir), ignore_errors=True)

    def _write_py(self, content=GOOGLE_STYLE_PY, name="sample.py"):
        (self.tmpdir / name).write_text(content, encoding="utf-8")

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as ctx:
                main(argv)
        return ctx.exception.code, out.getvalue(), err.getvalue()

    def _expected_section(self):
        entries = DocstringExtractor().extract(self.tmpdir / "sample.py")
        return ReadmeManager().render_section(_format_entries(entries))

    def _readme_bytes(self):
        return self.readme.read_bytes()

    def _fake_git_ok(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "abc1234\n", "")

    # --- parse_args / --help (FR-1, FR-10, NFR-7) ---

    def test_parse_args_defaults_and_flag(self):
        self.assertFalse(parse_args([]).dry_run)
        self.assertTrue(parse_args(["--dry-run"]).dry_run)

    def test_help_lists_dry_run_on_one_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                parse_args(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        lines = [l for l in out.getvalue().splitlines() if "--dry-run" in l]
        self.assertTrue(lines)
        # The option and its description share one rendered line at a wide width.
        wide = io.StringIO()
        with patch.dict(os.environ, {"COLUMNS": "200"}):
            with contextlib.redirect_stdout(wide):
                with self.assertRaises(SystemExit):
                    parse_args(["-h"])
        opt_lines = [
            l for l in wide.getvalue().splitlines()
            if l.strip().startswith("--dry-run")
        ]
        self.assertEqual(len(opt_lines), 1)
        self.assertIn("Preview", opt_lines[0])
        description = opt_lines[0].strip()[len("--dry-run"):].strip()
        self.assertLessEqual(len(description), 100)

    def test_write_stdout_utf8_buffer_fallback(self):
        import sync_docs

        class BufOnly:
            def __init__(self):
                self.buffer = io.BytesIO()

        fake = BufOnly()
        with patch.object(sync_docs.sys, "stdout", fake):
            sync_docs._write_stdout_utf8("a → b")
        self.assertEqual(fake.buffer.getvalue(), "a → b".encode("utf-8"))

    def test_write_stdout_utf8_plain_write_fallback(self):
        import sync_docs

        class WriteOnly:
            def __init__(self):
                self.text = ""

            def write(self, value):
                self.text += value

        fake = WriteOnly()
        with patch.object(sync_docs.sys, "stdout", fake):
            sync_docs._write_stdout_utf8("plain")
        self.assertEqual(fake.text, "plain")

    def test_unknown_flag_exits_2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                parse_args(["--bogus"])
        self.assertEqual(ctx.exception.code, 2)

    # --- changed section (AC1, AC2) ---

    def test_dry_run_prints_section_and_leaves_readme_untouched(self):
        self._write_py()
        before = self._readme_bytes()
        mtime = self.readme.stat().st_mtime_ns
        with patch("sync_docs.subprocess.run") as run:
            code, out, err = self._run(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(out, self._expected_section())
        self.assertEqual(self._readme_bytes(), before)
        self.assertEqual(self.readme.stat().st_mtime_ns, mtime)
        run.assert_not_called()

    def test_dry_run_does_not_construct_git_committer(self):
        self._write_py()
        with patch("sync_docs.GitCommitter") as gc:
            self._run(["--dry-run"])
        gc.assert_not_called()

    # --- up to date (AC3) ---

    def test_dry_run_up_to_date_message(self):
        self._write_py()
        with patch("sync_docs.subprocess.run") as run:
            self._fake_git_ok(run)
            self._run([])
        before = self._readme_bytes()
        with patch("sync_docs.subprocess.run") as run:
            code, out, err = self._run(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("README.md is up to date", out)
        self.assertNotIn("README.md is up to date", err)
        self.assertEqual(self._readme_bytes(), before)
        run.assert_not_called()

    # --- no dry-run: unchanged behaviour (AC6) ---

    def test_main_empty_argv_real_run_commits(self):
        self._write_py()
        with patch("sync_docs.subprocess.run") as run:
            self._fake_git_ok(run)
            code, out, err = self._run([])
        self.assertEqual(code, 0)
        cmds = [c.args[0][:2] for c in run.call_args_list]
        self.assertEqual(
            cmds, [["git", "rev-parse"], ["git", "add"], ["git", "commit"]]
        )
        self.assertIn("README.md updated and committed", err)
        self.assertEqual(out, "")
        self.assertIn("## API Reference", self.readme.read_text(encoding="utf-8"))

    # --- missing inputs (FR-12, FR-13, FR-14) ---

    def test_dry_run_missing_readme_not_created(self):
        self._write_py()
        self.readme.unlink()
        code, out, _ = self._run(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(out, self._expected_section())
        self.assertFalse(self.readme.exists())

    def test_dry_run_readme_without_section(self):
        self._write_py()
        before = self._readme_bytes()
        code, out, _ = self._run(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("## API Reference\n"))
        self.assertEqual(self._readme_bytes(), before)

    def test_dry_run_no_py_files(self):
        before = self._readme_bytes()
        with patch("sync_docs.subprocess.run") as run:
            code, out, err = self._run(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("no .py files", err)
        self.assertEqual(self._readme_bytes(), before)
        run.assert_not_called()

    # --- warnings and errors (FR-15, FR-17, FR-18) ---

    def test_dry_run_warnings_on_stderr_only(self):
        self._write_py()
        self._write_py("def broken(:\n", "bad.py")
        (self.tmpdir / "latin.py").write_bytes(
            b'def f():\n    """Doc \xff\xfe."""\n'
        )
        code, out, err = self._run(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("parse error", err)
        self.assertIn("non-UTF-8", err)
        self.assertNotIn("sync_docs:", out)
        self.assertIn("## API Reference", out)

    def test_dry_run_unexpected_error_exits_1(self):
        self._write_py()
        before = self._readme_bytes()
        with patch.object(
            DocstringExtractor, "extract", side_effect=RuntimeError("boom")
        ):
            code, out, err = self._run(["--dry-run"])
        self.assertEqual(code, 1)
        self.assertIn("unexpected error", err)
        self.assertEqual(self._readme_bytes(), before)

    # --- KL-4 pinned edge cases ---

    def test_dry_run_no_docstrings_missing_readme_reports_up_to_date(self):
        self._write_py("x = 1\n")
        self.readme.unlink()
        code, out, _ = self._run(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("README.md is up to date", out)
        self.assertFalse(self.readme.exists())

    def test_dry_run_no_docstrings_sectionless_readme(self):
        self._write_py("x = 1\n")
        code, out, _ = self._run(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("README.md is up to date", out)

    def test_dry_run_docstrings_removed_prints_empty_heading(self):
        self._write_py()
        with patch("sync_docs.subprocess.run") as run:
            self._fake_git_ok(run)
            self._run([])
        self._write_py("x = 1\n")
        code, out, _ = self._run(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "## API Reference\n")

    # --- preview equals real run (NFR-2, RISK-07) ---

    def test_preview_equals_real_run_section(self):
        self._write_py()
        _, preview, _ = self._run(["--dry-run"])
        with patch("sync_docs.subprocess.run") as run:
            self._fake_git_ok(run)
            self._run([])
        written = ReadmeManager().read_section(self.readme)
        self.assertEqual(
            preview.replace("\r\n", "\n"),
            "## API Reference\n" + written.replace("\r\n", "\n"),
        )

    # --- UTF-8 stdout (RISK-01) ---

    def _dry_run_subprocess(self):
        script = str(Path(__file__).parent.parent / "src" / "sync_docs.py")
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        return subprocess.run(
            [sys.executable, script, "--dry-run"],
            cwd=self.tmpdir, capture_output=True, env=env,
        )

    def test_dry_run_utf8_stdout_under_cp1252(self):
        self._write_py(
            'def f():\n    """Arrow → and CJK 中文."""\n'
        )
        proc = self._dry_run_subprocess()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = proc.stdout.decode("utf-8")
        self.assertIn("→", text)
        self.assertIn("中文", text)

    def test_dry_run_non_utf8_source_under_cp1252(self):
        (self.tmpdir / "latin.py").write_bytes(
            b'def f():\n    """Doc \xff\xfe."""\n'
        )
        proc = self._dry_run_subprocess()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(b"non-UTF-8", proc.stderr)
        self.assertIn("## API Reference", proc.stdout.decode("utf-8"))

    # --- git state untouched (NFR-1) ---

    def test_dry_run_leaves_git_state_untouched(self):
        _init_git_repo(self.tmpdir)
        self._write_py()

        def git(*cmd):
            return subprocess.run(
                ["git", *cmd], cwd=self.tmpdir, capture_output=True, text=True
            ).stdout

        before = (git("status", "--porcelain"), git("rev-parse", "HEAD"),
                  hashlib.sha256(self._readme_bytes()).hexdigest())
        code, _, _ = self._run(["--dry-run"])
        self.assertEqual(code, 0)
        after = (git("status", "--porcelain"), git("rev-parse", "HEAD"),
                 hashlib.sha256(self._readme_bytes()).hexdigest())
        self.assertEqual(before, after)

    # --- FR-9 placeholder ---

    @unittest.skip("FR-9: needs CLAUDE-2")
    def test_dry_run_with_src_dir(self):
        """Dry run combined with --src-dir scans that directory (owned by CLAUDE-2)."""


if __name__ == "__main__":
    unittest.main(verbosity=2)
