# Investor Report PDF to Excel Parser

This project converts investor reports from PDF into structured Excel workbooks without using an LLM.

The parser is designed for financial statements that appear as text-based tables inside earnings releases, annual reports, and quarterly reports.

## Architecture

1. PDF text extraction
   - Uses `pdftotext -layout` to preserve table alignment from the PDF text layer.
   - Falls back cleanly at the statement level if a page has no useful text.

2. Statement detection
   - Detects statement blocks by matching known headings such as:
     - `Condensed consolidated statement of profit or loss and other comprehensive income`
     - `Condensed consolidated statement of financial position`
     - `Condensed consolidated statement of cash flows`
   - Each statement is exported to its own sheet.

3. Table parsing
   - Parses rows deterministically using whitespace column boundaries.
   - Preserves negatives written as parentheses, commas in thousands, blank cells, and `*` footnotes.
   - Handles wrapped labels and subtotal rows that omit an explicit label.

4. Excel export
   - Writes a summary sheet with the extracted statement inventory.
   - Writes one worksheet per statement with source metadata and the parsed rows.

## Why this approach

- No language model is needed to understand the report.
- Output is stable and reproducible.
- The parser can be tuned with issuer-specific statement templates when the report format changes.

## Files

- `src/investor_report_parser/cli.py`: command-line entry point.
- `src/investor_report_parser/pdftotext_reader.py`: PDF text extraction wrapper.
- `src/investor_report_parser/statement_parser.py`: statement segmentation and row parsing.
- `src/investor_report_parser/number_parser.py`: financial number normalization.
- `src/investor_report_parser/excel_exporter.py`: Excel workbook writer.
- `src/investor_report_parser/config.py`: statement templates and aliases.

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the parser:

```bash
python -m investor_report_parser.cli \
  --pdf "Grab-Reports-Q1-2026-Results.pdf" \
  --output "grab_q1_2026.xlsx"
```

## Extending to other issuers

Add or adjust statement aliases in `src/investor_report_parser/config.py`.
If a report uses a different layout, update the statement template columns and parsing heuristics in `statement_parser.py`.