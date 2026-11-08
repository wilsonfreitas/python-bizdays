"""Cases of the v1-to-v2 matrix (WIL-145): case list, input decoding, result normalizing and the 1.0.19 capture.

This module runs under bizdays 1.0.19 and v2, so it imports only the standard library, numpy and pandas.
Capture (from the repo root; never edit ``tests/v1_matrix.json`` by hand)::

    uv run --isolated --no-project --python 3.12 --with "bizdays==1.0.19" \\
      --with "numpy==2.5.4" --with "pandas==2.3.3" --with "pandas-market-calendars==4.6.1" \\
      python -I tests/v1_matrix_cases.py > tests/v1_matrix.json
"""

import datetime as dt
import json
import os
import sys
import tempfile
import warnings

import numpy as np
import pandas as pd

WE = ["Saturday", "Sunday"]
CALENDARS = {
    "ANBIMA": {"load": "ANBIMA"},
    "B3": {"load": "B3"},
    "Actual": {"load": "Actual"},
    "WE": {"weekdays": WE, "startdate": "2010-01-01", "enddate": "2030-12-31"},
    "DEFAULT": {},
    "PMC_NYSE": {"load": "PMC/NYSE"},
    "WE_NF": {"weekdays": WE, "startdate": "2010-01-01", "enddate": "2030-12-31", "financial": False},
}


def decode(x):
    if isinstance(x, dict):
        (k, v), = x.items()
        if k == "date":
            return dt.date.fromisoformat(v)
        if k == "datetime":
            return dt.datetime.fromisoformat(v)
        if k == "ts":
            return pd.Timestamp(v)
        if k == "np":
            return np.array(v, dtype="datetime64[D]")
        if k == "npint":
            return np.array(v)
        if k == "series":
            return pd.Series(pd.to_datetime(v))
        if k == "strseries":
            return pd.Series(v)  # pandas 3 gives the str dtype here
        if k in ("calfile", "jsonfile"):
            path = os.path.join(tempfile.mkdtemp(), "matrix.cal" if k == "calfile" else "matrix.json")
            with open(path, "w") as f:
                f.write(v if k == "calfile" else json.dumps(v))
            return path
        if k == "tuple":
            return tuple(decode(i) for i in v)
        raise ValueError(k)
    if isinstance(x, list):
        return [decode(i) for i in x]
    return x


def normalize(r):
    """Turn a v1 or v2 result into plain JSON values: ISO strings, numbers, bools, None for missing."""
    if r is None or r is np.ma.masked:
        return None
    if isinstance(r, str):
        return r
    if hasattr(r, "holidays") and hasattr(r, "weekdays"):  # a Calendar
        return [len(set(r.holidays)), list(r.weekdays), r.startdate.isoformat(), r.enddate.isoformat()]
    if isinstance(r, np.ma.MaskedArray):
        return [None if m else normalize(v) for v, m in zip(r.data.tolist(), np.ma.getmaskarray(r))]
    if isinstance(r, (pd.Series, pd.Index, np.ndarray, list, tuple)):
        return [normalize(v) for v in list(r)]
    if isinstance(r, (np.datetime64, pd.Timestamp, dt.date)):
        if pd.isna(r):
            return None
        return pd.Timestamp(r).date().isoformat()
    if isinstance(r, (bool, np.bool_)):
        return bool(r)
    if isinstance(r, (int, float, np.integer, np.floating)):
        if np.isnan(r):
            return None
        return int(r) if float(r).is_integer() else float(r)
    raise TypeError(type(r))


def C(id, cal, method, *args, v2=None, **kwargs):
    return {"id": id, "cal": cal, "method": method, "args": list(args), "kwargs": kwargs, "v2_args": v2}


JSON_CAL = {"name": "TEST", "weekdays": ["Saturday", "Sunday"], "holidays": ["2024-01-01", "2024-12-25"]}


