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
import goocanvas
import gobject
import datetime
import math
from gettext import gettext as _
from schedule import Schedule, Event
from command import UndoStack, MenuCommand, Command, MouseCommand
from behavior import MouseInteraction

WIDTH = 600
HEIGHT = 400
DAY_WIDTH = WIDTH / 8
HOUR_HEIGHT = 50

#TODO: edit the name of an event
#TODO: repeating events
#TODO: event alarms
#TODO: save to file
#TODO: sync with google calendar
#TODO: sync with facebook calendar
#TODO: sync with evolution ??
#TODO: message area (gtk-info bar?)
#TODO: go to today
#TODO: go to next {week, month}
#TODO: go to selected
#TODO: forward, back buttons
#TODO: make calendar view "roll" so that sunday is always on the left
#TODO: zooming support (changes day_width/height size)
#TODO: change cursors
#TODO: start writing test cases, we've got too many features already
#TODO: don't hard-code colors or drawing styles
#TODO: port away from goocanvas ?
#TODO: allow multiple selections
#TODO: do something sane when events overlap
#TODO: clamp values on selector to something sane
#TODO: move events between days
#TODO: specify working day (hide unused hours)

def quantize(x, modulus):
    return (x // modulus) * modulus

class Selector(MouseInteraction):

    def __init__(self, undo):
        self.selected = None
        self.item = None
        self.undo = undo
        self.mode = None
        self.command = None
        self.commands = (SetEventStart, SetEventEnd, MoveEvent, SelectArea)

    def drag_start(self):
        for command in self.commands:
            self.command = command.create_for_point(self.instance, self.abs)
            if self.command:
                break

        handle = self.instance.point_in_handle(*self.abs)
        self.item = self.instance.point_to_event(*self.abs)

    def move(self):
        if self.command:
            shift = not self.event.get_state() & gtk.gdk.SHIFT_MASK
            self.command.update(self.abs, self.rel, shift)

    def drag_end(self):
        if self.command:
            self.undo.commit(self.command)
        self.command = None

    def click(self):
        cmd = SelectPoint(self.instance, *self.abs)
        cmd.do()
        self.undo.commit(cmd)

class VelocityController(MouseInteraction):

    _velocity = 0

    def point_in_area(self, point):
        x, y = point
        return (self.instance.x <= x <= self.instance.width and 
            self.instance.y <= y <= HOUR_HEIGHT)

    def observe(self, instance):
        self.area = goocanvas.Bounds(instance.day_width, 0, instance.width,
            instance.hour_height)
        MouseInteraction.observe(self, instance)

    def button_press(self):
        self._velocity = 0

    def drag_start(self):
        self._temp_date = self.instance.date

    def move(self):
        self.instance.date = self._temp_date - (self.rel[0] / self.instance.day_width)
        self.instance.changed(False)

    def click(self):
        pass

    def drag_end(self):
        self._velocity = self.delta[0] / self.instance.day_width
        gobject.timeout_add(30, self._move)

    def _move(self):
        self.instance.date -= self._velocity
        self._velocity *= 0.99
        if 0 < abs(self._velocity) < 0.01:
            self._velocity = 0
        return bool(self._velocity)

class CalendarBase(goocanvas.ItemSimple, goocanvas.Item):

    __gtype_name__ = "CalendarBase"

    x = gobject.property(type=int, default=0)
    y = gobject.property(type=int, default=0)
    width = gobject.property(type=int, default=WIDTH)
    height = gobject.property(type=int, default=HEIGHT)
    hour_height = gobject.property(type=int, default=HOUR_HEIGHT)
    day_width = gobject.property(type=int, default=DAY_WIDTH)
    date = gobject.property(type=float,
        default=datetime.date.today().toordinal())
    y_scroll_offset = gobject.property(type=int, default=0)
    selected_start = gobject.property(type=gobject.TYPE_PYOBJECT)
    selected_end = gobject.property(type=gobject.TYPE_PYOBJECT)
    selected = gobject.property(type=gobject.TYPE_PYOBJECT)
    handle_locations = None

    def __init__(self, *args, **kwargs):
        goocanvas.ItemSimple.__init__(self, *args, **kwargs)
        self.model = Schedule("schedule.csv")
        self.model.set_changed_cb(self.model_changed)
        self.connect("notify", self.do_notify)
        self.events = {}
        self.selected = None
        self.font_desc = pango.FontDescription("Sans 8")

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
        minute = quantize(int((y / self.hour_height) * 60), 15)

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

    def do_simple_update(self, cr):
        cr.identity_matrix()
        self.bounds = goocanvas.Bounds(self.x, self.y,
            self.x + self.width, self.y + self.height)

    def centered_text(self, cr, text, x, y, width, height):
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

    def text_above(self, cr, text, x, y, width):
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

    def text_below(self, cr, text, x, y, width):
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

    def selection_handles(self, cr, x, y, width, height):
        radius = 10
        cr.save()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.55)
        x1, y1 = (x + 2, y - 2)
        x2, y2 = (x + width - 2, y + height + 2)

        cr.move_to(x1, y1)
        cr.new_sub_path()
        cr.arc(x1 + radius, y1, radius, math.pi, 1.5 * math.pi)
        cr.line_to(x2 - radius, y1 - radius)
        cr.new_sub_path()
        cr.arc(x2 - radius, y1, radius, 1.5 * math.pi, 0)
        cr.line_to(x1, y1)

        cr.move_to(x2, y2)
        cr.new_sub_path()
        cr.arc(x2 - radius, y2, radius, 0, 0.5 * math.pi)
        cr.line_to(x1 + radius, y2 + radius)
        cr.new_sub_path()
        cr.arc(x1 + radius, y2, radius, 0.5 * math.pi, math.pi)
        cr.line_to(x2, y2)
        cr.fill()

        cr.set_source_rgb(1, 1, 1)

        cr.move_to (x1 + width / 2, y1 - radius + 1)
        cr.rel_line_to (-3, radius - 2)
        cr.rel_line_to (6, 0)
        cr.move_to (x1 + width / 2, y1 - radius + 1)

        cr.move_to (x1 + width / 2, y2 + radius - 1)
        cr.rel_line_to (-3, -radius + 2)
        cr.rel_line_to (6, 0)
        cr.move_to (x1 + width / 2, y2 + radius - 1)
        cr.fill()

        cr.restore()
        self.handle_locations = (x1, y1, x2, y2)

    def point_in_handle (self, x, y):
        if not self.handle_locations:
            return 0

        x1, y1, x2, y2 = self.handle_locations

        if (x1 + 2 <= x <= x2 + 2) and (y1 - 10 <= y <= y1 + 4):
            return 1
        if (x1 + 2 <= x <= x2 + 4) and (y2 - 4 <= y <= y2 + 10):
            return 2
        return 0

    def clear_background(self, cr):
        cr.rectangle(self.x, self.y, self.width, self.height)
        cr.set_source_rgb(0.8, 0.8, 0.8)
        cr.fill()

    def draw_grid(self, cr, x, y):
        cr.save()
        cr.rectangle(self.day_width, self.hour_height, 
            self.width - self.day_width, self.height - self.hour_height)
        cr.clip()

        cr.set_source_rgb(1, 1, 1)
        for i in xrange(1, 25):
            cr.move_to(self.day_width, self.y_scroll_offset + i * self.hour_height)
            cr.line_to(self.width, self.y_scroll_offset + i * self.hour_height)
            cr.stroke()

        for i in xrange(0, (self.width / self.day_width) + 1):
            # draw vertical lines
            x += self.day_width
            cr.move_to (x, self.hour_height)
            cr.line_to (x, self.height)
            cr.stroke()

    def draw_day_headers(self, cr, x, y, day):
        cr.save()
        cr.rectangle(self.day_width, y, self.width - self.day_width,
            self.height)
        cr.clip()

        for i in xrange(0, (self.width / self.day_width) + 1):
            date = self.get_date(day + i)
            weekday = date.weekday()

            cr.rectangle (x, y, self.day_width, self.hour_height)

            if weekday > 4:
                cr.set_source_rgb(0.75, 0.85, 0.75)
            else:
                cr.set_source_rgb(0.75, 0.75, 0.85)
            cr.fill_preserve()

            cr.set_source_rgb(1, 1, 1)
            cr.stroke()

            # draw heading
            cr.set_source_rgba (0, 0, 0, 0.75)
            self.text_above(cr, date.strftime("%a"), x, y +
                self.hour_height / 2 - 2, self.day_width)
            self.text_below(cr, date.strftime("%x"), x, y +
                self.hour_height / 2 + 2, self.day_width)
            x += self.day_width

        y = self.y_scroll_offset
        x = self.day_width - (self.date * self.day_width % self.day_width)

        cr.restore()
        
    def do_simple_paint(self, cr, bounds):
        cr.identity_matrix()
        self.events = {}
        x = self.day_width - (self.date * self.day_width % self.day_width)
        y = self.x
        day = int (self.date)

        self.clear_background(cr)
        self.draw_day_headers(cr, x, y, day)
        self.draw_grid(cr, x, y)

        cr.set_source_rgb(0, 0, 0)
        for i in xrange (0, (self.width / self.day_width) + 1):
            for start, duration, text, evt in self.get_schedule(self.date + i):
                y = self.y_scroll_offset + start * self.hour_height +\
                    self.hour_height
                height = duration * self.hour_height

                cr.rectangle(x + 2, y, self.day_width - 4, height)
                cr.set_source_rgba(0.55, 0.55, 0.55)
                cr.fill_preserve()

                cr.save()
                cr.clip()
                cr.set_source_rgb(0, 0, 0)
                
                pcr = pangocairo.CairoContext(cr)
                lyt = pcr.create_layout()
                lyt.set_font_description(self.font_desc)
                lyt.set_text(text)
                lyt.set_width(pango.PIXELS(self.day_width - 4 + 100))
                cr.move_to(x + 2, y)
                pcr.show_layout(lyt)
                cr.restore()

                self.events[evt] = (x, y, self.day_width, height)

                if evt == self.selected:
                    selected_x, selected_y, selected_height = x, y, height

            x += self.day_width

        if self.selected:
            self.selection_handles (cr, selected_x, selected_y,
                self.day_width, selected_height)

        if self.selected_start and self.selected_end:
            start = self.datetime_to_point(self.selected_start)
            end = self.datetime_to_point(self.selected_end)
            if start and end:
                x1, y1 = start
                x2, y2 = end
                cr.set_source_rgba(0, 0, 0, 0.25)
                height = y2 - y1
                cr.rectangle(x1, y1, self.day_width, height)
                cr.fill()
                cr.set_source_rgba(0, 0, 0, 0.75)

                text = self.selected_start.strftime ("%X")
                self.text_above(cr, text, x1, y1 - 2, self.day_width)

                text = self.selected_end.strftime ("%X")
                self.text_below(cr, text, x1, y1 + height + 2, self.day_width)

                duration = self.selected_end - self.selected_start
                m = int (duration.seconds / 60) % 60
                h = int (duration.seconds / 60 / 60)

                text = "%dh %dm" % (h, m)
                self.centered_text(cr, text, x1, y1, self.day_width, height)

        cr.restore()

        cr.save()
        cr.rectangle(0, self.hour_height, self.day_width, self.height -
            self.hour_height)
        cr.clip()

        for i in range(0, 24):
            y = (i + 1) * self.hour_height + self.y_scroll_offset
            cr.rectangle(0, y, self.day_width, self.hour_height)
            cr.set_source_rgb (0.75, 0.75, 0.75)
            cr.fill_preserve()
            cr.set_source_rgb (1, 1, 1)
            cr.stroke()

            # draw heading
            cr.set_source_rgba(0, 0, 0, .75)
            text = "%2d:00" % i
            tw, th = cr.text_extents(text)[2:4]
            cr.move_to ((self.day_width / 2) - tw / 2,
                y + (self.hour_height / 2) - th / 2)
            cr.show_text(text)

        cr.restore()

        cr.set_source_rgba(0.75, 0.75, 0.75)
        cr.rectangle (self.x, self.y, self.day_width, self.hour_height)
        cr.fill_preserve()
        cr.set_source_rgb(1, 1, 1)
        cr.stroke()

        cr.set_source_rgba(0.55, 0.55, 0.55)
        cr.move_to(self.x, self.hour_height)
        cr.line_to(self.width, self.hour_height)
        cr.stroke()

        cr.move_to(self.day_width, self.y)
        cr.line_to(self.day_width, self.height)
        cr.stroke()

        cr.set_source_rgb(0, 0, 0)
        self.centered_text(cr, datetime.date.fromordinal(int(self.date + 1)).strftime("%x"),
            0, 0, self.day_width, self.hour_height)

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
        self.selected = event
        self.changed(False)

    def get_schedule(self, date):
        # test schedule
        return [(event.start.hour + (event.start.minute / 60.0), 
            event.get_duration().seconds / 60.0/ 60.0,
            event.description,
            event)
                for event in self.model.get_events(date)]

