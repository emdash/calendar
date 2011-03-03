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

    def __init__(self, id, creator, date, start=None, end=None):
        if start:
            self.start = datetime.datetime(
                date.year,
                date.month,
                date.day,
                start.hour,
                start.minute)
        if end and isinstance(end, datetime.time):
            self.end = datetime.datetime(
                date.year,
                date.month,
                date.day,
                end.hour,
                end.minute)
        if start and end:
            self.duration = self.end - self.start
        self.date = date
        self.id = (creator, id)
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
        if not other:
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __add__(self, delta):
        return Occurrence(self.id, self.date + delta,
                          self.start + delta, self.end + delta)

class Node(object):

    def __init__(self, *children):
        self.children = children

    def __eq__(self, other):
        return (type(self) == type(other)) and (self.children == other.children)

    def __str__(self):
        return self.__class__.__name__ + "(" + \
            ", ".join((str(c) for c in self.children)) + ')'

    def __add__(self, other):
        raise NotImplemented

    def toEnglish(self):
        raise NotImplemented

    def occursOnDate(self, date):
        raise NotImplemented

    def untimedOccurrences(self, start, end):
        return (date for date in dateRange(start, end) if self.occursOnDate(date))

    def timedOccurrences(self, start, end):
        return ()

class DateSet(Node):

    def __init__(self, *children):
        Node.__init__(self, *sorted(children))
        self.dates = set(children)

    def __add__(self, delta):
        return DateSet(*(c + delta for c in self.dates))

    def toEnglish(self):
        return ", ".join((dateToStr(c) for c in self.children))

    def occursOnDate(self, date):
        return date in self.dates

    def untimedOccurrences(self, start, end):
        return (c for c in self.children if start <= c <= end)

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

    def occursOnDate(self, date):
        ord = date.toordinal()
        return ord >= self.start and ((ord - self.start) % self.step) == 0

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
        return ", ".join((daynames[d] for d in self.days))

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
        if self.offset < datetime.timedelta():
            fmt = "%s before %s"
        else:
            fmt = "%s after %s"
        return fmt % (timeDeltaToStr(self.offset), self.child.toEnglish())

    def __add__(self, delta):
        return Offset(self.child, self.offset + delta)

    def untimedOccurrences(self, start, end):
        return ((c + self.offset for c in self.child.untimedOccurrences(start, end)))

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

    def occursOnDate(self, date):
        if self.month and not date.month == self.month:
            return False
        if self.n > 0:
            return (date.weekday() in self.days) and\
                (((date.day / 7) + 1) == self.n)
        else:
            return (date.weekday() in self.days) and\
                (((self.last_day(date) - date.day) / 7) + 1 == abs(self.n))

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
    
class And(Node):

    pass

class Except(Node):

    def __init__(self, include, exclude):
        Node.__init__(self, include, exclude)
        self.include = include
        self.exclude = exclude

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
                if self.filterPeriod(c))

    def filter(self, date):
        raise NotImplemented

    def filterPeriod(self, period):
        return self.filter(period.date)

class From(Filter):

    def toEnglish(self):
        return "%s from %s" % (self.child.toEnglish(), dateToStr(self.args[0]))

    def filter(self, date):
        return date >= self.args[0]

class Until(Filter):

    def toEnglish(self):
        return "%s until %s" % (self.child.toEnglish(), dateToStr(self.args[0]))

    def filter(self, date):
        return date <= self.args[0]

import itertools

class For(Filter):

    def __add__(self, delta):
        return For(self.child + delta, *self.args)

    def toEnglish(self):
        return "%s repeating %d times" % (self.child.toEnglish(), self.args[0])

    def untimedOccurrences(self, start, end):
        return itertools.islice(self.child.untimedOccurrences(start, end), self.args[1])

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
            return "%s at %s for %s" % \
                (self.child.toEnglish(), timeToStr(self.start), timeToStr(self.end))
        return "%s from %s until %s" %\
            (self.child.toEnglish(), timeToStr(self.start), timeToStr(self.end))
    
    def filter(self, date):
        return True

    def untimedOccurrences(self, start, end):
        return ()
    
    def timedOccurrences(self, start, end):
        id = 0
        for c in self.child.untimedOccurrences(start, end):
            yield Occurrence(id, self, c, self.start, self.end)
            id += 1

if __name__ == '__main__':

    delta = datetime.timedelta(days=1, hours=1)

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

    assert (Offset(Monthly(None, 24), datetime.timedelta(days=1)).toEnglish() ==
            "1 days after 24 of each month")
    assert (Offset(Monthly(None, 24), datetime.timedelta(days=-1)).toEnglish() ==
            "1 days before 24 of each month")
    assert (Offset(Monthly(None, 24),
                   datetime.timedelta(days=1, hours=1, minutes=1)).toEnglish() ==
            "1 days, 10 hours and 1 minutes after 24 of each month")

    assert (NthWeekday(2, None, 2).toEnglish() ==
            "every 2nd wednesday")

    assert (For(NthWeekday(2, None, 2), 100).toEnglish() ==
            "every 2nd wednesday repeating 100 times")
