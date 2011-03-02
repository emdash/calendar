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
import recurrence
import settings
import shapes
import parser
import os

#TODO: repeating events
#TODO: event alarms
#TODO: sync with google calendar
#TODO: sync with facebook calendar
#TODO: sync with evolution ??
#TODO: message area (gtk-info bar?)
#TODO: go to next {week, month}
#TODO: make calendar view "roll" so that sunday is always on the left
#TODO: change cursors
#TODO: port away from goocanvas ?
#TODO: allow multiple selections
#TODO: do something sane when events overlap
#TODO: specify working day (hide unused hours)
#TODO: tomboy integration

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

class DateNotVisible(Exception):

    pass

def scaled_getter(name):
    def scaled_getter_impl(self):
        val = getattr(self, name)
        return max(val, val / self.scale)
    return scaled_getter_impl

def scaled_setter(name):
    def scaled_setter_impl(self, value):
        setattr(self, name, value)
    return scaled_setter_impl

def scaled_property(name):
    name = "_" + name
    return gobject.property(
        scaled_getter(name),
        scaled_setter(name),
        type=float)

class WeekView(goocanvas.ItemSimple, goocanvas.Item):

    __gtype_name__ = "WeekView"
    
    scale = gobject.property(type=float, default=1.0)

    x = gobject.property(type=int, default=0)
    y = gobject.property(type=int, default=0)

    _width = settings.width
    _height = settings.height
    _day_width = settings.day_width
    _y_scroll_offset = 0
    
    width = scaled_property("width")
    height = scaled_property("height")
    y_scroll_offset = scaled_property("y_scroll_offset")
    
    hour_height = gobject.property(type=float, default=settings.hour_height)
    day_width = gobject.property(type=float, default=settings.day_width)
    
    date = gobject.property(type=float,
        default=datetime.date.today().toordinal())
    selected = gobject.property(type=gobject.TYPE_PYOBJECT)
    selection_recurrence = gobject.property(type=gobject.TYPE_PYOBJECT)
    handle_locations = None

    def __init__(self, *args, **kwargs):
        goocanvas.ItemSimple.__init__(self, *args, **kwargs)
        self.editing = False
                
        self.model = Schedule("schedule.csv")
        self.model.set_changed_cb(self.model_changed)
        self.connect("notify", self.do_notify)
        self.occurrences = {}
        self.selected = None
        self.font_desc = pango.FontDescription("Sans 8")
        self.cursor_showing = True
        self.ti = TextInput(self.text_changed_cb)
        self.ti.observe(self)
        gobject.timeout_add(500, self._blink_cursor)
        self.selection_recurrence = recurrence.Period(
            recurrence.Daily(datetime.date.today(), 2),
            datetime.time(14),
            datetime.time(16))

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

    def days_visible(self):
        return int(self.width / self.day_width)

    def point_to_datetime(self, x, y, snap=True):
        x /= self.scale
        y /= self.scale
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
        x /= self.scale
        y /= self.scale
        day = int(x / self.day_width)
        if y < 0:
            day += 1
        minute = (day * 24 * 60) + quantize(int((y / self.hour_height) * 60), 15)

        return datetime.timedelta(minutes=minute)

    def date_visible(self, dt):
        return (self.date - 1 <
                dt.toordinal() <
                self.date + self.days_visible())

    def datetime_to_point(self, dt):
        if not self.date_visible(dt):
            raise DateNotVisible(dt)
        
        return (
            ((dt.toordinal() - self.date + 1) * self.day_width),
            (dt.hour + 1 + dt.minute / 60.0)
            * self.hour_height + self.y_scroll_offset)

    def area_from_start_end(self, start, end):
        start = self.datetime_to_point(start)
        end = self.datetime_to_point(end)
        return shapes.Area(start[0], start[1], self.day_width, end[1] - start[1])

    def point_to_occurrence(self, x, y):
        point = (x / self.scale, y / self.scale)
        for period, (event, area) in self.occurrences.iteritems():
            if area.contains_point(point):
                return event, period, area

        return None

    def point_to_event(self, x, y):
        ret = self.point_to_occurrence(x, y)
        return ret[0] if ret else None

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
        area = self.occurrences[self.selected][1]
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
        point = (x / self.scale, y / self.scale)

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
        for i in xrange(1, 26):
            cr.move_to(self.day_width, self.y_scroll_offset + i * self.hour_height)
            cr.line_to(self.width, self.y_scroll_offset + i * self.hour_height)
            cr.stroke()

        x = self.get_week_pixel_offset()
        max_height = min(self.hour_height * 25 + self.y_scroll_offset, self.height)

        for i in xrange(0, (self.days_visible()) + 1):
            # draw vertical lines
            x += self.day_width
            cr.move_to (x, self.hour_height)
            cr.line_to (x, max_height)
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

        for i in xrange(0, (self.days_visible()) + 1):
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

    def draw_event(self, cr, event, period):
        try:
            area = self.area_from_start_end(period.start, period.end).shrink(2, 0)
        except DateNotVisible:
            return
        
        shapes.filled_box(cr, area, settings.default_event_bg_color)

        if (period == self.selected) and (self.cursor_showing):
            cursor_pos = self.ti.get_cursor_pos()
        else:
            cursor_pos = -1

        lyt = shapes.left_aligned_text(cr, area, event.description,
                                       settings.default_event_text_color,
                                       cursor_pos)
           
        self.occurrences[period] = (event, area)

    def dates_visible(self):
        s = datetime.date.fromordinal(int(self.date))
        e = datetime.date.fromordinal(int(self.date) + self.days_visible())
        return s, e

    def draw_events(self, cr):
        self.occurrences = {}
        for evt, period in self.model.timedOccurrences(*self.dates_visible()):
            self.draw_event(cr, evt, period)
        cr.restore()

    def draw_marquee(self, cr):
        if not self.selection_recurrence:
            return
        s, e = self.dates_visible()
        for instance in self.selection_recurrence.timedOccurrences(s, e):

            try:
                area = self.area_from_start_end(instance.start,
                                                instance.end).shrink(2, 0)
            except DateNotVisible:
                return

            shapes.filled_box(cr, area, settings.marquee_fill_color)
            cr.set_source(settings.marquee_text_color)

            text = instance.start.strftime ("%X")
            shapes.text_above(cr, text, area.x, area.y - 2, area.width)
        
            text = instance.end.strftime ("%X")
            shapes.text_below(cr, text, area.x, area.y2 + 2, area.width)

            duration = instance.duration
            m = int (duration.seconds / 60) % 60
            h = int (duration.seconds / 60 / 60)

            text = "%dh %dm" % (h, m)
            shapes.centered_text(cr, area, text, settings.text_color)

    def draw_top_left_corner(self, cr):
        area = shapes.Area(0, 0, self.day_width, self.hour_height)

        shapes.labeled_box(
            cr,
            area,
            datetime.date.fromordinal(int(self.date + 1)).strftime("%x"),
            settings.corner_bg_color,
            settings.heading_outline_color,
            settings.text_color)

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
        cr.scale(self.scale, self.scale)

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
        if (self.selected) and (self.selected in self.occurrences):
            self.selection_handles (cr)
        cr.restore()
        
        self.draw_top_left_corner (cr)
        self.draw_comfort_lines(cr)

    def select_area(self, x, y, width, height, quantize=True):
        try:
            start = self.point_to_datetime (x, y, quantize)
            end = self.point_to_datetime(x + width, y + height, quantize)
        except DateNotVisible:
            return

        start_date = datetime.date(start.year, start.month, start.day)
        end_date = datetime.date(end.year, end.month, end.day)
        start_time = datetime.time(start.hour, start.minute)
        end_time = datetime.time(end.hour, end.minute)

        if (end_date - start_date).days < 4:
            self.selection_recurrence = recurrence.Period(
                recurrence.DateSet(*recurrence.dateRange(start_date, end_date)),
                start_time,
                end_time)
        else:
            self.selection_recurrence = recurrence.Period(
                recurrence.Until(recurrence.Daily(start_date, 1), end_date),
                start_time,
                end_time)
        
    def select_point(self, x, y):
        occurrence = self.point_to_occurrence(x, y)
        if occurrence:
            self.select_occurrence(occurrence[1])
        else:
            self.select_occurrence(None)

    def select_occurrence(self, occurrence):
        self.selected = occurrence
        if occurrence:
            self.configure_editor(self.occurrences[occurrence][0])
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

