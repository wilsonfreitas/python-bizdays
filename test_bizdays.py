
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
        self.assertEqual(cal.bizdays(('2013-01-01', '2013-01-02')), 1)
        self.assertEqual(cal.bizdays(('2013-01-01', '2013-01-05')), 3)
        self.assertEqual(cal.bizdays(('2013-01-01', '2013-01-06')), 3)
        self.assertEqual(cal.bizdays(('2013-01-01', '2013-01-07')), 4)
    
    def testCalendar_consistency_check(self):
        'it should compare bizdays and currentdays'
        cal = Calendar(startdate='2013-01-01', enddate='2013-12-31', weekdays=[])
        self.assertEqual(cal.bizdays(('2013-01-01', '2013-01-06')), cal.currentdays(('2013-01-01', '2013-01-06')))
    
    def testCalendarSpec_name(self):
        "it should check the calendar's name"
        cal = CalendarSpec('Test')
        self.assertEqual(cal.name, 'Test')
    
    def testCalendarSpec(self):
        'calendar instanciation'
        with self.assertRaises(Exception):
            CalendarSpec('AAA')
        with self.assertRaises(Exception):
            CalendarSpec('calAAA')
        cal = CalendarSpec('Test')
        self.assertEqual(cal, CalendarSpec('Test'))
        self.assertEqual(cal.startdate.isoformat(), '2001-01-01')
        self.assertEqual(cal.enddate.isoformat(), '2013-12-31')
        self.assertEqual(len(cal.holidays), 4)
        self.assertEqual(date(2001, 1, 1) in cal.holidays, True)
        self.assertEqual(cal.index[cal.startdate], (1, 1, True))
        self.assertEqual(cal.index[cal.enddate], (3388, 4748, False))
        cal = CalendarSpec('Test', enddate='2013-01-05')
        self.assertEqual(cal.enddate.isoformat(), '2013-01-05')
        self.assertEqual(cal.index[cal.enddate], (3132, 4388, True))
        cal = CalendarSpec('Test', startdate='2000-01-01')
        self.assertEqual(cal.startdate.isoformat(), '2000-01-01')
        self.assertEqual(cal.index[cal.startdate], (1, 1, True))
        
    def test_CalendarSpec_big_calendar_load_and_bizdays(self):
        'loading a big calendar and computing bizdays between 2 dates'
        cal = CalendarSpec('ANBIMA')
        days = cal.bizdays(('2002-01-01', '2002-01-02'))
        self.assertEqual(0, days, 'Wrong business days amount')
        self.assertEqual(cal.bizdays(('2013-01-01', '2013-01-31')), 21)
        self.assertEqual(cal.bizdays(('2013-01-01', '2014-01-01')), 252)
        self.assertEqual(cal.bizdays(('2014-01-01', '2015-01-01')), 252)
        self.assertEqual(cal.bizdays(('2013-08-21', '2013-08-24')), 2)
        self.assertEqual(cal.bizdays(('2002-07-12', '2002-07-22')), 6)
        self.assertEqual(cal.bizdays(('2012-12-31', '2013-01-03')), 2)
    
    def test_CalendarSpec_currentdays(self):
        'calendar count of currentdays'
        cal = CalendarSpec('Test')
        days = cal.currentdays(('2002-01-01', '2002-01-02'))
        self.assertEqual(1, days, 'Wrong current days amount')
    
    def test_CalendarSpec_isbizday(self):
        'calendar count of currentdays'
        cal = CalendarSpec('Test')
        self.assertEqual(cal.isbizday('2002-01-01'), False) # New year
        self.assertEqual(cal.isbizday('2002-01-02'), True)  # First bizday
        self.assertEqual(cal.isbizday('2002-01-05'), False) # Saturday
    
    def test_CalendarSpec_next_bizday(self):
        """next_bizday calculations"""
        cal = CalendarSpec('Test')
        self.assertEqual(cal.adjust_next('2001-01-01'), '2001-01-02')
        self.assertEqual(cal.adjust_next('2001-01-02'), '2001-01-02')
        
    def test_CalendarSpec_previous_bizday(self):
        """previous_bizday calculations"""
        cal = CalendarSpec('Test')
        self.assertEqual(cal.adjust_previous('2001-08-12'), '2001-08-10')
    
    def test_CalendarSpec_seq(self):
        '''sequence generator of bizdays'''
        cal = CalendarSpec('Test')
        seq = cal.seq(('2013-01-01', '2013-01-05'))
        dts = ('2013-01-02', '2013-01-03', '2013-01-04')
        for i, dt in enumerate(seq):
            self.assertEqual(dt, dts[i])
        seq = cal.seq(('2013-01-02', '2013-01-02'))
        for i, dt in enumerate(seq):
            self.assertEqual(dt, '2013-01-02')
        seq = cal.seq(('2013-01-01', '2013-01-01'))
        with self.assertRaises(StopIteration):
            seq.next()
            
    def test_CalendarSpec_offset(self):
        """it should offset the given date by n days (forward or backward)"""
        cal = CalendarSpec('Test')
        self.assertEqual(cal.offset('2013-01-02', 1), '2013-01-03')
        self.assertEqual(cal.offset('2013-01-02', 3), '2013-01-07')
        self.assertEqual(cal.offset('2013-01-01', 1), '2013-01-03')
        self.assertEqual(cal.offset('2013-01-01', 0), '2013-01-02')
        self.assertEqual(cal.offset('2013-01-02', 0), '2013-01-02')
        self.assertEqual(cal.offset('2013-01-02', -1), '2012-12-31')
        self.assertEqual(cal.offset('2013-01-02', -3), '2012-12-27')
        self.assertEqual(cal.offset('2013-01-01', -1), '2012-12-28')


if __name__ == '__main__':
    unittest.main(verbosity=1)
