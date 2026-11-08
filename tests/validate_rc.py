"""Validate a bizdays release candidate from clean installations (WIL-153).

Usage, from the repo root:

    uv run --no-project python -m tests.validate_rc DIST_DIR --version VERSION \\
        [--source CLEAN_CLONE] [--sums SHA256SUMS] [--no-suite] [--pythons 3.10 ...] \\
        [--work DIR] [--report FILE]

For each Python, artifact (wheel, sdist) and extras it makes a clean venv with uv,
installs the artifact and runs tests/smoke_installed.py outside the source tree.
Suite jobs run the full test suite from ``git archive`` of the clean clone, with
``bizdays/`` removed, against the installed package. Then it compares wheel and
sdist and writes a Markdown report. Standard library only. It never pushes,
uploads or deletes anything outside its work folder.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.check_dist import check_dist

PYTHONS = ("3.10", "3.11", "3.12", "3.13", "3.14")
EXTRAS = ("core", "pmc", "xcal", "work", "all")
SMOKE = Path(__file__).resolve().parent / "smoke_installed.py"


@dataclass(frozen=True)
class Job:
    python: str
    artifact: str  # "wheel" or "sdist"
    extras: str
    suite: bool = False
    requirement: str = ""

    @property
    def name(self) -> str:
        kind = "suite" if self.suite else self.extras
        tail = "-pandas2" if self.requirement == "pandas<3" else ""
        return f"{self.python}-{self.artifact}-{kind}{tail}"


def build_jobs(pythons: Sequence[str], suite: bool = True) -> list[Job]:
    jobs = [Job(p, a, e) for p in pythons for a in ("wheel", "sdist") for e in EXTRAS]
    if suite:
        jobs += [Job(p, a, "dev", suite=True) for p in pythons for a in ("wheel", "sdist")]
        if "3.12" in pythons:
            jobs.append(Job("3.12", "wheel", "dev", suite=True, requirement="pandas<3"))
    return jobs


def sha256sums(dist_dir: Path) -> str:
    """``sha256sum`` format for the wheel and the sdist only, sorted by file name."""
    files = sorted([*Path(dist_dir).glob("*.whl"), *Path(dist_dir).glob("*.tar.gz")], key=lambda p: p.name)
    return "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files)


def _lines(text: str) -> list[str]:
    return sorted(line.strip() for line in text.splitlines() if line.strip())


def check_sums(computed: str, expected: str) -> list[str]:
    """Compare as sorted non-empty lines: the order of the expected file can depend on the locale."""
    have, want = _lines(computed), _lines(expected)
    if have == want:
        return []
    problems = [f"SHA256SUMS: computed but not expected: {line}" for line in have if line not in want]
    problems += [f"SHA256SUMS: expected but not computed: {line}" for line in want if line not in have]
    return problems or [f"SHA256SUMS: line counts differ: computed {have}, expected {want}"]


def compare_pairs(results: Mapping[Job, Mapping[str, Any]]) -> list[str]:
    """For each Python and extras, the wheel and sdist smoke jobs must give the same values and files."""
    pairs: dict[tuple[str, str], dict[str, Mapping[str, Any]]] = {}
    for job, res in results.items():
        if not job.suite:
            pairs.setdefault((job.python, job.extras), {})[job.artifact] = res
    problems = []
    for (py, extras), pair in sorted(pairs.items()):
        if set(pair) != {"wheel", "sdist"}:
            missing = ({"wheel", "sdist"} - set(pair)).pop()
            problems.append(f"{py} {extras}: no {missing} result to compare")
            continue
        w, s = pair["wheel"], pair["sdist"]
        wv, sv = w.get("values", {}), s.get("values", {})
        keys = sorted(k for k in set(wv) | set(sv) if wv.get(k) != sv.get(k))
        if keys:
            problems.append(f"{py} {extras}: wheel and sdist differ in values: {', '.join(keys)}")
        wf, sf = set(w.get("files", [])), set(s.get("files", []))
        if wf != sf:
            diff = [f"wheel only {f}" for f in sorted(wf - sf)] + [f"sdist only {f}" for f in sorted(sf - wf)]
            problems.append(f"{py} {extras}: wheel and sdist differ in files: {', '.join(diff)}")
    return problems


def _cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_report(
    meta: Mapping[str, str],
    sums: str,
    results: Mapping[Job, Mapping[str, Any]],
    problems: Sequence[str],
) -> str:
    passed = bool(results) and all(r.get("ok") for r in results.values()) and not problems
    out = ["# bizdays release-candidate validation", ""]
    out += [f"* {key}: {value}" for key, value in meta.items()]
    out += ["", "## SHA256SUMS", "", "```", sums.rstrip(), "```", "", "## Jobs", ""]
    out += ["| job | ok | python | numpy | pandas | detail |", "|---|---|---|---|---|---|"]
    for job, r in results.items():
        cells = [job.name, "ok" if r.get("ok") else "FAIL", r.get("python", ""), r.get("numpy", ""), r.get("pandas", "")]
        out.append("| " + " | ".join(_cell(c) for c in [*cells, r.get("detail", "")]) + " |")
    out += ["", "## Wheel versus sdist", ""]
    out += [f"* {p}" for p in problems] or ["No differences."]
    out += ["", f"RESULT: {'PASS' if passed else 'FAIL'}", ""]
    return "\n".join(out)


def _clean_env() -> dict[str, str]:
    return {
        k: v
        for k, v in os.environ.items()
        if not (k.startswith("PYTHON") or k.startswith("VIRTUAL_ENV") or (k.startswith("UV_") and k != "UV_CACHE_DIR"))
    }


def _run(cmd: Sequence[str], env: Mapping[str, str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(cmd), cwd=cwd, env=dict(env), capture_output=True, text=True)


def _tail(proc: subprocess.CompletedProcess[str], n: int = 3) -> str:
    lines = [line for line in (proc.stdout + "\n" + proc.stderr).splitlines() if line.strip()]
    return " / ".join(lines[-n:])


def _fresh(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def install_spec(job: Job, artifact: Path) -> str:
    # bizdays has no "all" extra: "all" means the three provider extras
    names = {"core": "", "all": "pmc,xcal,work"}.get(job.extras, job.extras)
    return f"bizdays{f'[{names}]' if names else ''} @ {artifact.resolve().as_uri()}"


def run_job(job: Job, dist: Mapping[str, Path], version: str, source: Path | None, work: Path) -> dict[str, Any]:
    env = _clean_env()
    venv = work / "venvs" / job.name
    if venv.exists():
        shutil.rmtree(venv)
    venv.parent.mkdir(parents=True, exist_ok=True)
    # shortcut: POSIX venv layout only (bin/python), add Scripts/python.exe if this ever runs on Windows
    python = str(venv / "bin" / "python")
    result: dict[str, Any] = {"ok": False, "python": "", "numpy": "", "pandas": "", "detail": ""}

    proc = _run(["uv", "venv", "--no-config", "--managed-python", "--python", job.python, str(venv)], env)
    if proc.returncode:
        result["detail"] = f"uv venv failed: {_tail(proc)}"
        return result
    cmd = ["uv", "pip", "install", "--no-config", "--python", python, install_spec(job, dist[job.artifact])]
    proc = _run(cmd + ([job.requirement] if job.requirement else []), env)
    if proc.returncode:
        result["detail"] = f"install failed: {_tail(proc)}"
        return result

    if not job.suite:
        run_dir = _fresh(work / "run" / job.name)
        shutil.copy(SMOKE, run_dir / SMOKE.name)
        extras_arg = "" if job.extras == "core" else job.extras
        proc = _run([python, "-I", SMOKE.name, "--version", version, "--extras", extras_arg], env, cwd=run_dir)
        try:
            data = json.loads(proc.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            result["detail"] = f"smoke script gave no JSON: {_tail(proc)}"
            return result
        result.update({k: data.get(k, "") for k in ("python", "numpy", "pandas")})
        result.update(values=data.get("values", {}), files=data.get("files", []))
        result["ok"] = proc.returncode == 0 and bool(data.get("ok"))
        result["detail"] = "; ".join(data.get("problems", []))
        return result

    assert source is not None
    src = _fresh(work / "src" / job.name)
    tar = work / "src" / f"{job.name}.tar"
    proc = _run(["git", "-C", str(source), "archive", "--format=tar", "-o", str(tar), "HEAD"], env)
    if proc.returncode:
        result["detail"] = f"git archive failed: {_tail(proc)}"
        return result
    subprocess.run(["tar", "-xf", str(tar), "-C", str(src)], check=True)
    tar.unlink()
    shutil.rmtree(src / "bizdays")  # the suite must import the installed package
    probe = (
        "import json, platform, importlib.metadata as m, bizdays, numpy;"
        "print(json.dumps({'file': bizdays.__file__, 'python': platform.python_version(),"
        "'numpy': numpy.__version__, 'pandas': m.version('pandas')}))"
    )
    proc = _run([python, "-I", "-c", probe], env, cwd=src)
    if proc.returncode:
        result["detail"] = f"import failed: {_tail(proc)}"
        return result
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    result.update({k: data[k] for k in ("python", "numpy", "pandas")})
    file, prefix = os.path.realpath(data["file"]), os.path.realpath(venv)
    if os.path.commonpath([file, prefix]) != prefix:
        result["detail"] = f"leak: bizdays imported from {data['file']}, not from {venv}"
        return result
    proc = _run([python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"], env, cwd=src)
    result["ok"] = proc.returncode == 0
    result["detail"] = _tail(proc, 1)
    return result


def _hatchling(wheel: Path) -> str:
    with zipfile.ZipFile(wheel) as zf:
        for name in zf.namelist():
            if name.endswith(".dist-info/WHEEL"):
                for line in zf.read(name).decode().splitlines():
                    if line.startswith("Generator:"):
                        return line.split(":", 1)[1].strip()
    return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dist_dir", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source", type=Path, help="clean clone at the candidate commit")
    parser.add_argument("--sums", type=Path, help="expected SHA256SUMS file")
    parser.add_argument("--no-suite", action="store_true")
    parser.add_argument("--pythons", nargs="+", default=list(PYTHONS))
    parser.add_argument("--work", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    problems = check_dist(args.dist_dir, args.version)
    if problems:
        print("\n".join(problems))
        return 1
    sums = sha256sums(args.dist_dir)
    if args.sums:
        problems = check_sums(sums, args.sums.read_text())
        if problems:
            print("\n".join(problems))
            return 1
    if not args.no_suite and args.source is None:
        print("--source is needed unless --no-suite")
        return 1
    commit = "-"
    if args.source is not None:
        status = subprocess.run(["git", "-C", str(args.source), "status", "--porcelain"], capture_output=True, text=True)
        if status.returncode or status.stdout.strip():
            print(f"source {args.source} is not a clean git tree:\n{status.stdout}{status.stderr}")
            return 1
        rev = subprocess.run(["git", "-C", str(args.source), "rev-parse", "HEAD"], capture_output=True, text=True)
        if rev.returncode:
            print(f"source {args.source} has no commit: {rev.stderr}")
            return 1
        commit = rev.stdout.strip()

    work = (args.work or Path(tempfile.mkdtemp(prefix="bizdays-rc-"))).resolve()
    work.mkdir(parents=True, exist_ok=True)
    print(f"work folder: {work}", file=sys.stderr)
    dist = {"wheel": next(args.dist_dir.glob("*.whl")), "sdist": next(args.dist_dir.glob("*.tar.gz"))}
    uv = subprocess.run(["uv", "--version"], capture_output=True, text=True).stdout.strip()
    meta = {
        "version": args.version,
        "source commit": commit,
        "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "uv": uv,
        "hatchling": _hatchling(dist["wheel"]),
    }
    results: dict[Job, dict[str, Any]] = {}
    for job in build_jobs(args.pythons, suite=not args.no_suite):
        results[job] = run_job(job, dist, args.version, args.source, work)
        print(f"{job.name}: {'ok' if results[job]['ok'] else 'FAIL'} {results[job]['detail']}", file=sys.stderr)
    problems = compare_pairs(results)
    report = render_report(meta, sums, results, problems)
    (args.report or work / "report.md").write_text(report)
    print(report)
    return 0 if report.rstrip().endswith("RESULT: PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
