bizdays
=======

In several countries and markets, the accountability of the price of a financial
instrument, mainly bonds and derivatives, involves the use of different
rules to compute the way the days go by.
Those rules are related to holidays which are intrinsically related to counties
and local markets. Usually you have a list with the holidays and all you want
is to find out the number of business days between two dates, nothing more. 
It is necessary for pricing properly the financial instrument.
This functionality can be found in several financial packages, but sometimes you
just want to compute the number of days between two dates according a given 
calendar. And you don't want to import a huge package just for doing that.

bizdays fills that gap, is is a pure python relying on its simplicity and the
power of the batteries. bizdays computes business days between two dates and
other collateral effects, like adjust a given date for the next or previous
business day, check whether a date is a business day, creates generators of
business days sequences, and so forth. bizdays is a module without
dependencies, what makes it appropriate for small implementations.

Business days calculations are done for a given calendar specification. The
calendar specification is a `.cal` file containing the weekdays to be
considered as non-business days and a iso-formated list of dates representing
holidays. Here follows an example:

	Saturday
	Sunday
	2012-12-25
	2013-01-01

Let's suppose that file is named `Test.cal`.
So, that file specifies the `Test` calendar.
To create that calendar you need to instanciate the class `Calendar` providing the calendar's name.

	cal = Calendar('Test')

Here we have the output of `cal` command for January of 2013.

	      Janeiro       
	Do Se Te Qu Qu Se Sá
	       1  2  3  4  5
	 6  7  8  9 10 11 12
	13 14 15 16 17 18 19
	20 21 22 23 24 25 26
	27 28 29 30 31      

To compute the business days between two dates you call `bizdays` passing a tuple with the dates defining the period you are interested in.

	days = cal.bizdays(('2012-12-31', '2013-01-03'))
	# 2

For simplicity it is provided the `currentdays` method, to keep similar functionalities in the same framewokr.

	days = cal.bizdays(('2012-12-31', '2013-01-03'))
	# 3

Several contracts have a standard rule for computing maturities, for example,
first January, which isn't a business day, so instead of carrying your code
with awful test you could call `adjust_next` which returns the given date
whether it is a business day or the next business day. We also have
`adjust_previous`, but it is unusual.

	cal.adjust_next('2013-01-01')
	# '2013-01-02'
	cal.adjust_previous('2013-01-01')
	# '2012-12-31'

To execute massive calculations througth many dates you must consider only business days, for example, you want to compute the price of a bond from its issue date up to its maturity.
In order to do that you use the `seq` method which returns a sequence generator of business days.

	for dt in cal.seq(('2012-12-31', '2013-01-03')):
	    print dt
			
	# 2012-12-31
	# 2013-01-02
	# 2013-01-03

