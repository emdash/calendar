import gtk
import goocanvas
import gobject
import datetime

WIDTH = 600
HEIGHT = 400
DAY_WIDTH = WIDTH / 8
HOUR_HEIGHT = 50

class Event(object):

    def __init__(self, start, end, description):
        self.start = start
        self.end = end
        self.description = description

    def get_date(self):
        return self.start.date()

    def get_duration(self):
        return self.end - self.start

class Behavior(object):

    __signals__ = []
    instance = None

    def observe(self, instance):
        if self.instance:
            self._disconnect()
        self.instance = instance
        if instance:
            self._connect()

    def _disconect(self):
        for sigid in self.handlers:
            self.instance.disconect()
        self.handlers = []

    def _connect(self):
        pass

    def connect(self, signame):
        handler = "on_" + signame.replace("-", "_")
        self.instance.connect(signame, getattr(self, handler))

class MouseInteraction(Behavior):

    def _connect(self):
        self.connect("button-press-event")
        self.connect("button-release-event")
        self.connect("motion-notify-event")

    _button_down = False
    _dragging = False
    _canvas = None

    mdown = (0, 0)
    abs = (0, 0)
    rel = (0, 0)
    delta = (0, 0)

    def _common(self, item, target, event):
        if not self._canvas:
            self._canvas = item.get_canvas()

    def on_button_press_event(self, item, target, event):
        self._common(item, target, event)
        self.mdown = (event.x, event.y)
        self._button_down = True
        self.button_press()

    def on_button_release_event(self, item, target, event):
        self._common(item, target, event)
        if self._dragging:
            self.drag_end()
        else:
            self.click()
        self._dragging = False
        self._button_down = False
        self.button_release()

    def on_motion_notify_event(self, item, target, event):
        self._common(item, target, event)
        self.last = self.abs
        self.abs = self._canvas.convert_from_pixels(event.x, event.y)
        self.rel = (self.abs[0] - self.mdown[0], self.abs[1] - self.mdown[1])
        self.delta = (self.abs[0] - self.last[0], self.abs[1] -
            self.last[1])
        if self._button_down and (not self._dragging):
            self._dragging = True
            self.drag_start()
        if self._dragging:
            self.move()

    def button_press(self):
        pass

    def button_release(self):
        pass

    def drag_start(self):
        pass

    def drag_end(self):
        pass

    def move(self):
        pass

    def click(self):
        pass

class VelocityController(MouseInteraction):

    _velocity = 0

    def button_press(self):
        self._velocity = 0

    def drag_start(self):
        self._temp_date = self.instance.date

    def move(self):
        self.instance.date = self._temp_date - (self.rel[0] / self.instance.day_width)
        self.instance.changed(False)

    def click(self):
        pass

    def drag_end(self):
        self._velocity = self.delta[0] / self.instance.day_width
        gobject.timeout_add(20, self._move)
        self.instance.changed(False)

    def _move(self):
        self.instance.date -= self._velocity
        self._velocity *= 0.99
        if 0 < abs(self._velocity) < 0.01:
            self._velocity = 0
        self.instance.changed(False)
        return bool(self._velocity)

class Schedule(object):

    def __init__(self, path):

        self.events = []
        self.by_date = {}
        self.load(path)

    def add_event(self, event):
        self.events.append(event)
        date = event.get_date().toordinal()
        if not date in self.by_date:
            self.by_date[date] = []
        self.by_date[date].append(event)

    def get_events(self, date):
        return self.by_date.get(int(date), [])

    def load(self, path):
        data = open(path, "r").readlines()
        for line in data:
            start, end, description = line.split(",")
            start = datetime.datetime.strptime(start.strip(), "%m/%d/%Y:%H:%M:%S")
            end = datetime.datetime.strptime(end.strip(), "%m/%d/%Y:%H:%M:%S")
            self.add_event(Event(start, end, description.strip()))

