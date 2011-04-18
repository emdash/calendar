# Calendar, Graphical calendar applet with novel interface
#
#       weekview.py
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
import cairo
import gobject
import pango
import datetime
import math
import recurrence
import settings
import shapes
from behavior import TextInput
from command import Command, MouseCommand
from dispatcher import MouseCommandDispatcher
from schedule import Schedule

from calendarwidget import CalendarWidget, CalendarInfo, scaled_property
from calendarwidget import DateNotVisible, quantize, KineticScrollAnimation

class WeekViewBase(CalendarWidget):
    
    _day_width = settings.day_width
    hour_height = gobject.property(type=float, default=settings.hour_height)
    day_width = gobject.property(type=float, default=settings.day_width)
    
    def get_week_pixel_offset(self):
        return self.day_width - (self.date * self.day_width % self.day_width)

    def draw_comfort_lines(self, cr):
        cr.save()
        cr.set_line_width(2.0)
        cr.set_source(settings.comfort_line_color)
        cr.rectangle(0, 0, self.width, self.height)
        cr.stroke()
        cr.move_to(self.day_width, 0)
        cr.line_to(self.day_width, self.height)
        cr.stroke()
        cr.restore()

class DayHeader(WeekViewBase):

    def __init__(self, info, history, *args, **kwargs):
        WeekViewBase.__init__(self, info, *args, **kwargs)
        self.scrolling = MouseCommandDispatcher(
            history,
            (DragCalendarHorizontal,))
        self.scrolling.observe(self)
        self.set_size_request(600, int(30))

    def paint(self, cr):
        self.clear_background(cr)
        self.draw_day_headers(cr)
        self.draw_top_left_corner(cr)
        self.draw_comfort_lines(cr)
        
        cr.save()
        cr.rectangle(1, 0, self.width - 2, self.height / 2)
        cr.set_source(settings.gloss_gradient)
        m = cairo.Matrix()
        m.scale(1.0/self.width, 1.0/self.height)
        settings.gloss_gradient.set_matrix(m)
        cr.fill()
        cr.restore()


    def draw_day_header(self, cr, nth_day):
        x = self.get_week_pixel_offset() + nth_day * self.day_width
        leftmost_day = int(self.date)
        
        date = self.get_date(leftmost_day + nth_day)
        weekday = date.weekday()

        if weekday > 4:
            bgcolor = settings.weekday_bg_color
        else:
            bgcolor = settings.weekend_bg_color

        area = shapes.Area(x, 0, self.day_width, self.height)

        shapes.labeled_box(
            cr,
            area,
            date.strftime("%a\n%x"),
            bgcolor,
            settings.heading_outline_color,
            settings.text_color)

    def draw_day_headers(self, cr):
        cr.save()
        cr.rectangle(self.day_width, 0, self.width - self.day_width,
            self.height)
        cr.clip()

        for i in xrange(0, (self.days_visible()) + 1):
            self.draw_day_header(cr, i)
        cr.restore()
        
    def draw_top_left_corner(self, cr):
        area = shapes.Area(0, 0, self.day_width, self.height)

        shapes.labeled_box(
            cr,
            area,
            datetime.date.fromordinal(int(self.date + 1)).strftime("%x"),
            settings.corner_bg_color,
            settings.heading_outline_color,
            settings.text_color)

class UntimedEvents(WeekViewBase):

    __gtype_name__ = "UntimedEvents"

    def __init__(self, info, undo, *args, **kwargs):
        WeekViewBase.__init__(self, info, *args, **kwargs)
        self.info = info
        self.undo = undo
        self.set_size_request(600, 50)

    def sort_allday_events_by_date(self):
        events = {}
        

    def paint(self, cr):
        self.clear_background(cr)
        cr.set_source(settings.grid_line_color)
        cr.set_line_width(settings.grid_line_width)
        cr.set_antialias(cairo.ANTIALIAS_NONE)
        x = self.get_week_pixel_offset()
        for i in xrange(0, (self.days_visible()) + 1):
            # draw vertical lines
            x += self.day_width
            cr.move_to (x, 0)
            cr.line_to (x, self.height)
            cr.stroke()
        self.draw_comfort_lines(cr)

