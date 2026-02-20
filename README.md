placeholder (logo)

QuickDash is a customizable TUI dashboard.
- It can be used over ssh.
- The configs are live loaded!
## Screenshots
placeholder

# Installation
pipx, uvx (TODO)

Installation Script (TODO)

*OR, clone the repo, install deps, and run main.py!*
# Configuration
The configuration file can be found in
- a) `settings.toml` inside the folder you installed QuickDash in, if you installed via cloning the repo or using the installation script.
- b) ~~`~/.config/quickdash/settings.toml` if you installed using pipx or uvx~~ <-- WIP

The settings.toml contains an example configuration. You can edit that to customize your setup.

## disks:
```toml
[[disks]]
name = "ROOT"
path = "/"

[[disks]]
name = "HOME"
path = "/home"
```
The `disks` section is where the disk usage shown in the top bar is configured.
- `name` is the displayed name of each disk.
- `path` is the path to check disk usage
## tabs:
```toml
[tabs."Tab Name"]
container = "container name"
command = { exec = "command to run", parse = "parsing code" }
log = { command = "log command", ignore = ["strings to ignore"], parse = "parsing code" }
```
The `tabs` section is where tabs containing log viewers and custom command outputs are configured.
### If tab is for a docker container:
1. Set `container` to your docker container name.
(or, for some reason you don't want to, follow [this](#if-tab-is-not-for-a-docker-container))

2. If you want to see a custom command output, set `command`.
    - `command.exec` is the disired command to run inside the container.
        
        (because the container is specified, the actual command will look like `docker exec {container} {command.exec}`)
    - `command.parse` is optional. It parses the command output using the given python code snippet. The variable `output` contains the command output.
    - ex) `command = { exec = "date", parse = "f'The current date and time is: {output}'" }` 

3. The log is fetched using `docker logs -f {container}` by default.
    - The command to use can be specified by setting `log.command = "your command"`
    - `log.ignore = []` is optional. It can be set to ignore lines containing the strings specified.
    - `log.parse` is optional. It parses each line of log using the given python code snippet. The variable `line` contains one line of log.

```toml
# Example using docker container (itzg/docker-minecraft-server)
[tabs."Minecraft Server"]
container = "minecraft-mc-1"
command = { exec = "rcon-cli list", parse = "f'online: {output.split(' ')[2]}/{output.split(' ')[7]}'" }
#           ^^^^ This will execute "docker exec minecraft-mc-1 rcon-cli list"
log = { ignore = ["RCON","villager"], parse = "f'the server says: {line}'" }
```
### If tab is not for a docker container
*LXC, VM, some service on host, etc...*

1. Do not specify `container` (which is ment for docker)

2. If you want to see a custom command output, set `command`.
    - `command.exec` is the disired command to run.
    - `command.parse` is optional. it parses the command output using the given python code snippet. the variable `output` contains the command output.
    - ex) `command = { exec = "date", parse = "f'The current date and time is: {output}'" }`

3. You can fetch logs by setting `log`
    - Set `log.command` to fetch logs. Use the `-f` flag if available.
    - `log.ignore = []` is optional. It can be set to ignore lines containing the strings specified.
    - `log.parse` is optional. It parses each line of log using the given python code snippet. The variable `line` contains one line of log.

```toml
# Example using journalctl and date
[tabs."System Journal"]
command = { exec = "date", parse = "f'The current date and time is: {output}'" }
log = { command = "journalctl -f", ignore = ["CRON","ACPI"], parse = "f'[System Journal] ==> {line}'" }
```