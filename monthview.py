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
from behavior import Animation

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

    def get_week_pixel_offset(self):
        return self.header_height - ((self.date / 7) * self.day_height % self.day_height)

    def weeks_visible(self):
        return int(self.height / self.day_height) + 1

    def paint(self, cr):
        cr.rectangle(0, 0, self.width, self.height)
        cr.set_source(settings.grid_line_color)
        cr.fill()
        
        ordinal = int(self.date) - (int(self.date) % 7) + 1
        cr.set_source(settings.text_color)
        y = self.get_week_pixel_offset()
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
                ordinal += 1
            y += self.day_height

        x = 0
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
