from __future__ import annotations

import re
import math
from pathlib import Path

from .config import STATEMENT_SPECS
from .models import ParseResult, ParsedRow, StatementBlock, StatementSpec
from .number_parser import is_numeric_token, parse_numeric_token
from .pdftotext_reader import extract_pages


SECTION_RE = re.compile(r"^[A-Z][A-Za-z0-9 ,/()&\-–'’]+:?$")


def detect_statement_spec(page_text: str) -> StatementSpec | None:
    lowered = page_text.lower()
    for spec in STATEMENT_SPECS:
        for alias in spec.heading_aliases:
            if alias.lower() in lowered:
                return spec
    return None


def build_statement_blocks(pdf_path: Path) -> list[StatementBlock]:
    pages = extract_pages(pdf_path)
    page_specs: list[tuple[int, StatementSpec, str]] = []
    for page in pages:
        spec = detect_statement_spec(page.text)
        if spec is not None:
            page_specs.append((page.page_number, spec, find_heading_line(page.text, spec)))

    blocks: list[StatementBlock] = []
    for index, (start_page, spec, heading) in enumerate(page_specs):
        end_page = page_specs[index + 1][0] - 1 if index + 1 < len(page_specs) else pages[-1].page_number
        block_pages: list[str] = []
        for page in pages:
            if not (start_page <= page.page_number <= end_page):
                continue
            if page.page_number == start_page:
                block_pages.append(slice_from_heading(page.text, spec))
            else:
                block_pages.append(page.text)
        raw_text = "\n\n".join(block_pages)
        blocks.append(
            StatementBlock(
                spec=spec,
                start_page=start_page,
                end_page=end_page,
                heading=heading,
                raw_text=raw_text,
            )
        )
    return blocks


def find_heading_line(page_text: str, spec: StatementSpec) -> str:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    for line in lines[:20]:
        lowered = line.lower()
        if any(alias.lower() in lowered for alias in spec.heading_aliases):
            return line
    return spec.name


def slice_from_heading(page_text: str, spec: StatementSpec) -> str:
    lines = page_text.splitlines()
    for index, line in enumerate(lines):
        lowered = line.lower()
        if any(alias.lower() in lowered for alias in spec.heading_aliases):
            return "\n".join(lines[index:])
    return page_text


def parse_statement_block(block: StatementBlock) -> StatementBlock:
    lines = [line.rstrip() for line in block.raw_text.splitlines()]
    rows: list[ParsedRow] = []
    header_lines: list[str] = []
    pending_label = ""
    current_section = ""
    seen_data = False

    for raw_line in lines:
        line = normalize_line(raw_line)
        if not line:
            continue
        if should_skip_line(line):
            continue
        if is_heading_line(line, block.spec):
            continue
        if not seen_data:
            if is_section_header(line):
                current_section = line.rstrip(":")
                continue
            if is_header_line(line):
                header_lines.append(line)
                continue
            if contains_numeric_token(line):
                block.column_headers = tuple(infer_column_headers(header_lines, line))
                seen_data = True
            else:
                header_lines.append(line)
                continue
        if is_section_header(line):
            current_section = line.rstrip(":")
            pending_label = ""
            continue

        if contains_numeric_token(line):
            combined = f"{pending_label} {line}".strip() if pending_label else line
            pending_label = ""
            row = parse_row(combined, current_section, block.spec)
            if row is not None:
                rows.append(row)
                seen_data = True
            continue

        if pending_label:
            pending_label = f"{pending_label} {line}".strip()
        else:
            pending_label = line

    if not block.column_headers:
        block.column_headers = tuple(infer_column_headers(header_lines, None))
    block.header_lines = tuple(header_lines)
    block.rows = rows
    return block


def normalize_line(line: str) -> str:
    return line.replace("\u00a0", " ").replace("●", " ").strip()


def should_skip_line(line: str) -> bool:
    lowered = line.lower()
    if lowered.startswith("grab reports"):
        return True
    if "summary of financial results" in lowered:
        return True
    if lowered.startswith("for inquiries regarding grab"):
        return True
    if lowered.startswith("source: grab holdings limited"):
        return True
    if lowered.startswith("*") and "amount less than" in lowered:
        return True
    return False


def is_header_line(line: str) -> bool:
    stripped = line.strip()
    lowered = stripped.lower()
    if lowered.startswith("three months ended"):
        return True
    if lowered.startswith("for the year ended"):
        return True
    if lowered.startswith("three months ended") or lowered.startswith("for the six months ended"):
        return True
    if lowered.startswith("($ in millions"):
        return True
    if "per share data" in lowered:
        return True
    if lowered in {"$", "($", "$ $", "$  $", "(unaudited)"}:
        return True
    if re.match(r"^(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?$", lowered):
        return True
    if re.match(r"^\d{4}(\s+\d{4})+$", stripped):
        return True
    if is_numeric_only_header_line(stripped):
        return True
    return False


