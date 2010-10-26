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

    def on_button_press_event(self, item, target, event):
        if self.area:
            if not self.point_in_area(self.abs):
                return False

        self._common(item, target, event)
        self.mdown = (event.x, event.y)
        self._button_down = True
        self.button_press()
        return True

    def on_button_release_event(self, item, target, event):
        self._common(item, target, event)
        ret = False
        if self._dragging:
            self.drag_end()
            ret = True
        elif self._button_down:
            self.click()
            ret = True
        self._dragging = False
        self._button_down = False
        self.button_release()
        return ret

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
        return ret

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