class TimedEvents(WeekViewBase):

    __gtype_name__ = "WeekView"

    x = gobject.property(type=int, default=0)
    y = gobject.property(type=int, default=0)
    
    _y_scroll_offset = 0
    
    height = scaled_property("height")
    y_scroll_offset = scaled_property("y_scroll_offset")
    
    handle_locations = None

    def __init__(self, info, undo, *args, **kwargs):
        WeekViewBase.__init__(self, info, *args, **kwargs)
        self.editing = False
        self.occurrences = {}
        self.selected = None
        self.font_desc = pango.FontDescription("Sans 8")
        self.cursor_showing = True
        self.ti = TextInput(self.text_changed_cb)
        self.ti.observe(self)
        gobject.timeout_add(500, self._blink_cursor)

        self.dispatcher = MouseCommandDispatcher(
            undo,
            drag_commands = (DragCalendarVertical,
                             SetEventStart,
                             SetEventEnd,
                             MoveEvent,
                             SelectArea),
            click_commands = (SelectPoint,))
        self.dispatcher.observe(self)

    def _blink_cursor(self):
        if not self.editing:
            return True
        self.cursor_showing = not self.cursor_showing
        self.queue_draw()
        return True

    def point_to_datetime(self, x, y, snap=True):
        x /= self.scale
        y /= self.scale
        hour = ((y + (- self.y_scroll_offset)) /
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
            (dt.hour + dt.minute / 60.0)
            * self.hour_height + self.y_scroll_offset)

    def area_from_start_end(self, start, end):
        start = self.datetime_to_point(start)
        end = self.datetime_to_point(end)
        return shapes.Area(start[0], start[1], self.day_width, end[1] - start[1])

    def point_to_occurrence(self, x, y):
        point = (x / self.scale, y / self.scale)
        for ordinal, (event, area, period) in self.occurrences.iteritems():
            if area.contains_point(point):
                return event, ordinal, area

        return None

    def point_to_event(self, x, y):
        ret = self.point_to_occurrence(x, y)
        return ret[0] if ret else None
        
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

    def draw_grid(self, cr):
        cr.save()
        cr.rectangle(0, 0, 
            self.width, self.height)
        cr.clip()

        cr.set_source(settings.grid_line_color)
        cr.set_line_width(settings.grid_line_width)
        cr.set_antialias(cairo.ANTIALIAS_NONE)
        for i in xrange(1, 25):
            cr.move_to(0, self.y_scroll_offset + i * self.hour_height)
            cr.line_to(self.width, self.y_scroll_offset + i * self.hour_height)
            cr.stroke()

        x = self.get_week_pixel_offset()
        max_height = min(self.hour_height * 24 + self.y_scroll_offset, self.height)

        for i in xrange(0, (self.days_visible()) + 1):
            # draw vertical lines
            x += self.day_width
            cr.move_to (x, 0)
            cr.line_to (x, max_height)
            cr.stroke()
        cr.restore()
        
    def draw_hour_header(self, cr, hour):
        area = shapes.Area(0,
                           hour * self.hour_height + self.y_scroll_offset,
                           self.day_width,
                           self.hour_height)
        
        shapes.centered_text(
            cr,
            area,
            "%2d:00" % hour,
            settings.text_color)

    def draw_hour_headers(self, cr):
        cr.save()
        cr.rectangle(0, 0, self.day_width, self.height)
        cr.clip()

        for i in range(0, 24):
            self.draw_hour_header(cr, i)

        cr.restore()

    def draw_event(self, cr, event, period):
        try:
            area = self.area_from_start_end(period.start, period.end)
        except DateNotVisible:
            return
        
        #shapes.filled_box(cr, area, settings.default_event_bg_color)
        shapes.rounded_rect(cr, area, 5)
        m = cairo.Matrix()
        m.scale(1.0/area.width, 1.0/area.height)
        m.translate(-area.x, -area.y)

        settings.default_event_bg_color.set_matrix(m)
        cr.set_source(settings.default_event_bg_color)
        cr.fill_preserve()
        #cr.set_line_width(1.0)
        cr.set_source(settings.default_event_outline_color)
        settings.default_event_outline_color.set_matrix(m)
        #cr.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        cr.stroke()

        if (self.selected and
            (event == self.selected[0]) and
            (period.ordinal == self.selected[1]) and
            (self.cursor_showing)):
            cursor_pos = self.ti.get_cursor_pos()
        else:
            cursor_pos = -1

        lyt = shapes.left_aligned_text(cr, area.shrink(1, 3), event.description,
                                       settings.default_event_text_color,
                                       cursor_pos)
           
        self.occurrences[(event, period.ordinal)] = (event, area, period)

    def dates_visible(self):
        s = datetime.date.fromordinal(int(self.date))
        e = datetime.date.fromordinal(int(self.date) + self.days_visible())
        return s, e

    def draw_events(self, cr):
        cr.save()
        cr.rectangle(self.day_width, 0, self.width - self.day_width, self.height)
        cr.clip()
        self.occurrences = {}
        for evt, period in self.model.timedOccurrences(*self.dates_visible()):
            if period.all_day:
                continue
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

    def paint(self, cr):
        cr.identity_matrix()
        cr.scale(self.scale, self.scale)

        self.clear_background(cr)
        self.draw_hour_headers(cr)
        self.draw_grid(cr)
        self.draw_events(cr)
        
        cr.save()
        cr.rectangle(self.day_width, 0,
                     self.width - self.day_width, self.height)
        cr.clip()
        self.draw_marquee(cr)
        if (self.selected) and (self.selected in self.occurrences):
            self.selection_handles (cr)
        cr.restore()
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
            self.info.selection_recurrence = recurrence.Period(
                recurrence.DateSet(*recurrence.dateRange(start_date, end_date)),
                start_time,
                end_time)
        else:
            self.info.selection_recurrence = recurrence.Period(
                recurrence.Until(recurrence.Daily(start_date, 1), end_date),
                start_time,
                end_time)
        
    def select_point(self, x, y):
        occurrence = self.point_to_occurrence(x, y)
        if occurrence:
            self.select_occurrence(occurrence[1])
        else:
            self.select_occurrence(None)

    def get_occurence_event(self, occurrence):
        try:
            return self.occurrences[occurrence][0]
        except KeyError:
            return None

    def select_occurrence(self, occurrence):
        self.info.selected = occurrence
        if occurrence:
            self.configure_editor(self.get_occurence_event(occurrence))
        self.queue_draw()

    def configure_editor(self, event):
        if event:
            self.grab_focus()
            self.ti.set_text(event.description)
            self.editing = True
        else:
            self.editing = False

    def text_changed_cb(self):
        if not self.editing:
            return

        self.get_occurence_event(self.selected).description = self.ti.get_text()
        self.queue_draw()

class WeekView(gtk.VBox):

    def __init__(self, info, undo, history):
        gtk.VBox.__init__(self)
        self.day_header = DayHeader(info, history)
        self.timed = TimedEvents(info, undo)
        self.untimed = UntimedEvents(info, history)
        pane = gtk.VPaned()
        pane.add(self.untimed)
        pane.add(self.timed)
        pane.show()
        self.pack_start(self.day_header, False, False)
        self.pack_start(pane, True, True)
        self.show()

class SelectPoint(Command):

    @classmethod
    def create_for_point(cls, instance, point):
        return cls(instance, *point)

    @classmethod
    def can_do(cls, instance, point):
        return True

    def __init__(self, instance, x, y):
        self.instance = instance
        self.point = x, y
        self.selected = self.instance.selected
        self.selection = self.instance.selection_recurrence

    def do(self):
        self.instance.select_point(*self.point)
        self.instance.info.selection_recurrence = None
        return True

    def undo(self):
        self.instance.select_occurrence(self.selected)
        self.instance.info.selection_recurrence = self.selection

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
        self.instance.info.selection_recurrence = self.selection_recurrence


class MoveEvent(MouseCommand):

    cursor = gtk.gdk.Cursor(gtk.gdk.HAND2)

    @classmethod
    def create_for_point(cls, instance, abs):
        event = instance.point_to_event(*abs)
        if event:
            return MoveEvent(instance, event, abs)

    @classmethod
    def can_do(cls, instance, abs):
        return not (instance.point_to_event(*abs) is None)

    def __init__(self, instance, event, abs):
        self.instance = instance
        self.selected = instance.selected
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
        self.instance.info.selected = self.selected

class SetEventStart(MouseCommand):

    cursor = gtk.gdk.Cursor(gtk.gdk.TOP_SIDE)

    @classmethod
    def can_do(cls, instance, abs):
        return instance.point_in_handle(*abs) == 1

    def __init__(self, instance, abs):
        self.mdown = abs
        self.instance = instance
        self.selected = instance.selected
        occurrence = instance.occurrences[self.selected][2]
        self.recurrence = occurrence.creator
        self.pos = self.recurrence.start

    def do(self):
        self.recurrence.start = min(
            self.instance.point_to_datetime(self.mdown[0], self.abs[1],
                self.shift).time(),
            self.recurrence.end)
        self.instance.queue_draw()
        return True

    def undo(self):
        self.recurrence.start = self.pos
        self.selected = self.selected

class SetEventEnd(MouseCommand):

    cursor = gtk.gdk.Cursor(gtk.gdk.BOTTOM_SIDE)

    @classmethod
    def can_do(cls, instance, abs):
        return instance.point_in_handle(*abs) == 2

    def __init__(self, instance, abs):
        self.mdown = abs
        self.instance = instance
        self.selected = instance.selected
        occurrence = instance.occurrences[self.selected][2]
        self.recurrence = occurrence.creator
        self.pos = self.recurrence.end

    def do(self):
        self.recurrence.end = max(
            self.instance.point_to_datetime(self.mdown[0], self.abs[1],
                self.shift).time(),
            self.recurrence.start)
        self.instance.queue_draw()
        return True

    def undo(self):
        self.recurrence.end = self.pos

class DragCalendarHorizontal(MouseCommand):

    cursor = gtk.gdk.Cursor(gtk.gdk.HAND1)

    @classmethod
    def can_do(cls, instance, abs):
        return (0 <= abs[0] / instance.scale <= instance.width and 
                0 <= abs[1] / instance.scale <= instance.hour_height)

    def __init__(self, instance, abs):
        self.mdown = abs
        self.instance = instance
        self.pos = instance.date
        self.flick_pos = None
        self.scroller = KineticScrollAnimation(30, finished_cb=self._upate_pos)

    def do(self):
        if self.flick_pos is None:
            self.instance.info.date = (self.pos - (self.rel[0] / self.instance.scale) /
                                  self.instance.day_width)
        else:
            self.instance.info.date = self.flick_pos

    def undo(self):
        self.instance.date = self.pos

    def flick_start(self):
        self.scroller.observe(self.instance)
        self.scroller.flick(self.flick_velocity[0] / self.instance.day_width)

    def flick_stop(self):
        self.scroller.stop()

    def _upate_pos(self):
        self.flick_pos = self.instance.date

class DragCalendarVertical(MouseCommand):

    undoable = False

    cursor = gtk.gdk.Cursor(gtk.gdk.HAND1)

    @classmethod
    def can_do(cls, instance, abs):
        return ((instance.x <= abs[0] <= instance.x + instance.day_width) and
                (abs[1] > instance.y + instance.hour_height))

    def __init__(self, instance, abs):
        self.instance = instance
        self.pos = self.instance.y_scroll_offset

    def do(self):
        self.instance.y_scroll_offset = max(
            -((self.instance.hour_height * 25) - self.instance.height),
            min(
                0, self.pos + self.rel[1]))
