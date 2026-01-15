#    ____        _      __   ____             __  
#   / __ \__  __(_)____/ /__/ __ \____ ______/ /_ 
#  / / / / / / / / ___/ //_/ / / / __ `/ ___/ __ \
# / /_/ / /_/ / / /__/ ,< / /_/ / /_/ (__  ) / / /
# \___\_\__,_/_/\___/_/|_/_____/\__,_/____/_/ /_/  v1.0
# 
# TUI Dashbord with on the fly configs!

from textual.app import App, ComposeResult
from textual.color import Gradient
from textual.containers import HorizontalGroup, VerticalGroup, Center, Middle
from textual.widgets import Header, Footer, Button, Digits, Label, Static, ProgressBar, Placeholder
from textual.reactive import reactive

import psutil
import asyncio

gradient = Gradient.from_colors(
    "#663399",
    "#3366bb",
    "#0099cc",
    "#00bbcc",
    "#22ccbb",
    "#44dd88",
    "#99dd55",
    "#eedd00",
    "#ee9944",
    "#cc6666",
    "#aa3355",
    "#881177",
)

# Main window
class QuickDash(App):
    CSS_PATH = "main.tcss"

    def compose(self) -> ComposeResult:
        #yield Header()
        yield Bar()
        yield Placeholder()
        #yield Footer()

# Top bar
class Bar(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Ram()
        yield HorizontalGroup(
            Disk("/", "Root"),
            Disk("/home", "Home"),
            id="disks" #TODO: make dynamic.
        )
        yield Cpu()

class Ram(VerticalGroup):
    
    def on_mount(self) -> None:
        self.set_interval(1.0, self.update_stats)
    
    async def update_stats(self) -> None:
        ram = psutil.virtual_memory()

        usage_label = self.query_one(Digits)
        usage_label.update(f"{(ram.used / (1024**3)):.1f}G")

        usage_bar = self.query_one(ProgressBar)
        usage_bar.update(total=ram.total, progress=ram.used)

    def compose(self) -> ComposeResult:
        yield Label("RAM")
        yield Digits()
        yield ProgressBar(gradient=gradient)

class Disk(VerticalGroup):

    def __init__(self, path:str, type:str) -> None:
        super().__init__()
        self.path = path
        self.type = type

    def on_mount(self) -> None:
        self.set_interval(1.0, self.update_stats)
    
    async def update_stats(self) -> None:
        disk = psutil.disk_usage(self.path)

        usage_label = self.query_one(Digits)
        if disk.used // (1024**4): usage_label.update(f"{(disk.used / (1024**4)):.1f}T")
        else: usage_label.update(f"{(disk.used / (1024**3)):.1f}G")

        usage_bar = self.query_one(ProgressBar)
        usage_bar.update(total=disk.total, progress=disk.used)
    
    def compose(self) -> ComposeResult:
        yield Label(self.type)
        yield Digits()
        yield ProgressBar(gradient=gradient)

class Cpu(VerticalGroup):

    def on_mount(self) -> None:
        self.set_interval(1, self.update_stats)
    
    async def update_stats(self) -> None:
        usage = psutil.cpu_percent(interval=0.1, percpu=False) # TODO: per core later
        freq = psutil.cpu_freq().current
        temps = psutil.sensors_temperatures()

        usage_label = self.query_one(Digits)
        usage_label.update(f"{usage:.1f}%")
        
        freq_label = self.query_one("#cpu-freq", Label)
        freq_label.update(f"{freq:.0f}MHz")

        temp_label = self.query_one("#cpu-temp", Label)
        temp_label.update(f"{temps['coretemp'][0].current:.1f}°C")

        usage_bar = self.query_one(ProgressBar)
        usage_bar.update(total=100, progress=usage)
    
    def compose(self) -> ComposeResult:
        yield Label("CPU")
        yield HorizontalGroup(
            Digits(),
            VerticalGroup(
                Label(id="cpu-freq"),
                Label(id="cpu-temp"),
            ),
        )
        yield ProgressBar(gradient=gradient)

# Log widget
class Log: pass

# Custom command widgets
class Custom:
    def __init__(self, id:int):
        self.id = id
        self.name = "New Widget"

if __name__ == "__main__":
    app = QuickDash()
    app.run()
