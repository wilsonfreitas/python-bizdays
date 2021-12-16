
import math
import unittest
from datetime import date
from random import shuffle
from bizdays import *


def asDate(dt):
    return Date(dt).date


class TestBizdays(unittest.TestCase):
    cal = Calendar(name='actual')

    def test_bizdays_default_calendar(self):
        bizdays = self.cal.bizdays
        self.assertEqual(bizdays('2013-01-02', '2013-01-03'), 1)
        self.assertEqual(bizdays(asDate('2013-01-02'), '2013-01-03'), 1)
        self.assertEqual(bizdays(asDate('2013-01-02'), asDate('2013-01-03')),
                         1)

    def test_bizdays_default_calendar_sequence(self):
        bizdays = self.cal.bizdays
        self.assertEqual(bizdays(('2013-01-02', '2013-01-03'), '2013-01-03'),
                         [1, 0])


class TestVectorizedOpsInCalendar(unittest.TestCase):
    cal = Calendar(name='actual')

    def test_isbizday(self):
        self.assertEqual(self.cal.isbizday(('2013-01-02', '2013-01-03')),
                         [True, True])

    def test_bizdays(self):
        bizdays = self.cal.bizdays
        self.assertEqual(bizdays(('2013-01-02', '2013-01-03'), '2013-01-03'),
                         [1, 0])

    def test_adjust(self):
        adjust = self.cal.adjust_next
        self.assertEqual(adjust(('2013-01-02', '2013-01-03'), iso=True),
                         ['2013-01-02', '2013-01-03'])
        adjust = self.cal.following
        self.assertEqual(adjust(('2013-01-02', '2013-01-03'), iso=True),
                         ['2013-01-02', '2013-01-03'])
        adjust = self.cal.adjust_previous
        self.assertEqual(adjust(('2013-01-02', '2013-01-03'), iso=True),
                         ['2013-01-02', '2013-01-03'])
        adjust = self.cal.preceding
        self.assertEqual(adjust(('2013-01-02', '2013-01-03'), iso=True),
                         ['2013-01-02', '2013-01-03'])
        adjust = self.cal.modified_following
        self.assertEqual(adjust(('2013-01-02', '2013-01-03'), iso=True),
                         ['2013-01-02', '2013-01-03'])
        adjust = self.cal.modified_preceding
        self.assertEqual(adjust(('2013-01-02', '2013-01-03'), iso=True),
                         ['2013-01-02', '2013-01-03'])

    def test_offset(self):
        offset = self.cal.offset
        self.assertEqual(offset(('2013-01-02', '2013-01-03'), 1, iso=True),
                         ['2013-01-03', '2013-01-04'])
        self.assertEqual(offset('2013-01-02', [1, 2], iso=True),
                         ['2013-01-03', '2013-01-04'])


