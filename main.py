#    ____        _      __   ____             __  
#   / __ \__  __(_)____/ /__/ __ \____ ______/ /_ 
#  / / / / / / / / ___/ //_/ / / / __ `/ ___/ __ \
# / /_/ / /_/ / / /__/ ,< / /_/ / /_/ (__  ) / / /
# \___\_\__,_/_/\___/_/|_/_____/\__,_/____/_/ /_/  v1.0
# 
# TUI Dashbord with on the fly configs!

from textual.app import App, ComposeResult
from textual.color import Gradient
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Header, Footer, Button, Digits, Label, Static, ProgressBar, Placeholder, RichLog
from textual.reactive import reactive
from textual import work
from textual.message import Message

import psutil
import asyncio
import docker
import json
import os

from watchfiles import awatch

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
    settings = reactive({})

    class Load(Message):
        pass

    def on_mount(self):
        self.live_load()
    
    @work(thread=True)
    async def live_load(self):
        async for changes in awatch("settings.json"):
            self.call_from_thread(self.load_settings)

    def load_settings(self):
        with open("settings.json", "r") as p:
            self.settings = json.load(p)
        print(self.settings)
        self.post_message(self.Load())

    def compose(self) -> ComposeResult:
        #yield Header()
        yield Bar()
        yield HorizontalGroup(
            *[Custom(p) for p in (self.settings["custom"]).keys()]
        )
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
    
    def on_mount(self):
        self.set_interval(2, self.update_content)
    
    async def update_content(self):
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

    def __init__(self, path:str, type:str):
        super().__init__()
        self.path = path
        self.type = type

    def on_mount(self):
        self.set_interval(10, self.update_content)
    
    async def update_content(self):
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

    def on_mount(self):
        self.set_interval(2, self.update_content)
    
    async def update_content(self):
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

# Customizable widget
class Custom(VerticalGroup):

    def __init__(self, name:str):
        super().__init__(name=name)
        self.load()
    
    def on_mount(self):
        if self.log_command:
            self.run_worker(self.stream_log_command(), exclusive=True)
        else:
            self.stream_logs()

    def on_quickdash_load(self, _):
        self.load()
    
    def load(self):
        setting = self.app.settings["custom"][self.name]
        self.container = setting["container"]
        self.log_ignore = setting.get("log", {}).get("ignore", [])
        self.log_command = setting.get("log", {}).get("command", None)


    
    @work(thread=True, exclusive=True)
    def stream_logs(self):
        client = docker.from_env()
        container = client.containers.get(self.container)
        log = self.query_one(RichLog)

        stream = container.logs(stream=True, follow=True, tail=50)
        buffer = b""
        for chunk in stream:
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                line = line.decode().strip()
                if sum([(i in line) for i in self.log_ignore]):
                    continue

    async def stream_log_command(self): # NOTE: this is for Nextcloud AIO only for now.
        log = self.query_one(RichLog)

        proc = await asyncio.create_subprocess_shell(
            self.log_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        async for line in proc.stdout:
            json_line = json.loads(line.decode().strip())
            message = json_line.get("message", "")
            level = json_line.get("level", 0)

            if level >= 3: # Error
                log.write(f"[red]{message}[/red]")
            elif level == 2: # Warning
                log.write(f"[yellow]{message}[/yellow]")
            else: # Info
                log.write(message)
    
    def compose(self) -> ComposeResult:
        yield HorizontalGroup(
            Label(self.name),
            Command(self.name, self.container),
        )
        yield RichLog()

class Command(Label):
    def __init__(self, parent_name:str, parent_container:str):
        super().__init__()
        self.parent_name = parent_name
        self.parent_container = parent_container
        self.load()

    def on_mount(self):
        if not self.exec: return
        self.set_interval(5, self.update_content)
    
    def on_quickdash_load(self, _):
        self.load()
    
    def load(self):
        setting = self.app.settings["custom"][self.parent_name]
        self.exec = setting.get("command", {}).get("exec", None)
        self.parse = setting.get("command", {}).get("parse", None)
    
    async def update_content(self):
        proc = await asyncio.create_subprocess_shell(
            f"docker exec {self.parent_container} {self.exec}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        o = stdout.decode().strip()
        if self.parse:
            o = eval(self.parse)
        self.update(o)

if __name__ == "__main__":
    app = QuickDash()
    app.load_settings()
    app.run()
