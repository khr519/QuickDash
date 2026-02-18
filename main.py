# QuickDash v1.0

from textual.app import App, ComposeResult
from textual.color import Gradient
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Digits, Label, ProgressBar, RichLog, TabbedContent, Sparkline
from textual.reactive import reactive

import psutil
import asyncio
import json # <-- unused in the main code, but the user might use this in `log.parse` for logs in json.
import tomllib

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

class Buffer:
    def __init__(self, size:int):
        self.size = size
        self.buffer = [0] * size
        self.pointer = 0
    
    def add(self, item):
        self.buffer[self.pointer] = item
        self.pointer = (self.pointer+1) % self.size
    
    def get(self):
        return self.buffer[self.pointer:]+self.buffer[:self.pointer]

# Main window
class QuickDash(App):
    CSS_PATH = "main.tcss"
    settings = reactive({}, recompose=True)

    def __init__(self):
        super().__init__()
        self.load_settings()

    def on_mount(self):
        self.run_worker(self.live_load())
    
    async def live_load(self):
        async for changes in awatch("."):
            # editors sometimes delete and recreate files, instead of "editing"...
            # so we have to watch the entire directory :(
            for _, path in changes:
                if path.endswith("settings.toml"):
                    self.load_settings()
                    break

    def load_settings(self):
        with open("settings.toml", "rb") as f:
            self.settings = tomllib.load(f)

    def compose(self) -> ComposeResult:
        yield Bar()
        with TabbedContent(*(tabs:=self.settings["tabs"].keys())):
            for tab in tabs: yield Custom(tab)

# Top bar
class Bar(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Ram()
        yield Cpu()
        yield HorizontalGroup(
            *[Disk(*map(lambda i:i[1],p.items())) for p in (self.app.settings["disks"])],
            id="disks"
        )

class Ram(VerticalGroup):
    
    def on_mount(self):
        self.update_content()
        self.set_interval(2, self.update_content)
    
    def update_content(self):
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

    def __init__(self, name:str, path:str):
        super().__init__(name=name)
        self.path = path

    def on_mount(self):
        self.update_content()
        self.set_interval(10, self.update_content)
    
    def update_content(self):
        disk = psutil.disk_usage(self.path)

        usage_label = self.query_one(Digits)
        if disk.used // (1024**4): usage_label.update(f"{(disk.used / (1024**4)):.1f}T")
        else: usage_label.update(f"{(disk.used / (1024**3)):.1f}G")

        usage_bar = self.query_one(ProgressBar)
        usage_bar.update(total=disk.total, progress=disk.used)
    
    def compose(self) -> ComposeResult:
        yield Label(self.name)
        yield Digits()
        yield ProgressBar(gradient=gradient)

class Cpu(VerticalGroup):

    def on_mount(self):
        self.buffer = Buffer(19)
        self.update_content()
        self.set_interval(2, self.update_content)
    
    def update_content(self):
        usage = psutil.cpu_percent(interval=0.1, percpu=False) # TODO: per core later
        freq = psutil.cpu_freq().current
        temps = psutil.sensors_temperatures()

        self.buffer.add(usage)

        usage_label = self.query_one(Digits)
        usage_label.update(f"{usage:.1f}%")
        
        freq_label = self.query_one("#cpu-freq", Label)
        freq_label.update(f"{freq:.0f}MHz")

        temp_label = self.query_one("#cpu-temp", Label)
        temp_label.update(f"{temps['coretemp'][0].current:.1f}°C")

        # usage_bar = self.query_one(ProgressBar)
        # usage_bar.update(total=100, progress=usage)

        usage_graph = self.query_one(Sparkline)
        usage_graph.data=self.buffer.get()
    
    def compose(self) -> ComposeResult:
        yield Label("CPU")
        yield HorizontalGroup(
            Digits(),
            VerticalGroup(
                Label(id="cpu-freq"),
                Label(id="cpu-temp"),
            ),
        )
        # yield ProgressBar(gradient=gradient)
        yield Sparkline(max_color="#cc6666", min_color="#eedd00")

# Customizable widget
class Custom(VerticalGroup):

    def __init__(self, name:str):
        super().__init__(name=name)
        self.load()
    
    def on_mount(self):
        self.run_worker(self.stream_logs(), exclusive=True)
    
    def load(self):
        setting = self.app.settings["tabs"][self.name]
        self.container = setting.get("container", None)
        self.log_ignore = setting.get("log", {}).get("ignore", [])
        self.log_command = setting.get("log", {}).get("command", None)
        self.log_parse = setting.get("log", {}).get("parse", "line")

    async def stream_logs(self):
        log = self.query_one(RichLog)

        if self.log_command:
            proc = await asyncio.create_subprocess_shell(
                self.log_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                limit=10*1024*1024,
            )
        elif self.container:
            proc = await asyncio.create_subprocess_shell(
                f"docker logs -f {self.container}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        else:
            log.write(":(\nNo log command or docker container")
            return
        try:
            while line := await proc.stdout.readline():
                line = line.decode().strip()
                if self.log_parse: line = eval(self.log_parse)
                if any(ignore in line for ignore in self.log_ignore): continue
                log.write(line)
        except asyncio.CancelledError:
            proc.terminate()
            raise
    
    def compose(self) -> ComposeResult:
        yield Command(self.name, self.container)
        yield RichLog()

class Command(Label):
    def __init__(self, parent_name:str, parent_container:str):
        super().__init__()
        self.parent_name = parent_name
        self.parent_container = parent_container
        self.load()

    def on_mount(self):
        if not self.exec: return
        self.run_worker(self.update_content(), exclusive=True)
        self.set_interval(5, lambda: self.run_worker(self.update_content(), exclusive=True))
    
    def load(self):
        setting = self.app.settings["tabs"][self.parent_name]
        self.exec = setting.get("command", {}).get("exec", None)
        if not self.exec:
            self.display = False
            return
        self.display = True
        if self.parent_container:
            self.exec = f"docker exec {self.parent_container} {self.exec}"
        self.parse = setting.get("command", {}).get("parse", None)
    
    async def update_content(self):
        proc = await asyncio.create_subprocess_shell(
            self.exec,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode().strip()
        if self.parse:
            output = eval(self.parse)
        self.update(output)

if __name__ == "__main__":
    app = QuickDash()
    app.run()
