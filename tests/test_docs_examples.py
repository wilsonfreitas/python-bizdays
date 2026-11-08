"""The examples in README.md and docs/source/api.rst run as doctests (WIL-147)."""

import doctest
import inspect
import json
import re
from pathlib import Path

import numpy as np
import pytest

from bizdays import Calendar

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "docs/source/api.rst"
README = ROOT / "README.md"

PUBLIC_METHODS = sorted(n for n in vars(Calendar) if not n.startswith("_") and callable(getattr(Calendar, n)))


def _text(path: Path) -> str:
    # the build job runs the tests from a temp folder, and the sdist has no docs/
    if not path.exists():
        pytest.skip(f"{path} not in this tree")
    return path.read_text("utf-8")


def _headings(text: str) -> list[str]:
    lines = text.splitlines()
    return [
        a.strip()
        for a, b in zip(lines, lines[1:])
        if a.strip() and len(b) == len(a) and len(set(b)) == 1 and b[0] in "-^\""
    ]


def _section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = lines.index(heading) + 2
    names = set(_headings(text))
    end = next((i for i in range(start, len(lines)) if lines[i].strip() in names), len(lines))
    return "\n".join(lines[start:end])


@pytest.mark.skipif(np.lib.NumpyVersion(np.__version__) < "2.0.0", reason="doctests use NumPy 2 reprs")
@pytest.mark.parametrize("path", ["README.md", "docs/source/api.rst"])
def test_doc_examples_pass(path):
    _text(ROOT / path)
    r = doctest.testfile(
        str(ROOT / path), module_relative=False, optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
    )
    assert r.attempted > 0
    assert r.failed == 0


@pytest.mark.parametrize("name", PUBLIC_METHODS)
def test_every_public_method_has_an_example(name):
    text = _text(API)
    assert f".. automethod:: Calendar.{name}" in text
    lines = [line.strip() for line in text.splitlines()]
    assert any(line.startswith((">>>", "...")) and re.search(rf"\.{name}\(", line) for line in lines)


def test_api_reference_topics():
    headings = _headings(_text(API))
    missing = [
        t
        for t in ("Output types", "Missing values", "Vector arguments", "Errors", "Range recipes", "Adjust maturities first")
        if t not in headings
    ]
    assert missing == []


def test_docs_cross_links():
    text = _text(API)
    assert ":doc:`migration`" in text
    assert "CHANGELOG.md" in text
    assert ":doc:`calendar-data`" in _section(text, "Loading calendars")


def test_readme_cross_links():
    text = _text(README)
    for url in (
        "https://wilsonfreitas.github.io/python-bizdays/migration.html",
        "https://wilsonfreitas.github.io/python-bizdays/api.html",
        "https://github.com/wilsonfreitas/python-bizdays/blob/master/CHANGELOG.md",
    ):
        assert url in text
    layout = text.split("## JSON calendar layout", 1)[1].split("\n## ", 1)[0]
    assert "start.date" in layout
    assert "end.date" in layout


def test_readme_links_are_absolute():
    # README is the PyPI description, where relative links break
    targets = re.findall(r"\]\(([^)\s]+)", _text(README))
    assert [t for t in targets if not t.startswith(("https://", "#"))] == []


def test_readme_install_line():
    assert "pip install bizdays" in _text(README)


STALE = ["schema compatibility", "current public API", "current NumPy-backed", "get_option", "set_option"]


NOTEBOOKS = ["quick", "pandas", "calendars", "getdate"]


@pytest.mark.parametrize(
    "path",
    ["README.md", "docs/source/index.rst", "docs/source/api.rst", *(f"docs/source/{n}.ipynb" for n in NOTEBOOKS)],
)
def test_no_stale_wording(path):
    text = _text(ROOT / path)
    if path.endswith(".ipynb"):
        text = "\n".join("".join(cell["source"]) for cell in json.loads(text)["cells"])
    assert [s for s in STALE if s in text] == []


def _documented_parameters(doc: str) -> list[str]:
    m = re.search(r"Parameters\n-+\n(.*?)(?:\n\S[^\n]*\n-{3,}\n|\Z)", doc, re.S)
    return re.findall(r"^(\w+)\s*:", m.group(1), re.M) if m else []


@pytest.mark.parametrize("name", PUBLIC_METHODS)
def test_docstring_parameters_match_signature(name):
    method = getattr(Calendar, name)
    expected = [p for p in inspect.signature(method).parameters if p not in ("self", "cls")]
    assert _documented_parameters(inspect.getdoc(method) or "") == expected


@pytest.mark.parametrize(
    "name",
    [
        "bizdays",
        "isbizday",
        "offset",
        "following",
        "preceding",
        "modified_following",
        "modified_preceding",
        "adjust_next",
        "adjust_previous",
        "seq",
        "diff",
        "getdate",
        "getbizdays",
    ],
)
def test_docstrings_name_their_errors(name):
    doc = inspect.getdoc(getattr(Calendar, name)) or ""
    assert "Raises" in doc
    assert "DateOutOfRange" in doc
    assert "ValueError" in doc


def test_load_docstring_names_its_errors():
    doc = inspect.getdoc(Calendar.load) or ""
    for word in ("Raises", "FileNotFoundError", "ImportError", "ValueError"):
        assert word in doc
