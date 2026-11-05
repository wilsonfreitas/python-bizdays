"""Internal input conversion for ``Calendar`` (contract sections 5 and 7).

Every converter returns a 1-D NumPy array with the missing values written
into it (NaT for dates, NaN for counts) and a flag that says whether the
input was a vector.
"""

import re
from datetime import date, datetime
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd

DateArray = npt.NDArray[np.datetime64]
FloatArray = npt.NDArray[np.float64]
BoolArray = npt.NDArray[np.bool_]

_DATE_STRING = r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
_DATE_STRING_RE = re.compile(_DATE_STRING)
_COARSE_UNITS = ("Y", "M", "W", "generic")


def _not_1d(name: str, ndim: int) -> ValueError:
    return ValueError(f"{name} must be 1-D, got {ndim}-D input")


def to_1d(x: object, name: str) -> tuple[npt.NDArray[Any], BoolArray, bool]:
    """Return ``(values, missing, is_vector)`` for any accepted input."""
    mask: object = False
    if isinstance(x, pd.DataFrame):
        raise ValueError(f"{name} must be 1-D, got a DataFrame")
    if isinstance(x, (pd.Series, pd.Index)):
        px: pd.Series | pd.Index = x
        if isinstance(px.dtype, pd.DatetimeTZDtype):
            # wall-clock date, as pandas .dt.date
            px = px.dt.tz_localize(None) if isinstance(px, pd.Series) else px.tz_localize(None)
        values = px.to_numpy() if isinstance(px.dtype, np.dtype) else px.to_numpy(dtype=object)
        is_vector = True
    elif isinstance(x, (list, tuple)):
        values = np.asarray(x, dtype=object)
        if values.ndim != 1:
            raise _not_1d(name, values.ndim)
        is_vector = True
    elif isinstance(x, np.ndarray):
        if x.ndim >= 2:
            raise _not_1d(name, x.ndim)
        is_vector = x.ndim == 1
        mask = np.ma.getmaskarray(x).reshape(-1)
        values = np.ma.getdata(x).reshape(-1)
    elif isinstance(x, (str, bytes)) or not hasattr(x, "__iter__"):
        values = np.empty(1, dtype=object)
        values[0] = x
        is_vector = False
    else:
        raise ValueError(
            f"{name}: {type(x).__name__} is not a supported sequence; "
            "use a list, tuple, NumPy array or pandas Series/Index"
        )
    missing = np.asarray(mask | pd.isna(values), dtype=np.bool_)
    if values.dtype == object:
        missing |= np.fromiter((v is np.ma.masked for v in values), dtype=np.bool_, count=len(values))
    return values, missing, is_vector


def _days_from_datetime64(values: npt.NDArray[np.datetime64], name: str) -> DateArray:
    unit = np.datetime_data(values.dtype)[0]
    if unit in _COARSE_UNITS:
        raise ValueError(f"{name}: numpy.datetime64 with unit {unit!r} is not a date; use unit 'D' or finer")
    return values.astype("datetime64[D]")


def _days_from_strings(values: npt.NDArray[Any], name: str) -> DateArray:
    strings = values.astype(str)
    ok = pd.Series(strings, dtype=object).str.fullmatch(_DATE_STRING).to_numpy(dtype=bool)
    if not ok.all():
        raise ValueError(f"{name}: invalid date string {strings[~ok][0]!r}; expected YYYY-MM-DD")
    try:
        # the date as written: drop any time and offset
        return strings.astype("U10").astype("datetime64[D]")
    except ValueError:
        for s in strings:
            try:
                np.datetime64(s[:10], "D")
            except ValueError:
                raise ValueError(f"{name}: invalid date string {s!r}; expected YYYY-MM-DD") from None
        raise


def _is_number(value: object) -> bool:
    return isinstance(value, (bool, int, float, np.number, np.bool_))


def date_scalar(value: object, name: str) -> np.datetime64:
    """Convert one non-missing value to ``datetime64[D]``."""
    if _is_number(value):
        raise ValueError(f"{name}: numbers are not dates (got {value!r})")
    if isinstance(value, str):
        return _days_from_strings(np.array([value]), name)[0]
    if isinstance(value, datetime):
        return np.datetime64(value.date(), "D")
    if isinstance(value, date):
        return np.datetime64(value, "D")
    if isinstance(value, np.datetime64):
        return _days_from_datetime64(np.array([value]), name)[0]
    raise ValueError(f"{name}: {type(value).__name__} is not a date")


def to_dates(x: object, name: str) -> tuple[DateArray, bool]:
    """Convert a date argument to 1-D ``datetime64[D]``, NaT where missing."""
    values, missing, is_vector = to_1d(x, name)
    out = np.full(values.shape, np.datetime64("NaT"), dtype="datetime64[D]")
    valid = ~missing
    v = values[valid]
    if len(v) == 0:
        return out, is_vector
    kind = values.dtype.kind
    if kind == "M":
        out[valid] = _days_from_datetime64(v, name)
    elif kind in "biufc":
        raise ValueError(f"{name}: numbers are not dates (got {v[0]!r})")
    elif kind == "U" or (kind == "O" and pd.api.types.infer_dtype(v, skipna=True) == "string"):
        out[valid] = _days_from_strings(v, name)
    elif kind == "O":
        out[valid] = np.array([date_scalar(e, name) for e in v], dtype="datetime64[D]")
    else:
        raise ValueError(f"{name}: {values.dtype} values are not dates")
    return out, is_vector


def _count_error(name: str, value: object) -> ValueError:
    return ValueError(f"{name} must be whole numbers or missing (got {value!r})")


def to_counts(x: object, name: str) -> tuple[FloatArray, bool]:
    """Convert a count argument to 1-D ``float64`` with whole values, NaN where missing."""
    values, missing, is_vector = to_1d(x, name)
    out = np.full(values.shape, np.nan)
    valid = ~missing
    v = values[valid]
    if len(v) == 0:
        return out, is_vector
    kind = values.dtype.kind
    if kind == "O":
        for e in v:
            if isinstance(e, (bool, np.bool_)) or not isinstance(e, (int, float, np.integer, np.floating)):
                raise _count_error(name, e)
        v = v.astype(np.float64)
    elif kind not in "iuf":
        raise _count_error(name, v[0])
    counts = v.astype(np.float64)
    bad = ~np.isfinite(counts) | (counts != np.floor(counts))
    if bad.any():
        raise _count_error(name, v[bad][0])
    out[valid] = counts
    return out, is_vector
