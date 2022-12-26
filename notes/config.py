"""App configuration."""


import json
from pathlib import Path
from typing import Optional

import typer
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder

APP = "notes"
CONFIG_PATH = Path(typer.get_app_dir(APP)) / "config.json"


@dataclass
class Config:
    """App configuration."""

    vault: Path = Path(".")
    tags_note: Path = Path("meta") / Path("Tags")
    blog: Optional[Path] = None

    def dump(self) -> None:
        """Write config to config file."""
        CONFIG_PATH.write_text(
            json.dumps(self, indent=4, default=pydantic_encoder), encoding="utf-8"
        )


def load() -> Config:
    """Load config from config file."""
    if not CONFIG_PATH.is_file():
        return Config()
    return Config(**dict(json.loads(CONFIG_PATH.read_text(encoding="utf-8"))))
