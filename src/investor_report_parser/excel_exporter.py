from __future__ import annotations

from pathlib import Path

from .models import ParseResult


def write_workbook(result: ParseResult, output_path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    summary_sheet.append(["Statement", "Sheet", "Pages", "Rows", "Heading"])
    summary_sheet.freeze_panes = "A2"

    header_font = Font(bold=True)
    for cell in summary_sheet[1]:
        cell.font = header_font

    for block in result.blocks:
        column_headers = list(block.column_headers)
        if not column_headers:
            max_values = max((len(row.values) for row in block.rows), default=0)
            column_headers = [f"Column {index + 1}" for index in range(max_values)]

        summary_sheet.append([
            block.spec.name,
            block.spec.sheet_name,
            f"{block.start_page}-{block.end_page}",
            len(block.rows),
            block.heading,
        ])

        sheet = workbook.create_sheet(title=block.spec.sheet_name)
        sheet.freeze_panes = "A2"
        sheet.append(["Section", "Label", *column_headers, "Raw Line"])
        for cell in sheet[1]:
            cell.font = header_font

        for row in block.rows:
            sheet.append([row.section, row.label, *row.values, row.raw_line])

        for column in sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                value = "" if cell.value is None else str(cell.value)
                max_length = max(max_length, len(value))
            sheet.column_dimensions[column_letter].width = min(max_length + 2, 60)

    for column in summary_sheet.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))
        summary_sheet.column_dimensions[column_letter].width = min(max_length + 2, 60)

    workbook.save(output_path)
