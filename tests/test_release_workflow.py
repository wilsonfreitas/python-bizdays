"""Rules for .github/workflows/release.yml (WIL-152) and the workflows it calls."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

pytestmark = pytest.mark.skipif(not WORKFLOWS.is_dir(), reason="no .github in this tree (installed artifact run)")

yaml = pytest.importorskip("yaml")


def load(name):
    return yaml.safe_load((WORKFLOWS / name).read_text())


def on(wf):
    # PyYAML reads the key `on` as True
    return wf.get("on", wf.get(True))


def jobs():
    return load("release.yml")["jobs"]


def steps(job):
    return jobs()[job]["steps"]


def uses(step, action):
    return step.get("uses", "").startswith(action + "@")


def test_release_runs_only_on_version_tags():
    assert on(load("release.yml")) == {"push": {"tags": ["v*"]}}


def test_default_permissions_read_only():
    assert load("release.yml")["permissions"] == {"contents": "read"}


def test_only_publish_jobs_get_id_token():
    j = jobs()
    assert {n for n, job in j.items() if "id-token" in (job.get("permissions") or {})} == {"testpypi", "pypi"}
    for name in ("testpypi", "pypi"):
        assert j[name]["permissions"] == {"id-token": "write"}
    assert j["smoke"]["permissions"] == {}


def test_gates_before_build():
    j = jobs()
    assert j["tests"]["uses"] == "./.github/workflows/pytest.yml"
    assert j["docs"]["uses"] == "./.github/workflows/sphinx.yml"
    assert j["build"]["needs"] == ["tests", "docs"]


def test_build_once():
    builds = [
        (name, s) for name, job in jobs().items() for s in job.get("steps", []) if "uv build" in s.get("run", "")
    ]
    assert len(builds) == 1
    name, step = builds[0]
    assert name == "build"
    assert step["run"] == "uv build --no-sources"
    upload = [s for s in steps("build") if uses(s, "actions/upload-artifact")]
    assert len(upload) == 1
    assert upload[0]["with"]["name"] == "release-dist"
    assert upload[0]["with"]["if-no-files-found"] == "error"
    checkout = [s for s in steps("build") if uses(s, "actions/checkout")]
    assert len(checkout) == 1
    assert checkout[0]["with"]["persist-credentials"] is False
    assert checkout[0]["with"]["fetch-depth"] == 0


@pytest.mark.parametrize("job", ["testpypi", "pypi"])
def test_publish_jobs_only_download_the_build(job):
    s = steps(job)
    assert not any(uses(x, "actions/checkout") or uses(x, "astral-sh/setup-uv") for x in s)
    assert uses(s[0], "actions/download-artifact")
    assert s[0]["with"]["name"] == "release-dist"
    publish = [i for i, x in enumerate(s) if uses(x, "pypa/gh-action-pypi-publish")]
    assert len(publish) == 1
    after = s[publish[0] + 1 :]
    assert any("diff" in x.get("run", "") and "SHA256SUMS" in x.get("run", "") for x in after)


def publish_step(job):
    return next(s for s in steps(job) if uses(s, "pypa/gh-action-pypi-publish"))


def test_publish_targets():
    j = jobs()
    assert publish_step("testpypi")["with"]["repository-url"] == "https://test.pypi.org/legacy/"
    assert j["testpypi"]["environment"]["name"] == "testpypi"
    assert "repository-url" not in (publish_step("pypi").get("with") or {})
    assert j["pypi"]["environment"]["name"] == "pypi"


def test_pypi_waits_for_testpypi_and_approval():
    j = jobs()
    assert j["smoke"]["needs"] == "testpypi"
    assert set(j["pypi"]["needs"]) == {"build", "smoke"}
    assert j["pypi"]["if"] == "needs.build.outputs.final == 'true'"
    assert j["build"]["outputs"]["final"] == "${{ steps.tag.outputs.final }}"


def test_actions_pinned_by_sha():
    for job in jobs().values():
        for s in job.get("steps", []):
            u = s.get("uses")
            if u is None or u.startswith("./"):
                continue
            assert re.match(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$", u), u
            if uses(s, "astral-sh/setup-uv"):
                assert s["with"]["enable-cache"] is False


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
@pytest.mark.parametrize(
    "tag, files, final",
    [
        ("v2.0.0", "2.0.0", "true"),
        ("v2.0.0rc1", "2.0.0rc1", "false"),
        ("v2.0.1", "2.0.0", None),
        ("v2.0.0", "2.0.0rc1", None),
    ],
)
def test_tag_check_step(tmp_path, tag, files, final):
    step = next(s for s in steps("build") if s.get("id") == "tag")
    dist = tmp_path / "dist"
    dist.mkdir()
    for name in (f"bizdays-{files}-py3-none-any.whl", f"bizdays-{files}.tar.gz", ".gitignore"):
        (dist / name).touch()
    out = tmp_path / "out"
    out.touch()
    r = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        env={**os.environ, "TAG": tag, "GITHUB_OUTPUT": str(out)},
    )
    if final is None:
        assert r.returncode != 0
    else:
        assert r.returncode == 0
        assert f"final={final}" in out.read_text()


def test_master_check_only_for_final():
    step = next(s for s in steps("build") if s.get("name") == "Final releases must be on master")
    assert step["if"] == "steps.tag.outputs.final == 'true'"
    assert step["run"] == "git merge-base --is-ancestor HEAD origin/master"


@pytest.mark.parametrize("name", ["pytest.yml", "sphinx.yml"])
def test_called_workflows_accept_workflow_call(name):
    assert "workflow_call" in on(load(name))


def test_build_checks_artifact_contents():
    s = steps("build")
    run = 'uv run --no-project python tests/check_dist.py dist --version "${TAG#v}"'
    check = [i for i, x in enumerate(s) if x.get("run") == run]
    assert len(check) == 1
    assert s[check[0]]["env"]["TAG"] == "${{ github.ref_name }}"
    tag = next(i for i, x in enumerate(s) if x.get("id") == "tag")
    upload = next(i for i, x in enumerate(s) if uses(x, "actions/upload-artifact"))
    assert tag < check[0] < upload


LEVEL = {"none": 0, "read": 1, "write": 2}


@pytest.mark.parametrize("caller, called", [("tests", "pytest.yml"), ("docs", "sphinx.yml")])
def test_called_workflow_permissions_fit_the_caller(caller, called):
    wf = load("release.yml")
    grant = wf["jobs"][caller].get("permissions", wf["permissions"])
    target = load(called)
    blocks = [target.get("permissions")] + [job.get("permissions") for job in target["jobs"].values()]
    for block in (b for b in blocks if b is not None):
        assert isinstance(block, dict), block
        assert "id-token" not in block
        for key, level in block.items():
            assert LEVEL[level] <= LEVEL[grant.get(key, "none")], (key, level)
    assert wf["jobs"]["tests"].get("permissions") is None
    assert wf["jobs"]["docs"]["permissions"] == {"contents": "write"}


def test_sphinx_deploy_is_master_only():
    deploys = [
        s
        for job in load("sphinx.yml")["jobs"].values()
        for s in job.get("steps", [])
        if s.get("uses", "").startswith("peaceiris/actions-gh-pages@")
    ]
    assert deploys
    for s in deploys:
        assert "github.event_name == 'push'" in s["if"]
        assert "github.ref == 'refs/heads/master'" in s["if"]
