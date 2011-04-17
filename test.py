# Calendar, Graphical calendar applet with novel interface
#
#       test.py
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

import cal
import weekview
import gobject
import gtk
import traceback
import sys
import datetime
import os
import recurrence

class TestApp(cal.App):

    path = "test.data"

class Tester:
    def __init__(self, test_case):
        self.app = TestApp()
        gobject.timeout_add(1000, self.run_test_case, test_case(self.app))
        self.app.run()
        os.unlink("test.data")

    def run_test_case(self, iterator):
        print "Tick"
        
        try:
            scheduler = iterator.next()
            
        except StopIteration:
            print "Test Case Finished Successfully"
            self.app.quit()
            return False

        except Exception, e:
            print "An error occured"
            self.app.quit()
            traceback.print_exc()
            return False

        scheduler.schedule(self, iterator)
        return False

class Sleep(object):

    def __init__(self, timeout=1000):
        self.timeout = timeout
        
    def schedule(self, tester, iterator):
        gobject.timeout_add(self.timeout, tester.run_test_case, iterator)

class WaitForSignal(object):
    
    def __init__(self, obj, signame):
        self.obj = obj
        self.signame = signame
        self.iterator = None
        self.sigid = None
        
    def schedule(self, tester, iterator):
        self.sigid = self.obj.connect(self.signame, self._handler)
        self.iterator = iterator
        self.tester = tester
        
    def _handler(self, *args):
        self.tester.run_test_case(self.iterator)
        self.obj.disconnect(self.sigid)
    
def basic_test(app):
    yield Sleep(100)

def test_select_area(app):
    yield Sleep(100)
    cmd = weekview.SelectArea(app.weekview.timed, [100, 100])
    cmd.update((100, 100 + app.weekview.timed.hour_height),
               (0, app.weekview.timed.hour_height),
               True)
    
    yield Sleep()
    
    assert type(app.info.selection_recurrence) == recurrence.Period
    r = app.info.selection_recurrence

    yield Sleep()
    
    cmd.undo()
    assert app.info.selection_recurrence == None

    yield Sleep()
    
    cmd.do()
    assert app.info.selection_recurrence == r

    yield Sleep()

def test_new_event(app):
    yield Sleep(100)
    s = datetime.datetime.today()
    e = s + datetime.timedelta(hours=1)

    app.info.selection_recurrence = r = recurrence.Period(
        recurrence.Weekly(0), datetime.time(12, 00), datetime.time(13, 00))
    
    cmd = cal.NewEvent(app)
    cmd.do()
    assert app.info.selection_recurrence == None

    cmd.undo()
    assert app.info.selection_recurrence == r

    cmd.do()
    assert app.info.selection_recurrence == None

def test_select_and_delete_event(app):
    cmd = weekview.SelectArea(app.weekview.timed, (100, 100))
    cmd.update((100, 100 + app.weekview.timed.hour_height),
               (0, app.weekview.timed.hour_height))

    r = app.info.selection_recurrence

    cmd = cal.NewEvent(app)
    cmd.do()
    yield Sleep()
    event = cmd.event

    cmd = weekview.SelectPoint(app.weekview.timed, 110, 110)
    cmd.do()
    yield Sleep()
    assert app.info.selected == (event, 0)

    cmd = cal.DelEvent(app)
    cmd.do()
    assert app.weekview.timed.selected == None
    cmd.undo()

for test in [basic_test,
             test_select_area,
             test_new_event,
             test_select_and_delete_event]:
    Tester(test)
