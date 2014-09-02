import kivy
kivy.require('1.0.6')

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.listview import ListView
from kivy.uix.boxlayout import BoxLayout

from centinel import centinel

class CentinelApp(App):
    def build(self):
        btn1 = Button(text="Start Tests")
        btn1.bind(on_press=self.start_tests)

        btn2 = Button(text="Show Results")
        btn2.bind(on_press=self.btn_pressed)

        buttons = BoxLayout(orientation='horizontal')
        buttons.add_widget(btn1)
        buttons.add_widget(btn2)

        layout = BoxLayout(orientation="vertical")
        layout.add_widget(buttons)

        return layout

    def start_tests(self, instance):
        centinel.run()

    def btn_pressed(self, instance):
        print instance.text


if __name__ == '__main__':
    CentinelApp().run()
