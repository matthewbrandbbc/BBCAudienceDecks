from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

from pypdf import PdfReader


class ConversionError(RuntimeError):
    pass


def libreoffice_path() -> str | None:
    return shutil.which("libreoffice") or shutil.which("soffice")


def convert_with_libreoffice(source: Path, target_format: str, output_dir: Path) -> Path:
    binary = libreoffice_path()
    if not binary:
        raise ConversionError(
            "LibreOffice is not installed. On Streamlit Community Cloud it is installed through packages.txt."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        binary,
        "--headless",
        "--nologo",
        "--nolockcheck",
        "--nodefault",
        "--nofirststartwizard",
        "--convert-to",
        target_format,
        "--outdir",
        str(output_dir),
        str(source),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    target = output_dir / f"{source.stem}.{target_format.split(':')[0]}"
    if result.returncode != 0 or not target.exists():
        raise ConversionError(f"LibreOffice conversion failed: {result.stderr or result.stdout}")
    if target.suffix.lower() == ".pdf" and len(PdfReader(target).pages) != 9:
        raise ConversionError("Generated PDF does not contain exactly nine pages.")
    return target


def render_pdf_pages(pdf_path: Path, output_dir: Path) -> list[Path]:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise ConversionError("Poppler pdftoppm is not installed.")
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / "slide"
    result = subprocess.run(
        [pdftoppm, "-png", "-r", "120", str(pdf_path), str(prefix)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise ConversionError(f"PDF rendering failed: {result.stderr}")
    pages = sorted(output_dir.glob("slide-*.png"))
    if len(pages) != 9:
        raise ConversionError(f"Expected nine rendered slides; found {len(pages)}.")
    return pages

