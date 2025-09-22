from __future__ import annotations
import os
from pathlib import Path
import logging

APP_NAME = "termgrid"

def get_data_dir() -> Path:
    # %APPDATA%/termgrid en Windows, ~/.local/share/termgrid en Linux, ~/Library/Application Support/termgrid en macOS
    env = os.getenv("APPDATA")
    if env:  # Windows
        base = Path(env)
    else:
        home = Path.home()
        if os.name == "posix":
            if "darwin" in os.sys.platform:  # macOS
                base = home / "Library" / "Application Support"
            else:
                base = home / ".local" / "share"
        else:
            base = home
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_db_path() -> Path:
    return get_data_dir() / "servers.db"

def setup_logging(level: int = logging.INFO) -> None:
    log_dir = get_data_dir()
    logfile = log_dir / "termgrid.log"
    logging.basicConfig(
        filename=logfile,
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )