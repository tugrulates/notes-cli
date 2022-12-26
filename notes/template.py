"""Generate paths from templates."""

from pathlib import Path
from typing import Optional


def generate(
    template: str, target: Optional[Path] = None, **kwargs: str
) -> Optional[str]:
    """Replace tokens in template and write generated file."""
    path = Path(__file__).parent / "templates" / template
    with path.open("r", encoding="utf-8") as file:
        content = file.read()
    for key, value in kwargs.items():
        content = content.replace(f"{{{{ {key} }}}}", value)
    if target:
        with target.open("w", encoding="utf-8") as file:
            file.write(content)
        return None
    return content
