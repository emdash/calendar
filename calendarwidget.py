# Calendar, Graphical calendar applet with novel interface
#
#       calendarwidget.py
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
import settings
import datetime

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

class CustomWidget(gtk.DrawingArea):

    __gtype_name__ = "CustomWidget"

    scale = gobject.property(type=float, default=1.0)
    
    _width = settings.width
    _height = settings.height

    width = scaled_property("width")

    def __init__(self, *args, **kwargs):
        gtk.DrawingArea.__init__(self, *args, **kwargs)
        self.connect("size-allocate", self.size_allocate_cb)
        self.connect("expose-event", self.do_expose)
        self.connect("notify", self.do_notify)
        self.set_size_request(600, 400)
        self.set_events(gtk.gdk.ALL_EVENTS_MASK)
        self.props.can_focus = True
        
    def size_allocate_cb(self, widget, allocation):
        self.width = allocation.width
        self.height = allocation.height
        
    def do_notify(self, something, something_else):
        self.queue_draw()

    def do_expose(self, widget, event):
        self.paint(widget.window.cairo_create())

    def paint(self, cr):
        raise NotImplemented

class CalendarWidget(CustomWidget):

    __gtype_name__ = "CalendarWidget"
    
    _day_width = settings.day_width
    hour_height = gobject.property(type=float, default=settings.hour_height)
    day_width = gobject.property(type=float, default=settings.day_width)

    def __init__(self, info, *args, **kwargs):
        CustomWidget.__init__(self, *args, **kwargs)
        self.info = info
        info.connect("date-changed", self.info_changed)
        info.connect("selection-recurrence-changed", self.info_changed)
        info.connect("selected-changed", self.info_changed)
        self.date = info.date
        self.selection_recurrence = info.selection_recurrence
        self.selected = info.selected
        
    def info_changed(self, info):
        self.selection_recurrence = info.selection_recurrence
        self.date = info.date
        self.selected = info.selected
        self.queue_draw()

    def get_week_pixel_offset(self):
        return self.day_width - (self.date * self.day_width % self.day_width)
    
    def days_visible(self):
        return int(self.width / self.day_width)

    def get_date(self, i):
        return datetime.date.fromordinal(int(i))

class CalendarInfo(gobject.GObject):

    __gtype_name__ = "CalendarInfo"
    
    _date = float(datetime.date.today().toordinal())

    def _get_date(self):
        return self._date

    def _set_date(self, value):
        self._date = value
        self.emit("date-changed")

    date = gobject.property(_get_date, _set_date)
        
    _sr = None

    def _get_sr(self):
        return self._sr

    def _set_sr(self, value):
        self._sr = value
        self.emit("selection-recurrence-changed")
        
    selection_recurrence = property(_get_sr, _set_sr)

    _selected = None

    def _get_selected(self):
        return self._selected

    def _set_selected(self, value):
        self._selected = value
        self.emit("selected-changed")

    selected = gobject.property(_get_selected, _set_selected)

    __gsignals__ = {
        "selection-recurrence-changed": (gobject.SIGNAL_RUN_LAST,
                                         gobject.TYPE_NONE,
                                         ()),
        "date-changed": (gobject.SIGNAL_RUN_LAST,
                         gobject.TYPE_NONE,
                         ()),
        "selected-changed": (gobject.SIGNAL_RUN_LAST,
                             gobject.TYPE_NONE,
                             ())
        }

    def __init__(self, *args, **kwargs):
        gobject.GObject.__init__(self, *args, **kwargs)