class TestCalendar(unittest.TestCase):
    cal_ANBIMA = Calendar.load('ANBIMA.cal')

    def test_Calendar_instanciate_calendar(self):
        'it should instanciate the calendar'
        cal = Calendar(startdate='1970-01-01', enddate='2071-01-01',
                       weekdays=('Saturday', 'Sunday'))
        self.assertEqual(cal.weekdays, ('Saturday', 'Sunday'))
        self.assertEqual(cal.startdate.isoformat(), '1970-01-01')
        self.assertEqual(cal.enddate.isoformat(), '2071-01-01')

    def test_Calendar_weekdays_case_sensitive(self):
        'it should check if weekdays definition is case sensitive'
        cal = Calendar(startdate='2013-01-01', enddate='2013-12-31',
                       weekdays=('saturday', 'sunday'))
        self.assertEqual(cal.weekdays, ('Saturday', 'Sunday'))
        cal = Calendar(startdate='2013-01-01',
                       enddate='2013-12-31', weekdays=('sat', 'sun'))
        self.assertEqual(cal.weekdays, ('Saturday', 'Sunday'))

    def test_Calendar_default_calendar(self):
        'it should use the default calendar'
        cal = Calendar(startdate='1970-01-01', enddate='2071-01-01',
                       weekdays=('Saturday', 'Sunday'))
        self.assertEqual(cal.bizdays('2013-01-02', '2013-01-03'), 1)
        self.assertEqual(cal.bizdays('2013-01-02', '2013-01-04'), 2)
        self.assertEqual(cal.bizdays('2013-01-02', '2013-01-05'), 2)
        self.assertEqual(cal.bizdays('2013-01-02', '2013-01-06'), 2)
        self.assertEqual(cal.bizdays('2013-01-02', '2013-01-07'), 3)
        with self.assertRaises(DateOutOfRange):
            cal.bizdays('2013-01-02', '2090-01-07')
            cal.bizdays('1700-01-02', '2013-01-07')
            cal.seq('1969-01-01', '1970-12-31')
            cal.seq('2071-01-01', '2071-12-31')

    def test_Calendar_default_calendar2(self):
        'it should create a short calendar and test its boundaries'
        cal = Calendar(startdate='2013-01-01', enddate='2013-12-31',
                       weekdays=('Saturday', 'Sunday'))
        self.assertEqual(cal.weekdays, ('Saturday', 'Sunday'))
        self.assertEqual(cal.startdate.isoformat(), '2013-01-01')
        self.assertEqual(cal.enddate.isoformat(), '2013-12-31')
        self.assertEqual(cal.bizdays('2013-01-02', '2013-01-03'), 1)

    def test_Calendar_actual_calendar(self):
        'it should create an Actual Calendar'
        cal = Calendar(name='Actual')
        self.assertEqual(cal.weekdays, ())
        self.assertEqual(cal.startdate.isoformat(), '1970-01-01')
        self.assertEqual(cal.enddate.isoformat(), '2071-01-01')
        df = Date('2013-01-03').date - Date('2013-01-02').date
        self.assertEqual(cal.bizdays('2013-01-02', '2013-01-03'), df.days)

    def test_Calendar_load(self):
        'it should load  the calendar from a file'
        cal = Calendar.load('Test.cal')
        self.assertEqual(cal.startdate.isoformat(), '2001-01-01')
        self.assertEqual(cal.enddate.isoformat(), '2013-01-01')
        self.assertEqual(cal.isbizday('2001-01-02'), True)

    def test_Calendar_bizdays(self):
        'it should create a business Calendar: Brazil\'s ANBIMA'
        cal = Calendar.load('ANBIMA.cal')
        self.assertEqual(cal.bizdays('2013-07-12', '2014-07-12'), 251)
        self.assertEqual(cal.bizdays('2013-08-21', '2013-08-24'), 2)
        self.assertEqual(cal.bizdays('2013-01-01', '2013-01-31'), 21)
        self.assertEqual(cal.bizdays('2013-01-01', '2014-01-01'), 252)
        self.assertEqual(cal.bizdays('2014-01-01', '2015-01-01'), 252)
        self.assertEqual(cal.bizdays('2014-10-10', '2015-02-11'), 86)
        self.assertEqual(cal.bizdays('2013-08-13', '2013-09-02'), 14)
        self.assertEqual(cal.bizdays('2013-08-13', '2013-10-01'), 35)
        self.assertEqual(cal.bizdays('2013-08-13', '2013-11-01'), 58)
        self.assertEqual(cal.bizdays('2013-08-13', '2013-12-02'), 78)
        self.assertEqual(cal.bizdays('2013-08-13', '2014-01-02'), 99)
        self.assertEqual(cal.bizdays('2013-08-13', '2014-04-01'), 160)
        self.assertEqual(cal.bizdays('2013-08-13', '2014-07-01'), 221)
        self.assertEqual(cal.bizdays('2013-08-13', '2014-10-01'), 287)
        self.assertEqual(cal.bizdays('2013-08-13', '2015-01-02'), 352)
        self.assertEqual(cal.bizdays('2013-08-13', '2015-04-01'), 413)
        self.assertEqual(cal.bizdays('2013-08-13', '2015-07-01'), 474)
        self.assertEqual(cal.bizdays('2013-08-13', '2015-10-01'), 539)
        self.assertEqual(cal.bizdays('2013-08-13', '2016-01-04'), 602)
        self.assertEqual(cal.bizdays('2013-08-13', '2016-04-01'), 663)
        self.assertEqual(cal.bizdays('2013-08-13', '2016-07-01'), 726)
        self.assertEqual(cal.bizdays('2013-08-13', '2016-10-03'), 791)
        self.assertEqual(cal.bizdays('2013-08-13', '2017-01-02'), 853)
        self.assertEqual(cal.bizdays('2013-08-13', '2017-04-03'), 916)
        self.assertEqual(cal.bizdays('2013-08-13', '2017-07-03'), 977)
        self.assertEqual(cal.bizdays('2013-08-13', '2017-10-02'), 1041)
        self.assertEqual(cal.bizdays('2013-08-13', '2018-01-02'), 1102)
        self.assertEqual(cal.bizdays('2013-08-13', '2018-04-02'), 1163)
        self.assertEqual(cal.bizdays('2013-08-13', '2018-07-02'), 1226)
        self.assertEqual(cal.bizdays('2013-08-13', '2018-10-01'), 1290)
        self.assertEqual(cal.bizdays('2013-08-13', '2019-01-02'), 1352)
        self.assertEqual(cal.bizdays('2013-08-13', '2019-04-01'), 1413)
        self.assertEqual(cal.bizdays('2013-08-13', '2019-07-01'), 1475)
        self.assertEqual(cal.bizdays('2013-08-13', '2019-10-01'), 1541)
        self.assertEqual(cal.bizdays('2013-08-13', '2020-01-02'), 1605)
        self.assertEqual(cal.bizdays('2013-08-13', '2020-04-01'), 1667)
        self.assertEqual(cal.bizdays('2013-08-13', '2020-07-01'), 1728)
        self.assertEqual(cal.bizdays('2013-08-13', '2020-10-01'), 1793)
        self.assertEqual(cal.bizdays('2013-08-13', '2021-01-04'), 1856)
        self.assertEqual(cal.bizdays('2013-08-13', '2021-07-01'), 1979)
        self.assertEqual(cal.bizdays('2013-08-13', '2022-01-03'), 2107)
        self.assertEqual(cal.bizdays('2013-08-13', '2022-07-01'), 2231)
        self.assertEqual(cal.bizdays('2013-08-13', '2023-01-02'), 2358)
        self.assertEqual(cal.bizdays('2013-08-13', '2024-01-02'), 2607)
        self.assertEqual(cal.bizdays('2013-08-13', '2025-01-02'), 2861)

    def test_Calendar_unordered_holidays(self):
        'it should work with unordered calendars'
        ca1 = Calendar.load('ANBIMA.cal')
        _hol = ca1._holidays.copy()
        shuffle(_hol)
        cal = Calendar(holidays=_hol, weekdays=('sun', 'sat'))
        self.assertEqual(ca1.bizdays('2013-08-13', '2025-01-02'),
                         cal.bizdays('2013-08-13', '2025-01-02'))

    def test_Calendar_financial_calendar(self):
        'it should check consistency'
        hd = [
            '2017-01-02',  # New Year's Day
            '2017-01-16',  # Birthday of Martin Luther King, Jr.
            '2017-02-20',  # Washington's Birthday
            '2017-05-29',  # Memorial Day
            '2017-07-04',  # Independence Day
            '2017-09-04',  # Labor Day
            '2017-10-09',  # Columbus Day
            '2017-11-10',  # Veterans Day
            '2017-11-23',  # Thanksgiving Day
            '2017-12-25'  # Christmas Day
        ]
        cal = Calendar(
            holidays=hd,
            weekdays=('saturday', 'sunday'),
            startdate='2017-01-01',
            enddate='2017-12-31',
            financial=True)

        self.assertEqual(cal.bizdays('2017-09-04', '2017-09-08'),
                         cal.bizdays('2017-09-04', '2017-09-09'))
        # from is non bizdays
        self.assertEqual(cal.bizdays('2017-09-04', '2017-09-08'),
                         cal.bizdays('2017-09-05', '2017-09-08'))
        # to is non bizdays
        self.assertEqual(cal.bizdays('2017-09-05', '2017-09-09'),
                         cal.bizdays('2017-09-05', '2017-09-08'))

    def test_Calendar_non_financial_calendars(self):
        'it should create non financial calendars'
        cal = Calendar(weekdays=('sun', 'sat'), financial=False)
        self.assertEqual(cal.bizdays('2018-03-02', '2018-03-05'), 2)

        hd = [
            '2017-01-02',  # New Year's Day
            '2017-01-16',  # Birthday of Martin Luther King, Jr.
            '2017-02-20',  # Washington's Birthday
            '2017-05-29',  # Memorial Day
            '2017-07-04',  # Independence Day
            '2017-09-04',  # Labor Day
            '2017-10-09',  # Columbus Day
            '2017-11-10',  # Veterans Day
            '2017-11-23',  # Thanksgiving Day
            '2017-12-25'  # Christmas Day
        ]
        cal = Calendar(
            holidays=hd,
            weekdays=('saturday', 'sunday'),
            startdate='2017-01-01',
            enddate='2017-12-31',
            financial=False)

        self.assertEqual(cal.bizdays('2017-09-04', '2017-09-08'),
                         cal.bizdays('2017-09-04', '2017-09-09'))
        # from is non bizdays
        self.assertEqual(cal.bizdays('2017-09-04', '2017-09-08'),
                         cal.bizdays('2017-09-05', '2017-09-08'))
        # to is non bizdays
        self.assertEqual(cal.bizdays('2017-09-05', '2017-09-09'),
                         cal.bizdays('2017-09-05', '2017-09-08'))

    def test_Calendar_isbizday(self):
        'is business day'
        self.assertEqual(self.cal_ANBIMA.isbizday(
            '2013-01-01'), False)  # New year
        self.assertEqual(self.cal_ANBIMA.isbizday(
            '2013-01-02'), True)  # First bizday
        self.assertEqual(self.cal_ANBIMA.isbizday(
            '2013-01-05'), False)  # Saturday

    def test_Calendar_next_bizday(self):
        '''next_bizday calculations'''
        self.assertEqual(self.cal_ANBIMA.adjust_next(
            '2013-01-01', iso=True), '2013-01-02')
        self.assertEqual(self.cal_ANBIMA.adjust_next(
            '2013-01-02', iso=True), '2013-01-02')
        self.assertEqual(self.cal_ANBIMA.following(
            '2013-01-02', iso=True), '2013-01-02')

    def test_Calendar_previous_bizday(self):
        '''previous_bizday calculations'''
        self.assertEqual(self.cal_ANBIMA.adjust_previous(
            '2013-02-02', iso=True), '2013-02-01')
        self.assertEqual(self.cal_ANBIMA.preceding(
            '2013-02-02', iso=True), '2013-02-01')
        self.assertEqual(self.cal_ANBIMA.adjust_previous(
            '2013-02-01', iso=True), '2013-02-01')
        self.assertEqual(self.cal_ANBIMA.preceding(
            '2013-02-01', iso=True), '2013-02-01')

    def test_Calendar_modified_following(self):
        '''modified_following calculations'''
        self.assertEqual(self.cal_ANBIMA.modified_following(
            '2013-01-01', iso=True), '2013-01-02')
        self.assertEqual(self.cal_ANBIMA.modified_following(
            '2016-01-31', iso=True), '2016-01-29')

    def test_Calendar_modified_preceding(self):
        '''modified_preceding calculations'''
        self.assertEqual(self.cal_ANBIMA.modified_preceding(
            '2013-01-01', iso=True), '2013-01-02')
        self.assertEqual(self.cal_ANBIMA.modified_preceding(
            '2016-01-31', iso=True), '2016-01-29')

    def test_Calendar_seq(self):
        '''sequence generator of bizdays'''
        dts = ('2013-01-02', '2013-01-03', '2013-01-04', '2013-01-07',
               '2013-01-08',
               '2013-01-09', '2013-01-10')
        seq = list(self.cal_ANBIMA.seq('2013-01-01', '2013-01-10'))
        self.assertEqual(len(seq), len(dts))
        for i, dt in enumerate(seq):
            self.assertEqual(dt.isoformat(), dts[i])
        seq = self.cal_ANBIMA.seq('2012-01-02', '2012-01-02')
        for i, dt in enumerate(seq):
            self.assertEqual(dt.isoformat(), '2012-01-02')

    def test_Calendar_offset(self):
        '''it should offset the given date by n days (forward or backward)'''
        self.assertEqual(self.cal_ANBIMA.offset(
            '2013-01-02', 1, iso=True), '2013-01-03')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2013-01-02', 0, iso=True), '2013-01-02')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2013-01-02', -1, iso=True), '2012-12-31')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2012-01-02', 1, iso=True), '2012-01-03')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2012-01-02', 3, iso=True), '2012-01-05')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2012-01-02', 0, iso=True), '2012-01-02')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2012-01-02', -1, iso=True), '2011-12-30')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2012-01-02', -3, iso=True), '2011-12-28')
        # offset non working days
        self.assertEqual(self.cal_ANBIMA.offset(
            '2013-01-01', 2, iso=True), '2013-01-03')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2013-01-01', 1, iso=True), '2013-01-02')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2013-01-01', 0, iso=True), '2013-01-01')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2013-01-01', -1, iso=True), '2012-12-31')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2013-01-01', -2, iso=True), '2012-12-28')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2012-01-01', 1, iso=True), '2012-01-02')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2012-01-01', 0, iso=True), '2012-01-01')
        self.assertEqual(self.cal_ANBIMA.offset(
            '2012-01-01', -1, iso=True), '2011-12-30')

    def test_Calendar_getdate_getnth_bizday(self):
        # first
        self.assertEqual(self.cal_ANBIMA.getdate(
            'first bizday', 2002, iso=True), '2002-01-02')
        self.assertEqual(self.cal_ANBIMA.getdate(
            'first day', 2002, 1, iso=True), '2002-01-01')
        self.assertEqual(self.cal_ANBIMA.getdate(
            'first bizday', 2002, 1, iso=True), '2002-01-02')
        self.assertEqual(self.cal_ANBIMA.getdate(
            'first wed', 2002, 2, iso=True), '2002-02-06')
        # last
        self.assertEqual(self.cal_ANBIMA.getdate(
            'last day', 2002, 2, iso=True), '2002-02-28')
        self.assertEqual(self.cal_ANBIMA.getdate(
            'last bizday', 2002, 2, iso=True), '2002-02-28')
        # nth
        self.assertEqual(self.cal_ANBIMA.getdate(
            'second bizday', 2002, 2, iso=True), '2002-02-04')
        self.assertEqual(self.cal_ANBIMA.getdate(
            'third tue', 2002, 2, iso=True), '2002-02-19')
        # closest
        # self.assertEqual(
        # cal.get_closestweekday_to_nthday(15, 'wed', 2002, 2, iso=True),
        # '2002-02-13')
        # self.assertEqual(
        # cal.get_closestweekday_to_nthday(50, 'wed', 2002, iso=True),
        # '2002-02-20')
        # before
        # self.assertEqual(
        # cal.get_nth_offset_nthday(-1, -6, 2002, 2, iso=True),
        # '2002-02-20')
        # last day before month == offset('first day of month', -1)
        # self.assertEqual(
        # cal.get_nth_offset_nthday(1, -1, 2002, 6, iso=True, adjust='next'),
        # '2002-05-31')


