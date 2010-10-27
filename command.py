import gtk

class Command(object):

    def do(self):
        return False

    def undo(self):
        return False

class MenuCommand(Command):

    label = ""
    stockid = None
    tooltip = None

    def __init__(self, app):
        self.app = app
        self.configure()

    def configure(self):
        pass

    @classmethod
    def can_do(cls, app):
        return True

    @classmethod
    def create_action_group(cls, app):
        ret = gtk.ActionGroup("command_actions")
        for sbcls in cls.__subclasses__():
            action = gtk.Action(sbcls.__name__, sbcls.label, sbcls.tooltip,
                sbcls.stockid)
            action.connect("activate", app.do_command, sbcls)
            action.set_sensitive(sbcls.can_do(app))
            ret.add_action(action)
            sbcls.action = action
        return ret

    @classmethod
    def update_actions(cls, app):
        for sbcls in cls.__subclasses__():
            sbcls.action.set_sensitive(sbcls.can_do(app))

class UndoStack(object):

    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []
        self.undo_action = gtk.Action("Undo", None, None, gtk.STOCK_UNDO)
        self.undo_action.set_sensitive(False)
        self.undo_action.connect("activate", self.undo)
        self.redo_action = gtk.Action("Redo", None, None, gtk.STOCK_REDO)
        self.redo_action.set_sensitive(False)
        self.redo_action.connect("activate", self.redo)

    def commit(self, action):
        # an action will return True if it can be undone
        self.undo_stack.append(action)
        self.redo_stack = []
        self.redo_action.set_sensitive(False)
        self.undo_action.set_sensitive(True)

    def undo(self, unused_action):
        action = self.undo_stack.pop()
        action.undo()
        self.redo_stack.append(action)
        self.undo_action.set_sensitive(len(self.undo_stack))
        self.redo_action.set_sensitive(True)

    def redo(self, unused_action):
        action = self.redo_stack.pop()
        action.do()
        self.undo_stack.append(action)
        self.undo_action.set_sensitive(True)
        self.redo_action.set_sensitive(len(self.redo_stack))

