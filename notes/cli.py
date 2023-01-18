"""A CLI tool to manage a repository of markdown files."""

from pathlib import Path
from typing import Iterator, Optional

import typer
from jinja2 import Environment, PackageLoader, select_autoescape
from rich.console import Console
from rich.syntax import Syntax

from notes import config
from notes.models import Vault

app = typer.Typer(help=__doc__)
tag = typer.Typer()
blog = typer.Typer()
obsidian = typer.Typer()
app.add_typer(tag, name="tag", help="Manage tags.", rich_help_panel="Modules")
app.add_typer(blog, name="blog", help="Manage blog.", rich_help_panel="Modules")
app.add_typer(
    obsidian, name="obsidian", help="Manage Obsidian.", rich_help_panel="Modules"
)
cfg = config.load()
templates = Environment(
    loader=PackageLoader(config.APP), autoescape=select_autoescape()
)
console = Console()


def get_vault() -> Vault:
    """Create new vault from config values."""
    return Vault(cfg.vault, tags_note=cfg.tags_note)


def set_vault(ctx: typer.Context, vault: Path) -> Path:
    """Register vault parameter."""
    if ctx.resilient_parsing:
        return vault
    if not vault.is_dir():
        raise typer.BadParameter(f"Vault '{vault}' does not exist.")
    cfg.vault = vault
    return vault


def complete_note(incomplete: str) -> Iterator[str]:
    """Return note paths using vault from config for autocompletion."""
    pattern = incomplete
    if not pattern.endswith("*"):
        pattern += "*"
    for note in get_vault().notes(Path(pattern)):
        yield str(note.name).replace(" ", "\\ ")


def validate_note(ctx: typer.Context, note: Path) -> Path:
    """Validate note parameter."""
    if ctx.resilient_parsing:
        return note
    path = get_vault().note(note).path
    if not path.is_file():
        raise typer.BadParameter(f"Note '{note}' does not exist ('{path}').")
    return note


PatternArg = typer.Argument(
    "*", help="Note name pattern.", autocompletion=complete_note
)


@app.command("config")
def configure_app(
    vault: Path = typer.Option(  # noqa: B008
        cfg.vault,
        is_eager=True,
        prompt=not cfg.vault,
        exists=True,
        file_okay=False,
        help="Vault directory containing notes. Specify at least once.",
        callback=set_vault,
    ),
    tags_note: Path = typer.Option(  # noqa: B008
        cfg.tags_note,
        prompt=not cfg.tags_note,
        help="Special note containing tags.",
        autocompletion=complete_note,
        callback=validate_note,
    ),
) -> None:
    """Update or print configuration."""
    cfg.tags_note = tags_note
    cfg.dump()
    console.print_json(cfg.json())


@app.command("list")
def list_notes(
    pattern: Path = PatternArg,
) -> None:
    """List notes."""
    for note in get_vault().notes(pattern):
        console.print(note)


@tag.command(name="list")
def list_tags(
    pattern: Path = PatternArg,
) -> None:
    """List tags."""
    for tag in get_vault().tags(pattern):
        console.print(tag.name)


@tag.command(name="css")
def generate_tag_css(
    pattern: Path = PatternArg,
    *,
    rich: bool = True,
    output: Optional[Path] = None,
) -> None:
    """Output stylesheet for tags."""
    result = templates.get_template("tag.css").render(tags=get_vault().tags(pattern))
    if output:
        output.write_text(result, encoding="utf-8")
    elif rich:
        console.print(Syntax(result, "css", line_numbers=True))
    else:
        print(result)


@blog.command("css")
def generate_blog_css(
    blog: Path = typer.Option(  # noqa: B008
        cfg.blog,
        prompt=not cfg.blog,
        exists=True,
        file_okay=False,
        help="Repo directory containing blog code. Specify at least once.",
    ),
) -> None:
    """Generate css styles for tags."""
    generate_tag_css(
        Path("blog"),
        output=blog / "assets/css/tag.css",
    )


@obsidian.command(name="css")
def generate_obsidian_css() -> None:
    """Generate css styles for tags."""
    generate_tag_css(Path("*"), output=cfg.vault / ".obsidian/snippets/tag.css")


if __name__ == "__main__":
    app()
