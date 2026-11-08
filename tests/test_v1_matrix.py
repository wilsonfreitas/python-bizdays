"""Compare v2 with the saved results of bizdays 1.0.19 (WIL-145).

``tests/v1_matrix.json`` is written only by the capture command in ``tests/v1_matrix_cases.py``.
"""

import datetime
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import bizdays
from bizdays import Calendar

from .v1_matrix_cases import CASES, decode, make_calendar, normalize, run_case

FIXTURE = json.loads((Path(__file__).parent / "v1_matrix.json").read_text())

# The 22 migration-guide slugs of WIL-146 (``.. _migrate-<slug>:`` in docs/source/migration.rst).
MIGRATION_SLUGS = frozenset(
    {
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
    }
)

# Results that v2 changes on purpose: case id -> (design section, migration slug, exact v2 result).
CHANGED: dict[str, tuple[str, str, dict]] = {
    "bizdays-anbima-np": ("§5 NumPy date arrays are accepted", "input-containers", {"value": [252, 230]}),
    "bizdays-anbima-empty": ("§8 empty input", "vector-lengths", {"value": []}),
    "bizdays-anbima-len-2-4": ("§8 lengths 2 and 4 no longer recycle", "vector-lengths", {"error": "ValueError"}),
    "bizdays-anbima-len-3-2": ("§8 ValueError instead of Exception", "vector-lengths", {"error": "ValueError"}),
    "offset-anbima-len-3-2": ("§8 lengths 3 and 2 no longer recycle", "vector-lengths", {"error": "ValueError"}),
    "bizdays-anbima-unpadded": ("§5 full ISO dates only (§3 list)", "strict-date-strings", {"error": "ValueError"}),
    "modified_preceding-anbima-first-day": (
        "§9 the answer is known inside the month",
        "calendar-range",
        {"value": "2000-01-03"},
    ),
    "modified_following-b3-last-day": (
        "§9 the answer is known inside the month",
        "calendar-range",
        {"value": "2026-12-30"},
    ),
    "offset-anbima-past-end": ("§9 result past the end", "calendar-range", {"error": "DateOutOfRange"}),
    "offset-anbima-before-start": ("§9 no wrap-around (§3 list)", "calendar-range", {"error": "DateOutOfRange"}),
    "offset-anbima-float-n": ("§5 counts", "whole-counts", {"error": "ValueError"}),
    "offset-anbima-whole-float-n": ("§5 whole floats are counts", "whole-counts", {"value": "2024-01-04"}),
    "seq-anbima-none-start": ("§7 seq with a missing end", "missing-values", {"error": "ValueError"}),
    "getdate-anbima-composite": ("§10 composite expressions", "getdate-grammar", {"value": "2024-05-09"}),
    "getdate-anbima-before-first-day-year": ("§3 v1 bug with year refs", "getdate-year-ref", {"value": "2023-12-29"}),
    "getdate-anbima-5th-fri": ("§10 date not in the period", "getdate-grammar", {"error": "ValueError"}),
    "getdate-anbima-2099-12": (
        "§9 the period must be inside the range",
        "calendar-range",
        {"error": "DateOutOfRange"},
    ),
    "getbizdays-anbima-2099": ("§10 no partial counts (§3 list)", "getbizdays", {"error": "DateOutOfRange"}),
    "getbizdays-anbima-month-0": ("§10 month 1 to 12 (§3 list)", "getbizdays", {"error": "ValueError"}),
    "getbizdays-anbima-month-13": ("§10 month 1 to 12", "getbizdays", {"error": "ValueError"}),
    "prop-default-name": ("§4 constructor defaults", "constructor", {"value": ""}),
    "ctor-holidays-only": ("§9 a calendar with no business days", "constructor", {"error": "ValueError"}),
    "ctor-start-after-end": ("§9 startdate after enddate", "constructor", {"error": "ValueError"}),
    "ctor-weekday-numbers": ("§9 weekdays are English names", "constructor", {"error": "ValueError"}),
    "load-name-positional": ("§4 Calendar.load is keyword-only", "load-keyword-only", {"error": "TypeError"}),
    "load-unknown": ("§10 load error types", "load-errors", {"error": "ValueError"}),
    "load-missing-file": ("§10 load error types", "load-errors", {"error": "FileNotFoundError"}),
    "load-cal-file": ("§10 .cal files are not supported (D7)", "cal-files", {"error": "ValueError"}),
    "load-json-file": (
        "§10 v1 read a JSON file as an empty calendar",
        "load-errors",
        {"value": [2, ["Saturday", "Sunday"], "2024-01-01", "2024-12-25"]},
    ),
}


