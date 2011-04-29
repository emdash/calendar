# Calendar, Graphical calendar applet with novel interface
#
#       shapes.py
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

"Cairo convenience routines"

import cairo
import pangocairo
import pango
import settings

class Area(object):

    x = 0
    y = 0
    width = 0
    height = 0
    center = (0, 0)

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        self.bounds = (self.x, self.y,
                       self.x + self.width, self.y + self.height)
        self.x1, self.y1, self.x2, self.y2 = self.bounds
        
        self.center = (self.x + (self.width / 2),
                       self.y + (self.height / 2))
        self.center_x, self.center_y = self.center

    def contains_point(self, point):
        return ((self.x1 <= point[0] <= self.x2) and
                (self.y1 <= point[1] <= self.y2))

    def contains_area(self, area):
        return (self.contains_point(area.x1, area.y1) and
                self.contains_point(area.x2, area.y2))

    def grow(self, xpad, ypad):
        return Area(self.x - xpad, self.y - ypad,
                    self.width + 2 * xpad,
                    self.height + 2 * ypad)

    def shrink(self, xpad, ypad):
        return self.grow(-xpad, -ypad)

    def scale(self, xfact, yfact):
        new_width = self.width * xfact
        new_height = self.height * yfact
        return Area(self.center_x -  new_width / 2,
                    self.center_y - new_height / 2,
                    new_width,
                    new_height)

    def above(self, spacing, height):
        return Area(self.x, self.y - spacing - height, self.width, height)

    def below(self, spacing, height):
        return Area(self.x, self.y2 + spacing, self.width, height)

    def empty(self):
        return self.width and self.height

    @classmethod
    def from_bounds(self, x1, y1, x2, y2):
        return Area(x1, y1, (x2 - x1), (y2 - y1))

def subpath(func):
    def subpath_impl(cr, *args):
        cr.save()
        ret = func(cr, *args)
        cr.restore()
        return ret
    return subpath_impl

def create_layout(pcr, text, width):
    lyt = pcr.create_layout()
    lyt.set_font_description(settings.default_font)
    lyt.set_text(text)
    lyt.set_width(pango.units_from_double(width))
    lyt.set_wrap(pango.WRAP_WORD_CHAR)
    return lyt

def get_cursor_pos(lyt, index):
    return [pango.units_to_double(x)
            for x in
            lyt.get_cursor_pos(index)[0]]

@subpath
def draw_cursor(cr, lyt, area, index):
    cr.set_line_width(1)
    cr.set_source(settings.cursor_color)
    cr.set_antialias(cairo.ANTIALIAS_NONE)
    x, y, width, height = get_cursor_pos(lyt, index)
    cr.move_to(area.x + x + 2, area.y + y)
    cr.line_to(area.x + x + 2, area.y + y + height)
    cr.stroke()

def text_height(cr, width, text):
    pcr = pangocairo.CairoContext(cr)
    lyt = create_layout(pcr, text, width)
    return lyt.get_pixel_size()[1]

def text_function(func):
    
    def draw_pango_text(cr, area, text, color, cursor_pos=-1):
        cr.rectangle(area.x, area.y, area.width, area.height)
        cr.clip()
        cr.set_source(color)
        pcr = pangocairo.CairoContext(cr)
        lyt = create_layout(pcr, text, area.width)
        func(cr, lyt, area)
        pcr.show_layout(lyt)
        if cursor_pos != -1:
            draw_cursor(cr, lyt, area, cursor_pos)
        return lyt

    return subpath(draw_pango_text)

@text_function
def centered_text(cr, lyt, area):
    lyt.set_alignment(pango.ALIGN_CENTER)
    tw, th = lyt.get_pixel_size()
    cr.move_to(area.x, area.center_y - th / 2)

@text_function
def left_aligned_text(cr, lyt, area):
    cr.move_to(area.x, area.y)

@text_function
def right_aligned_text(cr, lyt, area):
    lyt.set_alignment(pango.ALIGN_RIGHT)
    cr.move_to(area.x, area.y)

