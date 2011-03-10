# Calendar, Graphical calendar applet with novel interface
#
#       settings.py
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

import cairo
import pango

## general options

width = 600
height = 400
day_width = width / 8
hour_height = 50
default_font = pango.FontDescription("Sans 8")

## colors

text_color = cairo.SolidPattern(0, 0, 0, .75)
cursor_color = cairo.SolidPattern(0, 0, 0, 1)

# grid
grid_line_color = cairo.SolidPattern(1, 1, 1)
grid_bg_color = cairo.SolidPattern(0.8, 0.8, 0.8)
comfort_line_color = cairo.SolidPattern(0.55, 0.55, 0.55)

# headings
heading_outline_color = cairo.SolidPattern(1, 1, 1)
weekday_bg_color = cairo.SolidPattern(0.75, 0.85, 0.75)
weekend_bg_color = cairo.SolidPattern(0.75, 0.75, 0.85)
hour_heading_color = cairo.SolidPattern(0.75, 0.75, 0.75)
corner_bg_color = cairo.SolidPattern(0.75, 0.75, 0.75)

# selection
handle_bg_color = cairo.SolidPattern(0.0, 0.0, 0.0, 0.55)
handle_arrow_color = cairo.SolidPattern(1, 1, 1)
marquee_fill_color = cairo.SolidPattern(0, 0, 0, 0.25)
marquee_text_color = cairo.SolidPattern(0, 0, 0, 0.75)

# default event color
default_event_bg_color = cairo.SolidPattern(0.55, 0.55, 0.55)
default_event_text_color = cairo.SolidPattern(0, 0, 0)
