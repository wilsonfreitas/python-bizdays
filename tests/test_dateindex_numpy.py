import importlib.resources
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest

from bizdays.calendarfile import load_calendar_definition
from bizdays.dateindex import DateIndex
from bizdays.utils import DateOutOfRange

_DATA_DIR = Path(str(importlib.resources.files("bizdays") / "data"))

_weekdays: tuple[str, str, str, str, str, str, str] = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

DATES_FROM = np.array(
    [
        "2013-07-12",
        "2013-08-21",
        "2013-01-01",
        "2013-01-01",
        "2014-01-01",
        "2014-10-10",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
        "2013-08-13",
    ],
    dtype="datetime64[D]",
)

DATES_TO = np.array(
    [
        "2014-07-12",
        "2013-08-24",
        "2013-01-31",
        "2014-01-01",
        "2015-01-01",
        "2015-02-11",
        "2013-09-02",
        "2013-10-01",
        "2013-11-01",
        "2013-12-02",
        "2014-01-02",
        "2014-04-01",
        "2014-07-01",
        "2014-10-01",
        "2015-01-02",
        "2015-04-01",
        "2015-07-01",
        "2015-10-01",
        "2016-01-04",
        "2016-04-01",
        "2016-07-01",
        "2016-10-03",
        "2017-01-02",
        "2017-04-03",
        "2017-07-03",
        "2017-10-02",
        "2018-01-02",
        "2018-04-02",
        "2018-07-02",
        "2018-10-01",
        "2019-01-02",
        "2019-04-01",
        "2019-07-01",
        "2019-10-01",
        "2020-01-02",
        "2020-04-01",
        "2020-07-01",
        "2020-10-01",
        "2021-01-04",
        "2021-07-01",
        "2022-01-03",
        "2022-07-01",
        "2023-01-02",
        "2024-01-02",
        "2025-01-02",
    ],
    dtype="datetime64[D]",
)

BDAYS = np.array(
    [
        251,
        2,
        21,
        252,
        252,
        86,
        14,
        35,
        58,
        78,
        99,
        160,
        221,
        287,
        352,
        413,
        474,
        539,
        602,
        663,
        726,
        791,
        853,
        916,
        977,
        1041,
        1102,
        1163,
        1226,
        1290,
        1352,
        1413,
        1475,
        1541,
        1605,
        1667,
        1728,
        1793,
        1856,
        1979,
        2107,
        2231,
        2358,
        2607,
        2860,
    ],
    dtype=int,
)


def load_calendar_from_file(filename: str) -> tuple[npt.NDArray[np.datetime64], list[int]]:
    """
    Load a calendar from a file.
    The file should contain a list of holidays and non-working weekdays.
    The holidays should be in the format YYYY-MM-DD.
    The non-working weekdays should be in the format of the weekday name (e.g. "Monday").
    """
    definition = load_calendar_definition(filename)
    return np.array(definition.holidays, dtype="datetime64[D]"), [
        _weekdays.index(day.title()) for day in definition.weekdays
    ]


HOL, WD = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.json"))
CAL = DateIndex(holidays=HOL, startdate=np.datetime64("2000-01-01"), enddate=np.datetime64("2099-12-31"), weekdays=WD)


def _call_bizdays(dti: DateIndex, date_from: str, date_to: str) -> npt.NDArray[np.int_]:
    """
    Call the bizdays method of the DateIndex class.
    """
    return dti.bizdays(np.array([date_from], dtype="datetime64[D]"), np.array([date_to], dtype="datetime64[D]"))


