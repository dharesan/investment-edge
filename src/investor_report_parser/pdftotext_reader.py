from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PdfPageText:
    page_number: int
    text: str


def extract_pages(pdf_path: Path) -> list[PdfPageText]:
    command = ["pdftotext", "-layout", str(pdf_path), "-"]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    raw_pages = completed.stdout.split("\f")
    pages: list[PdfPageText] = []
    for page_index, page_text in enumerate(raw_pages, start=1):
        text = page_text.rstrip()
        if text:
            pages.append(PdfPageText(page_number=page_index, text=text))
    return pages


def extract_page_count(pdf_path: Path) -> int:
    command = ["pdfinfo", str(pdf_path)]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    for line in completed.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise ValueError(f"Could not determine page count for {pdf_path}")
