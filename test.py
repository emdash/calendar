import cal
import gobject
import gtk
import traceback
import sys
import datetime
import os

class TestApp(cal.App):

    path = "test.data"

class Tester:
    def __init__(self, test_case):
        self.app = TestApp()
        gobject.timeout_add(1000, run_test_case, test_case(self.app))
        self.app.run()
        os.unlink("test.data")

def run_test_case(iterator):
    print "Tick"
    
    try:
        scheduler = iterator.next()

    except StopIteration:
        print "Test Case Finished Successfully"
        gtk.main_quit()
        return False

    except Exception, e:
        print "An error occured"
        gtk.main_quit()
        traceback.print_exc()
        return False

    scheduler.schedule(iterator)
    return False

class Sleep(object):

    def __init__(self, timeout=1000):
        self.timeout = timeout
        
    def schedule(self, iterator):
        gobject.timeout_add(self.timeout, run_test_case, iterator)

class WaitForSignal(object):
    
    def __init__(self, obj, signame):
        self.obj = obj
        self.signame = signame
        self.iterator = None
        self.sigid = None
        
    def schedule(self, iterator):
        self.sigid = self.obj.connect(self.signame, self._handler)
        self.iterator = iterator
        
    def _handler(self, *args):
        run_test_case(self.iterator)
        self.obj.disconnect(self.sigid)
    
def basic_test(app):
    yield Sleep(100)

def test_select_area(app):
    yield Sleep(100)
    cmd = cal.SelectArea(app.schedule, [100, 100])
    cmd.update((100, 100 + app.schedule.hour_height),
               (0, app.schedule.hour_height),
               True)
    
    yield Sleep()
    
    start = app.schedule.selected_start
    end = app.schedule.selected_end
    assert app.schedule.selected_end - app.schedule.selected_start == \
        datetime.timedelta(hours=1)

    yield Sleep()
    
    cmd.undo()
    assert app.schedule.selected_start == None
    assert app.schedule.selected_end == None

    yield Sleep()
    
    cmd.do()
    assert app.schedule.selected_end == end
    assert app.schedule.selected_start == start

    yield Sleep()

def test_new_event(app):
    yield Sleep(100)
    s = datetime.datetime.today()
    e = s + datetime.timedelta(hours=1)

    app.schedule.selected_start = s
    app.schedule.selected_end = e
    
    cmd = cal.NewEvent(app)
    cmd.do()
    assert app.schedule.selected_start == None
    assert app.schedule.selected_end == None
    assert app.schedule.selected.start == s
    assert app.schedule.selected.end == e

    cmd.undo()
    assert app.schedule.selected_start == s
    assert app.schedule.selected_end == e
    assert app.schedule.selected == None

    cmd.do()
    assert app.schedule.selected_start == None
    assert app.schedule.selected_end == None
    assert app.schedule.selected.start == s
    assert app.schedule.selected.end == e

for test in [basic_test, test_select_area, test_new_event]:
    Tester(test)
