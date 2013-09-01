
import math
import unittest
from datetime import date
from bizdays import *

class TestCalendar(unittest.TestCase):
	def testCalendar(self):
		'calendar instanciation'
		with self.assertRaises(Exception):
			Calendar('AAA')
		with self.assertRaises(Exception):
			Calendar('calAAA')
		cal = Calendar('Test')
		self.assertEqual(cal, Calendar('Test'))
		self.assertEqual(cal.startdate.isoformat(), '2001-01-01')
		self.assertEqual(cal.enddate.isoformat(), '2013-12-31')
		self.assertEqual(len(cal.holidays), 3)
		self.assertEqual(date(2001, 1, 1) in cal.holidays, True)
		self.assertEqual(cal.index[cal.startdate], (1, 1, True))
		self.assertEqual(cal.index[cal.enddate], (3389, 4748, False))
		
	def test_Calendar_big_calendar_load_and_bizdays(self):
		'loading a big calendar and computing bizdays between 2 dates'
		cal = Calendar('ANBIMA')
		days = cal.bizdays(('2002-01-01', '2002-01-02'))
		self.assertEqual(0, days, 'Wrong business days amount')
		self.assertEqual(cal.bizdays(('2013-01-01', '2013-01-31')), 21)
		self.assertEqual(cal.bizdays(('2013-01-01', '2014-01-01')), 252)
		self.assertEqual(cal.bizdays(('2014-01-01', '2015-01-01')), 252)
		self.assertEqual(cal.bizdays(('2013-08-21', '2013-08-24')), 2)
		self.assertEqual(cal.bizdays(('2002-07-12', '2002-07-22')), 6)
	
	def test_Calendar_currentdays(self):
		'calendar count of currentdays'
		cal = Calendar('Test')
		days = cal.currentdays(('2002-01-01', '2002-01-02'))
		self.assertEqual(1, days, 'Wrong current days amount')
	
	def test_Calendar_isbizday(self):
		'calendar count of currentdays'
		cal = Calendar('Test')
		self.assertEqual(cal.isbizday('2002-01-01'), False) # New year
		self.assertEqual(cal.isbizday('2002-01-02'), True)  # First bizday
		self.assertEqual(cal.isbizday('2002-01-05'), False) # Saturday
	
	def test_Calendar_next_bizday(self):
		"""next_bizday calculations"""
		cal = Calendar('Test')
		self.assertEqual(cal.adjust_next('2001-01-01'), '2001-01-02')
		
	def test_Calendar_previous_bizday(self):
		"""previous_bizday calculations"""
		cal = Calendar('Test')
		self.assertEqual(cal.adjust_previous('2001-08-12'), '2001-08-10')
	
	def test_Calendar_seq(self):
		'''sequence generator of bizdays'''
		cal = Calendar('Test')
		seq = cal.seq('2013-01-01', '2013-01-05')
		dts = ('2013-01-02', '2013-01-03', '2013-01-04')
		for i, dt in enumerate(seq):
			self.assertEqual(dt, dts[i])
		seq = cal.seq('2013-01-02', '2013-01-02')
		for i, dt in enumerate(seq):
			self.assertEqual(dt, '2013-01-02')
		seq = cal.seq('2013-01-01', '2013-01-01')
		with self.assertRaises(StopIteration):
			seq.next()


if __name__ == '__main__':
	unittest.main(verbosity=2)
