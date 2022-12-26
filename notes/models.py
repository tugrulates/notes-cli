"""Manage content and properties of notes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from functools import cached_property, total_ordering
from itertools import chain
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import yaml
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter.index import front_matter_plugin

Table = List[Dict[str, str]]


@dataclass
class Block:
    """Single token block in note."""

    kind: str
    content: str = ""
    children: list[Block] = field(default_factory=list)

    @staticmethod
    def parse_file(path: Path) -> Block:
        """Parse blocks from markdown file."""
        content = path.read_text(encoding="utf-8")
        tokens = MarkdownIt().use(front_matter_plugin).enable("table").parse(content)
        stack = [Block("root")]
        for token in tokens:
            if token.type.endswith("_open"):
                stack.append(Block(token.type.removesuffix("_open")))
                stack[-2].children.append(stack[-1])
            elif token.type.endswith("_close"):
                if not stack[-1].kind == token.type.removesuffix("_close"):
                    raise ValueError("error parsing markdown file", token)
                stack.pop()
            else:
                stack[-1].children.append(Block(token.type, token.content))
        if len(stack) != 1:
            raise ValueError("error parsing markdown file")
        return stack[0]

    def inline(self) -> str:
        """Recursive contents of block."""
        return self.content + "".join(x.inline() for x in self.children)

    def each(self, kind: str) -> Iterator[Block]:
        """Yield all children with given kind."""
        for x in self.children:
            if x.kind == kind:
                yield x

    def only(self, kind: str) -> Block:
        """Return the only assumed children with given kind."""
        try:
            return next(self.each(kind))
        except StopIteration:
            return Block(kind)


class State(Enum):
    """State of a note."""

    STUB = 1
    DRAFT = 2
    READY = 3
    PUBLIC = 4


@total_ordering
class Tag:
    """A tag on a note."""

    def __init__(self, name: str, group: str):
        """Initialize tag with its group."""
        self._name = name.lstrip("#")
        self._group = group.lstrip("#")

    @property
    def name(self) -> str:
        """Return the name of the without the leading hashtag."""
        return self._name

    @property
    def group(self) -> str:
        """Return the kebab-case color of the tag."""
        return self._group

    def __lt__(self, obj: Tag) -> bool:
        """Compare tags by name."""
        return (self.name) < (obj.name)

    def __str__(self) -> str:
        """Tag name with hashtag prepended."""
        return f"#{self.name}"

    def __repr__(self) -> str:
        """Tag object repr."""
        return f'Tag("#{self.name}", "#{self.group}")'


class Note:
    """A single Markdown note."""

    def __init__(self, note_vault: Vault, path: Path):
        """Initialize note from file path."""
        self._vault = note_vault
        self._path = path

    @property
    def vault(self) -> Vault:
        """Return the vault that this note belongs in."""
        return self._vault

    @property
    def path(self) -> Path:
        """Return path of the note inside the vault."""
        return self._path

    @property
    def name(self) -> Path:
        """Return name of the node."""
        return self._path.relative_to(self.vault.path).with_suffix("")

    @cached_property
    def root(self) -> Block:
        """Return commonmark ast node for the whole node."""
        return Block.parse_file(self.path)

    @cached_property
    def meta(self) -> Dict[str, Any]:
        """Return YAML frontmatter data."""
        matter = self.root.only("front_matter").inline()
        # wrap template values in string
        matter = re.sub(r"({{.*?}})", r'"\g<1>"', matter)
        return yaml.safe_load(matter) or {}

    @property
    def state(self) -> State:
        """Return the state of the note."""
        meta_state = self.meta.get("state")
        if not isinstance(meta_state, str):
            return State.STUB
        return {
            "stub": State.STUB,
            "draft": State.DRAFT,
            "ready": State.READY,
            "public": State.PUBLIC,
        }[meta_state]

    @property
    def date(self) -> Optional[date]:
        """Return the date when the note was written."""
        meta_date = self.meta.get("date")
        if not isinstance(meta_date, date):
            return None
        return meta_date

    @property
    def location(self) -> Optional[str]:
        """Return the location where the note was written."""
        meta_location = self.meta.get("date")
        if not isinstance(meta_location, str):
            return None
        return meta_location

    @property
    def tags(self) -> List[Tag]:
        """Return the location where the note was written."""
        meta_tags = self.meta.get("tags")
        if not isinstance(meta_tags, list):
            return []
        return [tag for tag in self.vault.all_tags if tag.name in meta_tags]

    @cached_property
    def tables(self) -> List[Table]:
        """Return the tables in the note."""
        tables = []
        for table in self.root.each("table"):
            headers = [th.inline() for th in table.only("thead").only("tr").each("th")]
            headers = ["-".join(x.lower().split()) for x in headers]
            tables.append(
                [
                    {headers[i]: td.inline() for i, td in enumerate(tr.each("td"))}
                    for tr in table.only("tbody").each("tr")
                ]
            )
        return tables

    def __str__(self) -> str:
        """Note path relative to vault root."""
        return f"{self.name}"

    def __repr__(self) -> str:
        """Note object repr."""
        return f'Note({self.vault}, "{self.name}")'


class Vault:
    """A note vault containing all the notes."""

    def __init__(self, path: Path, *, tags_note: Optional[Path]):
        """Initialize vault with optional meta data."""
        self._path = path
        self._tags_note = self.note(tags_note) if tags_note else None

    @property
    def path(self) -> Path:
        """Return filesystem path of vault."""
        return self._path

    def notes(self, pattern: Path) -> Iterator[Note]:
        """Return all notes in vault."""
        queries = [
            (pattern / "**" / "*").with_suffix(".md"),
            pattern.with_suffix(".md"),
        ]
        for x in chain(*(sorted(self.path.glob(str(q))) for q in queries)):
            yield Note(self, x)

    def note(self, name: Path) -> Note:
        """Return the note with given note name."""
        return Note(self, (self.path / name).with_suffix(".md"))

    def tags(self, pattern: Path) -> List[Tag]:
        """Return all tags in the vault using the meta tags note."""
        if pattern == Path("*") and self.all_tags:
            return self.all_tags
        notes = self.notes(pattern)
        return sorted(set(chain(*(note.tags for note in notes))))

    @cached_property
    def all_tags(self) -> List[Tag]:
        """All tags from the tags note."""
        if not self._tags_note:
            return []
        tags = []
        groups = [x["group"] for x in self._tags_note.tables[0]]
        meta_tags = [x["tag"] for x in self._tags_note.tables[1]]
        group = "unknown"
        for meta_tag in meta_tags:
            if meta_tag in groups:
                group = meta_tag.lstrip("#")
            tags.append(Tag(meta_tag, group))
        return tags

    def __repr__(self) -> str:
        """Vault object repr."""
        return f'Vault("{self.path}")'
