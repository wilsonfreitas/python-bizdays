import importlib.metadata
import io
import re
import tarfile
import zipfile

import pytest

from tests.check_dist import check_dist, main


def test_installed_version_is_2_0_0():
    # rehearsal builds (2.0.0rc1) must pass too
    assert re.match(r"\d+\.\d+\.\d+", importlib.metadata.version("bizdays")).group() == "2.0.0"


def test_project_metadata():
    meta = importlib.metadata.metadata("bizdays")
    assert meta["License-Expression"] == "MIT"
    classifiers = meta.get_all("Classifier") or []
    assert "Typing :: Typed" in classifiers
    assert "Programming Language :: Python :: 3.10" in classifiers
    assert "Programming Language :: Python :: 3.14" in classifiers
    assert "Programming Language :: Python :: 3.9" not in classifiers
    urls = meta.get_all("Project-URL") or []
    assert "Source, https://github.com/wilsonfreitas/python-bizdays" in urls
    assert "Documentation, https://wilsonfreitas.github.io/python-bizdays/" in urls


# --- artifact checker (tests/check_dist.py) on fake artifacts ---

PKG_FILES = [
    "bizdays/__init__.py",
    "bizdays/calendar.py",
    "bizdays/utils.py",
    "bizdays/py.typed",
    "bizdays/data/__init__.py",
    "bizdays/data/ANBIMA.json",
    "bizdays/data/Actual.json",
    "bizdays/data/B3.json",
]


def _wheel_members(version):
    info = f"bizdays-{version}.dist-info"
    return PKG_FILES + [f"{info}/METADATA", f"{info}/WHEEL", f"{info}/RECORD", f"{info}/licenses/LICENSE.txt"]


def _sdist_members():
    return PKG_FILES + [
        "PKG-INFO",
        "pyproject.toml",
        "README.md",
        "LICENSE.txt",
        "CHANGELOG.md",
        ".gitignore",
        "tests/__init__.py",
        "tests/check_dist.py",
        "tests/test_calendar.py",
        "tests/files/ANBIMA.json",
        "benchmarks/bench.py",
        "benchmarks/README.md",
    ]


def _make_dist(
    dist_dir, version="2.0.0", meta_version=None, wheel_extra=(), sdist_extra=(), wheel_drop=(), sdist_drop=()
):
    meta = f"Metadata-Version: 2.4\nName: bizdays\nVersion: {meta_version or version}\n".encode()
    wheel = dist_dir / f"bizdays-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        for name in _wheel_members(version) + list(wheel_extra):
            if name not in wheel_drop:
                zf.writestr(name, meta if name.endswith("/METADATA") else b"")
    sdist = dist_dir / f"bizdays-{version}.tar.gz"
    with tarfile.open(sdist, "w:gz") as tf:
        for name in _sdist_members() + list(sdist_extra):
            if name in sdist_drop:
                continue
            data = meta if name == "PKG-INFO" else b""
            info = tarfile.TarInfo(f"bizdays-{version}/{name}")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    (dist_dir / ".gitignore").write_text("*\n")  # uv build writes this file too


def test_check_dist_accepts_clean_artifacts(tmp_path, capsys):
    _make_dist(tmp_path)
    assert check_dist(tmp_path, "2.0.0") == []
    assert main([str(tmp_path), "--version", "2.0.0"]) == 0
    assert capsys.readouterr().out.startswith("dist OK")


@pytest.mark.parametrize(
    "kind, path",
    [
        ("sdist", ".claude/settings.local.json"),
        ("sdist", "AGENTS.md"),
        ("sdist", "CLAUDE.md"),
        ("sdist", "uv.lock"),
        ("sdist", "MANIFEST"),
        ("sdist", "docs/source/conf.py"),
        ("sdist", "notebooks/quick.ipynb"),
        ("sdist", "tests/legacy/legacy_bizdays.py"),
        ("sdist", "tests/sub/__pycache__/x.cpython-312.pyc"),
        ("sdist", "bizdays/__pycache__/utils.cpython-312.pyc"),
        ("sdist", "benchmarks/results.csv"),
        ("sdist", ".github/workflows/pytest.yml"),
        ("wheel", "bizdays/sub/x.py"),
        ("wheel", "tests/test_calendar.py"),
    ],
)
def test_check_dist_rejects_forbidden_paths(tmp_path, kind, path):
    _make_dist(tmp_path, **{f"{kind}_extra": [path]})
    problems = check_dist(tmp_path, "2.0.0")
    assert len(problems) == 1
    assert path in problems[0]
    assert main([str(tmp_path), "--version", "2.0.0"]) == 1


def test_check_dist_rejects_wrong_version(tmp_path):
    _make_dist(tmp_path, meta_version="1.0.20")
    problems = check_dist(tmp_path, "2.0.0")
    assert any("1.0.20" in p and ".whl" in p for p in problems)
    assert any("1.0.20" in p and ".tar.gz" in p for p in problems)
    assert check_dist(tmp_path, "2.0.1") != []


@pytest.mark.parametrize(
    "path",
    [
        "bizdays/py.typed",
        "bizdays/data/B3.json",
        "bizdays/data/ANBIMA.json",
        "bizdays/data/Actual.json",
        "bizdays/__init__.py",
    ],
)
def test_check_dist_requires_markers(tmp_path, path):
    wheel_dir = tmp_path / "wheel"
    sdist_dir = tmp_path / "sdist"
    wheel_dir.mkdir()
    sdist_dir.mkdir()
    _make_dist(wheel_dir, wheel_drop=[path])
    assert any(path in p and ".whl" in p for p in check_dist(wheel_dir, "2.0.0"))
    _make_dist(sdist_dir, sdist_drop=[path])
    assert any(path in p and ".tar.gz" in p for p in check_dist(sdist_dir, "2.0.0"))


def test_check_dist_requires_wheel_license(tmp_path):
    _make_dist(tmp_path, wheel_drop=["bizdays-2.0.0.dist-info/licenses/LICENSE.txt"])
    assert check_dist(tmp_path, "2.0.0") != []


@pytest.mark.parametrize(
    "path, ok",
    [
        ("tests/test_x.py", True),
        ("tests/files/x.cal", True),
        ("tests/typing/check.py", True),
        ("tests/legacy/x.py", False),
        ("tests/__pycache__/x.pyc", False),
        ("tests/x.pyc", False),
    ],
)
def test_check_dist_test_rule_matches_build_rule(tmp_path, path, ok):
    _make_dist(tmp_path, sdist_extra=[path])
    assert (check_dist(tmp_path, "2.0.0") == []) is ok


def test_check_dist_requires_one_of_each(tmp_path):
    assert check_dist(tmp_path, "2.0.0") != []
    _make_dist(tmp_path)
    with zipfile.ZipFile(tmp_path / "bizdays-1.0.20-py3-none-any.whl", "w") as zf:
        zf.writestr("bizdays/__init__.py", b"")
    assert check_dist(tmp_path, "2.0.0") != []
