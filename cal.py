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
import gobject
import datetime
import math
from gettext import gettext as _
from schedule import Schedule, Event
from command import UndoStack, MenuCommand, Command, MouseCommand
from behavior import MouseInteraction, TextInput, Animation
from dispatcher import MouseCommandDispatcher
from calendarwidget import CalendarInfo
from weekview import WeekViewHeader, WeekView
import recurrence
import settings
import shapes
import parser
import os
import time

#TODO: event alarms
#TODO: sync with google calendar
#TODO: sync with facebook calendar
#TODO: sync with evolution ??
#TODO: go to next {week, month}
#TODO: make calendar view "roll" so that sunday is always on the left
#TODO: do something sane when events overlap
#TODO: specify working day (hide unused hours)
#TODO: tomboy integration
#TODO: implement month view
#TODO: remove the selection marquee, replace with a 'temporary event'
#      clicking creates an event with a default duration
#      clicking and dragging creates an event over the specified area (min 15 min)
#TODO: exceptions to recurrences
    
class SelectRecurrence(Command):

    def __init__(self, app, text):
        self.app = app
        self.selected = app.weekview.selected
        self.old = app.weekview.selection_recurrence
        if text:
            self.new = parser.parse(text)
        else:
            self.new = None
        self.do()

    def do(self):
        self.app.info.selection_recurrence = self.new
        self.app.weekview.selected = None

    def undo(self):
        self.app.info.selected = self.selected
        self.app.weekview.selection_recurrence = self.old

class SetEventRecurrence(Command):

    def __init__(self, app, text):
        self.app = app
        self.selected = self.app.weekview.selected
        self.event = self.app.weekview.get_occurence_event(self.selected)
        self.old = self.event.recurrence
        self.new = parser.parse(text)
        self.do()

    def do(self):
        self.event.recurrence = self.new

    def undo(self):
        self.event.recurrence = self.old

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
        self.app.info.selection_recurrence = None
        self.app.weekview.queue_draw()
        return True

    def undo(self):
        self.app.model.del_event(self.event)
        self.app.info.selection_recurrence = self.selection
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
        self.event = self.app.weekview.occurrences[self.selected][0]

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
        self.app.info.date = self.selected.start.toordinal()

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
        self.app.weekview.hide()
        
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
        weekviewbox = gtk.VBox()
        self.info = CalendarInfo()
        self.weekviewheader = WeekViewHeader(self.info, self.history)
        self.weekview = WeekView(self.info, self.undo)
        self.model = self.weekview.model
        weekviewbox.pack_start(self.weekviewheader, False, False)
        weekviewbox.pack_start(self.weekview, True, True)

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

        vbox.pack_start(weekviewbox, True, True)

        toolbar = uiman.get_widget("/lowerToolbar")

        self.selection_buffer = gtk.TextBuffer()
        self.selection_buffer.create_tag("error",
                                         underline=pango.UNDERLINE_SINGLE)
        self.selection_entry = gtk.TextView(self.selection_buffer)
        
        self.pack_toolbar_widget(toolbar, self.selection_entry)
        vbox.pack_end (toolbar, False, False)

        w.add(vbox)
        w.show_all()
        self.window = w
        self.weekview.connect("notify::selected", self.update_actions)
        self.info.connect("selection-recurrence-changed", self.update_actions)
        self.selection_entry.connect("key-press-event", self.selection_entry_key_press_cb)

    def pack_toolbar_widget(self, toolbar, widget):
        toolitem = gtk.ToolItem()
        toolitem.add(widget)
        toolitem.set_expand(True)
        widget.show()
        toolitem.show()
        toolbar.add(toolitem)

    dont_update_entry = False

    def selection_entry_key_press_cb(self, entry, event):
        if event.keyval == gtk.keysyms.Return:
            self._parse_text()
            return True
        return False

    def _parse_text(self):
        self.dont_update_entry = True
        self.dirty = False
        b = self.selection_buffer
        text = b.get_text(b.get_start_iter(), b.get_end_iter())

        try:
            if not (self.weekview.selected is None):
                self.undo.commit(SetEventRecurrence(self, text))
            else:
                self.undo.commit(SelectRecurrence(self, text))
            b.remove_all_tags(b.get_start_iter(), b.get_end_iter())
        except parser.ParseError, e:
            self.selection_entry_error(e.position)
        self.dont_update_entry = False
        return False

    def selection_entry_error(self, pos=None):
        b = self.selection_buffer
        if not pos is None:
            b.remove_all_tags(b.get_start_iter(), b.get_end_iter())
            b.apply_tag_by_name("error",
                                b.get_iter_at_offset(pos),
                                b.get_end_iter())

    def update_actions(self, *unused):
        MenuCommand.update_actions(self)
        if self.dont_update_entry:
            return
        if not (self.weekview.selection_recurrence is None):
            text = self.weekview.selection_recurrence.toEnglish()
        elif not (self.weekview.selected is None):
            text = self.weekview.get_occurence_event(
                self.weekview.selected).recurrence.toEnglish()
        else:
            text = ""
        self.selection_buffer.set_text(text)
            
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
