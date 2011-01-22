class Behavior(object):

    __signals__ = []
    instance = None

    def observe(self, instance):
        if self.instance:
            self._disconnect()
        self.instance = instance
        if instance:
            self._connect()

    def _disconect(self):
        for sigid in self.handlers:
            self.instance.disconect()
        self.handlers = []

    def _connect(self):
        pass

    def connect(self, signame):
        handler = "on_" + signame.replace("-", "_")
        self.instance.connect(signame, getattr(self, handler))

import gtk

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

class MouseInteraction(Behavior):

    def _connect(self):
        self.connect("button-press-event")
        self.connect("button-release-event")
        self.connect("motion-notify-event")

    area = None

    _button_down = False
    _dragging = False
    _canvas = None

    mdown = (0, 0)
    abs = (0, 0)
    rel = (0, 0)
    delta = (0, 0)
    event = None

    def _common(self, item, target, event):
        if not self._canvas:
            self._canvas = item.get_canvas()
        self.event = event

    def point_in_area(self, point):
        bounds = self.area
        if not bounds.x1 <= point[0] <= bounds.x2:
            return False

        if not bounds.y1 <= point[1] <= bounds.y2:
            return False

        return True

    def flick_threshold(self):
        return True

    def on_button_press_event(self, item, target, event):
        if self.area:
            if not self.point_in_area(self.abs):
                return False

        self._common(item, target, event)
        self.mdown = (event.x, event.y)
        self._button_down = True
        self.button_press()
        return False

    def on_button_release_event(self, item, target, event):
        self._common(item, target, event)
        ret = False
        if self._dragging:
            self.drag_end()
            if self.flick_threshold():
                self.flick()
            ret = True
        elif self._button_down:
            self.click()
            ret = True
        self._dragging = False
        self._button_down = False
        self.button_release()
        return False

    def on_motion_notify_event(self, item, target, event):
        ret = False
        self._common(item, target, event)
        self.last = self.abs
        self.abs = self._canvas.convert_from_pixels(event.x, event.y)
        self.rel = (self.abs[0] - self.mdown[0], self.abs[1] - self.mdown[1])
        self.delta = (self.abs[0] - self.last[0], self.abs[1] -
            self.last[1])
        if self._button_down and (not self._dragging):
            self._dragging = True
            self.drag_start()
            ret = True
        if self._dragging:
            self.move()
            ret = True
        self.motion_notify()
        return False

    def button_press(self):
        pass

    def button_release(self):
        pass

    def drag_start(self):
        pass

    def motion_notify(self):
        pass

    def drag_end(self):
        pass

    def move(self):
        pass

    def click(self):
        pass

    def flick(self):
        pass

import gobject

class Animation(Behavior):

    def __init__(self, interval, duration=None, finished_cb=None):
        self.interval = interval
        self.running = False
        self.duration = duration
        self.finished_cb = finished_cb

    def start(self):
        self.running = True
        self.clock = 0
        gobject.timeout_add(self.interval, self._timeout_cb)

    def stop(self):
        self.running = False
        if self.finished_cb:
            self.finished_cb()
        self.finish()

    def _timeout_cb(self):
        self.clock += self.interval
        if self.duration and (self.clock > self.duration):
            self.stop()
        self.step()
        return self.running

    def step(self):
        pass

    def finish(self):
        pass
        
