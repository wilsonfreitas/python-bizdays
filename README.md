![downloads](https://pypip.in/download/bizdays/badge.png)

# bizdays

In several countries and markets, the accountability of the price of a financial
instrument, mainly bonds and derivatives, involves the use of different
rules to compute the way the days go by.
In some countries, like in Brazil, several financial instrument only pay interest for business days along their life cycle.
Therefore, having a way to compute the number of business days between 2 dates is quite useful to price the financial instruments properly.
It is necessary the holidays which occur between the 2 dates, to compute the business days and they are intrinsically related to counties and local markets.
In Brazil, [ANBIMA](www.anbima.com.br) prepares a file with a list of holidays up to the year of 1978 which is largely used by market practioners for pricing financial instruments.
<!-- Usually you have a list with the holidays and all you want
is to find out the number of business days between two dates, nothing more. 
It is necessary for pricing properly the financial instrument. -->
Several financial libraries compute the holidays, giving no option to users set it by their own.
Furtherly, the financial calendar is usually a small feature of a huge library, as [quantlib](quantlib.org), for example, and some users, including myself, don't want to put a hand in such a huge library only to use the financial calendar.

**bizdays** is a pure Python module relying on its simplicity and the power of Python's batteries.
bizdays computes business days between two dates and other collateral effects, like adjust a given date for the next or previous business day, check whether a date is a business day, creates generators of business days sequences, and so forth.
bizdays is a module without further dependencies, what makes it appropriated for small implementations.

## Install

**bizdays** is avalilable at PyPI, so it is pip and easy_install instalable.

	pip install bizdays

or

	easy_install bizdays

## Using

Business days calculations are done defining a `Calendar` object.

```python
from bizdays import Calendar
cal = Calendar(holidays, ['Sunday', 'Saturday'])
```

where `holidays` is a sequence of dates which represents nonworking dates and the second argument, `weekdays`, is a sequence with nonworking weekdays.
`holidays` must a sequence of strings with ISO formatted dates or `datetime.date` objects and `weekdays` a sequence of weekdays in words.

Once you have a `Calendar` you can

```python
>>> cal.isbizday('2014-01-12')
False
>>> cal.isbizday('2014-01-13')
True
>>> cal.bizdays('2014-01-13', '2015-01-13')
253
>>> cal.adjust_next('2015-12-25')
datetime.date(2015, 12, 28)
>>> cal.adjust_next('2015-12-28')
datetime.date(2015, 12, 28)
>>> cal.adjust_previous('2014-01-01')
datetime.date(2013, 12, 31)
>>> cal.adjust_previous('2014-01-02')
datetime.date(2014, 1, 2)
>>> cal.seq('2014-01-02', '2014-01-07')
<generator object seq at 0x1092b02d0>
>>> list(cal.seq('2014-01-02', '2014-01-07'))
[datetime.date(2014, 1, 2),
 datetime.date(2014, 1, 3),
 datetime.date(2014, 1, 6),
 datetime.date(2014, 1, 7)]
>>> cal.offset('2014-01-02', 5)
datetime.date(2014, 1, 9)
```

In this example I used the list of holidays released by [ANBIMA](http://www.anbima.com.br/feriados/feriados.asp).

> **Important note on date arguments and returning dates**
> 
> As you can see in the examples all date arguments are strings ISO formatted (`YYYY-mm-dd` or `%Y-%m-%d`), but they can also be passed as `datetime.date` objects.
> All returning dates are `datetime.date` objects (or a sequence of it), unless you set `iso=True`, that will return an ISO formatted string.

### Calendar Specification

Calendar specification is a text file containing the weekdays to be considered as nonworking days and a ISO formatted list of dates representing holidays.
I usually use a `.cal` extension on those files.
Here it follows an example called `Test.cal`:

	Saturday
	Sunday
	2001-01-01
	2002-01-01
	2012-12-25
	2013-01-01

It has 4 holidays and the weekend as nonworking days.
To create that calendar you need to call `Calendar.load`

```{python}
>>> cal = Calendar.load('Test.cal')
>>> cal
Calendar: Test
Start: 2001-01-01
End: 2013-01-01
Holidays: 4
```

> The `startdate` and `enddate` of a `Calendar` are defined accordingly the first and last given holidays.

### bizdays

To compute the business days between two dates you call `bizdays` passing a tuple with the dates defining the period you are interested in (*from* and *to* dates).

```{python}
>>> cal.bizdays('2012-12-31', '2013-01-03')
2
```

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

```{python}
>>> cal.adjust_next('2013-01-01')
datetime.date(2013, 1, 2)
>>> cal.adjust_next('2013-01-02')
datetime.date(2013, 1, 2)
```

We also have `adjust_previous`, although I suppose it is unusual, too.

```{python}
>>> cal.adjust_previous('2013-01-01')
datetime.date(2012, 12, 31)
```

### seq

To execute calculations through sequential dates, sometimes you must consider only business days.
For example, you want to compute the price of a bond from its issue date up to its maturity.
You have to walk over business days in order to carry the contract up to maturity.
To accomplish that you use the `seq` method (stolen from R) which returns a sequence generator of business days.

```{python}
>>> for dt in cal.seq('2012-12-31', '2013-01-03'):
...     print dt
... 
2012-12-31
2013-01-02
2013-01-03
```

### offset

This method offsets the given date by `n` days respecting the calendar, so it obligatorily returns a business day.

```{python}
>>> cal.offset('2013-01-02', 1)
datetime.date(2013, 1, 3)
>>> cal.offset('2013-01-02', 3)
datetime.date(2013, 1, 7)
>>> cal.offset('2013-01-02', 0)
datetime.date(2013, 1, 2)
```

Obviously, if you want to offset backwards you can use `-n`.

```{python}
>>> print cal.offset('2013-01-02', -1)
2012-12-31
>>> print cal.offset('2013-01-02', -3)
2012-12-27
```
Once the given date is a business day there is no problems, but if instead it isn't a working day the offset can lead to unexpected results. For example:

```{python}
>>> cal.offset('2013-01-01', 1)
datetime.date(2013, 1, 3)
>>> cal.offset('2013-01-01', 0)
datetime.date(2013, 1, 2)
>>> cal.offset('2013-01-01', -1)
datetime.date(2012, 12, 28)
```
This happens because before starting to offset the date, the given date is adjusted to its next or previous business day. If `n >= 0` the adjustment is positive, so to the next business day, otherwise it is adjusted to the previous business day.

## Actual Calendar

The Actual Calendar can be defined as

```{python}
>>> cal = Calendar(name='Actual')
>>> cal
Calendar: Actual
Start: 1970-01-01
End: 2071-01-01
Holidays: 0
```

The Actual Calendar doesn't consider holidays, nor nonworking weekdays for counting business days between 2 dates.
This is the same of subtracting 2 dates, and adjust methods will return the given argument.
But the idea of using the Actual Calendar is working with the same interface for any calendar you work with.
When you price financial instruments you don't have to check if it uses business days or not.

> `startdate` and `enddate` defaults to `1970-01-01` and `2071-01-01`, but they can be set during Calendar's instanciation.

## Vectorized operations

The Calendar's methods: `isbizday`, `bizdays`, `adjust_previous`, `adjust_next`, and `offset`, have a vectorized counterparty, inside `Calendar.vec` attribute.

```{python}
>>> cal = Calendar.load('Test.cal')
>>> dates = ('2002-01-01', '2002-01-02', '2002-01-03')
>>> tuple(cal.vec.adjust_next(dates))
(datetime.date(2002, 1, 2),
 datetime.date(2002, 1, 2),
 datetime.date(2002, 1, 3))
>>> list(cal.vec.bizdays('2001-12-31', dates))
[0, 1, 2]
```

These functions accept sequences and single values, but always return generators.
In `bizdays` call a date and a sequence have been passed, computing business days between that date and all the others.

### Recycle rule

Once you pass 2 sequences for `bizdays` and `offset` and those sequences doesn't have the same length, no problem.
The shorter collection is cycled to fit the longer's length.

```{python}
>>> dates = ('2002-01-01', '2002-01-02', '2002-01-03', '2002-01-04', '2002-01-05')
>>> tuple(cal.vec.offset(dates, (1, 2, 3)))
(datetime.date(2002, 1, 3),
 datetime.date(2002, 1, 4),
 datetime.date(2002, 1, 8),
 datetime.date(2002, 1, 7),
 datetime.date(2002, 1, 9))
```

> These methods work well with sequences but not with generators, since I haven't found an easy way to find out which generator is the shorter.