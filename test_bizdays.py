
import math
import unittest
from datetime import date
from bizdays import *

class TestCalendar(unittest.TestCase):
    def testCalendar_instanciate(self):
        'it should instanciate the calendar'
        cal = Calendar(startdate='2013-01-01', enddate='2013-12-31', weekdays=('Saturday', 'Sunday'))
        self.assertEqual(cal.startdate.isoformat(), '2013-01-01')
        self.assertEqual(cal.enddate.isoformat(), '2013-12-31')
        self.assertEqual(cal.weekdays, ('Saturday', 'Sunday'))
    
    def testCalendar_weekdays_case_sensitive(self):
        'it should check if weekdays definition is case sensitive'
        cal = Calendar(startdate='2013-01-01', enddate='2013-12-31', weekdays=('saturday', 'sunday'))
        self.assertEqual(cal.weekdays, ('Saturday', 'Sunday'))
        cal = Calendar(startdate='2013-01-01', enddate='2013-12-31', weekdays=('sat', 'sun'))
        self.assertEqual(cal.weekdays, ('Saturday', 'Sunday'))
    
    def testCalendar_bizdays(self):
        'it should return the amount of business days'
        cal = Calendar(startdate='2013-01-01', enddate='2013-12-31')
        self.assertEqual(cal.bizdays('2013-01-01', '2013-01-02'), 1)
        self.assertEqual(cal.bizdays('2013-01-01', '2013-01-05'), 4)
        self.assertEqual(cal.bizdays('2013-01-01', '2013-01-06'), 5)
        self.assertEqual(cal.bizdays('2013-01-01', '2013-01-07'), 6)
    
    def test_load_Calendar(self):
        'it should load a list of holidays from a file'
        cal = Calendar.load('Test.cal')
        self.assertEqual(cal.startdate.isoformat(), '2001-01-01')
        self.assertEqual(cal.enddate.isoformat(), '2013-01-01')
        self.assertEqual(cal.isbizday('2001-01-02'), True)
    
    def test_Calendar_big_calendar_load_and_bizdays(self):
        'loading a big calendar and computing bizdays between 2 dates'
        cal = Calendar.load('ANBIMA.cal')
        days = cal.bizdays('2002-01-01', '2002-01-02')
        self.assertEqual(0, days, 'Wrong business days amount')
        self.assertEqual(cal.bizdays('2013-01-01', '2013-01-31'), 21)
        self.assertEqual(cal.bizdays('2013-01-01', '2014-01-01'), 252)
        self.assertEqual(cal.bizdays('2014-01-01', '2015-01-01'), 252)
        self.assertEqual(cal.bizdays('2013-08-21', '2013-08-24'), 2)
        self.assertEqual(cal.bizdays('2002-07-12', '2002-07-22'), 6)
        self.assertEqual(cal.bizdays('2012-12-31', '2013-01-03'), 2)
    
    def test_Calendar_isbizday(self):
        'calendar count of currentdays'
        cal = Calendar.load('Test.cal')
        self.assertEqual(cal.isbizday('2002-01-01'), False) # New year
        self.assertEqual(cal.isbizday('2002-01-02'), True)  # First bizday
        self.assertEqual(cal.isbizday('2002-01-05'), False) # Saturday
    
    def test_Calendar_next_bizday(self):
        """next_bizday calculations"""
        cal = Calendar.load('Test.cal')
        self.assertEqual(cal.adjust_next('2001-01-01', iso=True), '2001-01-02')
        self.assertEqual(cal.adjust_next('2001-01-02', iso=True), '2001-01-02')
        self.assertEqual(cal.following('2001-01-02', iso=True), '2001-01-02')
    
    def test_Calendar_previous_bizday(self):
        """previous_bizday calculations"""
        cal = Calendar.load('Test.cal')
        self.assertEqual(cal.adjust_previous('2001-08-12', iso=True), '2001-08-10')
        self.assertEqual(cal.preceding('2001-08-12', iso=True), '2001-08-10')
        self.assertEqual(cal.adjust_previous('2002-03-31', iso=True), '2002-03-29')
        self.assertEqual(cal.preceding('2002-03-31', iso=True), '2002-03-29')
    
    def test_Calendar_modified_following(self):
        """modified_following calculations"""
        cal = Calendar.load('Test.cal')
        dt = cal.getdate('last day', 2002, 3)
        self.assertEqual(cal.modified_following(dt, iso=True), '2002-03-29')
    
    def test_Calendar_modified_preceding(self):
        """modified_preceding calculations"""
        cal = Calendar.load('Test.cal')
        dt = cal.getdate('first day', 2002, 6)
        self.assertEqual(cal.modified_preceding(dt, iso=True), '2002-06-03')
    
    def test_Calendar_seq(self):
        '''sequence generator of bizdays'''
        cal = Calendar.load('Test.cal')
        seq = list(cal.seq('2012-01-01', '2012-01-05'))
        dts = ('2012-01-02', '2012-01-03', '2012-01-04', '2012-01-05')
        self.assertEqual(len(seq), len(dts))
        for i, dt in enumerate(seq):
            self.assertEqual(dt.isoformat(), dts[i])
        seq = cal.seq('2012-01-02', '2012-01-02')
        for i, dt in enumerate(seq):
            self.assertEqual(dt.isoformat(), '2012-01-02')
    
    def test_Calendar_offset(self):
        """it should offset the given date by n days (forward or backward)"""
        cal = Calendar.load('Test.cal')
        self.assertEqual(cal.offset('2012-01-02', 1, iso=True), '2012-01-03')
        self.assertEqual(cal.offset('2012-01-02', 3, iso=True), '2012-01-05')
        self.assertEqual(cal.offset('2012-01-01', 1, iso=True), '2012-01-03')
        self.assertEqual(cal.offset('2012-01-01', 0, iso=True), '2012-01-02')
        self.assertEqual(cal.offset('2012-01-02', 0, iso=True), '2012-01-02')
        self.assertEqual(cal.offset('2012-01-02', -1).isoformat(), '2011-12-30')
        self.assertEqual(cal.offset('2012-01-02', -3).isoformat(), '2011-12-28')
        self.assertEqual(cal.offset('2012-01-01', -1).isoformat(), '2011-12-29')
    
    def test_Vectorized_operations_isbizday(self):
        'it should check in a vector of dates which are bizdays'
        cal = Calendar.load('Test.cal')
        dates = ('2002-01-01', '2002-01-02')
        self.assertEqual(list(cal.vec.isbizday(dates)), [False, True])
    
    def test_Vectorized_operations_bizdays(self):
        'it should compute bizdays for many dates at once'
        cal = Calendar.load('Test.cal')
        dates = ('2002-01-01', '2002-01-02', '2002-01-03')
        self.assertEqual(list(cal.vec.bizdays(dates, Date('2002-01-05'))), [2, 2, 1])
        self.assertEqual(list(cal.vec.bizdays('2001-12-31', dates)), [0, 1, 2])
    
    def test_Vectorized_operations_adjust_dates(self):
        'it should adjust (next or previous) many days at once'
        cal = Calendar.load('Test.cal')
        dates = ('2002-01-01', '2002-01-02', '2002-01-03')
        self.assertEqual(tuple(cal.vec.adjust_next(dates, iso=True)), ('2002-01-02', '2002-01-02', '2002-01-03'))
        self.assertEqual(tuple(cal.vec.adjust_previous(dates, iso=True)), ('2001-12-31', '2002-01-02', '2002-01-03'))
    
    def test_Vectorized_operations_offset(self):
        'it should offset many days at once'
        cal = Calendar.load('Test.cal')
        dates = ('2002-01-01', '2002-01-02', '2002-01-03')
        self.assertEqual(tuple(d.isoformat() for d in cal.vec.offset(dates, 1)), ('2002-01-03', '2002-01-03', '2002-01-04'))
    
    def test_isseq(self):
        'it should test if an object is a sequence or not'
        self.assertEqual(isseq('wilson'), False)
        self.assertEqual(isseq(1), False)
        self.assertEqual(isseq([]), True)
    
    def test_getnth_bizday(self):
        cal = Calendar.load('ANBIMA.cal')
        # first
        self.assertEqual(cal.getdate('first bizday', 2002, iso=True), '2002-01-02')
        self.assertEqual(cal.getdate('first day', 2002, 1, iso=True), '2002-01-01')
        self.assertEqual(cal.getdate('first bizday', 2002, 1, iso=True), '2002-01-02')
        self.assertEqual(cal.getdate('first wed', 2002, 2, iso=True), '2002-02-06')
        # last
        self.assertEqual(cal.getdate('last day', 2002, 2, iso=True), '2002-02-28')
        self.assertEqual(cal.getdate('last bizday', 2002, 2, iso=True), '2002-02-28')
        # nth
        self.assertEqual(cal.getdate('second bizday', 2002, 2, iso=True), '2002-02-04')
        self.assertEqual(cal.getdate('third tue', 2002, 2, iso=True), '2002-02-19')
        # closest
        # self.assertEqual(cal.get_closestweekday_to_nthday(15, 'wed', 2002, 2, iso=True), '2002-02-13')
        # self.assertEqual(cal.get_closestweekday_to_nthday(50, 'wed', 2002, iso=True), '2002-02-20')
        # before
        # self.assertEqual(cal.get_nth_offset_nthday(-1, -6, 2002, 2, iso=True), '2002-02-20')
        # last day before month == offset('first day of month', -1) 
        # self.assertEqual(cal.get_nth_offset_nthday(1, -1, 2002, 6, iso=True, adjust='next'), '2002-05-31')