def test_dateindex_bizdays():
    hol, wd = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.json"))
    cal = DateIndex(
        holidays=hol, startdate=np.datetime64("2000-01-01"), enddate=np.datetime64("2099-12-31"), weekdays=wd
    )
    assert _call_bizdays(cal, "2013-07-12", "2014-07-12") == 251
    assert _call_bizdays(cal, "2013-08-21", "2013-08-24") == 2
    assert _call_bizdays(cal, "2013-01-01", "2013-01-31") == 21
    assert _call_bizdays(cal, "2013-01-01", "2014-01-01") == 252
    assert _call_bizdays(cal, "2014-01-01", "2015-01-01") == 252
    assert _call_bizdays(cal, "2014-10-10", "2015-02-11") == 86
    assert _call_bizdays(cal, "2013-08-13", "2013-09-02") == 14
    assert _call_bizdays(cal, "2013-08-13", "2013-10-01") == 35
    assert _call_bizdays(cal, "2013-08-13", "2013-11-01") == 58
    assert _call_bizdays(cal, "2013-08-13", "2013-12-02") == 78
    assert _call_bizdays(cal, "2013-08-13", "2014-01-02") == 99
    assert _call_bizdays(cal, "2013-08-13", "2014-04-01") == 160
    assert _call_bizdays(cal, "2013-08-13", "2014-07-01") == 221
    assert _call_bizdays(cal, "2013-08-13", "2014-10-01") == 287
    assert _call_bizdays(cal, "2013-08-13", "2015-01-02") == 352
    assert _call_bizdays(cal, "2013-08-13", "2015-04-01") == 413
    assert _call_bizdays(cal, "2013-08-13", "2015-07-01") == 474
    assert _call_bizdays(cal, "2013-08-13", "2015-10-01") == 539
    assert _call_bizdays(cal, "2013-08-13", "2016-01-04") == 602
    assert _call_bizdays(cal, "2013-08-13", "2016-04-01") == 663
    assert _call_bizdays(cal, "2013-08-13", "2016-07-01") == 726
    assert _call_bizdays(cal, "2013-08-13", "2016-10-03") == 791
    assert _call_bizdays(cal, "2013-08-13", "2017-01-02") == 853
    assert _call_bizdays(cal, "2013-08-13", "2017-04-03") == 916
    assert _call_bizdays(cal, "2013-08-13", "2017-07-03") == 977
    assert _call_bizdays(cal, "2013-08-13", "2017-10-02") == 1041
    assert _call_bizdays(cal, "2013-08-13", "2018-01-02") == 1102
    assert _call_bizdays(cal, "2013-08-13", "2018-04-02") == 1163
    assert _call_bizdays(cal, "2013-08-13", "2018-07-02") == 1226
    assert _call_bizdays(cal, "2013-08-13", "2018-10-01") == 1290
    assert _call_bizdays(cal, "2013-08-13", "2019-01-02") == 1352
    assert _call_bizdays(cal, "2013-08-13", "2019-04-01") == 1413
    assert _call_bizdays(cal, "2013-08-13", "2019-07-01") == 1475
    assert _call_bizdays(cal, "2013-08-13", "2019-10-01") == 1541
    assert _call_bizdays(cal, "2013-08-13", "2020-01-02") == 1605
    assert _call_bizdays(cal, "2013-08-13", "2020-04-01") == 1667
    assert _call_bizdays(cal, "2013-08-13", "2020-07-01") == 1728
    assert _call_bizdays(cal, "2013-08-13", "2020-10-01") == 1793
    assert _call_bizdays(cal, "2013-08-13", "2021-01-04") == 1856
    assert _call_bizdays(cal, "2013-08-13", "2021-07-01") == 1979
    assert _call_bizdays(cal, "2013-08-13", "2022-01-03") == 2107
    assert _call_bizdays(cal, "2013-08-13", "2022-07-01") == 2231
    assert _call_bizdays(cal, "2013-08-13", "2023-01-02") == 2358
    assert _call_bizdays(cal, "2013-08-13", "2024-01-02") == 2607
    assert _call_bizdays(cal, "2013-08-13", "2025-01-02") == 2860


