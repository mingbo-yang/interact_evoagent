"""Tests for glob and outline navigation tools."""

import pytest

from evoagent.tools.navigation_tools import GlobTool, OutlineTool


@pytest.mark.asyncio
async def test_glob_matches_python_files(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    (tmp_path / "c.txt").write_text("nope\n")
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "d.py").write_text("z = 3\n")

    tool = GlobTool(tmp_path)
    res = await tool.run(pattern="**/*.py")
    assert res.success
    lines = set(res.output.splitlines())
    assert "a.py" in lines
    assert "b.py" in lines
    normalized = {ln.replace("\\", "/") for ln in lines}
    assert "pkg/d.py" in normalized
    assert "c.txt" not in res.output
    assert res.metadata["matches"] == 3


@pytest.mark.asyncio
async def test_glob_skips_ignored_dirs(tmp_path):
    (tmp_path / "keep.py").write_text("a = 1\n")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "junk.py").write_text("b = 2\n")

    tool = GlobTool(tmp_path)
    res = await tool.run(pattern="**/*.py")
    assert res.success
    assert "keep.py" in res.output
    assert "junk.py" not in res.output


@pytest.mark.asyncio
async def test_glob_no_match(tmp_path):
    tool = GlobTool(tmp_path)
    res = await tool.run(pattern="**/*.rs")
    assert res.success
    assert "No files matched" in res.output


@pytest.mark.asyncio
async def test_glob_rejects_escape(tmp_path):
    tool = GlobTool(tmp_path)
    res = await tool.run(pattern="*.py", path="..")
    assert res.success is False
    assert "escape" in (res.error or "").lower()


@pytest.mark.asyncio
async def test_glob_rejects_dotdot_pattern(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (tmp_path / "outside.py").write_text("secret = 1\n")
    tool = GlobTool(workspace)
    res = await tool.run(pattern="../*.py")
    assert res.success is False
    assert "outside.py" not in (res.output or "")


@pytest.mark.asyncio
async def test_outline_extracts_symbols(tmp_path):
    src = (
        "import os\n"
        "\n"
        "TOP = 1\n"
        "\n"
        "def foo(a, b):\n"
        "    return a + b\n"
        "\n"
        "class Bar(Base):\n"
        "    def method(self, x):\n"
        "        return x\n"
        "\n"
        "    async def amethod(self):\n"
        "        return None\n"
    )
    f = tmp_path / "mod.py"
    f.write_text(src)
    tool = OutlineTool(tmp_path)
    res = await tool.run(path="mod.py")
    assert res.success
    out = res.output
    assert "def foo(a, b)" in out
    assert "class Bar(Base)" in out
    assert "def method(self, x)" in out
    assert "async def amethod(self)" in out
    # method is nested under class → indented
    assert "  def method" in out
    # line numbers present
    assert "[L5]" in out  # foo at line 5


@pytest.mark.asyncio
async def test_outline_rejects_non_python(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("hello")
    tool = OutlineTool(tmp_path)
    res = await tool.run(path="data.txt")
    assert res.success is False
    assert "Python" in (res.error or "")


@pytest.mark.asyncio
async def test_outline_syntax_error(tmp_path):
    f = tmp_path / "broken.py"
    f.write_text("def (:\n")
    tool = OutlineTool(tmp_path)
    res = await tool.run(path="broken.py")
    assert res.success is False
    assert "parse" in (res.error or "").lower()


@pytest.mark.asyncio
async def test_outline_preserves_signature_markers(tmp_path):
    src = (
        "def f(a, b=1, *args, c, d=2, **kw):\n"
        "    return a\n"
        "\n"
        "def g(x, /, y):\n"
        "    return x\n"
    )
    f = tmp_path / "sig.py"
    f.write_text(src)
    tool = OutlineTool(tmp_path)
    res = await tool.run(path="sig.py")
    assert res.success
    out = res.output
    assert "b=1" in out
    assert "*args" in out
    assert "**kw" in out
    assert "/" in out  # positional-only marker preserved


@pytest.mark.asyncio
async def test_outline_empty(tmp_path):
    f = tmp_path / "empty.py"
    f.write_text("x = 1\n")
    tool = OutlineTool(tmp_path)
    res = await tool.run(path="empty.py")
    assert res.success
    assert "no top-level" in res.output.lower()