@subpath
def text_above(cr, text, x, y, width):
    tw, th = cr.text_extents(text)[2:4]
    tw = min(width, tw)
    th = th
    cr.rectangle(x, y - th, width, th)
    cr.clip()
    cr.move_to (x + (width / 2) - tw / 2,
                y)
    cr.show_text(text)

@subpath
def text_below(cr, text, x, y, width):
    tw, th = cr.text_extents(text)[2:4]
    tw = min(width, tw)
    th = th
    cr.rectangle(x, y, width, th)
    cr.clip()
    cr.move_to (x + (width / 2) - tw / 2,
                y + th)
    cr.show_text(text)

@subpath
def filled_box(cr, area, fill, stroke=None):
    cr.rectangle(area.x, area.y, area.width, area.height)
    cr.set_source(fill)
    cr.fill_preserve()
    if stroke:
        cr.set_source(stroke)
        cr.stroke()

@subpath
def labeled_box(cr, area, text, bgcolor, stroke_color, text_color):
    filled_box(cr, area, bgcolor, stroke_color)
    centered_text(cr, area, text, text_color)

def rect_to_bounds(x, y, width, height):
    return (x, y, x + width, y + height)

import math

@subpath
def upward_tab(cr, area):
    x1, y1, x2, y2 = area.bounds
    radius = area.height
    cr.move_to(x1, y2)
    cr.new_sub_path()
    cr.arc(x1 + radius, y2, radius, math.pi, 1.5 * math.pi)
    cr.line_to(x2 - radius, y1)
    cr.new_sub_path()
    cr.arc(x2 - radius, y2, radius, 1.5 * math.pi, 0)
    cr.line_to(x1, y2)
    cr.set_source(settings.handle_bg_color)
    cr.fill()

@subpath
def downward_tab(cr, area):
    x1, y1, x2, y2 = area.bounds
    radius = area.height
    cr.move_to(x2, y1)
    cr.new_sub_path()
    cr.arc(x2 - radius, y1, radius, 0, 0.5 * math.pi)
    cr.line_to(x1 + radius, y2)
    cr.new_sub_path()
    cr.arc(x1 + radius, y1, radius, 0.5 * math.pi, math.pi)
    cr.line_to(x2, y1)
    cr.set_source(settings.handle_bg_color)
    cr.fill()

@subpath
def rounded_rect(cr, area, r):
    x = area.x
    y = area.y
    w = area.width
    h = area.height

    "Draw a rounded rectangle"
    #   A****BQ
    #  H      C
    #  *      *
    #  G      D
    #   F****E

    cr.move_to(x+r,y)                      # Move to A
    cr.line_to(x+w-r,y)                    # Straight line to B
    cr.curve_to(x+w,y,x+w,y,x+w,y+r)       # Curve to C, Control points are both at Q
    cr.line_to(x+w,y+h-r)                  # Move to D
    cr.curve_to(x+w,y+h,x+w,y+h,x+w-r,y+h) # Curve to E
    cr.line_to(x+r,y+h)                    # Line to F
    cr.curve_to(x,y+h,x,y+h,x,y+h-r)       # Curve to G
    cr.line_to(x,y+r)                      # Line to H
    cr.curve_to(x,y,x,y,x+r,y)             # Curve to A
    return

@subpath
def upward_triangle(cr, area):
    cr.move_to(area.center_x, area.y)
    cr.line_to(area.x2, area.y2)
    cr.line_to(area.x, area.y2)
    cr.line_to(area.center_x, area.y)
    cr.set_source(settings.handle_arrow_color)
    cr.fill()

@subpath
def downward_triangle(cr, area):
    cr.move_to(area.x1, area.y1)
    cr.line_to(area.x2, area.y1)
    cr.line_to(area.center_x, area.y2)
    cr.line_to(area.x1, area.y1)
    cr.set_source(settings.handle_arrow_color)
    cr.fill()
