from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Literal, TypeAlias

import numpy as np
import numpy.typing as npt

from bizdays.convert import date_scalar, to_1d

TargetKind: TypeAlias = Literal["day", "bizday", "weekday"]
RefKind: TypeAlias = Literal["year", "month", "date"]

_YEAR_RE = re.compile(r"^\d{4}$")
_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")

_ORDINALS = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
    "next": 1,
    "last": -1,
}

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_WEEKDAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True)
class GetDateTarget:
    kind: TargetKind
    weekday: int | None = None


@dataclass(frozen=True)
class SimpleGetDateExpression:
    kind: Literal["simple"]
    count: int
    target: GetDateTarget
    text: str = field(default="", compare=False)


@dataclass(frozen=True)
class CompositeGetDateExpression:
    kind: Literal["composite"]
    count: int
    target: GetDateTarget
    operator: Literal["before", "after"]
    anchor_count: int
    anchor_target: GetDateTarget
    text: str = field(default="", compare=False)


@dataclass(frozen=True)
class RelativeGetDateExpression:
    kind: Literal["relative"]
    operator: Literal["previous"]
    weekday: int
    text: str = field(default="", compare=False)


GetDateExpression: TypeAlias = (
    SimpleGetDateExpression
    | CompositeGetDateExpression
    | RelativeGetDateExpression
)


@dataclass(frozen=True)
class NormalizedRef:
    kind: RefKind
    year: int | None = None
    month: int | None = None
    date: np.datetime64 | None = None

    def __str__(self) -> str:
        if self.kind == "date":
            return str(self.date)
        if self.kind == "month":
            return f"{self.year:04d}-{self.month:02d}"
        return str(self.year)


def _parse_ordinal(token: str, *, relative_offset: bool = False) -> int:
    token = token.lower()
    if token in _ORDINALS:
        value = _ORDINALS[token]
        if relative_offset and value < 0:
            return 1
        return value
    match = re.fullmatch(r"([1-9]\d*|0)(st|nd|rd|th)", token)
    if match is None:
        raise ValueError(f"Invalid ordinal in getdate expression: {token}")
    n = int(match.group(1))
    if n == 0:
        raise ValueError(f"Invalid ordinal in getdate expression: {token} (ordinals start at 1)")
    suffix = "th" if n % 100 in (11, 12, 13) else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    if match.group(2) != suffix:
        raise ValueError(f"Invalid ordinal in getdate expression: {token} (use {n}{suffix})")
    return n


def _parse_target(token: str) -> GetDateTarget:
    token = token.lower()
    if token == "day":
        return GetDateTarget("day")
    if token == "bizday":
        return GetDateTarget("bizday")
    for names in (_WEEKDAYS, _WEEKDAY_NAMES):
        if token in names:
            return GetDateTarget("weekday", weekday=names.index(token))
    raise ValueError(f"Invalid day token in getdate expression: {token}")


def parse_getdate_expression(expr: str) -> GetDateExpression:
    return replace(_parse_expression(expr), text=expr)


def _parse_expression(expr: str) -> GetDateExpression:
    tokens = expr.lower().split()
    if len(tokens) == 2 and tokens[0] == "previous":
        target = _parse_target(tokens[1])
        if target.weekday is None:
            raise ValueError("previous expressions require a weekday target")
        return RelativeGetDateExpression("relative", "previous", target.weekday)
    if len(tokens) == 2:
        return SimpleGetDateExpression(
            "simple",
            _parse_ordinal(tokens[0]),
            _parse_target(tokens[1]),
        )
    if len(tokens) == 5:
        operator = tokens[2]
        if operator not in {"before", "after"}:
            raise ValueError(
                f"Invalid operator in getdate expression: {operator}"
            )
        relative_operator: Literal["before", "after"] = (
            "before" if operator == "before" else "after"
        )
        return CompositeGetDateExpression(
            "composite",
            _parse_ordinal(tokens[0], relative_offset=True),
            _parse_target(tokens[1]),
            relative_operator,
            _parse_ordinal(tokens[3]),
            _parse_target(tokens[4]),
        )
    raise ValueError(f"Invalid getdate expression: {expr}")


def normalize_ref(ref: object) -> NormalizedRef:
    if isinstance(ref, bool):
        raise ValueError(f"Invalid getdate ref: {ref!r}")
    # years beyond 2**53 overflow the int64 datetime math, as for getbizdays counts
    if isinstance(ref, (int, np.integer)) and abs(int(ref)) <= 2**53:
        return NormalizedRef("year", year=int(ref))
    if isinstance(ref, (float, np.floating)):
        if np.isfinite(ref) and float(ref).is_integer() and abs(ref) <= 2**53:
            return NormalizedRef("year", year=int(ref))
        raise ValueError(f"Invalid getdate ref: {ref!r}")
    if isinstance(ref, str):
        month_match = _MONTH_RE.fullmatch(ref)
        if month_match is not None:
            year = int(month_match.group(1))
            month = int(month_match.group(2))
            if not 1 <= month <= 12:
                raise ValueError(f"Invalid getdate ref: {ref!r}")
            return NormalizedRef("month", year=year, month=month)
        if _YEAR_RE.fullmatch(ref):
            return NormalizedRef("year", year=int(ref))
        return NormalizedRef("date", date=_date_ref(ref))
    if isinstance(ref, (datetime, date)):
        return NormalizedRef("date", date=_date_ref(ref))
    if isinstance(ref, np.datetime64):
        if np.isnat(ref):
            raise ValueError("Invalid getdate ref: NaT")
        unit = np.datetime_data(ref.dtype)[0]
        if unit == "Y":
            return NormalizedRef("year", year=int(ref.astype(int)) + 1970)
        if unit == "M":
            months = int(ref.astype(int))
            return NormalizedRef("month", year=months // 12 + 1970, month=months % 12 + 1)
        return NormalizedRef("date", date=_date_ref(ref))
    raise ValueError(f"Invalid getdate ref: {ref!r}")


def _date_ref(ref: object) -> np.datetime64:
    try:
        return date_scalar(ref, "ref")
    except ValueError:
        raise ValueError(f"Invalid getdate ref: {ref!r}") from None


def to_exprs(x: object) -> tuple[npt.NDArray[np.object_], bool]:
    """Parse getdate expressions; ``None`` where missing."""
    values, missing, is_vector = to_1d(x, "expr")
    out = np.full(values.shape, None, dtype=object)
    parsed: dict[str, GetDateExpression] = {}
    for i in np.flatnonzero(~missing):
        value = values[i]
        if not isinstance(value, str):
            raise ValueError("getdate expressions must be strings or missing")
        if value not in parsed:
            parsed[value] = parse_getdate_expression(value)
        out[i] = parsed[value]
    return out, is_vector


def to_refs(x: object) -> tuple[npt.NDArray[np.object_], bool]:
    """Normalize getdate refs; ``None`` where missing."""
    values, missing, is_vector = to_1d(x, "ref")
    out = np.full(values.shape, None, dtype=object)
    for i in np.flatnonzero(~missing):
        out[i] = normalize_ref(values[i])
    return out, is_vector
