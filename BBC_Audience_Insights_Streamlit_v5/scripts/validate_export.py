from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pypdf import PdfReader

from src.pptx_service import validate_pptx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.path.suffix.lower() == ".pptx":
        validate_pptx(args.path)
        print("PPTX validation passed.")
    elif args.path.suffix.lower() == ".pdf":
        pages = len(PdfReader(args.path).pages)
        if pages != 9:
            raise SystemExit(f"Expected 9 PDF pages; found {pages}.")
        print("PDF validation passed.")
    else:
        raise SystemExit("Supported validation types are .pptx and .pdf.")


if __name__ == "__main__":
    main()
