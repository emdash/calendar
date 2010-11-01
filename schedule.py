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
        self.description = description

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

class Schedule(object):

    def __init__(self, path):
        self.events = []
        self.by_date = {}
        self.callback = None
        self.args = None
        self.load(path)

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

    def load(self, path):
        try:
            data = open(path, "r").readlines()
            for line in data:
                start, end, description = line.split(",")
                start = datetime.datetime.strptime(start.strip(), "%m/%d/%Y:%H:%M:%S")
                end = datetime.datetime.strptime(end.strip(), "%m/%d/%Y:%H:%M:%S")
                self.add_event(Event(start, end, description.strip()))
        except IOError:
            pass

    def set_changed_cb(self, callback, *args):
        self.callback = callback
        self.args = args
        for event in self.events:
            event.set_date_changed_cb(self._event_changed_cb, self.args)

    def _event_changed_cb(self, event, old):
        self.by_date[old.toordinal()].remove(event)
        self._update_cache(event)