class CalendarBase(goocanvas.ItemSimple, goocanvas.Item):

    __gtype_name__ = "CalendarBase"

    x = gobject.property(type=int, default=0)
    y = gobject.property(type=int, default=0)
    width = gobject.property(type=int, default=WIDTH)
    height = gobject.property(type=int, default=HEIGHT)
    hour_height = gobject.property(type=int, default=HOUR_HEIGHT)
    date = gobject.property(type=float,
        default=datetime.date.today().toordinal())
    y_scroll_offset = gobject.property(type=int, default=0)

    def __init__(self, *args, **kwargs):
        goocanvas.ItemSimple.__init__(self, *args, **kwargs)
        self.day_width = self.width / 8
        self._model = Schedule("schedule.csv")
        self.scrolling = VelocityController()
        self.scrolling.observe(self)

    def get_date(self, i):
        return datetime.date.fromordinal(int(i))

    def do_notify(self, something, something_else):
        self.day_width = self.width / 8
        self.changed(True)

    def do_simple_is_item_at(self, x, y, cr, pointer_event):
        if not (self.x <= x <= (self.x + self.width)):
            return False
        elif not (self.y <= y <= (self.y + self.height)):
            return False
        return True

    def do_simple_update(self, cr):
        cr.identity_matrix()
        self.bounds = goocanvas.Bounds(self.x, self.y,
            self.x + self.width, self.y + self.height)

    def centered_text(self, cr, text, x, y, width, height):
        cr.save()
        cr.rectangle(x, y, width, height)
        cr.clip()
        tw, th = cr.text_extents(text)[2:4]
        tw = min(width, tw)
        th = min(height, th)
        cr.move_to (x + (width / 2) - tw / 2,
            y + (height / 2) - th / 2)
        cr.show_text(text)
        cr.restore()

    def do_simple_paint(self, cr, bounds):
        cr.identity_matrix()
        x = self.day_width - (self.date * self.day_width % self.day_width)
        y = self.x
        day = int (self.date)

        cr.rectangle(self.x, self.y, self.width, self.height)
        cr.set_source_rgb(0.8, 0.8, 0.8)
        cr.fill()

        cr.save()
        cr.rectangle(self.day_width, y, self.width - self.day_width,
            self.height)
        cr.clip()

        for i in xrange(0, 8):
            date = self.get_date(day + i)
            weekday = date.weekday()

            cr.rectangle (x, y, self.day_width, self.hour_height)

            if weekday > 4:
                cr.set_source_rgb(0.75, 0.85, 0.75)
            else:
                cr.set_source_rgb(0.75, 0.75, 0.85)
            cr.fill_preserve()

            cr.set_source_rgb(1, 1, 1)
            cr.stroke()

            # draw heading
            cr.set_source_rgba (0, 0, 0, 0.75)
            self.centered_text(cr, date.strftime("%a %d"), x, y, self.day_width,
                self.hour_height)
            x += self.day_width

            # draw vertical lines
            cr.set_source_rgba(1, 1, 1)
            cr.move_to (x, self.hour_height)
            cr.line_to (x, self.height)
            cr.stroke()

        y = self.y_scroll_offset
        x = self.day_width - (self.date * self.day_width % self.day_width)

        cr.restore()
        cr.save()

        cr.rectangle(self.day_width, self.hour_height, 
            self.width - self.day_width, self.height - self.hour_height)
        cr.clip()

        cr.set_source_rgb(1, 1, 1)
        for i in xrange(1, 25):
            cr.move_to(self.day_width, self.y_scroll_offset + i * self.hour_height)
            cr.line_to(self.width, self.y_scroll_offset + i * self.hour_height)
            cr.stroke()

        cr.set_source_rgb(0, 0, 0)
        for i in xrange (0, 8):
            # vertical lines

            for start, duration, text in self.get_schedule(self.date + i):
                y = self.y_scroll_offset + start * self.hour_height
                height = duration * self.hour_height

                cr.rectangle(x + 2, y, self.day_width - 4, height)
                cr.set_source_rgba(0.55, 0.55, 0.55)
                cr.fill_preserve()
                cr.set_source_rgb(0, 0, 0)

                self.centered_text(cr, text, x + 2, y, self.day_width - 4,
                    height)
            x += self.day_width

        cr.restore()

        cr.save()
        cr.rectangle(0, self.hour_height, self.day_width, self.height -
            self.hour_height)
        cr.clip()

        for i in range(0, 24):
            y = (i + 1) * self.hour_height + self.y_scroll_offset
            cr.rectangle(0, y, self.day_width, self.hour_height)
            cr.set_source_rgb (0.75, 0.75, 0.75)
            cr.fill_preserve()
            cr.set_source_rgb (1, 1, 1)
            cr.stroke()

            # draw heading
            cr.set_source_rgba(0, 0, 0, .75)
            text = "%2d:00" % i
            tw, th = cr.text_extents(text)[2:4]
            cr.move_to ((self.day_width / 2) - tw / 2,
                y + (self.hour_height / 2) - th / 2)
            cr.show_text(text)

        cr.restore()

        cr.set_source_rgba(0.75, 0.75, 0.75)
        cr.rectangle (self.x, self.y, self.day_width, self.hour_height)
        cr.fill_preserve()
        cr.set_source_rgb(1, 1, 1)
        cr.stroke()

        cr.set_source_rgba(0.55, 0.55, 0.55)
        cr.move_to(self.x, self.hour_height)
        cr.line_to(self.width, self.hour_height)
        cr.stroke()

        cr.move_to(self.day_width, self.y)
        cr.line_to(self.day_width, self.height)
        cr.stroke()

        cr.set_source_rgb(0, 0, 0)
        self.centered_text(cr, datetime.date.fromordinal(int(self.date + 1)).strftime("%D"),
            0, 0, self.day_width, self.hour_height)

    def get_schedule(self, date):
        # test schedule
        return [(event.start.hour + (event.start.minute / 60.0), 
            event.get_duration().seconds / 60.0/ 60.0,
            event.description)
                for event in self._model.get_events(date)]


adj = gtk.Adjustment()
adj.props.upper = (HOUR_HEIGHT * 25) - HEIGHT

class CalendarItem(goocanvas.Group):

    __gtype_name__ = "CalendarItem"

    def __init__(self, *args, **kwargs):
        goocanvas.Group.__init__(self, *args, **kwargs)
        self.schedule = CalendarBase(parent=self)

        def update_scroll_pos(adjustment):
            self.schedule.y_scroll_offset = -adj.get_value()

        adj.connect("value-changed", update_scroll_pos)
        adj.props.value = datetime.datetime.now().hour * HOUR_HEIGHT


w = gtk.Window()
w.connect("destroy", gtk.main_quit)
hbox = gtk.HBox()
canvas = goocanvas.Canvas()
canvas.get_root_item().add_child(CalendarItem())
canvas.set_size_request(WIDTH, HEIGHT)
canvas.show()
hbox.pack_start(canvas)
hbox.pack_start(gtk.VScrollbar(adj), False, False)
w.add(hbox)
w.show_all()
gtk.main()
