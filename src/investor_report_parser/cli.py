from __future__ import annotations

import argparse
from pathlib import Path

from .excel_exporter import write_workbook
from .statement_parser import parse_pdf


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert an investor report PDF into Excel sheets.")
    parser.add_argument("--pdf", required=True, type=Path, help="Input PDF path")
    parser.add_argument("--output", required=True, type=Path, help="Output Excel path")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    result = parse_pdf(args.pdf)
    write_workbook(result, args.output)
    print(f"Wrote {len(result.blocks)} statement sheet(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())