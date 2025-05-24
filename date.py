from datetime import date, datetime

from utils import isstr


class Date:
    def __init__(self, d: str | date | datetime | None, format: str = "%Y-%m-%d"):
        # d = d if d else date.today()
        if isstr(d):
            d = datetime.strptime(d, format).date()  # type: ignore[arg-type]
        elif isinstance(d, datetime):
            d = d.date()
        elif isinstance(d, Date):
            d = d.date
        elif isinstance(d, date):
            pass
        elif d is None:
            pass
        else:
            raise ValueError()
        self.date: date | None = d

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
