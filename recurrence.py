import datetime

def dateRange(start, end):
    dt = datetime.timedelta(days=1)
    cur = start
    while cur <= end:
        yield cur
        cur += dt

class Occurrence(object):

    def __init__(self, date, start=None, end=None):
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
        else:
            self.end = self.start + end
        self.duration = self.end - self.start
        self.date = date

class Node(object):

    def __init__(self, *children):
        self.children = children

    def __eq__(self, other):
        return (type(self) == type(other)) and (self.children == other.children)

    def __str__(self):
        return self.__class__.__name__ + "(" + \
            ", ".join((str(c) for c in self.children)) + ')'

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

    def toEnglish(self):
        return ", ".join((str(c) for c in self.children))

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

    def toEnglish(self):
        return "every %d days starting %s" % \
            (self.step, self.children[0])

    def occursOnDate(self, date):
        ord = date.toordinal()
        return ord >= self.start and ((ord - self.start) % self.step) == 0
    
class Weekly(Node):

    pass

class Monthly(Node):

    pass

class NthWeekday(Node):

    pass

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
        return "%s from %s" % (self.child.toEnglish(), self.args[0])

    def filter(self, date):
        return date >= self.args[0]

class Until(Filter):

    def toEnglish(self):
        return "%s until %s" % (self.child.toEnglish(), self.args[0])

    def filter(self, date):
        return date <= self.args[0]

class For(Node):

    pass

class Period(Filter):

    def __init__(self, child, start, end):
        Filter.__init__(self, child, start, end)
        self.child = child
        self.start = start
        self.end = end

    def toEnglish(self):
        if isinstance(self.end, datetime.timedelta):
            return "%s at %s for %s" % \
                (self.child.toEnglish(), self.start, self.end)
        return "%s from %s until %s" %\
            (self.child.toEnglish(), self.start, self.end)
    
    def filter(self, date):
        return True

    def untimedOccurrences(self, start, end):
        return ()
    
    def timedOccurrences(self, start, end):
        for c in self.child.untimedOccurrences(start, end):
            yield Occurrence(c, self.start, self.end)

if __name__ == '__main__':

    print list(Period(Daily(datetime.date(2011, 2, 28), 2),
                 datetime.time(12),
                 datetime.time(14)).timedOccurrences(
        datetime.datetime(2011, 2, 20),
        datetime.datetime(2011, 3, 5)))
