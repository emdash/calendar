# Calendar, Graphical calendar applet with novel interface
#
#       recurrence.py
#
# Copyright (c) 2010, Brandon Lewis <brandon_lewis@berkeley.edu>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import datetime

def dateRange(start, end):
    dt = datetime.timedelta(days=1)
    cur = start
    while cur <= end:
        yield cur
        cur += dt

def fromDateTimes(start, end):
    return Period(DateSet(start.date()), start.time(), end.time())

def timePlusTimedelta(time, delta):
    result = datetime.datetime(2011, 3, 2, time.hour, time.minute) + delta
    return result.time()

def dateToStr(date):
    return "%d/%d/%d" % (date.month, date.day, date.year)

def timeToStr(time):
    return "%d:%02d" % (time.hour, time.minute)

def timeDeltaToStr(delta):
    ret = ""
    if delta.days != 0:
        ret += "%d days" % abs(delta.days)
    h = (delta.seconds / 360) % 24
    if h > 0:
        if ret: ret += ","
        ret += " %d hours" % h
    m = (delta.seconds / 60) % 60
    if m > 0:
        if ret: ret += " and"
        ret += " %d minutes" % m
    return ret

class Occurrence(object):

    def __init__(self, ordinal, creator, date, start=None, end=None):
        if start and end:
            self.start = datetime.datetime(
                date.year,
                date.month,
                date.day,
                start.hour,
                start.minute)
            self.end = datetime.datetime(
                date.year,
                date.month,
                date.day,
                end.hour,
                end.minute)
            self.all_day = False
        else:
            self.start = datetime.datetime(
                date.year,
                date.month,
                date.day,
                0,
                0)
            self.end = datetime.datetime(
                date.year,
                date.month,
                date.day,
                23,
                59)
            self.all_day = True
        self.duration = self.end - self.start
        self.date = date
        self.id = (self.start, self.end)
        self.ordinal = ordinal
        self.creator = creator

    @property
    def year(self):
        return self.date.year

    @property
    def month(self):
        return self.date.month

    @property
    def day(self):
        return self.date.day

    @property
    def hour(self):
        return self.date.hour

    @property
    def minute(self):
        return self.date.minute

    def __eq__(self, other):
        if other == None:
            return False
        return self.id == other.id

    def __lt__(self, other):
        if other == None:
            return False
        return self.id < other.id

    def __gt__(self, other):
        if other == None:
            return False
        return self.id > other.id
    
    def __hash__(self):
        return hash(self.id)

    def __add__(self, delta):
        return Occurrence(self.ordinal, self.creator, self.date + delta,
                          self.start + delta, self.end + delta)

    def clone(self, ordinal=None, creator=None, date=None, start=None, end=None):
        return Occurrence(ordinal if ordinal else self.ordinal,
                          creator if creator else self.creator,
                          date if date else self.date,
                          start if start else self.start,
                          end if end else self.end)

class Node(object):

    def __init__(self, *children):
        self.children = children

    def __eq__(self, other):
        return (type(self) == type(other)) and (self.children == other.children)

    def __hash__(self):
        return hash((type(self), self.children))

    def __str__(self):
        return self.__class__.__name__ + "(" + \
            ", ".join((str(c) for c in self.children)) + ')'

    def __add__(self, other):
        raise NotImplemented

    def toEnglish(self):
        raise NotImplemented

    def occursOnDate(self, date):
        raise NotImplemented

    def ordinal(self, date):
        raise NotImplemented

    def timedOccurrences(self, start, end):
        count = None
        for date in dateRange(start, end):
            if self.occursOnDate(date):
                if count is None:
                    count = self.ordinal(date)
                yield Occurrence(count, self, date)
                count += 1
                
class DateSet(Node):

    def __init__(self, *children):
        Node.__init__(self, *sorted(children))
        self.dates = set(children)

    def __add__(self, delta):
        return DateSet(*(c + delta for c in self.dates))

    def toEnglish(self):
        return ", ".join((dateToStr(c) for c in self.children))

    def ordinal(self, date):
        return self.children.index(date)

    def occursOnDate(self, date):
        return date in self.dates