def test_dateindex_bizdays_reversed():
    hol, wd = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.json"))
    cal = DateIndex(
        holidays=hol, startdate=np.datetime64("2000-01-01"), enddate=np.datetime64("2099-12-31"), weekdays=wd
    )
    assert _call_bizdays(cal, "2014-07-12", "2013-07-12") == -251
    assert _call_bizdays(cal, "2013-08-24", "2013-08-21") == -2
    assert _call_bizdays(cal, "2013-01-31", "2013-01-01") == -21
    assert _call_bizdays(cal, "2014-01-01", "2013-01-01") == -252
    assert _call_bizdays(cal, "2015-01-01", "2014-01-01") == -252
    assert _call_bizdays(cal, "2015-02-11", "2014-10-10") == -86
    assert _call_bizdays(cal, "2013-09-02", "2013-08-13") == -14
    assert _call_bizdays(cal, "2013-10-01", "2013-08-13") == -35
    assert _call_bizdays(cal, "2013-11-01", "2013-08-13") == -58
    assert _call_bizdays(cal, "2013-12-02", "2013-08-13") == -78
    assert _call_bizdays(cal, "2014-01-02", "2013-08-13") == -99
    assert _call_bizdays(cal, "2014-04-01", "2013-08-13") == -160
    assert _call_bizdays(cal, "2014-07-01", "2013-08-13") == -221
    assert _call_bizdays(cal, "2014-10-01", "2013-08-13") == -287
    assert _call_bizdays(cal, "2015-01-02", "2013-08-13") == -352
    assert _call_bizdays(cal, "2015-04-01", "2013-08-13") == -413
    assert _call_bizdays(cal, "2015-07-01", "2013-08-13") == -474
    assert _call_bizdays(cal, "2015-10-01", "2013-08-13") == -539
    assert _call_bizdays(cal, "2016-01-04", "2013-08-13") == -602
    assert _call_bizdays(cal, "2016-04-01", "2013-08-13") == -663
    assert _call_bizdays(cal, "2016-07-01", "2013-08-13") == -726
    assert _call_bizdays(cal, "2016-10-03", "2013-08-13") == -791
    assert _call_bizdays(cal, "2017-01-02", "2013-08-13") == -853
    assert _call_bizdays(cal, "2017-04-03", "2013-08-13") == -916
    assert _call_bizdays(cal, "2017-07-03", "2013-08-13") == -977
    assert _call_bizdays(cal, "2017-10-02", "2013-08-13") == -1041
    assert _call_bizdays(cal, "2018-01-02", "2013-08-13") == -1102
    assert _call_bizdays(cal, "2018-04-02", "2013-08-13") == -1163
    assert _call_bizdays(cal, "2018-07-02", "2013-08-13") == -1226
    assert _call_bizdays(cal, "2018-10-01", "2013-08-13") == -1290
    assert _call_bizdays(cal, "2019-01-02", "2013-08-13") == -1352
    assert _call_bizdays(cal, "2019-04-01", "2013-08-13") == -1413
    assert _call_bizdays(cal, "2019-07-01", "2013-08-13") == -1475
    assert _call_bizdays(cal, "2019-10-01", "2013-08-13") == -1541
    assert _call_bizdays(cal, "2020-01-02", "2013-08-13") == -1605
    assert _call_bizdays(cal, "2020-04-01", "2013-08-13") == -1667
    assert _call_bizdays(cal, "2020-07-01", "2013-08-13") == -1728
    assert _call_bizdays(cal, "2020-10-01", "2013-08-13") == -1793
    assert _call_bizdays(cal, "2021-01-04", "2013-08-13") == -1856
    assert _call_bizdays(cal, "2021-07-01", "2013-08-13") == -1979
    assert _call_bizdays(cal, "2022-01-03", "2013-08-13") == -2107
    assert _call_bizdays(cal, "2022-07-01", "2013-08-13") == -2231
    assert _call_bizdays(cal, "2023-01-02", "2013-08-13") == -2358
    assert _call_bizdays(cal, "2024-01-02", "2013-08-13") == -2607
    assert _call_bizdays(cal, "2025-01-02", "2013-08-13") == -2860


def test_dateindex_bizdays_vectorized():
    hol, wd = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.json"))
    cal = DateIndex(
        holidays=hol, startdate=np.datetime64("2000-01-01"), enddate=np.datetime64("2099-12-31"), weekdays=wd
    )
    assert np.array_equal(cal.bizdays(DATES_FROM, DATES_TO), BDAYS)


def test_dateindex_bizdays_vectorized_reversed():
    hol, wd = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.json"))
    cal = DateIndex(
        holidays=hol, startdate=np.datetime64("2000-01-01"), enddate=np.datetime64("2099-12-31"), weekdays=wd
    )
    assert np.array_equal(cal.bizdays(DATES_TO, DATES_FROM), -BDAYS)


def test_offset_single_values():
    hol, wd = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.json"))
    cal = DateIndex(
        holidays=hol, startdate=np.datetime64("2000-01-01"), enddate=np.datetime64("2099-12-31"), weekdays=wd
    )

    assert np.array_equal(
        cal.offset(np.array(["2025-05-19"], dtype="datetime64[D]"), np.array([0])),
        np.array(["2025-05-19"], dtype="datetime64[D]"),
    )

    assert np.array_equal(
        cal.offset(np.array(["2025-05-19"], dtype="datetime64[D]"), np.array([1])),
        np.array(["2025-05-20"], dtype="datetime64[D]"),
    )

    assert np.array_equal(
        cal.offset(np.array(["2025-05-20"], dtype="datetime64[D]"), np.array([-1])),
        np.array(["2025-05-19"], dtype="datetime64[D]"),
    )

    # add.bizdays("2012-02-27", -1, "weekends"), as.Date("2012-02-24")
    assert np.array_equal(
        cal.offset(np.array(["2012-02-27"], dtype="datetime64[D]"), np.array([-1])),
        np.array(["2012-02-24"], dtype="datetime64[D]"),
    )


