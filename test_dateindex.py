import unittest

from bizdays import Date, DateIndex, load_holidays, set_option


class BizdaysTest(unittest.TestCase):
    def setUp(self):
        set_option("mode", "python")


class TestDateIndex(BizdaysTest):
    def test_DateIndex_start_workday_end_workday(self):
        "it should instanciate the calendar starting and ending on workingdays"
        cix = DateIndex([], startdate=Date("2020-04-01").date, enddate=Date("2020-04-07").date, weekdays=(5, 6))
        assert all(
            cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
        )

    def test_DateIndex_start_nonworkday_end_workday(self):
        """
        it should instanciate the calendar starting on nonworkday
        and ending on workday
        """
        cix = DateIndex([], startdate=Date("2020-03-29").date, enddate=Date("2020-04-03").date, weekdays=(5, 6))
        assert all(
            cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
        )

    def test_DateIndex_start_weekend_end_workday(self):
        """
        it should instanciate the calendar starting on weekend and
        ending on workday
        """
        cix = DateIndex([], startdate=Date("2020-03-28").date, enddate=Date("2020-04-03").date, weekdays=(5, 6))
        assert all(
            cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
        )

    def test_DateIndex_start_workday_end_nonworkday(self):
        """
        it should instanciate the calendar starting on workday and
        ending on nonworkday
        """
        cix = DateIndex([], startdate=Date("2020-04-01").date, enddate=Date("2020-04-04").date, weekdays=(5, 6))
        assert all(
            cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
        )

    def test_DateIndex_start_workday_end_weekend(self):
        """
        it should instanciate the calendar starting on workday and
        ending on weekend
        """
        cix = DateIndex([], startdate=Date("2020-04-01").date, enddate=Date("2020-04-05").date, weekdays=(5, 6))
        assert all(
            cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
        )

    def test_DateIndex_start_nonworkday_end_nonworkday(self):
        """it should instanciate the calendar starting on nonworkday and
        ending on nonworkday"""
        cix = DateIndex([], startdate=Date("2020-03-29").date, enddate=Date("2020-04-04").date, weekdays=(5, 6))
        assert all(
            cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
        )

    def test_DateIndex_start_weekend_end_weekend(self):
        """it should instanciate the calendar starting on nonworkday and
        ending on nonworkday"""
        cix = DateIndex([], startdate=Date("2020-03-28").date, enddate=Date("2020-04-05").date, weekdays=(5, 6))
        assert all(
            cix._index[dt].workday == cix._index[dt].revworkday for dt in cix._index if not cix._index[dt].isholiday
        )

    def test_DateIndex_following_preceding(self):
        "it should test DateIndex"
        holidays = [Date(d) for d in load_holidays("ANBIMA.txt")]
        di = DateIndex(holidays, startdate=holidays[0].date, enddate=holidays[-1].date, weekdays=(5, 6))
        self.assertEqual(di.following(Date("2011-01-01").date).isoformat(), "2011-01-03")
        self.assertEqual(di.following(Date("2011-01-03").date).isoformat(), "2011-01-03")
        self.assertEqual(di.preceding(Date("2011-01-09").date).isoformat(), "2011-01-07")
        self.assertEqual(di.preceding(Date("2011-01-07").date).isoformat(), "2011-01-07")

    def test_DateIndex_offset(self):
        "it should test DateIndex"
        holidays = [Date(d) for d in load_holidays("ANBIMA.txt")]
        di = DateIndex(holidays, startdate=holidays[0].date, enddate=holidays[-1].date, weekdays=(5, 6))
        self.assertEqual(di.offset(Date("2011-01-07").date, 1).isoformat(), "2011-01-10")
        self.assertEqual(di.offset(Date("2011-01-10").date, -1).isoformat(), "2011-01-07")

    def test_DateIndex_seq(self):
        "it should test DateIndex"
        holidays = [Date(d) for d in load_holidays("ANBIMA.txt")]
        di = DateIndex(holidays, startdate=holidays[0].date, enddate=holidays[-1].date, weekdays=(5, 6))
        seq = di.seq(Date("2011-01-03").date, Date("2011-01-14").date)
        self.assertEqual(seq[0].isoformat(), "2011-01-03")
        self.assertEqual(seq[-1].isoformat(), "2011-01-14")
        seq = di.seq(Date("2011-01-03").date, Date("2011-01-03").date)
        self.assertEqual(len(seq), 1)

    def test_DateIndex_getdate(self):
        holidays = [Date(d) for d in load_holidays("ANBIMA.txt")]
        di = DateIndex(holidays, startdate=holidays[0].date, enddate=holidays[-1].date, weekdays=(5, 6))
        self.assertEqual(di.getdate("15th day", 2002, 1).isoformat(), "2002-01-15")
        self.assertEqual(di.getdate("first day before 15th day", 2002, 1).isoformat(), "2002-01-14")
        self.assertEqual(di.getdate("second day after 15th day", 2002, 1).isoformat(), "2002-01-17")
        self.assertEqual(
            di.getdate("second bizday before 15th day", 2002, 1).isoformat(),
            "2002-01-11",
        )
        self.assertEqual(
            di.getdate("second bizday after 15th day", 2002, 1).isoformat(),
            "2002-01-17",
        )
        self.assertEqual(di.getdate("first bizday", 2002, 1).isoformat(), "2002-01-02")
        self.assertEqual(di.getdate("second bizday", 2002, 1).isoformat(), "2002-01-03")
        self.assertEqual(di.getdate("third bizday", 2002, 1).isoformat(), "2002-01-04")
        self.assertEqual(
            di.getdate("second bizday before 10th bizday", 2002, 1).isoformat(),
            "2002-01-11",
        )
        # zero is before, -1 is before and 1 is after
        self.assertEqual(di.getdate("first tue before first day", 2002, 1).isoformat(), "2001-12-25")
        self.assertEqual(di.getdate("first tue after first day", 2002, 1).isoformat(), "2002-01-08")
        # zero is before, -1 is before and 1 is after
        self.assertEqual(di.getdate("first tue before second day", 2002, 1).isoformat(), "2002-01-01")
        self.assertEqual(di.getdate("first tue after second day", 2002, 1).isoformat(), "2002-01-08")
        # closest
        self.assertEqual(di.getdate("15th day", 2002, 1).isoformat(), "2002-01-15")
        self.assertEqual(di.getdate("first bizday", 2002, 1).isoformat(), "2002-01-02")
        self.assertEqual(di.getdate("2nd bizday", 2002, 1).isoformat(), "2002-01-03")
        self.assertEqual(di.getdate("3rd bizday", 2002, 1).isoformat(), "2002-01-04")
        self.assertEqual(di.getdate("first tue", 2002, 1).isoformat(), "2002-01-01")
        self.assertEqual(di.getdate("last fri", 2002, 1).isoformat(), "2002-01-25")
        self.assertEqual(di.getdate("first day before first day", 2002, 1).isoformat(), "2001-12-31")
        self.assertEqual(di.getdate("2nd day before first day", 2002, 1).isoformat(), "2001-12-30")
        self.assertEqual(di.getdate("last day", 2002, 1).isoformat(), "2002-01-31")
        self.assertEqual(
            di.getdate("first bizday before last day", 2002, 1).isoformat(),
            "2002-01-30",
        )
        self.assertEqual(
            di.getdate("second bizday before last day", 2002, 1).isoformat(),
            "2002-01-29",
        )
        self.assertEqual(di.getdate("10th fri before 10th bizday", 2002, 5).isoformat(), "2002-03-08")
        self.assertEqual(di.getdate("first wed after 15th day", 2002, 5).isoformat(), "2002-05-22")
        self.assertEqual(di.getdate("first wed before 15th day", 2002, 5).isoformat(), "2002-05-08")

    def test_DateIndex_getdate2(self):
        holidays = [Date(d) for d in load_holidays("ANBIMA.txt")]
        di = DateIndex(holidays, startdate=holidays[0].date, enddate=holidays[-1].date, weekdays=(5, 6))
        self.assertEqual(di.getdate("first day", 2002, 1).isoformat(), "2002-01-01")
        self.assertEqual(
            di.getdate("first bizday before first day", 2002, 1).isoformat(),
            "2001-12-31",
        )
        self.assertEqual(di.getdate("2nd bizday before first day", 2002, 1).isoformat(), "2001-12-28")
