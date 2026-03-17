# Zomboid Server Manager

<img src="./pics/zomboid_server_manager.gif" alt="zomboid_server_manager" height="450" width="750" />

A Python-based server management tool for dedicated Project Zomboid servers on Linux. It automates server lifecycle management including scheduled restarts, world backups, and Steam Workshop mod update detection via web scraping.

**Created by:** [Mr_Pink47 (pink9)](https://steamcommunity.com/id/Mr_Pink47/)
**Discord:** pink9
**Version:** 1.10.0

---

## Features

- **Automated Server Lifecycle** - Handles cold starts, graceful shutdowns, and scheduled restarts on a 4-hour cycle with in-game player warnings via RCON.
- **Steam Workshop Mod Monitoring** - Scrapes the Steam Workshop every 30 minutes to detect mod updates, automatically triggering a server restart when mods are out of sync.
- **World Backups** - Creates timestamped `.tgz` backups of the world save directory on start, restart, and shutdown.
- **RCON Integration** - Sends in-game server messages and commands through [gorcon/rcon-cli](https://github.com/gorcon/rcon-cli).
- **Optional Host Reboot** - Optionally reboots the host machine after a configurable number of server restart cycles (supports both native Linux and WSL environments).
- **Graceful Signal Handling** - Catches `SIGINT` (Ctrl+C) to safely save, back up, and shut down the server. A second `SIGINT` forces an immediate exit.

---

## Prerequisites

- **OS:** Linux x64 (tested on dedicated server and WSL1/2 environments)
- **Python:** >= 3.10
- **RCON Client:** [gorcon/rcon-cli](https://github.com/gorcon/rcon-cli/releases) extracted to `/usr/bin`
- **Project Zomboid Dedicated Server** installed and configured

---

## Installation

1. Clone or download this repository.

2. Install Python dependencies (a virtual environment is recommended):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Download and install the [gorcon rcon-cli](https://github.com/gorcon/rcon-cli/releases) binary to `/usr/bin`:

```bash
# Example (check for the latest release version)
tar -xzf rcon-*.tar.gz
sudo mv rcon /usr/bin/
```

4. Copy `server_config.json` into the same directory as `zomboid_server_manager.py` and edit it to match your server's paths and RCON credentials (see [Configuration](#configuration)).

---

## Configuration

All configuration is managed through `server_config.json`. Both `server_config.json` and `zomboidSoup.py` must reside in the same directory as `zomboid_server_manager.py`.

```json
{
    "server_config": {
        "start_server_command": "nohup /home/user/pzserver/./start-server.sh >/dev/null 2>&1 &",
        "server_ini_path": "/home/user/Zomboid/Server/servertest.ini",
        "mod_csv_path": "/home/user/Zomboid/Server/zomboid_mod_updateList.csv",
        "backup_folder_path": "/home/user/Zomboid/backups",
        "world_dict_path": "/home/user/Zomboid/Saves/Multiplayer/servertest/",
        "server_shell_process_name": "start-server.sh",
        "server_binary_process_name": "ProjectZomboid64",
        "rcon_local_ip": "127.0.0.1",
        "rcon_local_port": 27015,
        "rcon_password": "rcon_password",
        "reboot_enabled": false,
        "reboot_threshold": 3
    }
}
```

| Key | Description |
|-----|-------------|
| `start_server_command` | Shell command used to launch the PZ dedicated server. (Edit the path to your $USER/pzserver/ dir) |
| `server_ini_path` | Absolute path to your `servertest.ini`. This is used to read the `WorkshopItems=` line for mod IDs. |
| `mod_csv_path` | Path where the mod update tracking CSV will be written. (You can update the path and filename, but it must end in .csv)|
| `backup_folder_path` | Directory where you want to store your world backups (Saves are created on each stop and start of the server, and before a mod update reboot) |
| `world_dict_path` | Path to the multiplayer world save directory (Used for backups). |
| `server_shell_process_name` | Name of the server start script process (Used for process cleanup - Can be left as-is). |
| `server_binary_process_name` | Name of the server binary process (Used for process cleanup - Can be left as-is). |
| `rcon_local_ip` | RCON bind address (Default `127.0.0.1` for local network, otherwise if you're hosting remotely, replace with the server address). |
| `rcon_local_port` | RCON port (Must match your server's RCON config). |
| `rcon_password` | RCON password (Must match your server's RCON config). |
| `reboot_enabled` | If set `true`, the host machine reboots after the pzserver has restarted `reboot_threshold` times. |
| `reboot_threshold` | Number of internal pzserver restarts before triggering a host reboot. |

---

## Usage

### Running Manually

```bash
python3 zomboid_server_manager.py
```

### Running on Boot via Crontab

To have the server manager start automatically on system boot (required for the reboot counter to function properly):

```bash
crontab -e
```

Add the following line (be sure to update the path to where the script is!):

```
@reboot /usr/bin/python3 /path/to/zomboid_server_manager.py
```

### Stopping the Server

Press `Ctrl+C` in the terminal running the manager. This triggers a graceful shutdown sequence that saves the world, creates a backup, and then kills the server processes. Pressing `Ctrl+C` a second time forces an immediate exit.

---

## How It Works

### Server Lifecycle

1. On launch, any existing server instances are killed.
2. A world backup is created, then a server start command is executed.
3. After a 5-minute startup grace period, a "Server will restart in 4 hours" message is sent via RCON to the internal pzserver.
4. A scheduler is then initiated which starts the following recurring jobs:
   - **`Every 30 minutes`:** Check Steam Workshop for mod updates 
        - **IMPORTANT NOTE: If a mod updates during server up-time, the server will initiate a full restart cycle after 5 minutes!**
   - **`Every 3 hours`:** Send a "1 hour until restart" warning.
   - **`Every 4 hours`:** Execute a full restart cycle (warnings, save, backup, stop, start).



### Mod Update Detection (`zomboidSoup.py`)

The `zomboidSoup` module reads workshop mod IDs from `servertest.ini`, scrapes each mod's Steam Workshop page for its "last updated" timestamp using BeautifulSoup, and compares the results against a local CSV (`mod_csv_path`). If any timestamps differ, the server is flagged for restart.

### IMPORTANT NOTE:
The server will loop between Steps 1-4 infinitely until the server administrator manually stops the process, or the host is shutdown/reset. 

You can safely press Ctrl+C once to kill the server process gracefully. If you press it twice, the process will be killed instantly!
You may run the risk of losing your current WorldDict, or corrupting your backup in thise case. You have been warned! 

Should you want to reboot the host after so many pzserver reset cycles, this can be done by setting "reboot_enabled" to "true" in the server_config.json.

--- 
## Dependencies

| Package | Purpose |
|---------|---------|
| `beautifulsoup4` | HTML parsing for Steam Workshop scraping |
| `html5lib` | HTML5 parser backend for BeautifulSoup |
| `requests` | HTTP requests to Steam Workshop |
| `pandas` | DataFrame operations for mod list comparison |
| `numpy` | NaN handling in mod timestamp data |
| `psutil` | Process iteration and management |
| `schedule` | Lightweight job scheduling |
  **See `requirements.txt` for dependency versions used**
