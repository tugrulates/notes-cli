"""Unittests for the CLI."""


import importlib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from notes import cli, config
from notes.config import Config

runner = CliRunner()


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Test empty vault."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "meta").mkdir()
    (vault / "meta" / "Tags.md").write_text(
        "\n".join(
            [
                "| Group  | Color |",
                "| :----: | :---: |",
                "| #abc   | color |",
                "",
                "| Tag    | Scope |",
                "| :----: | :---: |",
                "| #abc   | test  |",
                "| #def   | test  |",
            ]
        )
    )
    (vault / "Note1.md").write_text(
        "\n".join(
            [
                "## Subitle",
                "",
                "Sample note with no frontmatter.",
                "",
                "Some more lines here.",
            ]
        )
    )
    (vault / "Note2.md").write_text(
        "\n".join(
            [
                "---",
                "state: draft",
                "date: 2000-01-01",
                "tags: [def]",
                "---",
                "",
                "",
                "Note with frontmatter.",
            ]
        )
    )
    return vault


@pytest.fixture(autouse=True)
def cfg(vault: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """Fixture for prefs."""
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    cfg = Config()
    cfg.vault = vault
    cfg.dump()
    importlib.reload(cli)
    return cfg


def test_bare() -> None:
    """Test invocation with no arguments."""
    result = runner.invoke(cli.app)
    assert result.exit_code != 0
    assert "Usage:" in result.stdout


def test_help() -> None:
    """Test help."""
    result = runner.invoke(cli.app, "--help")
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


def test_vault_missing() -> None:
    """Test that command with no vault fail."""
    result = runner.invoke(cli.app, "--vault missing-dir list")
    assert result.exit_code != 0
    assert "missing-dir" in result.stdout


def test_tags_note_missing() -> None:
    """Test that command with no vault fail."""
    result = runner.invoke(cli.app, "--tags-note missing-dir tag list")
    assert result.exit_code != 0
    assert "missing-dir" in result.stdout


def test_save_vault_to_config() -> None:
    """Test skipping vault on subsequent invocations."""
    result = runner.invoke(cli.app, "--vault . list")
    assert result.exit_code == 0
    cfg = config.load()
    assert cfg.vault == Path(".")


def test_note_list() -> None:
    """Test listing notes in vault."""
    result = runner.invoke(cli.app, "list")
    assert result.exit_code == 0
    assert result.stdout.strip().split("\n") == [
        str(Path("meta/Tags")),
        str(Path("Note1")),
        str(Path("Note2")),
    ]


def test_note_list_with_glob_pattern() -> None:
    """Test listing notes in vault."""
    result = runner.invoke(cli.app, "list Note*")
    assert result.exit_code == 0
    assert result.stdout.strip().split("\n") == [
        str(Path("Note1")),
        str(Path("Note2")),
    ]


def test_note_list_with_folder_pattern() -> None:
    """Test listing notes in vault."""
    result = runner.invoke(cli.app, "list meta*")
    assert result.exit_code == 0
    assert result.stdout.strip().split("\n") == [
        str(Path("meta/Tags")),
    ]


def test_note_list_with_missing_pattern() -> None:
    """Test listing notes in vault."""
    result = runner.invoke(cli.app, "list nada")
    assert result.exit_code == 0
    assert result.stdout == ""


def test_tag_list() -> None:
    """Test listing tags in vault."""
    result = runner.invoke(cli.app, "tag list")
    assert result.exit_code == 0
    assert result.stdout.strip().split("\n") == ["#abc", "#def"]


def test_tag_list_with_pattern() -> None:
    """Test listing tags in vault."""
    result = runner.invoke(cli.app, " tag list Note*")
    assert result.exit_code == 0
    assert result.stdout.strip().split("\n") == ["#def"]


def test_tag_list_with_missing_pattern() -> None:
    """Test listing tags in vault."""
    result = runner.invoke(cli.app, " tag list nada")
    assert result.exit_code == 0
    assert result.stdout == ""


def test_tag_css() -> None:
    """Test listing tags in vault."""
    result = runner.invoke(cli.app, "tag css --no-rich")
    assert result.exit_code == 0
    assert (
        '.tag[href$="/tags/def/"], .tag[href="#def"] '
        "{ --tag-group: var(--tag-group-abc); }"
    ) in result.stdout
    print(result.stdout)
