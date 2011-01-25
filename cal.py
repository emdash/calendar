#!/usr/bin/python cal.py
# Calendar, Graphical calendar applet with novel interface
#
#       cal.py
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
import pango
import pangocairo
import cairo
import goocanvas
import gobject
import datetime
import math
from gettext import gettext as _
from schedule import Schedule, Event
from command import UndoStack, MenuCommand, Command, MouseCommand
from behavior import MouseInteraction, TextInput, Animation
from dispatcher import MouseCommandDispatcher
import settings
import shapes
import os

#TODO: repeating events
#TODO: event alarms
#TODO: sync with google calendar
#TODO: sync with facebook calendar
#TODO: sync with evolution ??
#TODO: message area (gtk-info bar?)
#TODO: go to next {week, month}
#TODO: make calendar view "roll" so that sunday is always on the left
#TODO: zooming support (changes day_width/height size)
#TODO: change cursors
#TODO: start writing test cases, we've got too many features already
#TODO: port away from goocanvas ?
#TODO: allow multiple selections
#TODO: do something sane when events overlap
#TODO: clamp values on selector to something sane
#TODO: specify working day (hide unused hours)

def quantize(x, modulus):
    return (x // modulus) * modulus

class KineticScrollAnimation(Animation):

    def flick(self, velocity):
        self._velocity = velocity
        self.start()

    def step(self):
        self.instance.date -= self._velocity
        self._velocity *= 0.99
        if 0 < abs(self._velocity) < 0.01:
            self._velocity = 0
        if self._velocity == 0:
            self.stop()

class CalendarBase(goocanvas.ItemSimple, goocanvas.Item):

    __gtype_name__ = "CalendarBase"

    x = gobject.property(type=int, default=0)
    y = gobject.property(type=int, default=0)
    width = gobject.property(type=int, default=settings.width)
    height = gobject.property(type=int, default=settings.height)
    hour_height = gobject.property(type=int, default=settings.hour_height)
    day_width = gobject.property(type=int, default=settings.day_width)
    date = gobject.property(type=float,
        default=datetime.date.today().toordinal())
    y_scroll_offset = gobject.property(type=int, default=0)
    selected_start = gobject.property(type=gobject.TYPE_PYOBJECT)
    selected_end = gobject.property(type=gobject.TYPE_PYOBJECT)
    selected = gobject.property(type=gobject.TYPE_PYOBJECT)
    handle_locations = None

    def __init__(self, *args, **kwargs):
        goocanvas.ItemSimple.__init__(self, *args, **kwargs)
        self.editing = False
                
        self.model = Schedule("schedule.csv")
        self.model.set_changed_cb(self.model_changed)
        self.connect("notify", self.do_notify)
        self.events = {}
        self.selected = None
        self.font_desc = pango.FontDescription("Sans 8")
        self.cursor_showing = True
        self.ti = TextInput(self.text_changed_cb)
        self.ti.observe(self)
        gobject.timeout_add(500, self._blink_cursor)

    def _blink_cursor(self):
        if not self.editing:
            return True
        self.cursor_showing = not self.cursor_showing
        self.changed(False)
        return True

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

    def point_to_timedelta(self, x, y, snap=True):
        day = int(x / self.day_width)
        minute = (day * 24 * 60) + quantize(int((y / self.hour_height) * 60), 15)

        return datetime.timedelta(minutes=minute)

    def datetime_to_point(self, dt):
        if self.date - 1 < dt.toordinal() < self.date + (self.width /
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
        #self.day_width = self.width / 8
        self.changed(True)

    def do_simple_is_item_at(self, x, y, cr, pointer_event):
        if not (self.x <= x <= (self.x + self.width)):
            return False
        elif not (self.y <= y <= (self.y + self.height)):
            return False
        return True

    def get_week_pixel_offset(self):
        return self.day_width - (self.date * self.day_width % self.day_width)

    def do_simple_update(self, cr):
        cr.identity_matrix()
        self.bounds = goocanvas.Bounds(self.x, self.y,
            self.x + self.width, self.y + self.height)
        
    def selection_handles(self, cr):

        area = shapes.Area(*self.events[self.selected]).shrink(2, 0)
        radius = 10

        top = area.above(2, radius)
        bottom = area.below(2, radius)

        shapes.upward_tab(cr, top)
        shapes.downward_tab(cr, bottom)
        cr.set_source(settings.handle_arrow_color)

        shapes.upward_triangle(cr, top.scale(0.1, 0.8))
        shapes.downward_triangle(cr, bottom.scale(0.1, 0.8))
        self.handle_locations = top, bottom

    def point_in_handle (self, x, y):
        if not self.handle_locations:
            return 0

        top, bottom = self.handle_locations
        point = (x, y)

        if top.contains_point(point):
            return 1
        if bottom.contains_point(point):
            return 2
        return 0

    def clear_background(self, cr):
        cr.rectangle(self.x, self.y, self.width, self.height)
        cr.set_source(settings.grid_bg_color)
        cr.fill()

    def draw_grid(self, cr):
        cr.save()
        cr.rectangle(self.day_width, self.hour_height, 
            self.width - self.day_width, self.height - self.hour_height)
        cr.clip()

        cr.set_source(settings.grid_line_color)
        for i in xrange(1, 25):
            cr.move_to(self.day_width, self.y_scroll_offset + i * self.hour_height)
            cr.line_to(self.width, self.y_scroll_offset + i * self.hour_height)
            cr.stroke()

        x = self.get_week_pixel_offset()

        for i in xrange(0, (self.width / self.day_width) + 1):
            # draw vertical lines
            x += self.day_width
            cr.move_to (x, self.hour_height)
            cr.line_to (x, self.height)
            cr.stroke()

    def draw_day_header(self, cr, nth_day):
        x = self.get_week_pixel_offset() + nth_day * self.day_width
        y = self.y
        leftmost_day = int(self.date)
        
        date = self.get_date(leftmost_day + nth_day)
        weekday = date.weekday()

        if weekday > 4:
            bgcolor = settings.weekday_bg_color
        else:
            bgcolor = settings.weekend_bg_color

        area = shapes.Area(x, y, self.day_width, self.hour_height)

        shapes.labeled_box(
            cr,
            area,
            date.strftime("%a\n%x"),
            bgcolor,
            settings.heading_outline_color,
            settings.text_color)

    def draw_day_headers(self, cr):
        cr.save()
        cr.rectangle(self.day_width, self.y, self.width - self.day_width,
            self.height)
        cr.clip()

        for i in xrange(0, (self.width / self.day_width) + 1):
            self.draw_day_header(cr, i)
            
        cr.restore()
        
    def draw_hour_header(self, cr, hour):
        area = shapes.Area(0,
                           (hour + 1) * self.hour_height + self.y_scroll_offset,
                           self.day_width,
                           self.hour_height)
        
        shapes.labeled_box(
            cr,
            area,
            "%2d:00" % hour,
            settings.hour_heading_color,
            settings.heading_outline_color,
            settings.text_color)

    def draw_hour_headers(self, cr):
        cr.save()
        cr.rectangle(0, self.hour_height, self.day_width, self.height -
            self.hour_height)
        cr.clip()

        for i in range(0, 24):
            self.draw_hour_header(cr, i)

        cr.restore()
            
    def get_cursor_pos(self, lyt):
        return [pango.units_to_double(x)
                for x in
                lyt.get_cursor_pos(self.ti.get_cursor_pos())[0]]

    def draw_cursor(self, cr, lyt, tx, ty, width, height):
        if not self.cursor_showing:
            return

        cr.save()
        cr.rectangle(tx, ty, width, height)
        cr.clip()
        cr.set_line_width(1)
        cr.set_source_rgba(0, 0, 0, 1)
        cr.set_antialias(cairo.ANTIALIAS_NONE)
        x, y, width, height = self.get_cursor_pos(lyt)
        cr.move_to(tx + x + 2, ty + y)
        cr.line_to(tx + x + 2, ty + y + height)
        cr.stroke()
        cr.restore()

    def draw_event(self, cr, event, day):
        start = event.start.hour + (event.start.minute / 60.0)
        duration = event.get_duration().seconds / 60.0/ 60.0

        x = self.get_week_pixel_offset() + day * self.day_width
        y = self.y_scroll_offset + start * self.hour_height +\
            self.hour_height

        height = duration * self.hour_height

        area = shapes.Area(x, y, self.day_width, height).shrink(2, 0)
        shapes.filled_box(cr, area, settings.default_event_bg_color)

        lyt = shapes.left_aligned_text(cr, event.description,
                                       x + 2, y,
                                       self.day_width - 4, height,
                                       settings.default_event_text_color)

        if event == self.selected:
            self.draw_cursor(cr, lyt, x + 2, y, self.day_width - 4, height)

        self.events[event] = (x, y, self.day_width, height)

    def draw_events(self, cr):
        self.events = {}
        for i in xrange (0, (self.width / self.day_width) + 1):
            for evt in self.get_schedule(self.date + i):
                self.draw_event(cr, evt, i)
        cr.restore()

    def draw_marquee(self, cr):
        if self.selected_start and self.selected_end:
            start = self.datetime_to_point(self.selected_start)
            end = self.datetime_to_point(self.selected_end)
            if start and end:
                x1, y1 = start
                x2, y2 = end
                cr.set_source(settings.marquee_fill_color)
                height = y2 - y1
                cr.rectangle(x1, y1, self.day_width, height)
                cr.fill()
                cr.set_source(settings.marquee_text_color)

                text = self.selected_start.strftime ("%X")
                shapes.text_above(cr, text, x1, y1 - 2, self.day_width)

                text = self.selected_end.strftime ("%X")
                shapes.text_below(cr, text, x1, y1 + height + 2, self.day_width)

                duration = self.selected_end - self.selected_start
                m = int (duration.seconds / 60) % 60
                h = int (duration.seconds / 60 / 60)

                text = "%dh %dm" % (h, m)
                shapes.centered_text(cr, text, x1, y1, self.day_width, height, settings.text_color)

    def draw_top_left_corner(self, cr):
        cr.set_source(settings.corner_bg_color)
        cr.rectangle (self.x, self.y, self.day_width, self.hour_height)
        cr.fill_preserve()
        cr.set_source(settings.heading_outline_color)
        cr.stroke()
        
        cr.set_source(settings.text_color)
        shapes.centered_text(cr, datetime.date.fromordinal(int(self.date + 1)).strftime("%x"),
            0, 0, self.day_width, self.hour_height, settings.text_color)

    def draw_comfort_lines(self, cr):
        cr.set_source(settings.comfort_line_color)
        cr.move_to(self.x, self.hour_height)
        cr.line_to(self.width, self.hour_height)
        cr.stroke()

        cr.move_to(self.day_width, self.y)
        cr.line_to(self.day_width, self.height)
        cr.stroke()

    def do_simple_paint(self, cr, bounds):
        cr.identity_matrix()

        self.clear_background(cr)
        self.draw_day_headers(cr)
        self.draw_hour_headers(cr)
        self.draw_grid(cr)
        self.draw_events(cr)
        
        cr.save()
        cr.rectangle(self.day_width, self.hour_height,
                     self.width - self.day_width, self.height - self.hour_height)
        cr.clip()
        self.draw_marquee(cr)
        if (self.selected) and (self.selected in self.events):
            self.selection_handles (cr)
        cr.restore()
        
        self.draw_top_left_corner (cr)
        self.draw_comfort_lines(cr)

    def select_area(self, x, y, width, height, quantize=True):
        self.selected_start = self.point_to_datetime (x, y, quantize)
        # constrain selection to a single day
        self.selected_end = self.point_to_datetime(x, y + height, quantize)
        if self.selected_start == self.selected_end:
            self.selected_start = None
            self.selected_end = None

    def select_point(self, x, y):
        self.select_event(self.point_to_event(x, y))

    def select_event(self, event):
        self.configure_editor(event)
        self.selected = event
        self.changed(False)

    def configure_editor(self, event):
        if event:
            self.get_canvas().grab_focus(self)
            self.ti.set_text(event.description)
            self.editing = True
        else:
            self.editing = False

    def text_changed_cb(self):
        if not self.editing:
            return

        self.selected.description = self.ti.get_text()
        self.changed(False)

    def get_schedule(self, date):
        return self.model.get_events(date)

class CalendarItem(goocanvas.Group):

    __gtype_name__ = "CalendarItem"

    def __init__(self, undo, history, *args, **kwargs):
        goocanvas.Group.__init__(self, *args, **kwargs)
        self.schedule = CalendarBase(parent=self)
        self.scrolling = MouseCommandDispatcher(history, (DragCalendar,))
        self.scrolling.observe(self.schedule)
        self.dispatcher = MouseCommandDispatcher(
            undo,
            drag_commands = (SetEventStart,
                              SetEventEnd,
                              MoveEvent,
                              SelectArea),
            click_commands = (SelectPoint,))
        self.dispatcher.observe(self.schedule)

class SelectPoint(Command):

    @classmethod
    def create_for_point(cls, instance, point):
        return cls(instance, *point)

    def __init__(self, instance, x, y):
        self.instance = instance
        self.point = x, y
        self.selected = self.instance.selected
        self.selected_start = self.instance.selected_end
        self.selected_end = self.instance.selected_end

    def do(self):
        self.instance.select_point(*self.point)
        self.instance.selected_start = None
        self.instance.selected_end = None
        return True

    def undo(self):
        self.instance.select_event(self.selected)
        self.instance.selected_start = self.selected_start
        self.instance.selected_end = self.selected_end

class SelectArea(MouseCommand):

    @classmethod
    def can_do(cls, instance, abs):
        return True

    def __init__(self, instance, abs):
        self.instance = instance
        self.mdown = abs
        self.selected = self.instance.selected
        self.selected_start = self.instance.selected_start
        self.selected_end = self.instance.selected_end

    def do(self):
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
            self.shift)
        return True

    def undo(self):
        self.instance.select_event(self.selected)
        self.instance.selected_start = self.selected_start
        self.instance.selected_end = self.selected_end

class MoveEvent(MouseCommand):

    @classmethod
    def create_for_point(cls, instance, abs):
        event = instance.point_to_event(*abs)
        if event:
            return MoveEvent(instance, event, abs)

    def __init__(self, instance, event, abs):
        self.instance = instance
        self.mdown = abs
        self.start, self.end = event.start, event.end
        self.event = event
        self.offset = instance.day_width / 2

    def do(self):
        x, y = self.rel
        delta = self.instance.point_to_timedelta(int(x + self.offset), y, self.shift)
        self.event.end = self.end + delta
        self.event.start = self.start + delta
        return True

    def undo(self):
        self.event.start, self.event.end = self.start, self.end

class SetEventStart(MouseCommand):

    @classmethod
    def can_do(cls, instance, abs):
        return instance.point_in_handle(*abs) == 1

    def __init__(self, instance, abs):
        self.mdown = abs
        self.instance = instance
        self.event = instance.selected
        self.pos = self.event.start

    def do(self):
        self.event.start = min(
            self.instance.point_to_datetime(self.mdown[0], self.abs[1],
                self.shift),
            self.event.end)
        return True

    def undo(self):
        self.event.start = self.pos

class SetEventEnd(MouseCommand):

    @classmethod
    def can_do(cls, instance, abs):
        return instance.point_in_handle(*abs) == 2

    def __init__(self, instance, abs):
        self.mdown = abs
        self.instance = instance
        self.event = instance.selected
        self.pos = self.event.end

    def do(self):
        self.event.end = max(
            self.instance.point_to_datetime(self.mdown[0], self.abs[1],
                self.shift),
            self.event.start)
        return True

    def undo(self):
        self.event.end = self.pos

class DragCalendar(MouseCommand):

    @classmethod
    def can_do(cls, instance, abs):
        return (instance.x <= abs[0] <= instance.width and 
                instance.y <= abs[1] <= instance.hour_height)


    def __init__(self, instance, abs):
        self.mdown = abs
        self.instance = instance
        self.pos = instance.date
        self.flick_pos = None
        self.scroller = KineticScrollAnimation(30, finished_cb=self._upate_pos)

    def do(self):
        if self.flick_pos is None:
            self.instance.date = self.pos - (self.rel[0] / self.instance.day_width)
        else:
            self.instance.date = self.flick_pos

    def undo(self):
        self.instance.date = self.pos

    def flick_start(self):
        self.scroller.observe(self.instance)
        self.scroller.flick(self.flick_velocity[0] / self.instance.day_width)

    def flick_stop(self):
        self.scroller.stop()

    def _upate_pos(self):
        self.flick_pos = self.instance.date

class NewEvent(MenuCommand):

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
        self.app.schedule.select_event(self.event)
        return True

    def undo(self):
        self.app.model.del_event(self.event)
        return True

class DelEvent(MenuCommand):

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
        self.app.schedule.select_event(None)
        return True

    def undo(self):
        self.app.model.add_event(self.event)
        self.app.schedule.select_event(self.event)
        return True

class GoToToday(MenuCommand):

    label = _("Today")
    tooltip = _("Scroll to current day")

    @classmethod
    def can_do(cls, app):
        return True

    def configure(self):
        self.today = datetime.datetime.today().toordinal()
        self.date = self.app.schedule.date

    def do(self):
        self.app.schedule.date = self.today

    def undo(self):
        self.ap.schedule.date = self.date

class GoToSelected(MenuCommand):

    label = _("Selected")
    tooltip = _("Scroll to the currently-selected item")

    @classmethod
    def can_do(cls, app):
        return bool(app.schedule.selected)

    def configure(self):
        self.selected = self.app.schedule.selected
        self.date = self.app.schedule.date

    def do(self):
        self.app.schedule.date = self.selected.start.toordinal()

    def undo(self):
        self.app.schedule.date = self.date
        
class App(object):

    ui = """
    <ui>
        <toolbar name="mainToolBar">
            <toolitem action="Undo"/>
            <toolitem action="Redo"/>
            <separator />
            <toolitem action="NewEvent"/>
            <toolitem action="DelEvent"/>
            <separator />
            <toolitem action="Back"/>
            <toolitem action="Forward"/>
            <toolitem action="GoToToday"/>
            <toolitem action="GoToSelected"/>
        </toolbar>
    </ui>"""


    def __init__(self):
        self.undo = UndoStack()
        self.history = UndoStack(
            gtk.Action("Back", None, None, gtk.STOCK_GO_BACK),
            gtk.Action("Forward", None, None, gtk.STOCK_GO_FORWARD))
        w = gtk.Window()
        w.connect("destroy", gtk.main_quit)
        vbox = gtk.VBox()
        hbox = gtk.HBox()
        canvas = goocanvas.Canvas()
        self.calendar_item = CalendarItem(self.undo, self.history)
        self.schedule = self.calendar_item.schedule
        self.model = self.schedule.model
        canvas.get_root_item().add_child(self.calendar_item)
        canvas.set_size_request(settings.width, settings.height)
        canvas.show()
        canvas.connect("size-allocate", self.size_allocate_cb)
        hbox.pack_start(canvas)
        self.scrollbar = gtk.VScrollbar()
        hbox.pack_start(self.scrollbar, False, False)
        vbox.pack_end(hbox)

        self.scrollbar.connect("value-changed", self.update_scroll_pos)
        self.update_scroll_adjustment(None)
        self.scrollbar.set_value(datetime.datetime.now().hour *
            self.schedule.hour_height)

        uiman = gtk.UIManager ()
        actiongroup = MenuCommand.create_action_group(self)
        actiongroup.add_action(self.undo.undo_action)
        actiongroup.add_action(self.undo.redo_action)
        actiongroup.add_action(self.history.undo_action)
        actiongroup.add_action(self.history.redo_action)

        self.undo.undo_action.connect("activate", self.update_actions)
        self.undo.redo_action.connect("activate", self.update_actions)
        uiman.insert_action_group(actiongroup)
        uiman.add_ui_from_string(self.ui)
        toolbar = uiman.get_widget("/mainToolBar")
        vbox.pack_start (toolbar, False, False)

        w.add(vbox)
        w.show_all()
        self.schedule.connect("notify::selected", self.update_actions)
        self.schedule.connect("notify::selected_start", self.update_actions)
        self.schedule.connect("notify::selected_end", self.update_actions)
        self.schedule.connect("notify::height", self.update_scroll_adjustment)

    def update_scroll_pos(self, scrollbar):
        self.schedule.y_scroll_offset = -scrollbar.get_value()

    def update_scroll_adjustment(self, *unused):
        self.scrollbar.set_range(0, self.schedule.hour_height * 25 -
            self.schedule.height)

    def size_allocate_cb(self, canvas, allocation):
        self.schedule.width = allocation.width
        self.schedule.height = allocation.height
        canvas.props.x2 = allocation.width
        canvas.props.y2 = allocation.height

    def update_actions(self, *unused):
        MenuCommand.update_actions(self)

    def run(self):
        self.load()
        gtk.main()
        self.save()
        gobject.timeout_add(60000, self.save)
        
    path = os.path.expanduser("~/.calendar_data")
    
    def load(self):
        self.model.load(self.path)

    def save(self):
        self.model.save(self.path)
        return True

    def do_command(self, unused_action, command):
        cmd = command(self)
        cmd.configure()
        if cmd.do():
            self.undo.commit(cmd)

if __name__ == "__main__":
    App().run()
