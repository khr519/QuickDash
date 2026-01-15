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
class Ram(VerticalGroup):
    
    def on_mount(self) -> None:
        self.set_interval(1.0, self.update_stats)
    
    async def update_stats(self) -> None:
        ram = psutil.virtual_memory()
        progress_bar = self.query_one(ProgressBar)
        progress_bar.update(
            total=ram.total,
            progress=ram.used,
        )

        usage_label = self.query_one("#ram-usage", Digits)
        usage_label.update(f"{(ram.used / (1024**3)):.1f}G")

    def compose(self) -> ComposeResult:
        yield Label("RAM")
        yield Digits("", id="ram-usage")
        yield ProgressBar(gradient=gradient)

class Disk(VerticalGroup):

    def on_mount(self) -> None:
        progress_bar = self.query_one(ProgressBar)
        progress_bar.update(
            total=240,
            progress=40.2
        )
    
    def compose(self) -> ComposeResult:
        yield Label("SSD")
        yield Digits("940.2T")
        yield ProgressBar(gradient=gradient)

class Cpu(Digits):
    cpu = reactive({})

    def on_mount(self) -> None:
        self.set_interval(1, self.update_stats)
    
    async def update_stats(self) -> None:
        usage = psutil.cpu_percent(interval=0.1, percpu=False) # TODO: per core later
        freq = psutil.cpu_freq()
        temps = psutil.sensors_temperatures()
        
        self.update(f"{usage:.1f}%")
        
        self.cpu = {
            "cores": usage,
            "freq": freq.current if freq else 0,
            "temp": temps
        }

class Bar(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Ram()
        yield HorizontalGroup(
            Disk(),
            Disk(),
            id="disks"
        )
        yield Cpu()

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
