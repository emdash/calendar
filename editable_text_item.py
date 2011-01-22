import goocanvas
import gobject
from shapes import left_aligned_text
import settings
import cairo
import pango
import gtk

class EditableTextItem(goocanvas.ItemSimple, goocanvas.Item):

    __gtype_name__ = "EditableTextItem"

    x = gobject.property(type=int, default=0)
    y = gobject.property(type=int, default=0)
    width = gobject.property(type=int, default=0)
    height = gobject.property(type=int, default=0)
    text = gobject.property(type=str, default="text")
    show_frame = gobject.property(type=bool, default=True)

    def __init__(self, *args, **kwargs):
        goocanvas.ItemSimple.__init__(self, *args, **kwargs)
        self.connect("notify", self.do_notify)
        self.connect("key-press-event", self._key_press_event)
        self.connect("key-release-event", self._key_release_event)
        self.connect("focus-in-event", self._focus_in_event)
        self.connect("focus-out-event", self._focus_out_event)
        self.cursor_showing = True
        self.focused = False
        self.set_proxy(gtk.Entry())
        gobject.timeout_add(500, self._blink_cursor)


    def _focus_in_event(self, item, target, event):
        pass

    def _focus_out_event(self, item, target, event):
        pass

    def _blink_cursor(self):
        self.cursor_showing = not self.cursor_showing
        self.changed(False)
        return True

    def _key_press_event(self, item, target, event):
        if self.proxy:
            self.proxy.emit("key-press-event", event)
        self.cursor_showing = True

    def _key_release_event(self, item, target, event):
        if self.proxy:
            self.proxy.emit("key-release-event", event)

    def set_proxy(self, proxy):
        self.proxy = proxy
        self.proxy.set_text(self.text)
        self.proxy.connect("changed",
                           self._proxy_changed_cb)
        self.proxy.connect("notify::cursor-position", self._proxy_notify_curspor_position_cb)

    def _proxy_notify_curspor_position_cb(self, proxy, pspec):
        self.changed(False)

    def _proxy_changed_cb(self, entry):
        self.text = entry.get_text()

    def do_notify(self, unused, pspec):
        if pspec.name == "text":
            self.proxy.set_text(self.text)
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
                lyt.get_cursor_pos(self.proxy.props.cursor_position)[0]]

    def draw_cursor(self, cr, lyt):
        cr.save()
        cr.set_line_width(1)
        cr.set_antialias(cairo.ANTIALIAS_NONE)
        if not self.cursor_showing:
            return
        x, y, width, height = self.get_cursor_pos(lyt)
        cr.move_to(self.x + x, self.y + y)
        cr.line_to(self.x + x, self.y + y + height)
        cr.stroke()
        cr.restore()

    def draw_text(self, cr):
        lyt = left_aligned_text(cr, self.text, self.x, self.y, self.width, self.height,
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
