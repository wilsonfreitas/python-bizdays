from datetime import date, datetime

import numpy as np

from bizdays.utils import isstr


class Date:
    def __init__(self, d: str | date | datetime | np.datetime64 | None, format: str = "%Y-%m-%d"):
        # d = d if d else date.today()
        if isstr(d):
            _d = datetime.strptime(d, format).date()  # type: ignore[arg-type]
        elif isinstance(d, datetime):
            _d = d.date()
        elif isinstance(d, Date):
            _d = d.date
        elif isinstance(d, date):
            _d = d
        elif d is None:
            _d = None
        elif isinstance(d, np.datetime64):
            _d = d.astype("datetime64[D]").astype("O")
        else:
            raise ValueError()
        self.date: date | None = _d

    def format(self, fmts: str = "%Y-%m-%d") -> str:
        if self.date is None:
            raise ValueError("Date is None - cannot format")
        return date.strftime(self.date, fmts)

    def __gt__(self, other: "Date") -> bool:
        if self.date is None or other.date is None:
            raise ValueError("Date is None - cannot format")
        return self.date > other.date

    def __ge__(self, other: "Date") -> bool:
        if self.date is None or other.date is None:
            raise ValueError("Date is None - cannot format")
        return self.date >= other.date

    def __lt__(self, other: "Date") -> bool:
        if self.date is None or other.date is None:
            raise ValueError("Date is None - cannot format")
        return self.date < other.date

    def __le__(self, other: "Date") -> bool:
        if self.date is None or other.date is None:
            raise ValueError("Date is None - cannot format")
        return self.date <= other.date

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Date):
            return self.date == other.date
        raise ValueError("Invalid comparison")

    def __repr__(self) -> str:
        return self.format()

    __str__ = __repr__
