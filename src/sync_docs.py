"""Sync README.md ## API Reference section from Python docstrings on push."""

import ast
import re
import subprocess
import sys
import textwrap
from collections import namedtuple
from pathlib import Path

# T-02 — DocEntry data type
DocEntry = namedtuple("DocEntry", ["name", "signature", "docstring"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unparse_node(node) -> str:
    """Render an annotation AST node to a string (Python 3.8+ compatible)."""
    if sys.version_info >= (3, 9):
        return ast.unparse(node)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_unparse_node(node.value)}.{node.attr}"
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Subscript):
        # Python 3.8 wraps slice in ast.Index; 3.9+ does not
        slc = node.slice
        if isinstance(slc, ast.Index):
            slc = slc.value
        return f"{_unparse_node(node.value)}[{_unparse_node(slc)}]"
    if isinstance(node, ast.Tuple):
        return ", ".join(_unparse_node(e) for e in node.elts)
    return ""


def _build_signature(node) -> str:
    """Return parameter list string (no function name) from a def/class node."""
    if isinstance(node, ast.ClassDef):
        return ""

    args = node.args
    parts = []

    posonlyargs = getattr(args, "posonlyargs", [])
    all_positional = posonlyargs + args.args
    defaults_start = len(all_positional) - len(args.defaults)

    for i, arg in enumerate(all_positional):
        part = arg.arg
        if arg.annotation:
            part += f": {_unparse_node(arg.annotation)}"
        di = i - defaults_start
        if di >= 0:
            part += f" = {_unparse_node(args.defaults[di])}"
        parts.append(part)

    if args.vararg:
        v = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            v += f": {_unparse_node(args.vararg.annotation)}"
        parts.append(v)

    for i, kw in enumerate(args.kwonlyargs):
        part = kw.arg
        if kw.annotation:
            part += f": {_unparse_node(kw.annotation)}"
        kd = args.kw_defaults[i]
        if kd is not None:
            part += f" = {_unparse_node(kd)}"
        parts.append(part)

    if args.kwarg:
        k = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            k += f": {_unparse_node(args.kwarg.annotation)}"
        parts.append(k)

    if parts and parts[0] in ("self", "cls"):
        parts = parts[1:]

    return ", ".join(parts)


def _format_entries(entries: list) -> str:
    """Render a list of DocEntry items as a Markdown string."""
    parts = []
    for entry in entries:
        if entry.signature:
            header = f"### `{entry.name}({entry.signature})`"
        else:
            header = f"### `{entry.name}`"
        parts.append(f"{header}\n\n{entry.docstring}\n")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# T-02 — DocstringExtractor
# ---------------------------------------------------------------------------

class DocstringExtractor:
    """Extract top-level Google-style docstrings from a Python source file."""

    def extract(self, file_path: Path) -> list:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        if "�" in source:
            print(
                f"sync_docs: warning: {file_path} contains non-UTF-8 characters",
                file=sys.stderr,
            )
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as exc:
            print(
                f"sync_docs: warning: skipping {file_path} (parse error: {exc})",
                file=sys.stderr,
            )
            return []

        entries = []
        for node in ast.iter_child_nodes(tree):
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                continue
            raw = ast.get_docstring(node)
            if not raw:
                continue
            entries.append(
                DocEntry(
                    name=node.name,
                    signature=_build_signature(node),
                    docstring=textwrap.dedent(raw).strip(),
                )
            )
        return entries


# ---------------------------------------------------------------------------
# T-03 — ReadmeManager
# ---------------------------------------------------------------------------

class ReadmeManager:
    """Read and write the ## API Reference section in README.md."""

    _HEADING = "## API Reference"
    _SECTION_RE = re.compile(
        r"## API Reference\n(.*?)(?=\n## |\Z)", re.DOTALL
    )

    def read_section(self, readme_path: Path) -> str:
        if not readme_path.exists():
            return ""
        text = readme_path.read_text(encoding="utf-8")
        match = self._SECTION_RE.search(text)
        return match.group(1) if match else ""

    def write_section(self, readme_path: Path, content: str) -> None:
        text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
        new_section = f"{self._HEADING}\n{content}"
        if self._SECTION_RE.search(text):
            text = self._SECTION_RE.sub(lambda _m: new_section, text, count=1)
        else:
            if text and not text.endswith("\n"):
                text += "\n"
            text += f"\n{new_section}"
        readme_path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# T-04 — ChangeDetector
# ---------------------------------------------------------------------------

class ChangeDetector:
    """Detect whether the API Reference content has changed."""

    def has_changed(self, old: str, new: str) -> bool:
        return old.strip() != new.strip()


# ---------------------------------------------------------------------------
# T-05 — GitCommitter
# ---------------------------------------------------------------------------

class GitCommitter:
    """Stage README.md and create a sync commit; rollback on failure."""

    def get_short_hash(self) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(
                f"sync_docs: error: git rev-parse failed: {result.stderr.strip()}",
                file=sys.stderr,
            )
            sys.exit(1)
        return result.stdout.strip()

    def stage_and_commit(self, readme_path: Path, message: str) -> None:
        original = readme_path.read_text(encoding="utf-8")

        add = subprocess.run(
            ["git", "add", str(readme_path)], capture_output=True, text=True
        )
        if add.returncode != 0:
            print(
                f"sync_docs: error: git add failed: {add.stderr.strip()}",
                file=sys.stderr,
            )
            readme_path.write_text(original, encoding="utf-8")
            sys.exit(1)

        commit = subprocess.run(
            ["git", "commit", "-m", message], capture_output=True, text=True
        )
        if commit.returncode != 0:
            print(
                f"sync_docs: error: git commit failed: {commit.stderr.strip()}",
                file=sys.stderr,
            )
            readme_path.write_text(original, encoding="utf-8")
            sys.exit(1)


# ---------------------------------------------------------------------------
# T-06 — main() orchestrator
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        readme_path = Path("README.md")
        py_files = sorted(Path(".").glob("*.py"))

        if not py_files:
            print(
                "sync_docs: warning: no .py files in repo root; skipping README update",
                file=sys.stderr,
            )
            sys.exit(0)

        extractor = DocstringExtractor()
        all_entries: list = []
        for f in py_files:
            all_entries.extend(extractor.extract(f))

        new_content = _format_entries(all_entries)

        manager = ReadmeManager()
        old_content = manager.read_section(readme_path)

        if not ChangeDetector().has_changed(old_content, new_content):
            print("sync_docs: no docstring changes detected", file=sys.stderr)
            sys.exit(0)

        manager.write_section(readme_path, new_content)

        committer = GitCommitter()
        short_hash = committer.get_short_hash()
        committer.stage_and_commit(
            readme_path, f"docs: auto-sync from {short_hash}"
        )

        print("sync_docs: README.md updated and committed", file=sys.stderr)
        sys.exit(0)

    except Exception as exc:
        print(f"sync_docs: unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