class SelectPoint(Command):

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
        self.instance.selected = self.selected
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
        self.instance.selected = self.selected
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

    def do(self):
        x, y = self.rel
        delta = self.instance.point_to_timedelta(x, y, self.shift)
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

class CalendarItem(goocanvas.Group):

    __gtype_name__ = "CalendarItem"

    def __init__(self, undo, *args, **kwargs):
        goocanvas.Group.__init__(self, *args, **kwargs)
        self.schedule = CalendarBase(parent=self)
        self.scrolling = VelocityController()
        self.scrolling.observe(self.schedule)
        self.selection = Selector(undo)
        self.selection.observe(self.schedule)

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
        self.app.schedule.selected = None
        return True

    def undo(self):
        self.app.model.add_event(self.event)
        return True

class App(object):

    ui = """
    <ui>
        <toolbar name="mainToolBar">
            <toolitem action="Undo"/>
            <toolitem action="Redo"/>
            <separator />
            <toolitem action="NewEvent"/>
            <toolitem action="DelEvent"/>
        </toolbar>
    </ui>"""


    def __init__(self):
        self.undo = UndoStack()
        w = gtk.Window()
        w.connect("destroy", gtk.main_quit)
        vbox = gtk.VBox()
        hbox = gtk.HBox()
        canvas = goocanvas.Canvas()
        self.calendar_item = CalendarItem(self.undo)
        self.schedule = self.calendar_item.schedule
        self.model = self.schedule.model
        canvas.get_root_item().add_child(self.calendar_item)
        canvas.set_size_request(WIDTH, HEIGHT)
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
        gtk.main()

    def do_command(self, unused_action, command):
        cmd = command(self)
        cmd.configure()
        if cmd.do():
            self.undo.commit(cmd)

if __name__ == "__main__":
    App().run()