class Daily(Node):

    def __init__(self, start_date, step):
        Node.__init__(self, start_date, step)
        self.start = start_date.toordinal()
        self.step = step
        self.phase = self.start % self.step

    def __add__(self, delta):
        return Daily(self.children[0] + delta, self.step)

    def toEnglish(self):
        return "every %d days starting %s" % \
            (self.step, dateToStr(self.children[0]))

    def ordinal(self, date):
        return (date.toordinal() - self.start) / self.step

    def occursOnDate(self, date):
        ord = date.toordinal()
        return ord >= self.start and (((ord - self.start) % self.step) == 0)

daynames = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday"
    ]
    
class Weekly(Node):

    def __init__(self, *children):
        Node.__init__(self, *children)
        self.days = set(children)

    def __add__(self, delta):
        return Weekly(*((c + delta.days) % 7 for c in self.days))

    def toEnglish(self):
        return "every " + ", ".join((daynames[d] for d in self.days))

    def ordinal(self, date):
        days = [1 if (d in self.days) else 0 for d in range(7)]
        ordinal = date.toordinal()
        ordinals_per_week = len(days)
        base = ((ordinal / 7) - 1) * ordinals_per_week
        return base + sum(days[date.weekday():])

    def occursOnDate(self, date):
        return date.weekday() in self.days

monthnames = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "october",
    "november",
    "december"
    ]

class Monthly(Node):

    def __init__(self, month, day):
        Node.__init__(self, month, day)
        self.day = day
        self.month = month

    def __add__(self, delta):
        return Offset(self, delta)

    def toEnglish(self):
        if not self.month:
            return "%d of each month" % self.day
        else:
            return "%d of each %s" % (self.day, monthnames[self.month])

    def ordinal(self, date):
        if self.month:
            return date.year

        # note: no handling of leap years, or when day > 28
        return ((date.year - 1) * 12 + (date.month - 2) +
                (1 if date.day >= self.day else 0))

    def occursOnDate(self, date):
        if not self.month:
            return date.day == self.day
        else:
            return (date.day == self.day) and (date.month == self.month)

def toOrdinal(n):
    s = str(n)
    if 0 < int(s[-1]) < 4:
        ending = ['st', 'nd', 'rd'][int(s[-1]) - 1]
    else:
        ending = 'th'
    return s + ending

class Offset(Node):

    def __init__(self, child, offset):
        if isinstance(child, Offset):
            child = child.child
            offset = child.offset + offset
        Node.__init__(self, child, offset)
        self.child = child
        self.offset = offset

    def toEnglish(self):
        if not self.offset:
            return self.child.toEnglish()
        
        if self.offset < datetime.timedelta():
            fmt = "%s before (%s)"
        else:
            fmt = "%s after (%s)"
        return fmt % (timeDeltaToStr(self.offset), self.child.toEnglish())

    def __add__(self, delta):
        return Offset(self.child, self.offset + delta)

    def timedOccurrences(self, start, end):
        return ((c + self.offset for c in self.child.timedOccurrences(start, end)))
        
