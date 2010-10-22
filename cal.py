# PiTiVi , Non-linear video editor
#
#       pitivi/ui/controller.py
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

import gtk
import goocanvas
import gobject
import datetime
import math
from gettext import gettext as _

WIDTH = 600
HEIGHT = 400
DAY_WIDTH = WIDTH / 8
HOUR_HEIGHT = 50

#TODO: moving events
#TODO: edit the name of an event
#TODO: change the duration of an event
#TODO: repeating events
#TODO: event alarms
#TODO: save to file
#TODO: sync with google calendar
#TODO: sync with facebook calendar
#TODO: sync with evolution ??
#TODO: status bar
#TODO: go to today
#TODO: go to next week, previous week
#TODO: go to selected
#TODO: make calendar view "roll" so that sunday is always on the left
#TODO: zooming support (changes day_width/height size)
#TODO: resize canvas when window size changes
#TODO: change cursors
#TODO: start writing test cases, we've got too many features already
#TODO: don't hard-code colors or drawing styles
#TODO: port away from goocanvas ?
#TODO: allow multiple selections
#TODO: do something sane when events overlap

def quantize(x, modulus):
    return (x // modulus) * modulus

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

    area = None

    _button_down = False
    _dragging = False
    _canvas = None

    mdown = (0, 0)
    abs = (0, 0)
    rel = (0, 0)
    delta = (0, 0)
    event = None

    def _common(self, item, target, event):
        if not self._canvas:
            self._canvas = item.get_canvas()
        self.event = event

    def point_in_area(self, point, bounds):
        if not bounds.x1 <= point[0] <= bounds.x2:
            return False

        if not bounds.y1 <= point[1] <= bounds.y2:
            return False

        return True

    def on_button_press_event(self, item, target, event):
        if self.area:
            if not self.point_in_area(self.abs, self.area):
                return False

        self._common(item, target, event)
        self.mdown = (event.x, event.y)
        self._button_down = True
        self.button_press()
        return True

    def on_button_release_event(self, item, target, event):
        self._common(item, target, event)
        ret = False
        if self._dragging:
            self.drag_end()
            ret = True
        elif self._button_down:
            self.click()
            ret = True
        self._dragging = False
        self._button_down = False
        self.button_release()
        return ret

    def on_motion_notify_event(self, item, target, event):
        ret = False
        self._common(item, target, event)
        self.last = self.abs
        self.abs = self._canvas.convert_from_pixels(event.x, event.y)
        self.rel = (self.abs[0] - self.mdown[0], self.abs[1] - self.mdown[1])
        self.delta = (self.abs[0] - self.last[0], self.abs[1] -
            self.last[1])
        if self._button_down and (not self._dragging):
            self._dragging = True
            self.drag_start()
            ret = True
        if self._dragging:
            self.move()
            ret = True
        self.motion_notify()
        return ret

    def button_press(self):
        pass

    def button_release(self):
        pass

    def drag_start(self):
        pass

    def motion_notify(self):
        pass

    def drag_end(self):
        pass

    def move(self):
        pass

    def click(self):
        pass

class Selector(MouseInteraction):

    def __init__(self):
        self.selected = None

    def drag_start(self):
        self.update_marquee()

    def move(self):
        self.update_marquee()

    def click(self):
        self.instance.selection_start = None
        self.instance.selected_end = None
        self.instance.select_point(*self.abs)

    def update_marquee(self):
        self.instance.select_event(None)

        # normalize to x, y, width, height with positive values
        x1 = min(self.mdown[0], self.abs[0])
        y1 = min(self.mdown[1], self.abs[1])
        x2 = max(self.mdown[0], self.abs[0])
        y2 = max(self.mdown[1], self.abs[1])
        width = x2 - x1
        height = y2 - y1

        # constrain selection to the day where the mouse was first clicked.
        self.instance.select_area (self.mdown[0], y1, width, height,
            not (self.event.get_state () & gtk.gdk.SHIFT_MASK))

class VelocityController(MouseInteraction):

    _velocity = 0

    def observe(self, instance):
        self.area = goocanvas.Bounds(instance.day_width, 0, instance.width,
            instance.hour_height)
        MouseInteraction.observe(self, instance)

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

    def _move(self):
        self.instance.date -= self._velocity
        self._velocity *= 0.99
        if 0 < abs(self._velocity) < 0.01:
            self._velocity = 0
        return bool(self._velocity)

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
    selected_start = gobject.property(type=gobject.TYPE_PYOBJECT)
    selected_end = gobject.property(type=gobject.TYPE_PYOBJECT)
    selected = gobject.property(type=gobject.TYPE_PYOBJECT)

    def __init__(self, *args, **kwargs):
        goocanvas.ItemSimple.__init__(self, *args, **kwargs)
        self.day_width = self.width / 8
        self.model = Schedule("schedule.csv")
        self.model.set_changed_cb(self.model_changed)
        self.connect("notify", self.do_notify)
        self.events = {}
        self.selected = None

    def model_changed(self):
        self.changed(False)

    def get_date(self, i):
        return datetime.date.fromordinal(int(i))

    def point_to_datetime(self, x, y, snap=True):
        hour = ((y + (- self.y_scroll_offset)- self.hour_height) /
            self.hour_height)
        if snap:
            minute = quantize(hour % 1 * 60, 15)
        else:
            minute = hour % 1 * 60

        date =  int(self.date + (x - self.day_width)
            / self.day_width)
        ret = datetime.datetime.fromordinal(date)
        delta = datetime.timedelta(hours=int(hour), minutes=minute)
        return ret + delta

    def datetime_to_point(self, dt):
        if self.date < dt.toordinal() < self.date + (self.width /
            self.day_width):
            return (
                ((dt.toordinal() - self.date + 1) * self.day_width),
                (dt.hour + 1 + dt.minute / 60.0)
                    * self.hour_height + self.y_scroll_offset)
            
        return None

    def point_to_event(self, x, y):
        for event, (ex, ey, width, height) in self.events.iteritems ():
            if (ex <= x <= ex + width) and (ey <= y <= ey + height):
                return event

        return None

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

    def text_above(self, cr, text, x, y, width):
        cr.save()
        tw, th = cr.text_extents(text)[2:4]
        tw = min(width, tw)
        th = th
        cr.rectangle(x, y - th, width, th)
        cr.clip()
        cr.move_to (x + (width / 2) - tw / 2,
            y)
        cr.show_text(text)
        cr.restore()

    def text_below(self, cr, text, x, y, width):
        cr.save()
        tw, th = cr.text_extents(text)[2:4]
        tw = min(width, tw)
        th = th
        cr.rectangle(x, y, width, th)
        cr.clip()
        cr.move_to (x + (width / 2) - tw / 2,
            y + th)
        cr.show_text(text)
        cr.restore()

    def do_simple_paint(self, cr, bounds):
        cr.identity_matrix()
        self.events = {}
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

            for start, duration, text, evt in self.get_schedule(self.date + i):
                y = self.y_scroll_offset + start * self.hour_height +\
                    self.hour_height
                height = duration * self.hour_height

                cr.rectangle(x + 2, y, self.day_width - 4, height)
                if evt == self.selected:
                    cr.set_source_rgba(0.25, 0.25, 0.25)
                else:
                    cr.set_source_rgba(0.55, 0.55, 0.55)
                cr.fill_preserve()
                cr.set_source_rgb(0, 0, 0)

                self.centered_text(cr, text, x + 2, y, self.day_width - 4,
                    height)
                self.events[evt] = (x, y, self.day_width, height)
            x += self.day_width

        if self.selected_start and self.selected_end:
            start = self.datetime_to_point(self.selected_start)
            end = self.datetime_to_point(self.selected_end)
            if start and end:
                x1, y1 = start
                x2, y2 = end
                cr.set_source_rgba(0, 0, 0, 0.25)
                height = y2 - y1
                cr.rectangle(x1, y1, self.day_width, height)
                cr.fill()
                cr.set_source_rgba(1, 1, 1, 1)

                if height > self.hour_height:
                    text = self.selected_start.strftime ("%H:%M:%S")
                    self.text_below(cr, text, x1, y1 + 2, self.day_width)

                    text = self.selected_end.strftime ("%H:%M:%S")
                    self.text_above(cr, text, x1, y1 + height - 2, self.day_width)

                duration = self.selected_end - self.selected_start
                m = int (duration.seconds / 60) % 60
                h = int (duration.seconds / 60 / 60)

                text = "%dh %dm" % (h, m)
                self.centered_text(cr, text, x1, y1, self.day_width, height)

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

    def select_area(self, x, y, width, height, quantize=True):
        self.selected_start = self.point_to_datetime (x, y, quantize)
        # constrain selection to a single day
        self.selected_end = self.point_to_datetime(x, y + height, quantize)

    def select_point(self, x, y):
        self.select_event(self.point_to_event(x, y))

    def select_event(self, event):
        self.selected = event
        self.changed(False)

    def get_schedule(self, date):
        # test schedule
        return [(event.start.hour + (event.start.minute / 60.0), 
            event.get_duration().seconds / 60.0/ 60.0,
            event.description,
            event)
                for event in self.model.get_events(date)]


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
        self.scrolling = VelocityController()
        self.scrolling.observe(self.schedule)
        self.selection = Selector()
        self.selection.observe(self.schedule)

class Command(object):

    label = ""
    stockid = None
    tooltip = None

    def __init__(self, app):
        self.app = app
        self.configure()

    def configure(self):
        pass

    def do(self):
        return False

    def undo(self):
        return False

    @classmethod
    def can_do(cls, app):
        return True

    @classmethod
    def create_action_group(cls, app):
        ret = gtk.ActionGroup("command_actions")
        for sbcls in cls.__subclasses__():
            action = gtk.Action(sbcls.__name__, sbcls.label, sbcls.tooltip,
                sbcls.stockid)
            action.connect("activate", app.do_command, sbcls)
            action.set_sensitive(sbcls.can_do(app))
            ret.add_action(action)
            sbcls.action = action
        return ret

    @classmethod
    def update_actions(cls, app):
        for sbcls in cls.__subclasses__():
            sbcls.action.set_sensitive(sbcls.can_do(app))

class NewEvent(Command):

    label = _("New Event")
    tooltip = _("Add a new event")
    stockid = gtk.STOCK_ADD

    @classmethod
    def can_do(cls, app):
        return app.schedule.selected_start != None and\
            app.schedule.selected_end != None

    def configure(self):
        start = self.app.schedule.selected_start
        end = self.app.schedule.selected_end
        self.event = Event(start, end, "New Event")

    def do(self):
        self.app.model.add_event(self.event)
        self.app.schedule.selected_start = None
        self.app.schedule.selected_end = None
        return True

    def undo(self):
        self.app.model.del_event(self.event)
        return True

class DelEvent(Command):

    label = _("Delete Event")
    tooltip = _("Delete selected events")
    stockid = gtk.STOCK_DELETE

    @classmethod
    def can_do(cls, app):
        return app.schedule.selected != None

    def configure(self):
        self.event = self.app.schedule.selected

    def do(self):
        self.app.model.del_event(self.event)
        self.app.schedule.selected = None
        return True

    def undo(self):
        self.app.model.add_event(self.event)
        return True


class UndoStack(object):

    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []
        self.undo_action = gtk.Action("Undo", None, None, gtk.STOCK_UNDO)
        self.undo_action.set_sensitive(False)
        self.undo_action.connect("activate", self.undo)
        self.redo_action = gtk.Action("Redo", None, None, gtk.STOCK_REDO)
        self.redo_action.set_sensitive(False)
        self.redo_action.connect("activate", self.redo)

    def commit(self, action):
        # an action will return True if it can be undone
        if action.do():
            self.undo_stack.append(action)
            self.redo_stack = []
            self.redo_action.set_sensitive(False)
            self.undo_action.set_sensitive(True)

    def undo(self, unused_action):
        action = self.undo_stack.pop()
        action.undo()
        self.redo_stack.append(action)
        self.undo_action.set_sensitive(len(self.undo_stack))
        self.redo_action.set_sensitive(True)

    def redo(self, unused_action):
        action = self.redo_stack.pop()
        action.do()
        self.undo_stack.append(action)
        self.undo_action.set_sensitive(True)
        self.redo_action.set_sensitive(len(self.redo_stack))

class App(object):

    ui = """
    <ui>
        <toolbar name="mainToolBar">
            <toolitem action="Undo"/>
            <toolitem action="Redo"/>
            <separator />
            <toolitem action="NewEvent"/>
            <toolitem action="DelEvent"/>
        </toolbar>
    </ui>"""


    def __init__(self):
        self.undo = UndoStack()
        w = gtk.Window()
        w.connect("destroy", gtk.main_quit)
        vbox = gtk.VBox()
        hbox = gtk.HBox()
        canvas = goocanvas.Canvas()
        self.calendar_item = CalendarItem()
        self.schedule = self.calendar_item.schedule
        self.model = self.schedule.model
        canvas.get_root_item().add_child(self.calendar_item)
        canvas.set_size_request(WIDTH, HEIGHT)
        canvas.show()
        hbox.pack_start(canvas)
        hbox.pack_start(gtk.VScrollbar(adj), False, False)
        vbox.pack_end(hbox)

        uiman = gtk.UIManager ()
        actiongroup = Command.create_action_group(self)
        actiongroup.add_action(self.undo.undo_action)
        actiongroup.add_action(self.undo.redo_action)
        uiman.insert_action_group(actiongroup)
        uiman.add_ui_from_string(self.ui)
        toolbar = uiman.get_widget("/mainToolBar")
        vbox.pack_start (toolbar, False, False)

        w.add(vbox)
        w.show_all()
        self.schedule.connect("notify", self.update_actions)

    def update_actions(self, *unused):
        Command.update_actions(self)

    def run(self):
        gtk.main()

    def do_command(self, unused_action, command):
        cmd = command(self)
        cmd.configure()
        self.undo.commit(cmd)

App().run()