CASES = [
    # bizdays
    C("bizdays-anbima-year", "ANBIMA", "bizdays", "2024-01-01", "2025-01-01"),
    C("bizdays-anbima-reversed", "ANBIMA", "bizdays", "2025-01-01", "2024-01-01"),
    C("bizdays-anbima-same", "ANBIMA", "bizdays", "2024-01-02", "2024-01-02"),
    C("bizdays-anbima-holiday-ends", "ANBIMA", "bizdays", "2024-02-12", "2024-02-13"),
    C("bizdays-anbima-sat-end", "ANBIMA", "bizdays", "2024-01-02", "2024-06-15"),
    C("bizdays-anbima-vector", "ANBIMA", "bizdays", ["2024-01-02", "2024-03-01"], "2024-12-31"),
    C("bizdays-anbima-date", "ANBIMA", "bizdays", {"date": "2024-01-02"}, {"date": "2024-02-01"}),
    C("bizdays-anbima-datetime", "ANBIMA", "bizdays", {"datetime": "2024-01-02T15:00"}, "2024-02-01"),
    C("bizdays-anbima-ts", "ANBIMA", "bizdays", {"ts": "2024-01-02"}, {"ts": "2024-02-01"}),
    C("bizdays-anbima-tz-ts", "ANBIMA", "bizdays", {"ts": "2024-01-02T23:30-03:00"}, "2024-02-01"),
    C("following-anbima-tz-ts", "ANBIMA", "following", {"ts": "2024-12-24T23:30-03:00"}),
    C("isbizday-anbima-tz-series", "ANBIMA", "isbizday",
      {"series": ["2024-12-24T23:30-03:00", "2024-12-25T23:30-03:00"]}),
    C("bizdays-anbima-np", "ANBIMA", "bizdays", {"np": ["2024-01-02", "2024-02-01"]}, "2024-12-31"),
    C("bizdays-anbima-series", "ANBIMA", "bizdays", {"series": ["2024-01-02", "2024-02-01"]}, "2024-12-31"),
    C("bizdays-anbima-str-series", "ANBIMA", "bizdays", {"strseries": ["2024-01-02", None]}, "2024-12-31"),
    C("isbizday-anbima-str-series", "ANBIMA", "isbizday", {"strseries": ["2024-12-24", "2024-12-25"]}),
    C("bizdays-anbima-tuple", "ANBIMA", "bizdays", {"tuple": ["2024-01-02", "2024-02-01"]}, "2024-12-31"),
    C("bizdays-anbima-none", "ANBIMA", "bizdays", None, "2024-12-31"),
    C("bizdays-anbima-none-in-vector", "ANBIMA", "bizdays", ["2024-01-02", None], "2024-12-31"),
    C("bizdays-anbima-empty", "ANBIMA", "bizdays", [], "2024-12-31"),
    C("bizdays-anbima-len-2-4", "ANBIMA", "bizdays", ["2024-01-02", "2024-02-01"],
      ["2024-12-31", "2024-12-30", "2024-12-27", "2024-12-26"]),
    C("bizdays-anbima-len-3-2", "ANBIMA", "bizdays", ["2024-01-02", "2024-02-01", "2024-03-01"],
      ["2024-12-31", "2024-12-30"]),
    C("bizdays-anbima-before-start", "ANBIMA", "bizdays", "1999-12-31", "2024-01-02"),
    C("bizdays-anbima-at-start", "ANBIMA", "bizdays", "2000-01-01", "2000-01-10"),
    C("bizdays-anbima-at-end", "ANBIMA", "bizdays", "2099-12-01", "2099-12-25"),
    C("bizdays-anbima-bad-string", "ANBIMA", "bizdays", "2024-13-01", "2024-12-31"),
    C("bizdays-anbima-unpadded", "ANBIMA", "bizdays", "2024-1-2", "2024-12-31"),
    C("bizdays-anbima-number", "ANBIMA", "bizdays", 5, "2024-12-31"),
    C("bizdays-actual-leap", "Actual", "bizdays", "2024-02-28", "2024-03-01"),
    C("bizdays-b3-2023", "B3", "bizdays", "2023-01-01", "2024-01-01"),
    C("bizdays-we-nf-sat-sun", "WE_NF", "bizdays", "2013-06-22", "2013-06-23"),
    C("bizdays-we-nf-sun-sat", "WE_NF", "bizdays", "2013-06-23", "2013-06-22"),
    C("bizdays-we-nf-sat-same", "WE_NF", "bizdays", "2013-06-22", "2013-06-22"),
    C("bizdays-we-nf-sat-sat", "WE_NF", "bizdays", "2013-06-22", "2013-06-29"),
    C("bizdays-we-nf-mon-tue", "WE_NF", "bizdays", "2013-06-24", "2013-06-25"),
    C("bizdays-we-nf-same-bizday", "WE_NF", "bizdays", "2013-06-24", "2013-06-24"),
    # isbizday
    C("isbizday-anbima-holiday", "ANBIMA", "isbizday", "2024-12-25"),
    C("isbizday-anbima-weekday", "ANBIMA", "isbizday", "2024-12-26"),
    C("isbizday-anbima-weekend", "ANBIMA", "isbizday", "2024-12-28"),
    C("isbizday-anbima-vector", "ANBIMA", "isbizday", ["2024-12-24", "2024-12-25", "2024-12-28"]),
    C("isbizday-anbima-none", "ANBIMA", "isbizday", None),
    C("isbizday-anbima-none-in-vector", "ANBIMA", "isbizday", ["2024-12-24", None]),
    C("isbizday-anbima-out", "ANBIMA", "isbizday", "2100-01-04"),
    C("isbizday-b3-dec24", "B3", "isbizday", "2024-12-24"),
    C("isbizday-actual-number", "Actual", "isbizday", 5),
    C("isbizday-actual-sunday", "Actual", "isbizday", "2024-01-07"),
    # adjustments
    *[C(f"{m}-anbima-{tag}", "ANBIMA", m, d)
      for m in ["following", "preceding", "adjust_next", "adjust_previous", "modified_following",
                "modified_preceding"]
      for tag, d in [("bizday", "2024-01-02"), ("holiday", "2024-12-25"), ("month-end-sat", "2024-08-31"),
                     ("month-start-sun", "2024-09-01"), ("vector", ["2024-12-25", "2024-12-28"]),
                     ("none", None)]],
    C("following-anbima-last-day", "ANBIMA", "following", "2099-12-25"),
    C("preceding-anbima-first-day", "ANBIMA", "preceding", "2000-01-01"),
    C("modified_preceding-anbima-first-day", "ANBIMA", "modified_preceding", "2000-01-01"),
    C("modified_following-b3-last-day", "B3", "modified_following", "2026-12-31"),
    # offset
    C("offset-anbima-n0-holiday", "ANBIMA", "offset", "2013-01-01", 0),
    C("offset-anbima-n1", "ANBIMA", "offset", "2013-01-01", 1),
    C("offset-anbima-n2", "ANBIMA", "offset", "2013-01-01", 2),
    C("offset-anbima-nm1", "ANBIMA", "offset", "2013-01-01", -1),
    C("offset-anbima-nm2", "ANBIMA", "offset", "2013-01-01", -2),
    C("offset-anbima-vector-n", "ANBIMA", "offset", "2024-01-02", [1, 5, 10]),
    C("offset-anbima-vector-both", "ANBIMA", "offset", ["2024-01-02", "2024-02-01"], [1, -1]),
    C("offset-anbima-npint", "ANBIMA", "offset", "2024-01-02", {"npint": [1, 2]}),
    C("offset-anbima-len-3-2", "ANBIMA", "offset", ["2024-01-02", "2024-02-01", "2024-03-01"], [1, 2]),
    C("offset-anbima-past-end", "ANBIMA", "offset", "2099-12-25", 5),
    C("offset-anbima-before-start", "ANBIMA", "offset", "2000-01-03", -3),
    C("offset-anbima-none-date", "ANBIMA", "offset", None, 1),
    C("offset-anbima-float-n", "ANBIMA", "offset", "2024-01-02", 1.5),
    C("offset-anbima-whole-float-n", "ANBIMA", "offset", "2024-01-02", 2.0),
    C("offset-actual-leap", "Actual", "offset", "2024-02-28", 1),
    # seq
    C("seq-anbima-week", "ANBIMA", "seq", "2024-12-23", "2024-12-31"),
    C("seq-anbima-reversed", "ANBIMA", "seq", "2024-12-31", "2024-12-23"),
    C("seq-anbima-same-holiday", "ANBIMA", "seq", "2024-12-25", "2024-12-25"),
    C("seq-anbima-none-start", "ANBIMA", "seq", None, "2000-01-10"),
    C("seq-anbima-out", "ANBIMA", "seq", "2099-12-20", "2100-01-10"),
    # diff
    C("diff-anbima", "ANBIMA", "diff", ["2024-01-02", "2024-02-01", "2024-03-01"]),
    C("diff-anbima-one", "ANBIMA", "diff", ["2024-01-02"]),
    C("diff-anbima-none", "ANBIMA", "diff", ["2024-01-02", None, "2024-03-01"]),
    C("diff-we-nf", "WE_NF", "diff", ["2013-06-22", "2013-06-23", "2013-06-29"]),
    # getdate
    C("getdate-anbima-first-bizday-month", "ANBIMA", "getdate", "first bizday", 2024, 1, v2=["first bizday", "2024-01"]),
    C("getdate-anbima-last-bizday-month", "ANBIMA", "getdate", "last bizday", 2024, 12, v2=["last bizday", "2024-12"]),
    C("getdate-anbima-last-bizday-year", "ANBIMA", "getdate", "last bizday", 2024, v2=["last bizday", 2024]),
    C("getdate-anbima-10th-day", "ANBIMA", "getdate", "10th day", 2024, 2, v2=["10th day", "2024-02"]),
    C("getdate-anbima-3rd-wed", "ANBIMA", "getdate", "third wed", 2024, 5, v2=["third wed", "2024-05"]),
    C("getdate-anbima-last-fri", "ANBIMA", "getdate", "last fri", 2024, 5, v2=["last fri", "2024-05"]),
    C("getdate-anbima-composite", "ANBIMA", "getdate", "1st bizday before 2nd fri", 2024, 5,
      v2=["1st bizday before 2nd fri", "2024-05"]),
    C("getdate-anbima-before-first-day-month", "ANBIMA", "getdate", "first bizday before first day", 2002, 1,
      v2=["first bizday before first day", "2002-01"]),
    C("getdate-anbima-before-first-day-year", "ANBIMA", "getdate", "first bizday before first day", 2024,
      v2=["first bizday before first day", 2024]),
    C("getdate-anbima-5th-fri", "ANBIMA", "getdate", "5th fri", 2024, 2, v2=["5th fri", "2024-02"]),
    C("getdate-anbima-monkey", "ANBIMA", "getdate", "first monkey", 2024, 1, v2=["first monkey", "2024-01"]),
    C("getdate-anbima-vector-years", "ANBIMA", "getdate", "last bizday", [2023, 2024], v2=["last bizday", [2023, 2024]]),
    C("getdate-anbima-2099-12", "ANBIMA", "getdate", "last bizday", 2099, 12, v2=["last bizday", "2099-12"]),
    # getbizdays
    C("getbizdays-anbima-2024", "ANBIMA", "getbizdays", 2024),
    C("getbizdays-anbima-2024-01", "ANBIMA", "getbizdays", 2024, 1),
    C("getbizdays-anbima-2024-02", "ANBIMA", "getbizdays", 2024, 2),
    C("getbizdays-anbima-2024-12", "ANBIMA", "getbizdays", 2024, 12),
    C("getbizdays-actual-2024", "Actual", "getbizdays", 2024),
    C("getbizdays-actual-2024-02", "Actual", "getbizdays", 2024, 2),
    C("getbizdays-actual-vector", "Actual", "getbizdays", [2002, 2001], [1, 2]),
    C("getbizdays-anbima-2099", "ANBIMA", "getbizdays", 2099),
    C("getbizdays-anbima-2099-11", "ANBIMA", "getbizdays", 2099, 11),
    C("getbizdays-anbima-month-0", "ANBIMA", "getbizdays", 2024, 0),
    C("getbizdays-anbima-month-13", "ANBIMA", "getbizdays", 2024, 13),
    C("getbizdays-b3-2023", "B3", "getbizdays", 2023),
    # properties
    C("prop-anbima-startdate", "ANBIMA", "startdate"),
    C("prop-anbima-enddate", "ANBIMA", "enddate"),
    C("prop-anbima-weekdays", "ANBIMA", "weekdays"),
    C("prop-anbima-financial", "ANBIMA", "financial"),
    C("prop-anbima-name", "ANBIMA", "name"),
    C("prop-anbima-n-holidays", "ANBIMA", "holidays"),
    C("prop-we-nf-financial", "WE_NF", "financial"),
    C("prop-default-name", "DEFAULT", "name"),
    # construction and load
    C("ctor-weekdays", None, "Calendar", weekdays=WE, startdate="2024-01-01", enddate="2024-12-31"),
    C("ctor-holidays-weekdays", None, "Calendar", holidays=["2024-01-01", "2024-12-25"], weekdays=WE),
    C("ctor-holidays-only", None, "Calendar", holidays=["2024-01-01"]),
    C("ctor-start-after-end", None, "Calendar", startdate="2024-12-31", enddate="2024-01-01"),
    C("ctor-weekday-numbers", None, "Calendar", weekdays=[5, 6]),
    C("load-name-kw", None, "load", name="ANBIMA"),
    C("load-name-positional", None, "load", "ANBIMA"),
    C("load-unknown", None, "load", name="NOPE"),
    C("load-json-file", None, "load", filename={"jsonfile": JSON_CAL}),
    C("load-cal-file", None, "load", filename={"calfile": "Saturday\nSunday\n2024-01-01\n2024-12-25\n"}),
    C("load-missing-file", None, "load", filename="/nonexistent/x.json"),
    C("prop-pmc-nyse-weekdays", "PMC_NYSE", "weekdays"),  # not the holiday count or range: they follow the PMC version
    C("bizdays-pmc-nyse", "PMC_NYSE", "bizdays", "2024-01-02", "2024-12-31"),
    C("isbizday-pmc-nyse-july4", "PMC_NYSE", "isbizday", "2024-07-04"),
]


