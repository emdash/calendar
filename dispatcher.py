# Calendar, Graphical calendar applet with novel interface
#
#       dispatcher.py
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
from behavior import MouseInteraction

class MouseCommandDispatcher(MouseInteraction):

    area = "ensures point-in-area-is-called"
    cursor = gtk.gdk.Cursor(gtk.gdk.LEFT_PTR)

    def __init__(self, undo, drag_commands, click_commands=(), cursor=None):
        self.selected = None
        self.item = None
        self.undo = undo
        self.mode = None
        self.command = None
        self.drag_commands = drag_commands
        self.click_commands = click_commands
        self.cursor = cursor if cursor else None
        self.cur_cursor = self.cursor

    def motion_notify(self):
        cmd = self.find_command((cmd for cmd in self.drag_commands
                                 if cmd.cursor))
        if cmd:
            self.set_cursor(cmd.cursor)
        else:
            self.set_cursor(self.cursor)
            
    def set_cursor(self, cursor):
        if cursor != self.cur_cursor:
            self.instance.window.set_cursor(cursor)
            self.cur_cursor = cursor

    def point_in_area(self, point):
        return (self.can_do(self.drag_commands, point) or
                self.can_do(self.click_commands, point))

    def button_press(self):
        if self.command:
            self.command.flick_stop()

    def drag_start(self):
        self.command = self.find_and_create_command(self.drag_commands)

    def can_do(self, commands, point):
        return any((cmd.can_do(self.instance, point) for cmd in commands))
    
    def find_command(self, commands):
        for command in commands:
            if command.can_do(self.instance, self.abs):
                return command
        return None

    def find_and_create_command(self, commands):
        cmd = self.find_command(commands)
        if cmd:
            return cmd.create_for_point(self.instance, self.abs)
        return None

    def move(self):
        if self.command:
            shift = not self.event.get_state() & gtk.gdk.SHIFT_MASK
            self.command.update(self.abs, self.rel, shift)

    def drag_end(self):
        if self.command:
            self.undo.commit(self.command)

    def flick(self):
        if self.command:
            self.command.flick(self.delta, None,
                               not self.event.state & gtk.gdk.SHIFT_MASK)

    def click(self):
        cmd = self.find_and_create_command(self.click_commands)
        if cmd:
            cmd.do()
            self.undo.commit(cmd)
