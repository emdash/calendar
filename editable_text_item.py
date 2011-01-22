import goocanvas
import gobject
from shapes import left_aligned_text
import settings
import cairo
import pango
import gtk
from behavior import Behavior

class TextInput(Behavior):

    def __init__(self, text_changed_func):
        self.buffer = gtk.TextBuffer()
        self.buffer.connect("changed", self._buffer_changed_cb)
        self.text_changed_func = text_changed_func

    def _connect(self):
        self.connect("key-press-event")
        self.connect("key-release-event")
        self.connect("focus-in-event")
        self.connect("focus-out-event")

    def on_focus_in_event(self, item, target, event):
        pass

    def on_focus_out_event(self, item, target, event):
        pass

    def cursor_iter(self):
        return self.buffer.get_iter_at_mark(self.buffer.get_insert())

    def delete(self, control):
        fr = self.cursor_iter()
        if control:
            fr.backward_word_start()
        else:
            fr.backward_cursor_position()
        to = self.cursor_iter()
        self.buffer.delete(fr, to)
            
    def cursor_motion_func(func):
        def cursor_motion_func(self, control):
            i = self.cursor_iter()
            func(i, control)
            self.buffer.place_cursor(i)
        return cursor_motion_func

    @cursor_motion_func
    def left(i, control):
        if control:
            i.backward_word_start()
        else:
            i.backward_cursor_position()

    @cursor_motion_func
    def right(i, control):
        if control:
            i.forward_word_end()
        else:
            i.forward_cursor_position()

    keyfuncs = {
        gtk.keysyms.BackSpace: delete,
        gtk.keysyms.Left: left,
        gtk.keysyms.Right: right,
    }

    def on_key_press_event(self, item, target, event):
        self.instance.cursor_showing = True

        if event.keyval in self.keyfuncs:
            self.keyfuncs[event.keyval](self, event.state & gtk.gdk.CONTROL_MASK)
            self.text_changed_func()
            return
        self.buffer.insert_at_cursor(event.string)

    def on_key_release_event(self, item, target, event):
        pass

    def get_text(self):
        return self.buffer.get_text(*self.buffer.get_bounds())

    def set_text(self, text):
        self.buffer.set_text(text)
        self.cursor = self.buffer.get_end_iter()

    def get_cursor_pos(self):
        return self.cursor_iter().get_offset()

    def _buffer_changed_cb(self, buffer):
        self.text_changed_func()

class EditableTextItem(goocanvas.ItemSimple, goocanvas.Item):

    __gtype_name__ = "EditableTextItem"

    x = gobject.property(type=int, default=0)
    y = gobject.property(type=int, default=0)
    width = gobject.property(type=int, default=0)
    height = gobject.property(type=int, default=0)
    show_frame = gobject.property(type=bool, default=True)

    def get_text(self):
        return self.ti.get_text()

    def set_text(self, text):
        return self.ti.set_text(text)

    text = gobject.property(get_text, set_text, type=str)

    def __init__(self, *args, **kwargs):
        self.ti = TextInput(lambda : self.changed(False))
        goocanvas.ItemSimple.__init__(self, *args, **kwargs)
        self.connect("notify", self.do_notify)
        self.cursor_showing = True
        self.focused = False
        gobject.timeout_add(500, self._blink_cursor)
        self.ti.observe(self)

    def _blink_cursor(self):
        self.cursor_showing = not self.cursor_showing
        self.changed(False)
        return True

    def do_notify(self, unused, pspec):
        self.changed(True)

    def do_simple_is_item_at(self, x, y, cr, pointer_event):
        return False

    def do_simple_update(self, cr):
        cr.identity_matrix()
        self.bounds = goocanvas.Bounds(self.x, self.y,
                                       self.x + self.width,
                                       self.y + self.height)

    def draw_bounding_rectangle(self, cr):
        if not self.show_frame:
            return
        cr.save()
        cr.set_antialias(cairo.ANTIALIAS_NONE)
        cr.stroke_preserve()
        cr.restore()
        
    def get_cursor_pos(self, lyt):
        return [pango.units_to_double(x)
                for x in
                lyt.get_cursor_pos(self.ti.get_cursor_pos())[0]]

    def draw_cursor(self, cr, lyt):
        if not self.cursor_showing:
            return

        cr.save()
        cr.set_line_width(1)
        cr.set_antialias(cairo.ANTIALIAS_NONE)
        x, y, width, height = self.get_cursor_pos(lyt)
        cr.move_to(self.x + x + 2, self.y + y)
        cr.line_to(self.x + x + 2, self.y + y + height)
        cr.stroke()
        cr.restore()

    def draw_text(self, cr):
        lyt = left_aligned_text(cr, self.ti.get_text(), self.x + 2, self.y, self.width - 4, self.height,
                                settings.text_color)
        self.draw_cursor(cr, lyt)

    def do_simple_paint(self, cr, bounds):
        cr.identity_matrix()
        cr.rectangle(self.x, self.y, self.width, self.height)
        cr.set_source_rgba(0, 0, 0, 1)
        cr.clip_preserve()
        self.draw_bounding_rectangle(cr)
        self.draw_text(cr)

if __name__ == "__main__":
    w = gtk.Window()
    c = goocanvas.Canvas()
    c.set_events(gtk.gdk.ALL_EVENTS_MASK)

    w.add(c)
    c.set_size_request(320, 240)
    c.set_bounds(0, 0, 320, 240)
    i = (EditableTextItem(
            x = 100,
            y = 100,
            width = 40,
            height = 40,
            text="Hello, world",
            show_frame = False))
    
    c.get_root_item().add_child(i)
    c.grab_focus(i)
    w.show_all()
    gtk.main()