class WeekViewItem(goocanvas.Group):

    __gtype_name__ = "WeekViewItem"

    def __init__(self, undo, history, *args, **kwargs):
        goocanvas.Group.__init__(self, *args, **kwargs)
        self.weekview = WeekView(parent=self)
        self.scrolling = MouseCommandDispatcher(history, (DragCalendar,))
        self.scrolling.observe(self.weekview)
        self.dispatcher = MouseCommandDispatcher(
            undo,
            drag_commands = (SetEventStart,
                              SetEventEnd,
                              MoveEvent,
                              SelectArea),
            click_commands = (SelectPoint,))
        self.dispatcher.observe(self.weekview)

class SelectPoint(Command):

    @classmethod
    def create_for_point(cls, instance, point):
        return cls(instance, *point)

    def __init__(self, instance, x, y):
        self.instance = instance
        self.point = x, y
        self.selected = self.instance.selected
        self.selection = self.instance.selection_recurrence

    def do(self):
        self.instance.select_point(*self.point)
        self.instance.selection_recurrence = None
        return True

    def undo(self):
        self.instance.select_occurrence(self.selected)
        self.instance.selection_recurrence = self.selection

class SelectArea(MouseCommand):

    @classmethod
    def can_do(cls, instance, abs):
        return True

    def __init__(self, instance, abs):
        self.instance = instance
        self.mdown = abs
        self.selected = self.instance.selected
        self.selection_recurrence = self.instance.selection_recurrence

    def do(self):
        self.instance.select_occurrence(None)

        # normalize to x, y, width, height with positive values
        x1 = min(self.mdown[0], self.abs[0])
        y1 = min(self.mdown[1], self.abs[1])
        x2 = max(self.mdown[0], self.abs[0])
        y2 = max(self.mdown[1], self.abs[1])
        width = x2 - x1
        height = y2 - y1

        # constrain selection to the day where the mouse was first clicked.
        self.instance.select_area (x1, y1, width, height,
            self.shift)
        return True

    def undo(self):
        self.instance.select_occurrence(self.selected)
        self.instance.selection_recurrence = self.selection_recurrence

