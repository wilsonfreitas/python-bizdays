"""Compare v2 with the saved results of bizdays 1.0.19 (WIL-145).

``tests/v1_matrix.json`` is written only by the capture command in ``tests/v1_matrix_cases.py``.
"""

import datetime
import json
from pathlib import Path

import numpy as np
import pandas as pd

import bizdays

from .v1_matrix_cases import CASES, decode, normalize

FIXTURE = json.loads((Path(__file__).parent / "v1_matrix.json").read_text())


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