class NthWeekday(Node):

    def __init__(self, n, month, *weekdays):
        Node.__init__(self, n, month, *weekdays)
        self.n = n
        self.month = month
        self.days = set(weekdays)
        
    def __add__(self, delta):
        return Offset(self, delta)

    def toEnglish(self):
        n = toOrdinal(self.n)
        days = ", ".join((daynames[d] for d in self.days))
        if not self.month:
            return "every %s %s" % (n, days)
        else:
            return "every %s %s of each %s" % (n, days, monthnames[month])          

    def ordinal(self, date):
        def weekdays_in_month(weekday, month, year):
            first = datetime.date(year, month, 1)
            last = datetime.date(year, month, (self.last_day_year_month(year, month) / 7))
            base = 3
            if first.weekday() <= weekday:
                base += 1
            if last.weekday() >= weekday:
                base += 1

        if self.month:
            count = 0
            for year in xrange(1, date.year):
                for day in self.days:
                    if abs(self.n) <= weekdays_in_month(day, self.month, year):
                        count += 1
            return count


        count = 0
        for year in xrange(1, date.year):
            for month in xrange(1, date.month):
                for day in self.days:
                    if abs(self.n) <= weekdays_in_month(day, month, year):
                        count += 1
        return count
        
    def occursOnDate(self, date):
        if self.month and not date.month == self.month:
            return False
        first_of_month = datetime.date(date.year, date.month, 1)
        nth = (date.day / 7)
        if first_of_month.weekday() <= date.weekday():
            nth += 1
        return (nth == self.n) and (date.weekday() in self.days)

    last_days = {
        11 : 30,
        4 : 30,
        6 : 30,
        7 : 30,
        9 : 30,
        }
    
    def last_day(self, date):
        month = date.month
        if month == 2:
            return 29 if ((date.year % 4) == 0) else 28
        return self.last_days.get(month, 31)


    def last_day_year_month(self, year, month):
        if month == 2:
            return 29 if ((year % 4) == 0) else 28
        return self.last_days.get(month, 31)
    
class And(Node):

    def __init__(self, a, b):
        Node.__init__(self, a, b)
        self.a = a
        self.b = b

    def __add__(self, delta):
        return And(self.a + delta, self.b + delta)

    def toEnglish(self):
        return "(%s) and (%s)" % (self.a.toEnglish(), self.b.toEnglish())

    def timedOccurrences(self, start, end):
        # for now if there are overlapping occurrences in either set,
        # we return them both. In the future we may wisth to merge
        # overlapping events together
        values = list((v.clone(ordinal=(0, v.ordinal)) for v in self.a.timedOccurrences(start, end)))
        values.extend((v.clone(ordinal=(1, v.ordinal)) for v in self.b.timedOccurrences(start, end)))
        values.sort(key=lambda x: x.start)
        return iter(values)


class Except(Node):

    def __init__(self, include, exclude):
        Node.__init__(self, include, exclude)
        self.include = include
        self.exclude = exclude

    def __add__(self, delta):
        return Except(self.include + delta, self.exclude + delta)

    def toEnglish(self):
        return "(%s) except (%s)" % (self.include.toEnglish(), self.exclude.toEnglish())

    def timedOccurrences(self, start, end):
        # for now we exclude any occurrences which occur on the same
        # date as an occurrence in our exclusion list. In the future
        # we may wish to subtract out the intersection of the include
        # and exclude recurrences.
        include = list(self.include.timedOccurrences(start, end))
        include.sort()
        exclude = set((o.date for o in self.exclude.timedOccurrences(start, end)))
        for value in include:
            if not value.date in exclude:
                yield value

class Filter(Node):

    def __init__(self, child, *args):
        Node.__init__(self, child, *args)
        self.child = child
        self.args = args

    def __add__(self, delta):
        return type(self)(self.child + delta, *(c + delta for c in self.args))

    def occursOnDate(self, date):
        return self.filter(date) and self.child.occursOnDate(date)

    def timedOccurrences(self, start, end):
        return (p for p in self.child.timedOccurrences(start, end)
                if self.filter(p))

    def filter(self, period):
        raise NotImplemented

class From(Filter):

    def toEnglish(self):
        return "(%s) from %s" % (self.child.toEnglish(), dateToStr(self.args[0]))

    def filter(self, period):
        return period.date >= self.args[0]

class Until(Filter):

    def toEnglish(self):
        return "(%s) until %s" % (self.child.toEnglish(), dateToStr(self.args[0]))

    def filter(self, period):
        return period.date <= self.args[0]

import itertools

