"""
Illustrator to PDF conversion service.

Handles Adobe Illustrator (.ai) files, which come in two flavors:
  1. PDF-compatible AI files (Illustrator 9+ / CS+) — internally contain a PDF stream.
     These can be processed directly with pypdf (fastest, lossless).
  2. Legacy PostScript-based AI files — require Ghostscript or LibreOffice to render.

Conversion strategy (tried in order):
  1. pypdf direct extraction  (if the AI file is already PDF-compatible)
  2. Ghostscript rendering     (gs -dSAFER -sDEVICE=pdfwrite)
  3. LibreOffice fallback      (soffice --headless --convert-to pdf)

Page selection is applied via pypdf after the base PDF is produced.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.paths import Paths

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    PdfReader = None  # type: ignore[assignment,misc]
    PdfWriter = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


class IllustratorToPdfService:
    """Convert Adobe Illustrator (.ai) files to PDF."""

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _find_ghostscript() -> Optional[str]:
        """Return the Ghostscript executable path or None."""
        # Check PATH first
        for name in ("gswin64c", "gswin32c", "gs"):
            exe = shutil.which(name)
            if exe:
                return exe
        # Common Windows install locations
        if os.name == "nt":
            for base in (r"C:\Program Files", r"C:\Program Files (x86)"):
                gs_root = Path(base) / "gs"
                if gs_root.is_dir():
                    for sub in sorted(gs_root.iterdir(), reverse=True):
                        candidate = sub / "bin" / "gswin64c.exe"
                        if candidate.exists():
                            return str(candidate)
                        candidate = sub / "bin" / "gswin32c.exe"
                        if candidate.exists():
                            return str(candidate)
        return None

    @staticmethod
    def _find_soffice() -> str:
        """Return the LibreOffice executable path."""
        if os.name == "nt":
            for p in (
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ):
                if os.path.exists(p):
                    return p
        return "soffice"

    @staticmethod
    def _parse_page_range(range_str: str, total_pages: int) -> List[int]:
        """Parse ``'1,3,5-8'`` into a list of zero-indexed page numbers."""
        if not range_str or not range_str.strip():
            return list(range(total_pages))

        pages: set[int] = set()
        for part in range_str.strip().split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    start_s, end_s = part.split("-", 1)
                    start, end = int(start_s), int(end_s)
                    if start > end:
                        start, end = end, start
                    for p in range(start, end + 1):
                        pages.add(p - 1)
                except ValueError:
                    pass
            else:
                try:
                    pages.add(int(part) - 1)
                except ValueError:
                    pass

        valid = sorted(p for p in pages if 0 <= p < total_pages)
        return valid if valid else list(range(total_pages))

    # ── public API ─────────────────────────────────────────────────────

    def validate(self, file_path: Path) -> Dict[str, Any]:
        """Validate that the file is a proper Illustrator file."""
        if not file_path.exists():
            raise ValueError("File not found.")
        if file_path.stat().st_size == 0:
            raise ValueError("The uploaded Illustrator file is empty.")

        ext = file_path.suffix.lower()
        if ext not in (".ai",):
            raise ValueError("Unsupported format. Only .ai files are allowed.")

        # Quick PDF-compatibility check: PDF files start with %PDF
        is_pdf_compatible = False
        try:
            with open(file_path, "rb") as f:
                header = f.read(16)
            is_pdf_compatible = header[:5] == b"%PDF-"
        except Exception:
            pass

        return {
            "filename": file_path.name,
            "size_bytes": file_path.stat().st_size,
            "format": "Adobe Illustrator",
            "pdf_compatible": is_pdf_compatible,
        }

    async def process(
        self,
        request_id: str,
        filename: str,
        page_range: str = "",
    ) -> Dict[str, Any]:
        """Convert an Illustrator file to PDF.

        Tries pypdf extraction → Ghostscript → LibreOffice in order.
        Returns a dict with ``success``, ``filename``, ``download_url``, ``view_url``.
        """
        input_file = Paths.request_upload(request_id) / filename
        if not input_file.exists():
            raise ValueError("Illustrator file not found.")

        output_dir = Paths.request_output(request_id)
        temp_dir = Paths.request_temp(request_id) / "ai_processing"

        try:
            # Clean / create temp dir
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            temp_dir.mkdir(parents=True, exist_ok=True)

            base_name = filename.rsplit(".", 1)[0]
            temp_pdf = temp_dir / f"{base_name}.pdf"
            final_pdf = output_dir / f"{base_name}.pdf"

            converted = False

            # ── Strategy 1: pypdf direct extraction ────────────────
            try:
                reader = PdfReader(str(input_file))
                if reader.pages:  # file is valid PDF
                    writer = PdfWriter()
                    for page in reader.pages:
                        writer.add_page(page)
                    with open(temp_pdf, "wb") as fh:
                        writer.write(fh)
                    converted = True
                    logger.info("AI file is PDF-compatible; extracted via pypdf.")
            except Exception as exc:
                logger.debug("pypdf extraction failed (expected for legacy AI): %s", exc)

            # ── Strategy 2: Ghostscript ────────────────────────────
            if not converted:
                gs_cmd = self._find_ghostscript()
                if gs_cmd:
                    cmd = [
                        gs_cmd,
                        "-dSAFER",
                        "-dBATCH",
                        "-dNOPAUSE",
                        "-sDEVICE=pdfwrite",
                        f"-sOutputFile={temp_pdf}",
                        str(input_file),
                    ]
                    try:
                        proc = subprocess.run(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=120,
                        )
                        if proc.returncode == 0 and temp_pdf.exists() and temp_pdf.stat().st_size > 0:
                            converted = True
                            logger.info("AI file converted via Ghostscript.")
                        else:
                            err = proc.stderr.decode("utf-8", errors="ignore")[:500]
                            logger.warning("Ghostscript failed (rc=%s): %s", proc.returncode, err)
                    except FileNotFoundError:
                        logger.warning("Ghostscript executable not found at %s", gs_cmd)
                    except subprocess.TimeoutExpired:
                        logger.warning("Ghostscript timed out for %s", filename)

            # ── Strategy 3: LibreOffice ────────────────────────────
            if not converted:
                soffice = self._find_soffice()
                safe_input = temp_dir / filename
                shutil.copy2(input_file, safe_input)
                cmd = [
                    soffice,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(temp_dir),
                    str(safe_input),
                ]
                try:
                    proc = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=120,
                    )
                    expected = temp_dir / f"{base_name}.pdf"
                    if expected.exists() and expected.stat().st_size > 0:
                        converted = True
                        logger.info("AI file converted via LibreOffice.")
                    else:
                        err = proc.stderr.decode("utf-8", errors="ignore")[:500]
                        logger.warning("LibreOffice failed (rc=%s): %s", proc.returncode, err)
                except FileNotFoundError:
                    logger.error("LibreOffice not found at %s", soffice)
                except subprocess.TimeoutExpired:
                    logger.warning("LibreOffice timed out for %s", filename)

            if not converted:
                raise ValueError(
                    "All conversion methods failed. "
                    "Ensure Ghostscript or LibreOffice is installed and the file is a valid Illustrator file."
                )

            # ── Post-process: page selection ───────────────────────
            if page_range.strip():
                try:
                    reader = PdfReader(str(temp_pdf))
                    writer = PdfWriter()
                    indices = self._parse_page_range(page_range, len(reader.pages))
                    for idx in indices:
                        writer.add_page(reader.pages[idx])
                    with open(final_pdf, "wb") as fh:
                        writer.write(fh)
                except Exception as exc:
                    logger.error("pypdf page selection failed: %s", exc)
                    raise ValueError(f"Failed to apply page selection: {exc}")
            else:
                shutil.move(str(temp_pdf), str(final_pdf))

            return {
                "success": True,
                "request_id": request_id,
                "filename": final_pdf.name,
                "download_url": f"/api/convert-to-pdf/illustrator-to-pdf/download/{request_id}/{final_pdf.name}",
                "view_url": f"/api/convert-to-pdf/illustrator-to-pdf/view/{request_id}",
            }

        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)


illustrator_to_pdf_service = IllustratorToPdfService()
