import importlib.metadata

from packaging.requirements import Requirement


def test_requires_python():
    assert importlib.metadata.metadata("bizdays")["Requires-Python"] == ">=3.10"


def test_runtime_dependencies():
    """The core job in pytest.yml installs these floors (numpy==1.24.0, pandas==2.0.0); update it when they change."""
    requires = importlib.metadata.requires("bizdays") or []
    runtime = {str(Requirement(r)) for r in requires if Requirement(r).marker is None}
    assert runtime == {"numpy>=1.24", "pandas>=2"}
