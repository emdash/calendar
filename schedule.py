import datetime
import recurrence
import parser

def eventFromStartEnd(start, end, description):
    return Event(recurrence.fromDateTimes(start, end), description)

def null(*args):
    return

class Event(object):

    def __init__(self, recurrence, description):
        self.callback = null
        self.args = ()
        self._recurrence = None
        self.recurrence = recurrence
        self._description = None
        self.description = description

    def get_description(self):
        return self._description

    def set_description(self, value):
        if value != self.description:
            self._description = value
            # FIXME: make callback more generic
            self.notify()
 
    description = property(get_description, set_description)

    def get_recurrence(self):
        return self._recurrence

    def set_recurrence(self, value):
        # don't compare for equality, as this might be expensive
        self._recurrence = value
        self.notify()

    recurrence = property(get_recurrence, set_recurrence)

    def set_date_changed_cb(self, callback, args):
        self.callback = callback
        self.args = args

    def timedOccurences(self, start, end):
        return self.recurrence.timedOccurrences(start, end)

    def notify(self):
        self.callback(self, *self.args)

class FixedEvent(Event):

    pass
    
class Schedule(object):

    def __init__(self, path):
        self.events = []
        self.callback = None
        self.args = None

    def add_event(self, event):
        self.events.append(event)
        event.set_date_changed_cb(self._event_changed_cb, self.args)

    def del_event(self, event):
        self.events.remove(event)
        if self.callback:
            self.callback(*self.args)
            
    def timedOccurrences(self, start, end):
        for event in self.events:
            for inst in event.timedOccurences(start, end):
                yield event, inst

    dateformat = "%m/%d/%Y:%H:%M:%S"

    def _datetime_from_string(self, string):
        return datetime.datetime.strptime(string.strip(), self.dateformat)

    def load(self, path):
        try:
            data = open(path, "r").readlines()
            for line in data:
                recurrence, description = line.split("|")
                self.add_event(Event(parser.parse(recurrence), description.strip()))
        except IOError:
            pass

    def save(self, path):
        dest = open(path, "w")
        for event in self.events:
            self._save_event(dest, event)

    def _save_event(self, dest, event):
        print >> dest, "|".join((event.recurrence.toEnglish(),
                                event.description))

    def _datetime_to_string(self, datetime):
        return datetime.strftime(self.dateformat)

    def loadTimelog(self, path):

        def parseDate(s):
            return datetime.datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")

        def parseLine(line):
            return parseDate(line[0:16]), line[18:].strip()
        
        def parseStanza(data, line):
            prev_date, description = parseLine(data[line])
            line += 1
            while line < len(data) and data[line].strip():
                cur_date, description = parseLine(data[line])
                if not description.startswith("**"):
                    self.add_event(FixedEvent(prev_date, cur_date, description))
                prev_date = cur_date
                line += 1
            return None if line >= len(data) else line

        data = open(path, "r").readlines()
        line = parseStanza(data, 0)
        while line:
            line = parseStanza(data, line + 1)

    def set_changed_cb(self, callback, *args):
        self.callback = callback
        self.args = args
        for event in self.events:
            event.set_date_changed_cb(self._event_changed_cb, self.args)

    def _event_changed_cb(self, event):
        self.callback(*self.args)
