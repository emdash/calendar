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

import pangocairo
import pango
import settings

class Area(object):

    x = 0
    y = 0
    width = 0
    height = 0
    fill_color = None
    stroke_color = None
    center = (0, 0)

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.bounds = (self.x, self.y,
                       self.x + self.width, self.y + self.height)
        self.center = (self.x + (self.width / 2),
                       self.y + (self.height / 2))

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

def text_function(func):
    
    def draw_pango_text(cr, text, x, y, width, height, color):
        cr.rectangle(x, y, width, height)
        cr.clip()
        cr.set_source(color)
        pcr = pangocairo.CairoContext(cr)
        lyt = create_layout(pcr, text, width)
        func(cr, lyt, x, y, width, height)
        pcr.show_layout(lyt)
        return lyt

    return subpath(draw_pango_text)

@text_function
def centered_text(cr, lyt, x, y, width, height):
    lyt.set_alignment(pango.ALIGN_CENTER)
    tw, th = lyt.get_pixel_size()
    cr.move_to(x, y + height / 2 - th / 2)

@text_function
def left_aligned_text(cr, lyt, x, y, width, height):
    cr.move_to(x, y)

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
    cr.restore()

@subpath
def filled_box(cr, x, y, width, height, fill, stroke):
    cr.rectangle(x, y, width, height)
    cr.set_source(fill)
    cr.fill_preserve()
    cr.set_source(stroke)
    cr.stroke()

@subpath
def labeled_box(cr, x, y, text, width, height, bgcolor,
                stroke_color, text_color):
    filled_box(cr, x, y, width, height,
               bgcolor, stroke_color)
    cr.set_source(text_color)
    centered_text(cr, text, x, y, width, height, text_color)

def rect_to_bounds(x, y, width, height):
    return (x, y, x + width, y + height)

import math

@subpath
def upward_tab(cr, x, y, width, radius):
    x1, y1, x2, y2 = rect_to_bounds(x, y, width, radius)
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
def downward_tab(cr, x, y, width, radius):
    x1, y1, x2, y2 = rect_to_bounds(x, y, width, radius)
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
def upward_triangle(cr, x, y, width, height):
    cr.move_to(x + (width / 2), y)
    cr.line_to(x + width, y + height)
    cr.line_to(x, y + height)
    cr.line_to(x + (width / 2), y)
    cr.set_source(settings.handle_arrow_color)
    cr.fill()

@subpath
def downward_triangle(cr, x, y, width, height):
    cr.move_to(x, y)
    cr.line_to(x + width, y)
    cr.line_to(x + (width / 2), y + height)
    cr.line_to(x, y)
    cr.set_source(settings.handle_arrow_color)
    cr.fill()
