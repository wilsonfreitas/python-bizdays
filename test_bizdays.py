
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
        self.assertEqual(cal.adjust_next('2001-01-01').isoformat(), '2001-01-02')
        self.assertEqual(cal.adjust_next('2001-01-02').isoformat(), '2001-01-02')
    
    def test_Calendar_previous_bizday(self):
        """previous_bizday calculations"""
        cal = Calendar.load('Test.cal')
        self.assertEqual(cal.adjust_previous('2001-08-12').isoformat(), '2001-08-10')
    
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
        seq = cal.seq('2012-01-01', '2012-01-01')
        with self.assertRaises(StopIteration):
            seq.next()
    
    def test_Calendar_offset(self):
        """it should offset the given date by n days (forward or backward)"""
        cal = Calendar.load('Test.cal')
        self.assertEqual(cal.offset('2012-01-02', 1).isoformat(), '2012-01-03')
        self.assertEqual(cal.offset('2012-01-02', 3).isoformat(), '2012-01-05')
        self.assertEqual(cal.offset('2012-01-01', 1).isoformat(), '2012-01-03')
        self.assertEqual(cal.offset('2012-01-01', 0).isoformat(), '2012-01-02')
        self.assertEqual(cal.offset('2012-01-02', 0).isoformat(), '2012-01-02')
        self.assertEqual(cal.offset('2012-01-02', -1).isoformat(), '2011-12-30')
        self.assertEqual(cal.offset('2012-01-02', -3).isoformat(), '2011-12-28')
        self.assertEqual(cal.offset('2012-01-01', -1).isoformat(), '2011-12-29')


if __name__ == '__main__':
    unittest.main(verbosity=1)
