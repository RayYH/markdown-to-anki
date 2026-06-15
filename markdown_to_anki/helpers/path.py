import os
from importlib.resources import files
from pathlib import Path

_resources_override: Path | None = None


def set_resources_dir(path: str | None) -> None:
    global _resources_override
    _resources_override = Path(path).expanduser().resolve() if path else None


def get_resources_dir() -> Path | None:
    return _resources_override


def ensure_dir(filename: str):
    os.makedirs(os.path.dirname(filename), exist_ok=True)


def user_models_dir() -> Path | None:
    if _resources_override:
        models_dir = _resources_override / "models"
        if models_dir.is_dir():
            return models_dir
    return None


def read_resource(path: str) -> str:
    if _resources_override:
        custom = _resources_override / path
        if custom.exists():
            return custom.read_text(encoding="utf-8")
    ref = files("markdown_to_anki").joinpath("resources")
    for part in path.split("/"):
        ref = ref.joinpath(part)
    return ref.read_text(encoding="utf-8")