def test_isseq():
    'it should test if an object is a sequence or not'
    assert not isseq('wilson')
    assert not isseq(1)
    assert isseq([])


class TestVectorizedOperations(unittest.TestCase):
    cal = Calendar.load('Test.cal')

    def test_Vectorized_operations_isbizday(self):
        'it should check in a vector of dates which are bizdays'
        dates = ('2002-01-01', '2002-01-02')
        self.assertEqual(
            list(self.cal.vec.isbizday(dates)),
            [False, True]
        )

    def test_Vectorized_operations_bizdays(self):
        'it should compute bizdays for many dates at once'
        dates = ('2002-01-01', '2002-01-02', '2002-01-03')
        self.assertEqual(
            list(self.cal.vec.bizdays(dates, Date('2002-01-05'))),
            [2, 2, 1]
        )
        self.assertEqual(
            list(self.cal.vec.bizdays('2001-12-31', dates)),
            [0, 1, 2]
        )

    def test_Vectorized_operations_adjust_dates(self):
        'it should adjust (next or previous) many days at once'
        dates = ('2002-01-01', '2002-01-02', '2002-01-03')
        self.assertEqual(
            tuple(self.cal.vec.adjust_next(dates, iso=True)),
            ('2002-01-02', '2002-01-02', '2002-01-03')
        )
        self.assertEqual(
            tuple(self.cal.vec.adjust_previous(dates, iso=True)),
            ('2001-12-31', '2002-01-02', '2002-01-03')
        )

    def test_Vectorized_operations_offset(self):
        'it should offset many days at once'
        dates = ('2002-01-01', '2002-01-02', '2002-01-03')
        self.assertEqual(
            tuple(d.isoformat() for d in self.cal.vec.offset(dates, 1)),
            ('2002-01-02', '2002-01-03', '2002-01-04')
        )


