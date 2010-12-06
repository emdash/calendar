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

def centered_text(cr, text, x, y, width, height):
    cr.save()
    cr.rectangle(x, y, width, height)
    cr.clip()
    tw, th = cr.text_extents(text)[2:4]
    tw = min(width, tw)
    th = min(height, th)
    cr.move_to (x + (width / 2) - tw / 2,
                y + (height / 2) + (th / 2))
    cr.show_text(text)
    cr.restore()

def text_above(cr, text, x, y, width):
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
        
def text_below(cr, text, x, y, width):
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

def filled_box(cr, x, y, width, height, fill, stroke):
    cr.save()
    cr.rectangle(x, y, width, height)
    cr.set_source(fill)
    cr.fill_preserve()
    cr.set_source(stroke)
    cr.stroke()
    cr.restore()
    
def labeled_box(cr, x, y, text, width, height, bgcolor,
                stroke_color, text_color):
    cr.save()
    filled_box(cr, x, y, width, height,
               bgcolor, stroke_color)
    cr.set_source(text_color)
    centered_text(cr, text, x, y, width, height)
    cr.restore()