def test_offset_vectorized():
    hol, wd = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.json"))
    cal = DateIndex(
        holidays=hol, startdate=np.datetime64("2000-01-01"), enddate=np.datetime64("2099-12-31"), weekdays=wd
    )

    dates = np.array(
        [
            "2013-01-02",
            "2013-01-02",
            "2013-01-01",
            "2013-01-02",
            "2013-01-02",
            "2013-01-02",
            "2013-01-02",
            "2013-01-01",
            "2013-01-01",
            "2013-01-01",
            "2013-01-01",
            "2013-01-01",
        ],
        dtype="datetime64[D]",
    )
    n = np.array([1, 3, 1, 1, 1, 0, -1, 2, 1, 0, -1, -2], dtype=int)
    expected = np.array(
        [
            "2013-01-03",
            "2013-01-07",
            "2013-01-02",
            "2013-01-03",
            "2013-01-03",
            "2013-01-02",
            "2012-12-31",
            "2013-01-03",
            "2013-01-02",
            "2013-01-01",
            "2012-12-31",
            "2012-12-28",
        ],
        dtype="datetime64[D]",
    )
    assert np.array_equal(cal.offset(dates, n), expected)


def test_adjust_single_values():
    hol, wd = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.json"))
    cal = DateIndex(
        holidays=hol, startdate=np.datetime64("2000-01-01"), enddate=np.datetime64("2099-12-31"), weekdays=wd
    )

    assert np.array_equal(
        cal.adjust(np.array(["2025-05-19"], dtype="datetime64[D]"), 1),
        np.array(["2025-05-19"], dtype="datetime64[D]"),
    )
    assert np.array_equal(
        cal.adjust(np.array(["2025-05-17"], dtype="datetime64[D]"), 1),
        np.array(["2025-05-19"], dtype="datetime64[D]"),
    )
    assert np.array_equal(
        cal.adjust(np.array(["2025-05-18"], dtype="datetime64[D]"), -1),
        np.array(["2025-05-16"], dtype="datetime64[D]"),
    )


def test_adjust_vectorized():
    hol, wd = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.json"))
    cal = DateIndex(
        holidays=hol, startdate=np.datetime64("2000-01-01"), enddate=np.datetime64("2099-12-31"), weekdays=wd
    )

    dates = np.array(["2013-01-01", "2013-01-02"], dtype="datetime64[D]")
    assert np.array_equal(cal.adjust(dates, 1), np.array(["2013-01-02", "2013-01-02"], dtype="datetime64[D]"))
    assert np.array_equal(cal.adjust(dates, -1), np.array(["2012-12-31", "2013-01-02"], dtype="datetime64[D]"))


def test_seq():
    seq = CAL.seq(np.datetime64("2011-01-03"), np.datetime64("2011-01-14"))
    assert seq[0] == np.datetime64("2011-01-03")
    assert seq[-1] == np.datetime64("2011-01-14")
    seq = CAL.seq(np.datetime64("2011-01-03"), np.datetime64("2011-01-03"))
    assert len(seq) == 1
    seq = CAL.seq(np.datetime64("2012-01-01"), np.datetime64("2012-01-02"))
    assert np.array_equal(seq, np.array(["2012-01-02"], dtype="datetime64[D]"))


def test_seq2():
    act = DateIndex(
        holidays=np.array([], dtype="datetime64[D]"),
        startdate=np.datetime64("2000-01-01"),
        enddate=np.datetime64("2099-12-31"),
        weekdays=[],
    )
    dts = np.arange(np.datetime64("2013-01-01"), np.datetime64("2013-01-11"))
    seq = act.seq(np.datetime64("2013-01-01"), np.datetime64("2013-01-10"))
    assert np.array_equal(seq, dts)


def test_dateindex_requires_day_holidays():
    with pytest.raises(ValueError, match=r"datetime64\[D\]"):
        DateIndex(
            holidays=np.array([]),
            startdate=np.datetime64("2000-01-01"),
            enddate=np.datetime64("2099-12-31"),
            weekdays=[],
        )


# --- range edges (WIL-140): never wrap, never clamp ---