class TestDateIndex(unittest.TestCase):
    def test_DateIndex_start_workday_end_workday(self):
        'it should instanciate the calendar starting and ending on workingdays'
        cix = DateIndex([], startdate='2020-04-01',
                        enddate='2020-04-07', weekdays=(5, 6))
        assert all(cix._index[dt][0] == cix._index[dt][3]
                   for dt in cix._index if not cix._index[dt][2])

    def test_DateIndex_start_nonworkday_end_workday(self):
        '''
            it should instanciate the calendar starting on nonworkday
            and ending on workday
        '''
        cix = DateIndex([], startdate='2020-03-29',
                        enddate='2020-04-03', weekdays=(5, 6))
        assert all(cix._index[dt][0] == cix._index[dt][3]
                   for dt in cix._index if not cix._index[dt][2])

    def test_DateIndex_start_weekend_end_workday(self):
        '''
            it should instanciate the calendar starting on weekend and
            ending on workday
        '''
        cix = DateIndex([], startdate='2020-03-28',
                        enddate='2020-04-03', weekdays=(5, 6))
        assert all(cix._index[dt][0] == cix._index[dt][3]
                   for dt in cix._index if not cix._index[dt][2])

    def test_DateIndex_start_workday_end_nonworkday(self):
        '''
            it should instanciate the calendar starting on workday and
            ending on nonworkday
        '''
        cix = DateIndex([], startdate='2020-04-01',
                        enddate='2020-04-04', weekdays=(5, 6))
        assert all(cix._index[dt][0] == cix._index[dt][3]
                   for dt in cix._index if not cix._index[dt][2])

    def test_DateIndex_start_workday_end_weekend(self):
        '''
            it should instanciate the calendar starting on workday and
            ending on weekend
        '''
        cix = DateIndex([], startdate='2020-04-01',
                        enddate='2020-04-05', weekdays=(5, 6))
        assert all(cix._index[dt][0] == cix._index[dt][3]
                   for dt in cix._index if not cix._index[dt][2])

    def test_DateIndex_start_nonworkday_end_nonworkday(self):
        '''it should instanciate the calendar starting on nonworkday and
           ending on nonworkday'''
        cix = DateIndex([], startdate='2020-03-29',
                        enddate='2020-04-04', weekdays=(5, 6))
        assert all(cix._index[dt][0] == cix._index[dt][3]
                   for dt in cix._index if not cix._index[dt][2])

    def test_DateIndex_start_weekend_end_weekend(self):
        '''it should instanciate the calendar starting on nonworkday and
           ending on nonworkday'''
        cix = DateIndex([], startdate='2020-03-28',
                        enddate='2020-04-05', weekdays=(5, 6))
        assert all(cix._index[dt][0] == cix._index[dt][3]
                   for dt in cix._index if not cix._index[dt][2])

    def test_DateIndex_following_preceding(self):
        'it should test DateIndex'
        holidays = load_holidays('ANBIMA.txt')
        di = DateIndex(holidays, startdate=min(holidays),
                       enddate=max(holidays), weekdays=(5, 6))
        self.assertEqual(di.following('2011-01-01').isoformat(), '2011-01-03')
        self.assertEqual(di.following('2011-01-03').isoformat(), '2011-01-03')
        self.assertEqual(di.preceding('2011-01-09').isoformat(), '2011-01-07')
        self.assertEqual(di.preceding('2011-01-07').isoformat(), '2011-01-07')

    def test_DateIndex_offset(self):
        'it should test DateIndex'
        holidays = load_holidays('ANBIMA.txt')
        di = DateIndex(holidays, startdate=min(holidays),
                       enddate=max(holidays), weekdays=(5, 6))
        self.assertEqual(di.offset('2011-01-07', 1).isoformat(), '2011-01-10')
        self.assertEqual(di.offset('2011-01-10', -1).isoformat(), '2011-01-07')

    def test_DateIndex_seq(self):
        'it should test DateIndex'
        holidays = load_holidays('ANBIMA.txt')
        di = DateIndex(holidays, startdate=min(holidays),
                       enddate=max(holidays), weekdays=(5, 6))
        seq = di.seq('2011-01-03', '2011-01-14')
        self.assertEqual(seq[0].isoformat(), '2011-01-03')
        self.assertEqual(seq[-1].isoformat(), '2011-01-14')
        seq = di.seq('2011-01-03', '2011-01-03')
        self.assertEqual(len(seq), 1)

    def test_DateIndex_getdate(self):
        holidays = load_holidays('ANBIMA.txt')
        di = DateIndex(holidays, startdate=min(holidays),
                       enddate=max(holidays), weekdays=(5, 6))
        self.assertEqual(di.getdate('15th day', 2002,
                                    1).isoformat(), '2002-01-15')
        self.assertEqual(di.getdate('first day before 15th day',
                                    2002, 1).isoformat(), '2002-01-14')
        self.assertEqual(di.getdate('second day after 15th day',
                                    2002, 1).isoformat(), '2002-01-17')
        self.assertEqual(di.getdate(
            'second bizday before 15th day', 2002, 1).isoformat(),
            '2002-01-11')
        self.assertEqual(di.getdate(
            'second bizday after 15th day', 2002, 1).isoformat(), '2002-01-17')
        self.assertEqual(di.getdate('first bizday', 2002,
                                    1).isoformat(), '2002-01-02')
        self.assertEqual(di.getdate('second bizday', 2002,
                                    1).isoformat(), '2002-01-03')
        self.assertEqual(di.getdate('third bizday', 2002,
                                    1).isoformat(), '2002-01-04')
        self.assertEqual(di.getdate(
            'second bizday before 10th bizday', 2002, 1).isoformat(),
            '2002-01-11')
        # zero is before, -1 is before and 1 is after
        self.assertEqual(di.getdate('first tue before first day',
                                    2002, 1).isoformat(), '2001-12-25')
        self.assertEqual(di.getdate('first tue after first day',
                                    2002, 1).isoformat(), '2002-01-08')
        # zero is before, -1 is before and 1 is after
        self.assertEqual(di.getdate(
            'first tue before second day', 2002, 1).isoformat(), '2002-01-01')
        self.assertEqual(di.getdate('first tue after second day',
                                    2002, 1).isoformat(), '2002-01-08')
        # closest
        self.assertEqual(di.getdate('15th day', 2002,
                                    1).isoformat(), '2002-01-15')
        self.assertEqual(di.getdate('first bizday', 2002,
                                    1).isoformat(), '2002-01-02')
        self.assertEqual(di.getdate('2nd bizday', 2002,
                                    1).isoformat(), '2002-01-03')
        self.assertEqual(di.getdate('3rd bizday', 2002,
                                    1).isoformat(), '2002-01-04')
        self.assertEqual(di.getdate('first tue', 2002,
                                    1).isoformat(), '2002-01-01')
        self.assertEqual(di.getdate('last fri', 2002,
                                    1).isoformat(), '2002-01-25')
        self.assertEqual(di.getdate('first day before first day',
                                    2002, 1).isoformat(), '2001-12-31')
        self.assertEqual(di.getdate('2nd day before first day',
                                    2002, 1).isoformat(), '2001-12-30')
        self.assertEqual(di.getdate('last day', 2002,
                                    1).isoformat(), '2002-01-31')
        self.assertEqual(di.getdate(
            'first bizday before last day', 2002, 1).isoformat(), '2002-01-30')
        self.assertEqual(di.getdate(
            'second bizday before last day', 2002, 1).isoformat(),
            '2002-01-29')
        self.assertEqual(di.getdate(
            '10th fri before 10th bizday', 2002, 5).isoformat(), '2002-03-08')
        self.assertEqual(di.getdate('first wed after 15th day',
                                    2002, 5).isoformat(), '2002-05-22')
        self.assertEqual(di.getdate('first wed before 15th day',
                                    2002, 5).isoformat(), '2002-05-08')

    def test_DateIndex_getdate2(self):
        holidays = load_holidays('ANBIMA.txt')
        di = DateIndex(holidays, startdate=min(holidays),
                       enddate=max(holidays), weekdays=(5, 6))
        self.assertEqual(di.getdate('first day', 2002,
                                    1).isoformat(), '2002-01-01')
        self.assertEqual(di.getdate(
            'first bizday before first day', 2002, 1).isoformat(),
            '2001-12-31')
        self.assertEqual(di.getdate(
            '2nd bizday before first day', 2002, 1).isoformat(), '2001-12-28')


if __name__ == '__main__':
    unittest.main(verbosity=1)