class TestDateIndex(unittest.TestCase):
    def test_DateIndex(self):
        'it should test DateIndex'
        holidays = load_holidays('ANBIMA.txt')
        di = DateIndex(holidays, startdate=min(holidays), enddate=max(holidays), weekdays=(5, 6))
        self.assertEqual(di.following('2011-01-01').isoformat(), '2011-01-03')
        self.assertEqual(di.following('2011-01-03').isoformat(), '2011-01-03')
        self.assertEqual(di.preceding('2011-01-09').isoformat(), '2011-01-07')
        self.assertEqual(di.preceding('2011-01-07').isoformat(), '2011-01-07')
        self.assertEqual(di.offset('2011-01-07', 1).isoformat(), '2011-01-10')
        self.assertEqual(di.offset('2011-01-10', -1).isoformat(), '2011-01-07')
        with self.assertRaises(ValueError):
            di.offset('2011-01-01', -1)
        seq = di.seq('2011-01-03', '2011-01-14')
        self.assertEqual(seq[0].isoformat(), '2011-01-03')
        self.assertEqual(seq[-1].isoformat(), '2011-01-14')
        seq = di.seq('2011-01-03', '2011-01-03')
        self.assertEqual(len(seq), 1)
        self.assertEqual(di.getdate('15th day', 2002, 1).isoformat(), '2002-01-15')
        # self.assertEqual(di.getnthday_beforeafter_nthday(0, 15, 2002, 1).isoformat(), '2002-01-15')
        self.assertEqual(di.getdate('first day before 15th day', 2002, 1).isoformat(), '2002-01-14')
        self.assertEqual(di.getdate('second day after 15th day', 2002, 1).isoformat(), '2002-01-17')
        # self.assertEqual(di.getnthbizday_beforeafter_nthday(0, 15, 2002, 1).isoformat(), '2002-01-15')
        self.assertEqual(di.getdate('second bizday before 15th day', 2002, 1).isoformat(), '2002-01-11')
        self.assertEqual(di.getdate('second bizday after 15th day', 2002, 1).isoformat(), '2002-01-17')
        self.assertEqual(di.getdate('first bizday', 2002, 1).isoformat(), '2002-01-02')
        self.assertEqual(di.getdate('second bizday', 2002, 1).isoformat(), '2002-01-03')
        self.assertEqual(di.getdate('third bizday', 2002, 1).isoformat(), '2002-01-04')
        self.assertEqual(di.getdate('second bizday before 10th bizday', 2002, 1).isoformat(), '2002-01-11')
        # zero is before, -1 is before and 1 is after
        # self.assertEqual(di.getnthweekday_beforeafter_nthday(0, 'tue', 1, 2002, 1).isoformat(), '2002-01-01')
        self.assertEqual(di.getdate('first tue before first day', 2002, 1).isoformat(), '2001-12-25')
        self.assertEqual(di.getdate('first tue after first day', 2002, 1).isoformat(), '2002-01-08')
        # zero is before, -1 is before and 1 is after
        # self.assertEqual(di.getnthweekday_beforeafter_nthday(0, 'tue', 2, 2002, 1).isoformat(), '2002-01-01')
        self.assertEqual(di.getdate('first tue before second day', 2002, 1).isoformat(), '2002-01-01')
        self.assertEqual(di.getdate('first tue after second day', 2002, 1).isoformat(), '2002-01-08')
        # closest
        # self.assertEqual(di.get_closestweekday_to_nthday(15, 'wed', 2002, 1).isoformat(), '2002-01-16')
        # self.assertEqual(di.get_closestweekday_to_nthday(15, 'wed', 2002).isoformat(), '2002-01-16')
        # closest
        self.assertEqual(di.getdate('15th day', 2002, 1).isoformat(), '2002-01-15')
        self.assertEqual(di.getdate('first bizday', 2002, 1).isoformat(), '2002-01-02')
        self.assertEqual(di.getdate('2nd bizday', 2002, 1).isoformat(), '2002-01-03')
        self.assertEqual(di.getdate('3rd bizday', 2002, 1).isoformat(), '2002-01-04')
        self.assertEqual(di.getdate('first tue', 2002, 1).isoformat(), '2002-01-01')
        self.assertEqual(di.getdate('last fri', 2002, 1).isoformat(), '2002-01-25')
        self.assertEqual(di.getdate('first day before first day', 2002, 1).isoformat(), '2001-12-31')
        self.assertEqual(di.getdate('2nd day before first day', 2002, 1).isoformat(), '2001-12-30')
        self.assertEqual(di.getdate('2nd bizday before first day', 2002, 1).isoformat(), '2001-12-28')
        self.assertEqual(di.getdate('10th fri before 10th bizday', 2002, 5).isoformat(), '2002-03-08')
        self.assertEqual(di.getdate('first wed after 15th day', 2002, 5).isoformat(), '2002-05-22')
        self.assertEqual(di.getdate('first wed before 15th day', 2002, 5).isoformat(), '2002-05-08')



if __name__ == '__main__':
    unittest.main(verbosity=1)
