from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_engine import WorkbookRepository


def main():
    errors = WorkbookRepository().validate_all()
    if errors:
        print("Source validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("All eight workbooks satisfy the source-data contract.")


if __name__ == "__main__":
    main()
