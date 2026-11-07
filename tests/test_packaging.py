import importlib.metadata


def test_installed_version_is_2_0_0():
    assert importlib.metadata.version("bizdays") == "2.0.0"


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
