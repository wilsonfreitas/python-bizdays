"""Checks for the v1-to-v2 migration guide (docs/source/migration.rst)."""

import doctest
import re
from pathlib import Path

import pytest

from bizdays import Calendar

GUIDE = Path(__file__).resolve().parents[1] / "docs" / "source" / "migration.rst"

REQUIRED = [
    "python-and-dependencies",
    "optional-providers",
    "removed-top-level-names",
    "options-and-modes",
    "vec-removed",
    "date-out-of-range",
    "constructor",
    "load-keyword-only",
    "cal-files",
    "load-errors",
    "strict-date-strings",
    "input-containers",
    "whole-counts",
    "return-types",
    "missing-values",
    "vector-lengths",
    "calendar-range",
    "getdate-signature",
    "getdate-grammar",
    "getdate-year-ref",
    "getbizdays",
    "calendar-data",
]
# Install commands and optional packages cannot run inside the test suite.
NO_DOCTEST = {"python-and-dependencies", "optional-providers"}
KINDS = ("mechanical", "manual", "no direct replacement", "nothing to change")

# The sdist ships tests/ but not docs/.
needs_guide = pytest.mark.skipif(not GUIDE.exists(), reason="docs/ not in sdist")


def _entry(text: str, slug: str) -> str:
    start = text.index(f".. _migrate-{slug}:")
    end = text.find(".. _migrate-", start + 1)
    return text[start:] if end == -1 else text[start:end]


@needs_guide
def test_migration_guide_examples_run():
    result = doctest.testfile(
        str(GUIDE),
        module_relative=False,
        optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE | doctest.IGNORE_EXCEPTION_DETAIL,
    )
    assert result.failed == 0
    assert result.attempted >= 40


@needs_guide
def test_migration_guide_covers_inventory():
    text = GUIDE.read_text(encoding="utf-8")
    assert set(re.findall(r"^\.\. _migrate-(\S+):$", text, re.M)) == set(REQUIRED)
    for slug in REQUIRED:
        assert f":ref:`migrate-{slug}`" in text


@needs_guide
@pytest.mark.parametrize("slug", REQUIRED)
def test_migration_guide_entry_format(slug):
    entry = _entry(GUIDE.read_text(encoding="utf-8"), slug)
    for field in ("**v1:**", "**v2:**", "**Why:**", "Before (1.0.20):", "After (2.0):"):
        assert field in entry
    match = re.search(r"\*\*Migration:\*\* (.+)", entry)
    assert match is not None
    assert match.group(1).startswith(KINDS)
    if slug not in NO_DOCTEST:
        assert ">>>" in entry


def test_cal_error_points_to_guide(tmp_path):
    path = tmp_path / "old.cal"
    path.write_text("2001-01-01\nSaturday\n")
    with pytest.raises(ValueError, match="migration"):
        Calendar.load(filename=str(path))


@needs_guide
def test_guide_has_cal_recipe():
    assert ".. _migrate-cal-files:" in GUIDE.read_text(encoding="utf-8")
