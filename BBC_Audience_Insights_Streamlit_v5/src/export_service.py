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
    # Each Streamlit session gets an isolated LibreOffice profile. Without
    # this, simultaneous or rapidly repeated exports can contend for the same
    # profile and fail silently even though the generated PPTX is valid.
    with tempfile.TemporaryDirectory(prefix="bbc-libreoffice-profile-") as profile:
        profile_uri = Path(profile).resolve().as_uri()
        cmd = [
            binary,
            f"-env:UserInstallation={profile_uri}",
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
        detail = (result.stderr or result.stdout or "No diagnostic output was returned.").strip()
        raise ConversionError(f"LibreOffice conversion failed: {detail}")
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