class For(Filter):

    def __add__(self, delta):
        return For(self.child + delta, *self.args)

    def toEnglish(self):
        return "(%s) repeating %d times" % (self.child.toEnglish(), self.args[0])

    def timedOccurrences(self, start, end):
        return (c for c in self.child.timedOccurrences(start, end) if
                c.id < self.args[0])

class Period(Filter):

    def __init__(self, child, start, end):
        Filter.__init__(self, child, start, end)
        self.child = child
        self.start = start
        self.end = end

    def __add__(self, delta):
        return Period(self.child + delta,
                      timePlusTimedelta(self.start, delta),
                      timePlusTimedelta(self.end, delta))

    def toEnglish(self):
        if isinstance(self.end, datetime.timedelta):
            return "(%s) at %s for %s" % \
                (self.child.toEnglish(), timeToStr(self.start), timeToStr(self.end))
        return "(%s) from %s until %s" %\
            (self.child.toEnglish(), timeToStr(self.start), timeToStr(self.end))
    
    def filter(self, date):
        return True

    def timedOccurrences(self, start, end):
        for c in self.child.timedOccurrences(start, end):
            yield c.clone(creator=self, start=self.start, end=self.end)

if __name__ == '__main__':

    delta = datetime.timedelta(days=1, hours=1)

    ## test generated dates
    
    daterange = (datetime.date(2011, 3, 1), datetime.date(2011, 3, 10))

    def all_day(dates):
        return [(datetime.datetime(d.year, d.month, d.day, 0, 0),
                 datetime.datetime(d.year, d.month, d.day, 23, 59)) for d in dates]

    def test_range(recurrence, daterange, expected, ordinal=0):
        values = [(o.start, o.end) for o in recurrence.timedOccurrences(*daterange)]
        if not values == expected:
            print "failure: ", str(recurrence)
            print "exp: ", [(str(a), str(b)) for a, b in expected]
            print "got: ", [(str(a), str(b)) for a, b in values]

    test_range(DateSet(datetime.date(2011, 3, 1), datetime.date(2011, 3, 5),
                       datetime.date(2011, 3, 10)),
               daterange,
               all_day([datetime.date(2011, 3, 1),
                datetime.date(2011, 3, 5),
                datetime.date(2011, 3, 10)]))

    test_range(DateSet(datetime.date(2011, 2, 25),
                       datetime.date(2011, 2, 28),
                       datetime.date(2011, 3, 5),
                       datetime.date(2011, 3, 7),
                       datetime.date(2011, 3, 15)),
               daterange,
               all_day([datetime.date(2011, 3, 5),
                datetime.date(2011, 3, 7)]))
    
    test_range(Daily(datetime.date(2011, 2, 25), 2),
               daterange,
               all_day([datetime.date(2011, 3, 1),
                datetime.date(2011, 3, 3),
                datetime.date(2011, 3, 5),
                datetime.date(2011, 3, 7),
                datetime.date(2011, 3, 9)]))
    
    test_range(Daily(datetime.date(2011, 2, 25), 3),
               daterange,
               all_day([datetime.date(2011, 3, 3),
                datetime.date(2011, 3, 6),
                datetime.date(2011, 3, 9)]))

    test_range(Daily(datetime.date(2011, 2, 26), 3),
               daterange,
               all_day([datetime.date(2011, 3, 1),
                        datetime.date(2011, 3, 4),
                        datetime.date(2011, 3, 7),
                        datetime.date(2011, 3, 10)]))

    test_range(Weekly(0, 2),
               daterange,
               all_day([datetime.date(2011, 3, 2),
                datetime.date(2011, 3, 7),
                datetime.date(2011, 3, 9)]))

    test_range(Monthly(None, 5),
               daterange,
               all_day([datetime.date(2011, 3, 5)]))

    test_range(NthWeekday(2, None, 0, 2),
               daterange,
               all_day([datetime.date(2011, 3, 9)]))

    test_range(And(Weekly(0, 2, 4), DateSet(datetime.date(2011, 3, 8))),
               daterange,
               all_day([datetime.date(2011, 3, 2),
                datetime.date(2011, 3, 4),
                datetime.date(2011, 3, 7),
                datetime.date(2011, 3, 8),
                datetime.date(2011, 3, 9)]))

    test_range(Except(Daily(datetime.date(2011, 2, 28), 2), Weekly(1)),
               daterange,
               all_day([datetime.date(2011, 3, 2),
                datetime.date(2011, 3, 4),
                datetime.date(2011, 3, 6),
                datetime.date(2011, 3, 10)]))

    test_range(Period(Daily(datetime.date(2011, 2, 28), 3),
                      datetime.time(16, 35),
                      datetime.time(17, 45)),
               daterange,
               [(datetime.datetime(2011, 3, 3, 16, 35),
                 datetime.datetime(2011, 3, 3, 17, 45)),
                (datetime.datetime(2011, 3, 6, 16, 35),
                 datetime.datetime(2011, 3, 6, 17, 45)),
                (datetime.datetime(2011, 3, 9, 16, 35),
                 datetime.datetime(2011, 3, 9, 17, 45))])
                      
  
    ## test addition operator

    assert (DateSet(datetime.date(2011, 3, 2)) + delta ==
            DateSet(datetime.date(2011, 3, 3)))

    assert (Daily(datetime.date(2011, 3, 2), 2) + delta ==
            Daily(datetime.date(2011, 3, 3), 2))

    assert (Weekly(1, 2) + delta ==
            Weekly(2, 3))

    assert (Monthly(10, 31) + delta ==
            Offset(Monthly(10, 31), delta))

    assert (Monthly(None, 31) + delta ==
            Offset(Monthly(None, 31), delta))

    assert (Offset(Monthly(None, 31), delta) + delta ==
            Offset(Monthly(None, 31), datetime.timedelta(days=2, hours=2)))

    assert (NthWeekday(1, None, 4) + delta ==
            Offset(NthWeekday(1, None, 4), delta))

    assert (Until(Daily(datetime.date(2011, 3, 2), 1),
                  datetime.date(2011, 3, 10)) + delta ==
            Until(Daily(datetime.date(2011, 3, 3), 1),
                  datetime.date(2011, 3, 11)))

    assert (For(Daily(datetime.date(2011, 3, 2), 2), 10) + delta ==
            For(Daily(datetime.date(2011, 3, 3), 2), 10))

    assert (Period(DateSet(datetime.date(2011, 3, 2)),
                   datetime.time(15, 45),
                   datetime.time(16, 45)) + delta ==
            Period(DateSet(datetime.date(2011, 3, 3)),
                   datetime.time(16, 45),
                   datetime.time(17, 45)))

    assert (And(DateSet(datetime.date(2011, 3, 2)),
                DateSet(datetime.date(2011, 3, 5))) + delta ==
            And(DateSet(datetime.date(2011, 3, 3)),
                DateSet(datetime.date(2011, 3, 6))))

    assert (Except(Daily(datetime.date(2011, 3, 2), 2),
                   DateSet(datetime.date(2011, 3, 4))) + delta ==
            Except(Daily(datetime.date(2011, 3, 3), 2),
                   DateSet(datetime.date(2011, 3, 5))))

    assert (Weekly(1).toEnglish() == "every tuesday")

    assert (Offset(Monthly(None, 24), datetime.timedelta(days=1)).toEnglish() ==
            "1 days after (24 of each month)")
    assert (Offset(Monthly(None, 24), datetime.timedelta(days=-1)).toEnglish() ==
            "1 days before (24 of each month)")
    assert (Offset(Monthly(None, 24),
                   datetime.timedelta(days=1, hours=1, minutes=1)).toEnglish() ==
            "1 days, 10 hours and 1 minutes after (24 of each month)")

    assert (NthWeekday(2, None, 2).toEnglish() ==
            "every 2nd wednesday")

    assert (For(NthWeekday(2, None, 2), 100).toEnglish() ==
            "(every 2nd wednesday) repeating 100 times")