def test_fixture_is_current():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))
    assert FIXTURE["bizdays"] == "1.0.19"
    assert FIXTURE["pandas"].startswith("2.")
    assert set(FIXTURE["cases"]) == set(ids)


def test_normalize_keeps_missing_apart():
    assert normalize(np.float64("nan")) is None
    assert normalize(np.float64(0)) == 0
    assert normalize(np.ma.masked) is None
    assert normalize(np.ma.MaskedArray([True, False], mask=[False, True])) == [True, None]
    assert normalize(np.bool_(False)) is False
    assert normalize(np.datetime64("NaT")) is None
    assert normalize(np.array(["2024-01-02"], dtype="datetime64[D]")) == ["2024-01-02"]
    assert normalize(datetime.date(2024, 1, 2)) == "2024-01-02"
    assert normalize(np.float64(2.5)) == 2.5


def test_decode_tags():
    assert decode({"np": ["2024-01-02"]}).dtype == np.dtype("datetime64[D]")
    assert isinstance(decode({"series": ["2024-01-02"]}), pd.Series)
    assert decode({"tuple": ["a"]}) == ("a",)
    path = decode({"calfile": "x"})
    assert path.endswith("matrix.cal")
    assert Path(path).read_text() == "x"
    assert decode({"series": ["2024-12-24T23:30-03:00"]}).dt.tz is not None


def test_normalize_counts_unique_holidays():
    cal = bizdays.Calendar(
        holidays=["2024-01-01", "2024-01-01"],
        weekdays=["Saturday", "Sunday"],
        startdate="2024-01-01",
        enddate="2024-12-31",
    )
    assert normalize(cal)[0] == 1


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_v1_matrix(case):
    actual = run_case(bizdays, case, v2=True)
    if "skip" in actual:
        pytest.skip(actual["skip"])
    actual.pop("type", None)
    v1 = dict(FIXTURE["cases"][case["id"]])
    v1.pop("type", None)
    if case["id"] in CHANGED:
        _, _, v2_expected = CHANGED[case["id"]]
        assert actual == v2_expected
        assert v1 != v2_expected, "v2 gives the 1.0.19 result again: remove the CHANGED entry"
    else:
        assert actual == v1


def test_changed_entries_cite_the_design():
    ids = {c["id"] for c in CASES}
    for case_id, (reason, slug, _) in CHANGED.items():
        assert case_id in ids
        assert re.match(r"^§\d+", reason), reason
        assert slug in MIGRATION_SLUGS, slug


def test_every_public_member_is_covered():
    public = {n for n in dir(Calendar.load(name="ANBIMA")) if not n.startswith("_")}
    assert (public - {"inrange"}) | {"Calendar"} <= {c["method"] for c in CASES}


def test_v1_top_level_names():
    # §4: v1 `date` was datetime.date; in v2 it is the internal submodule bizdays.date.
    assert {n for n in FIXTURE["names"] if hasattr(bizdays, n)} == {"Calendar", "DateOutOfRange", "date"}


@pytest.mark.parametrize(
    ("case_id", "v1_type", "v2_class", "v2_dtype", "ndim"),
    [
        ("bizdays-anbima-year", "int", np.float64, "float64", 0),
        ("bizdays-anbima-vector", "list", np.ndarray, "float64", 1),
        ("isbizday-anbima-weekday", "bool", np.bool_, "bool", 0),
        ("isbizday-anbima-vector", "list", np.ma.MaskedArray, "bool", 1),
        ("following-anbima-bizday", "date", np.datetime64, "datetime64[D]", 0),
        ("seq-anbima-week", "list", np.ndarray, "datetime64[D]", 1),
        ("diff-anbima", "list", np.ndarray, "float64", 1),
        ("getbizdays-anbima-2024", "int", np.float64, "float64", 0),
        ("bizdays-anbima-series", "list", np.ndarray, "float64", 1),
    ],
)
def test_return_types_changed_on_purpose(case_id, v1_type, v2_class, v2_dtype, ndim):
    """§6 NumPy outputs; §3 list: "is True" no longer holds. Checked on raw results, not normalized ones."""
    case = next(c for c in CASES if c["id"] == case_id)
    assert FIXTURE["cases"][case_id]["type"] == v1_type
    r = getattr(make_calendar(bizdays, case["cal"]), case["method"])(*decode(case["v2_args"] or case["args"]))
    assert isinstance(r, v2_class)
    assert r.dtype == np.dtype(v2_dtype)
    assert np.ndim(r) == ndim
    if case_id == "isbizday-anbima-weekday":
        assert not isinstance(r, bool)  # v1 gave a Python bool