EDGE = DateIndex(holidays=HOL, startdate=np.datetime64("2000-01-01"), enddate=np.datetime64("2099-12-25"), weekdays=WD)


def _d(*values: str) -> npt.NDArray[np.datetime64]:
    return np.array(values, dtype="datetime64[D]")


def test_dateindex_offset_never_wraps():
    with pytest.raises(DateOutOfRange):
        EDGE.offset(_d("2099-12-24"), np.array([1]))
    with pytest.raises(DateOutOfRange):
        EDGE.offset(_d("2000-01-03"), np.array([-3]))
    assert EDGE.offset(_d("2099-12-25"), np.array([-1])).tolist() == _d("2099-12-24").tolist()
    assert EDGE.offset(_d("2000-01-01"), np.array([1])).tolist() == _d("2000-01-03").tolist()
    assert EDGE.offset(_d("2099-12-25"), np.array([0])).tolist() == _d("2099-12-25").tolist()
    with pytest.raises(DateOutOfRange) as e:
        EDGE.offset(_d("2024-01-02", "2099-12-24", "2099-12-24"), np.array([1, 1, -1]))
    assert e.value.positions.tolist() == [1]


def test_dateindex_adjust_at_edges():
    with pytest.raises(DateOutOfRange):
        EDGE.adjust(_d("2099-12-25"), 1)
    with pytest.raises(DateOutOfRange):
        EDGE.adjust(_d("2000-01-01"), -1)
    assert EDGE.adjust(_d("2000-01-01"), 1).tolist() == _d("2000-01-03").tolist()
    assert EDGE.adjust(_d("2099-12-25"), -1).tolist() == _d("2099-12-24").tolist()


def test_dateindex_input_out_of_range():
    with pytest.raises(DateOutOfRange) as e:
        EDGE.is_bizday(_d("2024-01-02", "1999-12-31"))
    assert e.value.positions.tolist() == [1]


def test_dateindex_bizdays_non_business_ends_match_r():
    # values from R bizdays 1.0.17 on Brazil/ANBIMA; the old index gave 0 for all three
    assert EDGE.bizdays(_d("2030-12-29", "2022-11-02"), _d("2031-01-01", "2022-11-06")).tolist() == [1, 1]
    assert EDGE.bizdays(_d("2016-09-11"), _d("2016-09-07")).tolist() == [-1]


def _walk(index: DateIndex, p: int, step: int, count: int) -> int | None:
    """Position of the count-th business day strictly after (step=1) or before (step=-1) position p."""
    while count:
        p += step
        if not 0 <= p < len(index._dates):
            return None
        count -= bool(index._is_bizday[p])
    return p


def _ref_offset(index: DateIndex, p: int, n: int) -> int | None:
    return p if n == 0 else _walk(index, p, 1 if n > 0 else -1, abs(n))


def _ref_adjust(index: DateIndex, p: int, step: int) -> int | None:
    return p if index._is_bizday[p] else _walk(index, p, step, 1)


def _check_against(call, expected: list[int | None], dates, *args) -> None:
    bad = [i for i, e in enumerate(expected) if e is None]
    if bad:
        with pytest.raises(DateOutOfRange) as e:
            call(dates, *args)
        assert e.value.positions.tolist() == bad
    good = np.array([e is not None for e in expected])
    result = call(dates[good], *(a[good] if isinstance(a, np.ndarray) else a for a in args))
    assert result.tolist() == EDGE._dates[[e for e in expected if e is not None]].tolist()


def test_dateindex_matches_reference_formulas():
    rng = np.random.default_rng(0)
    span = len(EDGE._dates)
    pos = np.concatenate([rng.integers(0, span, 10_000), np.arange(60), np.arange(span - 60, span)])
    dates = EDGE.startdate + pos
    n = rng.integers(-20, 21, len(pos))
    _check_against(EDGE.offset, [_ref_offset(EDGE, int(p), int(k)) for p, k in zip(pos, n)], dates, n)
    for step in (1, -1):
        _check_against(EDGE.adjust, [_ref_adjust(EDGE, int(p), step) for p in pos], dates, step)
    to_pos = np.minimum(pos + 30, span - 1)
    expected = [max(int(EDGE._is_bizday[p : q + 1].sum()) - 1, 0) for p, q in zip(pos, to_pos)]
    assert EDGE.bizdays(dates, EDGE.startdate + to_pos).tolist() == expected
    assert EDGE.bizdays(EDGE.startdate + to_pos, dates).tolist() == [-x for x in expected]
