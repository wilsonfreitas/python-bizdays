"""Rules for CHANGELOG.md: the 2.0.0 entry doubles as the GitHub Release text."""

import importlib.metadata
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
GUIDE = ROOT / "docs" / "source" / "migration.rst"
MIGRATION_URL = "https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-"
V2_SECTIONS = [
    "Upgrade",
    "Supported environments",
    "Breaking changes",
    "New features",
    "Bug fixes",
    "Calendar data",
    "Known limitations",
    "Contributors",
]

pytestmark = pytest.mark.skipif(not CHANGELOG.exists(), reason="no CHANGELOG.md")
needs_guide = pytest.mark.skipif(not GUIDE.exists(), reason="no migration guide")


def entry(version: str) -> str:
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(
        rf"^### version {re.escape(version)} .*?\n(.*?)(?=^### version |\Z)",
        text,
        re.M | re.S,
    )
    assert match, f"no entry for version {version}"
    return match.group(1)


def subsection(text: str, title: str) -> str:
    match = re.search(rf"^#### {re.escape(title)}\n(.*?)(?=^#### |\Z)", text, re.M | re.S)
    assert match, f"no subsection {title!r}"
    return match.group(1)


def breaking() -> str:
    return subsection(entry("2.0.0"), "Breaking changes")


def test_top_entry_matches_package_version() -> None:
    first = CHANGELOG.read_text(encoding="utf-8").splitlines()[0]
    match = re.match(r"^### version (\d+\.\d+\.\d+) \((unreleased|\d{4}-\d{2}-\d{2})\)$", first)
    assert match, first
    version = re.match(r"\d+\.\d+\.\d+", importlib.metadata.version("bizdays"))
    assert version
    assert match.group(1) == version.group()


def test_v2_entry_sections_in_order() -> None:
    assert re.findall(r"^#### (.+)$", entry("2.0.0"), re.M) == V2_SECTIONS


def test_every_breaking_item_links_migration() -> None:
    bullets = [b for b in re.split(r"^(?=\* )", breaking(), flags=re.M) if b.startswith("* ")]
    assert bullets
    for bullet in bullets:
        assert MIGRATION_URL in bullet, bullet


@needs_guide
def test_every_migration_change_is_listed() -> None:
    parts = re.split(r"^\.\. _migrate-(\S+):$", GUIDE.read_text(encoding="utf-8"), flags=re.M)
    section = breaking()
    slugs = parts[1::2]
    assert slugs
    for slug, chunk in zip(slugs, parts[2::2]):
        kind = re.search(
            r"\*\*Migration:\*\* (mechanical|manual|no direct replacement|nothing to change)",
            chunk,
        )
        assert kind, f"no migration kind for {slug}"
        if kind.group(1) != "nothing to change":
            assert f"{MIGRATION_URL}{slug})" in section, slug


@needs_guide
def test_migration_links_resolve() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    for slug in re.findall(r"migration\.html#migrate-([a-z0-9-]+)", entry("2.0.0")):
        assert f".. _migrate-{slug}:" in guide, slug


def test_v2_links_are_absolute() -> None:
    links = re.findall(r"\]\(([^)]+)\)", entry("2.0.0"))
    assert links
    for link in links:
        assert link.startswith("https://"), link


def test_1_0_20_entry_is_b3_only() -> None:
    text = entry("1.0.20")
    assert "B3" in text
    for word in ("getdate", "JSON", "NumPy"):
        assert word not in text, word


def test_no_placeholder_dates() -> None:
    headings = re.findall(r"^### version .*$", CHANGELOG.read_text(encoding="utf-8"), re.M)
    for heading in headings:
        assert "YYYY" not in heading, heading


def test_supported_environments_match_metadata() -> None:
    env = subsection(entry("2.0.0"), "Supported environments")
    meta = importlib.metadata.metadata("bizdays")
    assert meta["Requires-Python"] == ">=3.10"
    assert "3.10" in env and "3.14" in env
    for dep in meta.get_all("Requires-Dist") or []:
        if ";" not in dep:
            assert dep.replace(" ", "") in env, dep
    assert "pandas 3" in env
