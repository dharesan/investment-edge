from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StatementSpec:
    name: str
    sheet_name: str
    heading_aliases: tuple[str, ...]


@dataclass
class ParsedRow:
    label: str
    values: list[Any]
    raw_line: str
    section: str = ""
    row_type: str = "data"


@dataclass
class StatementBlock:
    spec: StatementSpec
    start_page: int
    end_page: int
    heading: str
    raw_text: str
    column_headers: tuple[str, ...] = ()
    header_lines: tuple[str, ...] = ()
    rows: list[ParsedRow] = field(default_factory=list)


@dataclass
class ParseResult:
    source_pdf: Path
    blocks: list[StatementBlock]