class SelectRecurrence(Command):

    def __init__(self, app, text):
        self.app = app
        self.selected = app.weekview.selected
        self.old = app.weekview.selection_recurrence

        self.new = parser.parse(text)
        self.do()

    def do(self):
        self.app.weekview.selection_recurrence = self.new
        self.app.weekview.selected = None

    def undo(self):
        self.app.weekview.selected = self.selected
        self.app.weekview.selection_recurrence = self.old

class MoveEvent(MouseCommand):

    @classmethod
    def create_for_point(cls, instance, abs):
        event = instance.point_to_event(*abs)
        if event:
            return MoveEvent(instance, event, abs)

    def __init__(self, instance, event, abs):
        self.instance = instance
        self.mdown = abs
        self.old = event.recurrence
        self.event = event
        self.offset = instance.day_width / 2

    def do(self):
        x, y = self.rel
        delta = self.instance.point_to_timedelta(int(x + self.offset), y, self.shift)
        self.event.recurrence = self.old + delta
        return True

    def undo(self):
        self.event.recurrence = self.old

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
        return (instance.x <= abs[0] / instance.scale <= instance.width and 
                instance.y <= abs[1] / instance.scale <= instance.hour_height)


    def __init__(self, instance, abs):
        self.mdown = abs
        self.instance = instance
        self.pos = instance.date
        self.flick_pos = None
        self.scroller = KineticScrollAnimation(30, finished_cb=self._upate_pos)

    def do(self):
        if self.flick_pos is None:
            self.instance.date = (self.pos - (self.rel[0] / self.instance.scale) /
                                  self.instance.day_width)
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
        return app.weekview.selection_recurrence != None
    
    def configure(self):
        self.selection = self.app.weekview.selection_recurrence
        self.event = Event(self.selection, "New Event")

    def do(self):
        self.app.model.add_event(self.event)
        self.app.weekview.selection_recurrence = None
        return True

    def undo(self):
        self.app.model.del_event(self.event)
        self.app.weekview.selection_recurrence = self.selection
        self.app.weekview.selected = None
        return True

class DelEvent(MenuCommand):

    label = _("Delete Event")
    tooltip = _("Delete selected events")
    stockid = gtk.STOCK_DELETE

    @classmethod
    def can_do(cls, app):
        return app.weekview.selected != None

    def configure(self):
        self.selected = self.app.weekview.selected
        self.event = self.app.weekview.occurrence[self.selected][0]

    def do(self):
        self.app.model.del_event(self.event)
        self.app.weekview.select_occurrence(None)
        return True

    def undo(self):
        self.app.model.add_event(self.event)
        self.app.weekview.select_occurrence(self.selected)
        return True

class GoToToday(MenuCommand):

    label = _("Today")
    tooltip = _("Scroll to current day")

    @classmethod
    def can_do(cls, app):
        return True

    def configure(self):
        self.today = datetime.datetime.today().toordinal()
        self.date = self.app.weekview.date

    def do(self):
        self.app.weekview.date = self.today

    def undo(self):
        self.ap.schedule.date = self.date

