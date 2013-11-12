# bizdays

In several countries and markets, the accountability of the price of a financial
instrument, mainly bonds and derivatives, involves the use of different
rules to compute the way the days go by.
In some countries, like in Brazil, several financial instrument only pay interest for business days along their life cycle.
Therefore, having a way to compute the number of business days between 2 dates is quite useful to price the financial instruments properly.
It is necessary the holidays which occur between the 2 dates, to compute the business days and they are intrinsically related to counties and local markets.
In Brazil, [ANBIMA](www.anbima.com.br) disposes a file with a list of holidays up to the year of 1978 which is largely used by market practioners for pricing financial instruments.
<!-- Usually you have a list with the holidays and all you want
is to find out the number of business days between two dates, nothing more. 
It is necessary for pricing properly the financial instrument. -->
Several financial libraries compute the holidays, giving no option to users set it by their own.
Furtherly, the financial calendar is usually a small feature of a huge library, as [quantlib](quantlib.org), for example, and some users, including myself, don't want to put a hand in such a huge library only to use the financial calendar.

**bizdays** is a pure Python module relying on its simplicity and the
power of Python's batteries.
bizdays computes business days between two dates and
other collateral effects, like adjust a given date for the next or previous
business day, check whether a date is a business day, creates generators of
business days sequences, and so forth.
bizdays is a module without further dependencies, what makes it appropriated for small implementations.

## Install

**bizdays** is avalilable at PyPI, so it is pip and easy_install instalable.

	pip install bizdays

or

	easy_install bizdays

## Using

Business days calculations are done for a given calendar specification. Calendar specification is a `.cal` file containing the weekdays to be
considered as non-business days and a iso-formated list of dates representing
holidays. Here follows an example:

	Saturday
	Sunday
	2012-12-25
	2013-01-01

Let's suppose that file is named `Test.cal`.
So, that file specifies a calendar named `Test`.
To create that calendar you need to instanciate the class `CalendarSpec` providing the calendar's name.

	cal = CalendarSpec('Test')

Important 1: the dates inside file must be ISO-formated (`YYYY-mm-dd` or `%Y-%m-%d`). 
Important 2: The calendar has `startdate` and `enddate`, which are defined as the first day of the first date's year and the last day of the last date's year, respectively. So that, for the example we would have, `startdate=2012-01-01` and `enddate=2013-12-31`.

Another way to create a calendar is instanciating `Calendar` directly providing `startdate`, `enddate`, a list of `holidays` and `weekdays` that will be considered non-working days.

	crazyCal = Calendar(holidays, startdate='2013-01-01', enddate='2013-12-31',
		weekdays=('Monday', 'Tuesday'))

The `holidays` list must be a list of `datetime.date` objects.

### bizdays

To compute the business days between two dates you call `bizdays` passing a tuple with the dates defining the period you are interested in (*from* and *to* dates).

	days = cal.bizdays(('2012-12-31', '2013-01-03'))
	# 2

For simplicity, and convenience, it is provided the `currentdays` method, to keep similar functionalities in the same framework, although I suppose it is useless.

	days = cal.currentdays(('2012-12-31', '2013-01-03'))
	# 3

Here we have the output of `cal` for January of 2013 which allow us to check the results.

	      Janeiro       
	Do Se Te Qu Qu Se Sá
	       1  2  3  4  5
	 6  7  8  9 10 11 12
	13 14 15 16 17 18 19
	20 21 22 23 24 25 26
	27 28 29 30 31      

### adjust_next and adjust_previous

Several contracts, by default, always expiry in the same day, for example, 1st Januray, which isn't a business day, so instead of carrying your code
with awful test you could call `adjust_next` which returns the given date
whether it is a business day or the next business day.

	cal.adjust_next('2013-01-01')
	# '2013-01-02'
	cal.adjust_next('2013-01-02')
	# '2013-01-02'

We also have `adjust_previous`, although I suppose it is unusual, too.

	cal.adjust_previous('2013-01-01')
	# '2012-12-31'

### seq

To execute calculations through sequential dates, sometimes you must consider only business days.
For example, you want to compute the price of a bond from its issue date up to its maturity.
You have to walk over business days in order to carry the contract up to maturity.
To accomplish that you use the `seq` method (stolen from R) which returns a sequence generator of business days.

	for dt in cal.seq(('2012-12-31', '2013-01-03')):
	    print dt
			
	# 2012-12-31
	# 2013-01-02
	# 2013-01-03

### offset

This method offsets the given date by `n` days respecting the calendar, so it obligatorily returns a business day.

	cal.offset('2013-01-02', 1)
	# '2013-01-03'
	cal.offset('2013-01-02', 3)
	# '2013-01-07'
	cal.offset('2013-01-02', 0)
	# '2013-01-02'

Obviously, if you want to offset backwards you can use `-n`.

	print cal.offset('2013-01-02', -1)
	# '2012-12-31'
	print cal.offset('2013-01-02', -3)
	# '2012-12-27'

Once the given date is a business day there is no problems, but if instead it isn't a working day the offset can lead to unexpected results. For example:

	cal.offset('2013-01-01', 1)
	# '2013-01-03'
	cal.offset('2013-01-01', 0)
	# '2013-01-02'
	print cal.offset('2013-01-01', -1)
	# '2012-12-28'

This happens because before starting to offset the date, the given date is adjusted to its next or previous business day. If `n >= 0` the adjustment is positive, so to the next business day, otherwise it is adjusted to the previous business day.

