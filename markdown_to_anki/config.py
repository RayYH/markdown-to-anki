import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def _load_file() -> dict:
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    config_path = Path(xdg) / "markdown-to-anki" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _from_file(key: str, default: Any) -> Any:
    return _load_file().get(key, default)


ANKI_BASE_URL: str = os.getenv(
    "ANKI_URL", _from_file("anki_url", "http://localhost:8765")
)
DEFAULT_DECK = "Default"
DEFAULT_MODEL = "m2a-basic"
TIME_RANGE: int = int(
    os.getenv("TIME_RANGE", _from_file("time_range", 2 * 3600))
)
MD_FOLDER: str = os.getenv("MD_FOLDER", _from_file("md_folder", "anki"))
RESOURCES_DIR: str | None = os.getenv(
    "M2A_RESOURCES_DIR", _from_file("resources_dir", None)
)
