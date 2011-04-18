# Calendar, Graphical calendar applet with novel interface
#
#       monthview.py
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
from calendarwidget import DateNotVisible
from calendarwidget import KineticScrollAnimation

today = datetime.date.today()

day_names = []
d = today.toordinal() - today.weekday()
for i in xrange(7):
    day_names.append(datetime.date.fromordinal(d + i).strftime("%a"))

class MonthView(CalendarWidget):

    @property
    def day_width(self):
        return self.width / 7

    header_height = 30
    day_height = 75

    def __init__(self, info, undo, history):
        CalendarWidget.__init__(self, info)
        self.undo = undo
        self.history = history
        self.dispatcher = MouseCommandDispatcher(
            history,
            drag_commands = (DragCalendarVertical,))
        self.dispatcher.observe(self)

    def get_week_pixel_offset(self):
        return self.header_height - ((self.date / 7) * self.day_height % self.day_height)

    def weeks_visible(self):
        return int(self.height / self.day_height) + 1

    def dates_visible(self):
        ordinal = int(self.date) - (int(self.date) % 7) + 1
        return (datetime.date.fromordinal(ordinal),
                datetime.date.fromordinal(ordinal + 7 * self.weeks_visible()))

    def get_events_by_date(self):
        events = {}
        for event, occurrence in self.info.model.timedOccurrences(*self.dates_visible()):
            if not (occurrence.date in events):
                events[occurrence.date] = []
            events[occurrence.date].append(event)
        return events

    def draw_events(self, cr, x, y, events):
        if not events:
            return
        
        cr.save()
        cr.rectangle(x, y, self.day_width, self.day_height)
        cr.clip()

        y += 10
        
        for e in events:
            area = shapes.Area(x, y, self.day_width, 20).shrink(3, 3)
            shapes.filled_box(
                cr,
                area,
                settings.default_event_bg_color,
                settings.default_event_bg_color)
            
            shapes.left_aligned_text(
                cr,
                area,
                e.description,
                settings.default_event_text_color)

            y += 20
        
        cr.restore()

    def paint(self, cr):
        cr.rectangle(0, 0, self.width, self.height)
        cr.set_source(settings.grid_line_color)
        cr.fill_preserve()
        cr.set_source(settings.comfort_line_color)
        cr.stroke()
        
        ordinal = int(self.date) - (int(self.date) % 7) + 1
        cr.set_source(settings.text_color)
        y = self.get_week_pixel_offset()

        events = self.get_events_by_date()
        
        for row in xrange(self.weeks_visible()):
            for col in xrange(7):
                x = self.day_width * col
                date = datetime.date.fromordinal(ordinal)
                area = shapes.Area(x, y, self.day_width, self.day_height).shrink(1, 1)
                if (date.month % 2) == 0:
                    fill_color = settings.weekday_bg_color
                else:
                    fill_color = settings.weekend_bg_color
                if date.day == 1:
                    fmt = "%b %d"
                else:
                    fmt = "%d"
                shapes.filled_box(
                    cr,
                    area,
                    fill_color)
                shapes.right_aligned_text(
                    cr,
                    area,
                    date.strftime(fmt),
                    settings.text_color)
                self.draw_events(cr, x, y, events.get(date, None))
                ordinal += 1
            y += self.day_height

        x = 0
        cr.set_antialias(cairo.ANTIALIAS_NONE)
        for i in xrange(7):
            area = shapes.Area(x, 0, self.day_width, self.header_height)
            shapes.labeled_box(
                cr,
                area,
                day_names[i],
                settings.grid_bg_color,
                settings.comfort_line_color,
                settings.text_color)
            x += self.day_width

class DragCalendarVertical(MouseCommand):

    cursor = gtk.gdk.Cursor(gtk.gdk.HAND1)

    @classmethod
    def can_do(cls, instance, abs):
        return (abs[1] >= instance.header_height)

    def __init__(self, instance, abs):
        self.mdown = abs
        self.instance = instance
        self.pos = instance.date
        self.flick_pos = None
        self.scroller = KineticScrollAnimation(30, finished_cb=self._upate_pos)

    def do(self):
        if self.flick_pos is None:
            self.instance.info.date = (self.pos - (self.rel[1] * 7 / self.instance.scale) /
                                  self.instance.day_height)
        else:
            self.instance.info.date = self.flick_pos

    def undo(self):
        self.instance.date = self.pos

    def flick_start(self):
        self.scroller.observe(self.instance)
        self.scroller.flick(self.flick_velocity[1] * 7 / self.instance.day_height)

    def flick_stop(self):
        self.scroller.stop()

    def _upate_pos(self):
        self.flick_pos = self.instance.date
