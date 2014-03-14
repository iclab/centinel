import kivy
kivy.require('1.0.6') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.label import Label

import blocker
import experiments.tcp_connect
import experiments.http_request

class MyApp(App):
    def build(self):
        blocker.run()
        return Label(text='Hello world')

if __name__ == '__main__':
    MyApp().run()
