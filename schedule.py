import datetime

class Event(object):

    def __init__(self, start, end, description):
        self._start = None
        self._end = None
        self.callback = None
        self.args = None
        self.date = None
        self.start = start
        self.end = end
        self._description = None
        self.description = description

    def get_description(self):
        return self._description

    def set_description(self, value):
        if value != self.description:
            self._description = value
            # FIXME: make callback more generic
            self._update_date()

    description = property(get_description, set_description)

    def set_date_changed_cb(self, callback, args):
        self.callback = callback
        self.args = args

    def get_start(self):
        return self._start

    def set_start(self, value):
        self._start = value
        self._update_date()

    def get_end(self):
        return self._end

    def set_end(self, value):
        self._end = value
        self._update_date()

    start = property(get_start, set_start)
    end = property(get_end, set_end)

    def _update_date(self):
        old = self.date
        self.date = self.start.date()
        if self.callback:
            self.callback(self, old, *self.args)

    def get_date(self):
        return self.date

    def get_duration(self):
        return self.end - self.start

class FixedEvent(Event):

    def __init__(self, start, end, description):
        Event.__init__(self, start, end, description)
        self._start = start
        self._end = end
        self._update_date()

    def ignore(self, value):
        pass

    def get_start(self):
        return Event.get_start(self)

    def get_end(self):
        return Event.get_end(self)

    start = property(get_start, ignore)
    end = property(get_end, ignore)

class Schedule(object):

    def __init__(self, path):
        self.events = []
        self.by_date = {}
        self.callback = None
        self.args = None

    def add_event(self, event):
        self.events.append(event)
        date = event.get_date().toordinal()
        self._update_cache(event)
        event.set_date_changed_cb(self._event_changed_cb, self.args)

    def _update_cache(self, event):
        date = event.get_date().toordinal()
        if not date in self.by_date:
            self.by_date[date] = []
        self.by_date[date].append(event)
        if self.callback:
            self.callback(*self.args)

    def del_event(self, event):
        self.events.remove(event)
        self.by_date[event.get_date().toordinal()].remove(event)
        if self.callback:
            self.callback(*self.args)

    def get_events(self, date):
        return self.by_date.get(int(date), [])

    dateformat = "%m/%d/%Y:%H:%M:%S"

    def _datetime_from_string(self, string):
        return datetime.datetime.strptime(string.strip(), self.dateformat)

    def load(self, path):
        try:
            data = open(path, "r").readlines()
            for line in data:
                start, end, description = line.split(",")
                start = self._datetime_from_string(start)
                end = self._datetime_from_string(end)
                self.add_event(Event(start, end, description.strip()))
        except IOError:
            pass

    def save(self, path):
        dest = open(path, "w")
        for event in self.events:
            self._save_event(dest, event)

    def _save_event(self, dest, event):
        print >> dest, ",".join((self._datetime_to_string(event.start),
                                self._datetime_to_string(event.end),
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

    def _event_changed_cb(self, event, old):
        self.by_date[old.toordinal()].remove(event)
        self._update_cache(event)

