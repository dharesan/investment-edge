from __future__ import annotations

import json
from pathlib import Path
import argparse
import logging

from adobe_api import load_credentials, fetch_access_token

from PyPDF2 import PdfReader


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def extract_text_from_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    text_parts = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            # Best-effort: skip pages that fail
            continue
    return "\n\n".join(text_parts)


def main(credentials_path: Path, inputs_dir: Path, outputs_dir: Path) -> None:
    creds = load_credentials(credentials_path)
    token = fetch_access_token(creds)

    outputs_dir.mkdir(parents=True, exist_ok=True)
    token_path = outputs_dir / "token.txt"
    token_path.write_text(token)
    logging.info("Saved access token to %s", token_path)

    texts_dir = outputs_dir / "texts"
    texts_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted([p for p in inputs_dir.glob("*.pdf") if p.is_file()])
    if not pdf_files:
        logging.warning("No PDF files found in %s", inputs_dir)
        return

    for pdf_file in pdf_files:
        logging.info("Processing %s", pdf_file.name)
        text = extract_text_from_pdf(pdf_file)
        out_file = texts_dir / f"{pdf_file.stem}.txt"
        out_file.write_text(text)
        logging.info("Wrote extracted text to %s", out_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch token and extract PDFs")
    parser.add_argument("--credentials", default=Path("./761BlackAardwolf-4199879-OAuth Server-to-Server.json"), type=Path)
    parser.add_argument("--inputs", default=Path("./inputs"), type=Path)
    parser.add_argument("--outputs", default=Path("./outputs"), type=Path)
    args = parser.parse_args()
    main(args.credentials, args.inputs, args.outputs)