def make_calendar(bizdays, key):
    spec = CALENDARS[key]
    if "load" in spec:
        return bizdays.Calendar.load(name=spec["load"])
    return bizdays.Calendar(**spec)


def run_case(bizdays, case, v2=False):
    """Run one case; warnings are ignored (the holidays-without-weekdays warning is pinned elsewhere)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return _run_case(bizdays, case, v2)


def _run_case(bizdays, case, v2):
    if case["cal"] is None:
        attr = bizdays.Calendar if case["method"] == "Calendar" else getattr(bizdays.Calendar, case["method"])
    else:
        try:
            cal = make_calendar(bizdays, case["cal"])
        except ImportError:
            return {"skip": "provider not installed"}
        attr = getattr(cal, case["method"])
    if not callable(attr):
        if case["method"] == "holidays":
            return {"value": len(set(attr))}
        return {"value": normalize(attr) if not isinstance(attr, str) else attr}
    args = case["v2_args"] if v2 and case["v2_args"] is not None else case["args"]
    try:
        r = attr(*decode(args), **{k: decode(v) for k, v in case["kwargs"].items()})
        return {"value": normalize(r), "type": type(r).__name__}
    except Exception as e:  # noqa: BLE001 - the matrix records any failure by its type name
        return {"error": type(e).__name__}


def _jsonable(v):
    if isinstance(v, tuple):
        return list(v)
    return v


if __name__ == "__main__":
    import bizdays  # bizdays 1.0.19, from the throwaway environment

    assert bizdays.__file__ and "site-packages" in bizdays.__file__, bizdays.__file__
    from importlib.metadata import version

    assert version("bizdays") == "1.0.19", version("bizdays")
    out = {
        "bizdays": version("bizdays"),
        "numpy": version("numpy"),
        "pandas": version("pandas"),
        "python": "%d.%d" % sys.version_info[:2],
        "names": sorted(n for n in dir(bizdays) if not n.startswith("_")),
        "cases": {},
    }
    for case in CASES:
        r = run_case(bizdays, case)
        if "value" in r:
            r["value"] = _jsonable(r["value"])
        out["cases"][case["id"]] = r
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