class GoToSelected(MenuCommand):

    label = _("Selected")
    tooltip = _("Scroll to the currently-selected item")

    @classmethod
    def can_do(cls, app):
        return bool(app.weekview.selected)

    def configure(self):
        self.selected = self.app.weekview.selected
        self.date = self.app.weekview.date

    def do(self):
        self.app.weekview.date = self.selected.start.toordinal()

    def undo(self):
        self.app.weekview.date = self.date

class ZoomIn(MenuCommand):

    label = _("Zoom In")
    stockid = gtk.STOCK_ZOOM_IN
    undoable = False

    def do(self):
        self.app.weekview.scale = min(self.app.weekview.scale + 0.10, 10)

class ZoomOut(MenuCommand):

    label = _("Zoom Out")
    stockid = gtk.STOCK_ZOOM_OUT
    undoable = False

    def do(self):
        self.app.weekview.scale = max(self.app.weekview.scale - 0.10, 0.1)

class SwitchViews(MenuCommand):

    label = _("Month View")
    undoable = False

    def do(self):
        self.app.weekview.props.visibility = goocanvas.ITEM_INVISIBLE
        
class App(object):

    ui = """
    <ui>
        <toolbar name="upperToolbar">
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
            <separator />
            <toolitem action="SwitchViews"/>
        </toolbar>
        <toolbar name="lowerToolbar">
           <toolitem action="ZoomIn"/>
           <toolitem action="ZoomOut"/>
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
        self.calendar_item = WeekViewItem(self.undo, self.history)
        self.weekview = self.calendar_item.weekview
        self.model = self.weekview.model
        canvas.get_root_item().add_child(self.calendar_item)
        canvas.set_size_request(settings.width, settings.height)
        canvas.show()
        canvas.connect("size-allocate", self.size_allocate_cb)
        hbox.pack_start(canvas)
        self.scrollbar = gtk.VScrollbar()
        hbox.pack_start(self.scrollbar, False, False)

        self.scrollbar.connect("value-changed", self.update_scroll_pos)
        self.update_scroll_adjustment(None)
        self.scrollbar.set_value(datetime.datetime.now().hour *
            self.weekview.hour_height)

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
        toolbar = uiman.get_widget("/upperToolbar")
        vbox.pack_start (toolbar, False, False)
        vbox.pack_start (hbox, True, True)
        toolbar = uiman.get_widget("/lowerToolbar")

        self.selection_entry = gtk.Entry()
        
        self.pack_toolbar_widget(toolbar, self.selection_entry)
        vbox.pack_start (toolbar, False, False)

        w.add(vbox)
        w.show_all()
        self.window = w
        self.weekview.connect("notify::selected", self.update_actions)
        self.weekview.connect("notify::selection_recurrence", self.update_actions)
        self.weekview.connect("notify::height", self.update_scroll_adjustment)
        self.weekview.connect("notify::scale", self.update_scroll_adjustment)
        self.selection_entry.connect("activate", self.selection_entry_activate_cb)
        self.selection_entry.connect("changed", self.selection_entry_changed_cb)

    def pack_toolbar_widget(self, toolbar, widget):
        toolitem = gtk.ToolItem()
        toolitem.add(widget)
        toolitem.set_expand(True)
        widget.show()
        toolitem.show()
        toolbar.add(toolitem)

    dont_update_entry = False

    def selection_entry_activate_cb(self, entry):
        self.dont_update_entry = True
        try:
            self.undo.commit(SelectRecurrence(self, self.selection_entry.get_text()))
        except Exception, e:
            print e
            self.selection_entry.set_icon_from_stock(1, gtk.STOCK_DIALOG_WARNING)
        self.dont_update_entry = False

    def selection_entry_changed_cb(self, entry):
        self.selection_entry.set_icon_from_stock(1, None)

    def update_scroll_pos(self, scrollbar):
        self.weekview.y_scroll_offset = -scrollbar.get_value()

    def update_scroll_adjustment(self, *unused):
        self.scrollbar.set_range(0, self.weekview.hour_height * 25 -
            self.weekview.height)

    def size_allocate_cb(self, canvas, allocation):
        self.weekview.width = allocation.width
        self.weekview.height = allocation.height
        canvas.props.x2 = allocation.width
        canvas.props.y2 = allocation.height

    def update_actions(self, *unused):
        MenuCommand.update_actions(self)
        if self.dont_update_entry:
            return
        if not (self.weekview.selection_recurrence is None):
            text = self.weekview.selection_recurrence.toEnglish()
        else:
            text = ""
        self.selection_entry.set_text(text)
            
    def run(self):
        self.load()
        gtk.main()
        self.save()
        gobject.timeout_add(60000, self.save)

    def quit(self):
        self.window.destroy()
        gtk.main_quit()
        
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
