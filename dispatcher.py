import gtk
from behavior import MouseInteraction

class MouseCommandDispatcher(MouseInteraction):

    area = "ensures point-in-area-is-called"

    def __init__(self, undo, drag_commands, click_commands=()):
        self.selected = None
        self.item = None
        self.undo = undo
        self.mode = None
        self.command = None
        self.drag_commands = drag_commands
        self.click_commands = click_commands

    def point_in_area(self, point):
        return (self.can_do(self.drag_commands, point) or
                self.can_do(self.click_commands, point))

    def button_press(self):
        if self.command:
            self.command.flick_stop()

    def drag_start(self):
        self.command = self.find_command(self.drag_commands)

    def can_do(self, commands, point):
        return any((cmd.can_do(self.instance, point) for cmd in commands))
    
    def find_command(self, commands):
        for command in commands:
            ret = command.create_for_point(self.instance, self.abs)
            if ret: return ret

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
                               self.event.state & gtk.gdk.SHIFT_MASK)

    def click(self):
        cmd = self.find_command(self.click_commands)
        if cmd:
            cmd.do()
            self.undo.commit(cmd)