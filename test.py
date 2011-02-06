import cal

class TestApp(cal.App):

    path = "test.data"

class Tester:
    def __init__(self):
        self.app = TestApp()

    def run(self):
        self.app.run()

Tester().run()
