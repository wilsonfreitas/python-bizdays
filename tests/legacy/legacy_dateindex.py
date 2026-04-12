import unittest
from pathlib import Path

from bizdays.bizdays import Date, DateIndex, load_holidays, set_option

_DATA_DIR = Path(__file__).resolve().parents[2] / "bizdays" / "data"


class BizdaysTest(unittest.TestCase):
    def setUp(self):
        set_option("mode", "python")


class TestDateIndex(BizdaysTest):
    def test_DateIndex_start_workday_end_workday(self):
        cix = DateIndex([], startdate=Date("2020-04-01").date, enddate=Date("2020-04-07").date, weekdays=(5, 6))
        self.assertTrue(
            all(
                cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
            )
        )

    def test_DateIndex_start_nonworkday_end_workday(self):
        cix = DateIndex([], startdate=Date("2020-03-29").date, enddate=Date("2020-04-03").date, weekdays=(5, 6))
        self.assertTrue(
            all(
                cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
            )
        )

    def test_DateIndex_start_weekend_end_workday(self):
        cix = DateIndex([], startdate=Date("2020-03-28").date, enddate=Date("2020-04-03").date, weekdays=(5, 6))
        self.assertTrue(
            all(
                cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
            )
        )

    def test_DateIndex_start_workday_end_nonworkday(self):
        cix = DateIndex([], startdate=Date("2020-04-01").date, enddate=Date("2020-04-04").date, weekdays=(5, 6))
        self.assertTrue(
            all(
                cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
            )
        )

    def test_DateIndex_start_workday_end_weekend(self):
        cix = DateIndex([], startdate=Date("2020-04-01").date, enddate=Date("2020-04-05").date, weekdays=(5, 6))
        self.assertTrue(
            all(
                cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
            )
        )

    def test_DateIndex_start_nonworkday_end_nonworkday(self):
        cix = DateIndex([], startdate=Date("2020-03-29").date, enddate=Date("2020-04-04").date, weekdays=(5, 6))
        self.assertTrue(
            all(
                cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
            )
        )

    def test_DateIndex_start_weekend_end_weekend(self):
        cix = DateIndex([], startdate=Date("2020-03-28").date, enddate=Date("2020-04-05").date, weekdays=(5, 6))
        self.assertTrue(
            all(
                cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
            )
        )

    def test_DateIndex_following_preceding(self):
        holidays = [Date(d) for d in load_holidays(str(_DATA_DIR / "ANBIMA.txt"))]
        di = DateIndex(holidays, startdate=holidays[0].date, enddate=holidays[-1].date, weekdays=(5, 6))
        self.assertEqual(di.following(Date("2011-01-01").date).isoformat(), "2011-01-03")
        self.assertEqual(di.following(Date("2011-01-03").date).isoformat(), "2011-01-03")
        self.assertEqual(di.preceding(Date("2011-01-09").date).isoformat(), "2011-01-07")
        self.assertEqual(di.preceding(Date("2011-01-07").date).isoformat(), "2011-01-07")

    def test_DateIndex_offset(self):
        holidays = [Date(d) for d in load_holidays(str(_DATA_DIR / "ANBIMA.txt"))]
        di = DateIndex(holidays, startdate=holidays[0].date, enddate=holidays[-1].date, weekdays=(5, 6))
        self.assertEqual(di.offset(Date("2011-01-07").date, 1).isoformat(), "2011-01-10")
        self.assertEqual(di.offset(Date("2011-01-10").date, -1).isoformat(), "2011-01-07")

    def test_DateIndex_seq(self):
        holidays = [Date(d) for d in load_holidays(str(_DATA_DIR / "ANBIMA.txt"))]
        di = DateIndex(holidays, startdate=holidays[0].date, enddate=holidays[-1].date, weekdays=(5, 6))
        seq = di.seq(Date("2011-01-03").date, Date("2011-01-14").date)
        self.assertEqual(seq[0].isoformat(), "2011-01-03")
        self.assertEqual(seq[-1].isoformat(), "2011-01-14")
        seq = di.seq(Date("2011-01-03").date, Date("2011-01-03").date)
        self.assertEqual(len(seq), 1)
