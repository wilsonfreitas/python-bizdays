"""The examples in README.md and docs/source/api.rst run as doctests (WIL-147)."""

import doctest
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
