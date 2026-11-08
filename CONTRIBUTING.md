# Contributing to bizdays

Set up the environment with `uv sync --extra dev --extra docs` and run the tests with `uv run pytest -q tests`.
Before you open a pull request, also run `uv run mypy` and `uv run ruff check .`.

## Releasing

This section is for the maintainer. The workflow is `.github/workflows/release.yml`.

### How it works

1. You push a tag `v<version>`, where `<version>` is the exact version in `pyproject.toml` (for example `v2.0.0`).
2. The jobs `tests` and `docs` run the normal test and docs workflows (`pytest.yml`, `sphinx.yml`).
3. The job `build` builds the sdist and the wheel once, checks that the file names match the tag, checks their contents
   and metadata, writes `SHA256SUMS`, and uploads everything as the artifact `release-dist`.
4. The job `testpypi` sends these files to TestPyPI and checks that the TestPyPI SHA-256 values match `SHA256SUMS`.
5. The job `smoke` installs the wheel in a new environment and runs a small calculation.
6. The job `pypi` waits until you approve the `pypi` environment. Then it sends the same files to PyPI and checks the
   SHA-256 values again.

Rehearsal tags (any version that is not `X.Y.Z`, for example `v2.0.0rc1`) stop after the smoke job: the `pypi` job
is skipped. Final tags (`v2.0.0`) must point to a commit on `main`, or the build fails.

Publishing uses trusted publishing: GitHub gives the job a short-lived identity token, and PyPI trusts it for this
repository, workflow and environment. No password or API token is stored. PyPI also gets attestations (signed records
of which workflow built each file).

### One-time setup

1. Create the GitHub environments (only tags `v*` can use them; `pypi` needs your approval):

   ```bash
   gh api -X PUT repos/wilsonfreitas/python-bizdays/environments/testpypi \
     --input - <<<'{"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}'
   gh api -X POST repos/wilsonfreitas/python-bizdays/environments/testpypi/deployment-branch-policies -f name='v*' -f type=tag
   gh api -X PUT repos/wilsonfreitas/python-bizdays/environments/pypi \
     --input - <<<'{"reviewers":[{"type":"User","id":1583922}],"prevent_self_review":false,"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}'
   gh api -X POST repos/wilsonfreitas/python-bizdays/environments/pypi/deployment-branch-policies -f name='v*' -f type=tag
   ```

2. On pypi.org, open project `bizdays` → Manage → Publishing and add a GitHub publisher: owner `wilsonfreitas`,
   repository `python-bizdays`, workflow `release.yml`, environment `pypi`.
3. Do the same on test.pypi.org with environment `testpypi`.

### Rehearsal

1. Create a branch from the commit you want to test: `git switch -c rehearsal/<version>rcN <commit>`.
2. Set `version = "<version>rcN"` in `pyproject.toml`, then run `uv lock`.
3. Run `uv sync --extra dev --extra docs && uv run pytest -q tests`: all tests must pass with the rc version.
4. Commit, then push the branch: `git push -u origin rehearsal/<version>rcN`.
5. Tag and push the tag: `git tag v<version>rcN && git push origin v<version>rcN`.
6. Watch the run: `gh run watch`. The jobs up to `smoke` must succeed; `pypi` shows "skipped".
7. Check TestPyPI: `curl -fsS https://test.pypi.org/pypi/bizdays/<version>rcN/json | jq -r '.urls[].filename'`.

Never merge a rehearsal branch.

### Release

1. Merge the release branch into `main` and switch to it: `git switch main && git pull`.
2. Check the version: `uv version --short` must print `2.0.0`.
3. Tag and push: `git tag -a v2.0.0 -m "bizdays 2.0.0" && git push origin v2.0.0`.
4. When the `build` job ends, read `SHA256SUMS` in its job summary.
5. When `testpypi` and `smoke` pass, open the run page in GitHub Actions and approve the `pypi` deployment.

### After the release

1. The PyPI hashes must equal `SHA256SUMS`:

   ```bash
   curl -fsS https://pypi.org/pypi/bizdays/2.0.0/json | jq -r '.urls[] | "\(.digests.sha256)  \(.filename)"'
   ```

2. The attestation must exist (this prints `200`):

   ```bash
   curl -fsS -o /dev/null -w '%{http_code}' https://pypi.org/integrity/bizdays/2.0.0/bizdays-2.0.0-py3-none-any.whl/provenance
   ```

3. Install in a new environment, outside the repository, and check the version (it prints `2.0.0`):

   ```bash
   cd /tmp && uv venv /tmp/bizdays-check && uv pip install --python /tmp/bizdays-check bizdays==2.0.0
   /tmp/bizdays-check/bin/python -c "import bizdays, importlib.metadata as m; print(m.version('bizdays'))"
   ```

4. Create the GitHub Release from the same files:

   ```bash
   gh run download <run-id> -n release-dist -D /tmp/release-dist
   gh release create v2.0.0 --verify-tag --title "bizdays 2.0.0" --notes-file <notes> /tmp/release-dist/*
   ```

### When something fails

1. Use "Re-run failed jobs", never "Re-run all jobs". "Re-run all jobs" builds again, possibly with a newer hatchling,
   so the files may differ and PyPI would refuse them under the same file name.
2. Uploading an identical file again is accepted, so a re-run after a half-done upload is safe.
3. PyPI never lets you reuse a file name, even after you delete the file.
4. A wrong tag that has not reached PyPI: reject the `pypi` approval, delete the tag with
   `git push --delete origin <tag>`, fix the problem, and tag again. For rehearsals use the next rc number, because
   the TestPyPI files of the old one stay there.

### Yank policy

1. Never delete a release.
2. If a release is broken, yank it on pypi.org (Manage → Options → Yank) and give a reason. `pip install bizdays`
   then skips it, but `bizdays==<version>` still installs it.
3. Fix the problem and release the next patch version (for example `2.0.1`).

### Manual fallback

Use this only if trusted publishing is down. Files sent this way have no attestations. `~/.pypirc` needs a
`[testpypi]` section with a token first.

1. Build from a fresh clone at the tag, never from your working copy (untracked files can end up in the sdist):

   ```bash
   git clone --branch v2.0.0 https://github.com/wilsonfreitas/python-bizdays /tmp/bizdays-release
   cd /tmp/bizdays-release && uv build --no-sources
   uvx twine check --strict dist/*
   (cd dist && sha256sum *.whl *.tar.gz)
   ```

2. Upload to TestPyPI, check it, then upload to PyPI:

   ```bash
   uvx twine upload --repository testpypi dist/*
   uvx twine upload dist/*
   ```
