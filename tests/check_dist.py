"""Check the built wheel and sdist of bizdays.

Usage: python tests/check_dist.py DIST_DIR --version VERSION

Standard library only, so it runs on Python 3.10 without installing anything.
In the patterns below ``*`` never matches ``/``.
"""

from __future__ import annotations

import argparse
import fnmatch
import tarfile
import zipfile
from pathlib import Path

PKG_ALLOWED = ("bizdays/*.py", "bizdays/py.typed", "bizdays/data/*.py", "bizdays/data/*.json")
PKG_REQUIRED = (
    "bizdays/__init__.py",
    "bizdays/py.typed",
    "bizdays/data/ANBIMA.json",
    "bizdays/data/B3.json",
    "bizdays/data/Actual.json",
)

WHEEL_ALLOWED = PKG_ALLOWED + (
    "bizdays-{version}.dist-info/METADATA",
    "bizdays-{version}.dist-info/WHEEL",
    "bizdays-{version}.dist-info/RECORD",
    "bizdays-{version}.dist-info/licenses/LICENSE.txt",
)
SDIST_ALLOWED = (
    "PKG-INFO",
    "pyproject.toml",
    "README.md",
    "LICENSE.txt",
    "CHANGELOG.md",
    ".gitignore",
    *PKG_ALLOWED,
    "benchmarks/*.py",
    "benchmarks/README.md",
)
WHEEL_REQUIRED = PKG_REQUIRED + ("bizdays-{version}.dist-info/licenses/LICENSE.txt",)
SDIST_REQUIRED = PKG_REQUIRED + ("LICENSE.txt",)


def _match(path: str, pattern: str) -> bool:
    parts, pparts = path.split("/"), pattern.split("/")
    return len(parts) == len(pparts) and all(fnmatch.fnmatchcase(a, b) for a, b in zip(parts, pparts))


def _sdist_test_path_ok(path: str) -> bool:
    # same rule as the sdist build: all of tests/ except tests/legacy/ and compiled files
    parts = path.split("/")
    return (
        len(parts) > 1
        and parts[0] == "tests"
        and parts[1] != "legacy"
        and "__pycache__" not in parts
        and not path.endswith(".pyc")
    )


def _version_line(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
        if not line.strip():
            break  # end of the headers
    return None


def _check_members(name, members, allowed, required, version, test_rule=False):
    problems = []
    allowed = tuple(p.format(version=version) for p in allowed)
    for m in members:
        if not (any(_match(m, p) for p in allowed) or (test_rule and _sdist_test_path_ok(m))):
            problems.append(f"{name}: forbidden path {m}")
    for p in required:
        p = p.format(version=version)
        if not any(_match(m, p) for m in members):
            problems.append(f"{name}: missing {p}")
    return problems


def _check_wheel(path: Path, version: str) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        members = [n for n in zf.namelist() if not n.endswith("/")]
        meta_name = f"bizdays-{version}.dist-info/METADATA"
        meta = zf.read(meta_name).decode() if meta_name in members else ""
    problems = _check_members(path.name, members, WHEEL_ALLOWED, WHEEL_REQUIRED, version)
    found = _version_line(meta)
    if found != version:
        problems.append(f"{path.name}: METADATA has Version {found}, expected {version}")
    return problems


def _check_sdist(path: Path, version: str) -> list[str]:
    prefix = f"bizdays-{version}/"
    problems: list[str] = []
    members: list[str] = []
    meta = ""
    with tarfile.open(path) as tf:
        for info in tf.getmembers():
            if info.isdir():
                continue
            if not info.name.startswith(prefix):
                problems.append(f"{path.name}: path outside {prefix}: {info.name}")
                continue
            rel = info.name[len(prefix) :]
            members.append(rel)
            if rel == "PKG-INFO":
                f = tf.extractfile(info)
                meta = f.read().decode() if f else ""
    problems += _check_members(path.name, members, SDIST_ALLOWED, SDIST_REQUIRED, version, test_rule=True)
    found = _version_line(meta)
    if found != version:
        problems.append(f"{path.name}: PKG-INFO has Version {found}, expected {version}")
    return problems


def check_dist(dist_dir: Path, version: str) -> list[str]:
    """Return the problems found in DIST_DIR; an empty list means OK."""
    dist_dir = Path(dist_dir)
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    problems = []
    if len(wheels) != 1 or len(sdists) != 1:
        found = [p.name for p in wheels + sdists]
        return [f"expected exactly one wheel and one sdist in {dist_dir}, found {found}"]
    wheel, sdist = wheels[0], sdists[0]
    if wheel.name != f"bizdays-{version}-py3-none-any.whl":
        problems.append(f"wheel file name {wheel.name} does not match version {version}")
    if sdist.name != f"bizdays-{version}.tar.gz":
        problems.append(f"sdist file name {sdist.name} does not match version {version}")
    if problems:
        return problems
    return _check_wheel(wheel, version) + _check_sdist(sdist, version)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dist_dir", type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args(argv)
    problems = check_dist(args.dist_dir, args.version)
    for p in problems:
        print(p)
    if problems:
        return 1
    names = [p.name for p in sorted(args.dist_dir.glob("*.whl")) + sorted(args.dist_dir.glob("*.tar.gz"))]
    print("dist OK:", " ".join(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