def is_numeric_only_header_line(line: str) -> bool:
    parts = split_value_parts(line)
    if not parts:
        return False
    return all(is_numeric_token(part) or part == "$" for part in parts)


def is_heading_line(line: str, spec: StatementSpec) -> bool:
    lowered = line.lower()
    return any(alias.lower() in lowered for alias in spec.heading_aliases)


def is_section_header(line: str) -> bool:
    if is_header_line(line):
        return False
    if contains_numeric_token(line):
        return False
    stripped = line.strip()
    lowered = stripped.lower()
    if stripped.endswith(":"):
        return True
    if any(month in lowered for month in ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")):
        return False
    if len(stripped) <= 90 and SECTION_RE.match(stripped):
        return True
    return False


def contains_numeric_token(line: str) -> bool:
    parts = split_value_parts(line)
    return any(is_numeric_token(part) for part in parts)


def parse_row(line: str, current_section: str, spec: StatementSpec) -> ParsedRow | None:
    parts = split_value_parts(line)
    if not parts:
        return None

    if all(is_numeric_token(part) for part in parts) and len(parts) > 1:
        label = f"Subtotal: {current_section}" if current_section else "Subtotal"
        values = [parse_numeric_token(part) for part in parts]
        return ParsedRow(label=label, values=values, raw_line=line, section=current_section, row_type="subtotal")

    label = parts[0]
    value_tokens = parts[1:]
    if not value_tokens and contains_numeric_token(label):
        label = f"Subtotal: {current_section}" if current_section else "Subtotal"
        value_tokens = parts

    values = [parse_numeric_token(token) for token in value_tokens]

    return ParsedRow(label=label, values=values, raw_line=line, section=current_section, row_type="data")


def split_value_parts(line: str) -> list[str]:
    return [part for part in re.split(r"\s{2,}", line.strip()) if part]


def infer_column_headers(header_lines: list[str], first_data_line: str | None) -> list[str]:
    candidate_lines = [line for line in header_lines if line.strip()]
    if not candidate_lines and first_data_line:
        value_count = len(extract_value_tokens(first_data_line))
        return [f"Column {index + 1}" for index in range(value_count)]

    value_reference_line = None
    for line in reversed(candidate_lines):
        if is_numeric_only_header_line(line):
            value_reference_line = line
            break

    if value_reference_line is None and first_data_line:
        value_reference_line = first_data_line

    if value_reference_line is None:
        return [line.strip() for line in candidate_lines if line.strip()]

    reference_values = extract_value_tokens(value_reference_line)
    column_count = max(1, len(reference_values))
    label_lines = [
        line
        for line in candidate_lines
        if line != value_reference_line
        and not is_numeric_only_header_line(line)
        and not is_header_annotation_line(line)
    ]
    label_segments = [header_segments_for_line(line) for line in label_lines if header_segments_for_line(line)]
    if not label_segments:
        return [f"Column {index + 1}" for index in range(column_count)]

    headers: list[str] = []
    for column_index in range(column_count):
        pieces: list[str] = []
        for segments in label_segments:
            segment_index = min(len(segments) - 1, math.floor(column_index * len(segments) / column_count))
            piece = segments[segment_index].strip()
            if piece:
                pieces.append(piece)
        value_part = reference_values[column_index].strip()
        if value_part:
            pieces.append(value_part)
        headers.append(" ".join(pieces).strip())
    return headers


def header_segments_for_line(line: str) -> list[str]:
    segments = split_value_parts(line)
    if len(segments) > 1:
        return segments

    tokens = line.split()
    if len(tokens) >= 4 and len(tokens) % 2 == 0:
        midpoint = len(tokens) // 2
        if tokens[:midpoint] == tokens[midpoint:]:
            return [" ".join(tokens[:midpoint]).strip()]

    return [line.strip()] if line.strip() else []


def is_header_annotation_line(line: str) -> bool:
    lowered = line.lower()
    return (
        lowered.startswith("($ in millions")
        or "per share data" in lowered
        or lowered in {"(unaudited)", "$"}
    )


def extract_value_tokens(line: str) -> list[str]:
    parts = split_value_parts(line)
    if not parts:
        return []
    if all(is_numeric_token(part) or part == "$" for part in parts):
        return parts
    return parts[1:]


def parse_pdf(pdf_path: Path) -> ParseResult:
    blocks = [parse_statement_block(block) for block in build_statement_blocks(pdf_path)]
    return ParseResult(source_pdf=pdf_path, blocks=blocks)
