"""
XPS to PDF conversion service.
Uses LibreOffice (soffice) in headless mode for native fidelity conversion.
XPS (XML Paper Specification) is a Microsoft document format similar to PDF.
LibreOffice supports XPS import via its built-in filters.

Supports batch conversion of multiple XPS files.
Optionally applies page selection using pypdf after conversion.
Validates generated PDFs after conversion.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import os
import zipfile
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.paths import Paths

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    PdfReader = None
    PdfWriter = None

logger = logging.getLogger(__name__)


class XpsToPdfService:
    """Convert XPS files to PDF using LibreOffice headless mode."""

    def _find_soffice(self) -> str:
        """Find the LibreOffice executable path."""
        if os.name == "nt":
            common_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                r"C:\Program Files\LibreOffice program\soffice.exe",
            ]
            for p in common_paths:
                if os.path.exists(p):
                    return p
        return "soffice"

    def validate(self, file_path: Path) -> Dict[str, Any]:
        """
        Validate that the file is a proper XPS file.
        Returns basic file info on success.
        """
        if not file_path.exists():
            raise ValueError("File not found.")

        if file_path.stat().st_size == 0:
            raise ValueError("The uploaded XPS file is empty.")

        ext = file_path.suffix.lower()
        if ext not in (".xps", ".oxps"):
            raise ValueError("Unsupported format. Only .xps and .oxps are allowed.")

        # Basic XPS structure validation (it is a ZIP archive containing specific XML files)
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                namelist = zf.namelist()
                if "[Content_Types].xml" not in namelist:
                    logger.warning("XPS file might be corrupted: Missing [Content_Types].xml")
        except zipfile.BadZipFile:
            raise ValueError("The XPS file appears to be corrupted or is not a valid ZIP archive.")
        except Exception as e:
            logger.warning(f"XPS validation warning: {e}")

        size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)

        return {
            "filename": file_path.name,
            "size_bytes": file_path.stat().st_size,
            "size_mb": size_mb,
            "format": "XPS Document",
            "extension": ext,
        }

    def _parse_page_range(self, range_str: str, total_pages: int) -> list[int]:
        """
        Parse a string like '1,3,5-8' into a sorted list of zero-indexed page numbers.
        """
        if not range_str or not range_str.strip():
            return list(range(total_pages))

        pages: set[int] = set()
        parts = range_str.strip().split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    start_str, end_str = part.split("-", 1)
                    start = int(start_str.strip())
                    end = int(end_str.strip())
                    if start > end:
                        start, end = end, start
                    for p in range(start, end + 1):
                        pages.add(p - 1)
                except (ValueError, TypeError):
                    pass
            else:
                try:
                    p = int(part)
                    pages.add(p - 1)
                except ValueError:
                    pass

        valid_pages = sorted(p for p in pages if 0 <= p < total_pages)
        if not valid_pages:
            return list(range(total_pages))
        return valid_pages

    def _validate_page_selection(self, range_str: str, total_pages: int) -> str:
        """
        Validate page range string and return an error message if invalid.
        Returns empty string if valid.
        """
        if not range_str or not range_str.strip():
            return ""

        import re
        if not re.match(r'^[\d,\-\s]+$', range_str.strip()):
            return "Invalid page range format. Use format like: 1,3,5-8"

        pages = set()
        parts = range_str.strip().split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    start_str, end_str = part.split("-", 1)
                    start = int(start_str.strip())
                    end = int(end_str.strip())
                    if start > end:
                        start, end = end, start
                    if start < 1 or end > total_pages:
                        return f"Page range {start}-{end} is outside document range (1-{total_pages})."
                    for p in range(start, end + 1):
                        pages.add(p)
                except (ValueError, TypeError):
                    return f"Invalid page range segment: '{part}'. Use numbers only."
            else:
                try:
                    p = int(part)
                    if p < 1 or p > total_pages:
                        return f"Page {p} is outside document range (1-{total_pages})."
                    pages.add(p)
                except ValueError:
                    return f"Invalid page number: '{part}'. Use numbers only."

        return ""

    async def _run_libreoffice(
        self, input_path: Path, output_dir: Path, timeout: int = 120
    ) -> None:
        """Run LibreOffice headless to convert XPS to PDF."""
        soffice_cmd = self._find_soffice()

        command = [
            soffice_cmd,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(input_path),
        ]

        loop = asyncio.get_event_loop()

        def _run():
            return subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout,
            )

        try:
            result = await loop.run_in_executor(None, _run)
        except FileNotFoundError:
            raise ValueError(
                "LibreOffice is not installed or not found. "
                "Please install LibreOffice and ensure it is accessible."
            )
        except subprocess.TimeoutExpired:
            raise ValueError(
                "Conversion timed out. The XPS file may be too large or complex."
            )

        if result.returncode != 0:
            err_msg = result.stderr.decode("utf-8", errors="ignore").strip()
            logger.error(f"LibreOffice XPS conversion failed (rc={result.returncode}): {err_msg}")
            raise ValueError(
                f"XPS to PDF conversion failed during processing. "
                f"Ensure the XPS file is valid and not corrupted."
            )

    def _validate_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Validate a generated PDF file.
        Returns page count and validation status.
        """
        if not pdf_path.exists():
            raise ValueError("Generated PDF file does not exist.")

        if pdf_path.stat().st_size == 0:
            raise ValueError("Generated PDF file is empty.")

        if PdfReader is None:
            return {"valid": True, "page_count": -1}

        try:
            reader = PdfReader(str(pdf_path))
            page_count = len(reader.pages)
            if page_count == 0:
                raise ValueError("Generated PDF has zero pages.")
            return {"valid": True, "page_count": page_count}
        except Exception as e:
            if "zero pages" in str(e).lower():
                raise
            raise ValueError(f"Generated PDF is invalid or corrupted: {e}")

    async def process(
        self,
        request_id: str,
        filenames: List[str],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convert one or more XPS files to PDF using LibreOffice headless mode.

        Args:
            request_id: Unique request identifier.
            filenames: List of XPS filenames to convert.
            config: Optional configuration dict with page_range, pdf_title, etc.

        Returns:
            Dict with success status, request_id, and per-file results.
        """
        config = config or {}
        upload_dir = Paths.request_upload(request_id)
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        page_range = config.get("page_range", "")
        pdf_title = config.get("pdf_title", "")
        pdf_author = config.get("pdf_author", "")
        pdf_subject = config.get("pdf_subject", "")

        results: List[Dict[str, Any]] = []
        temp_dir = Paths.request_temp(request_id) / "xps_processing"

        try:
            # Create isolated temp dir
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            temp_dir.mkdir(parents=True, exist_ok=True)

            for filename in filenames:
                input_path = upload_dir / filename
                if not input_path.exists():
                    results.append({
                        "original_filename": filename,
                        "status": "error",
                        "message": "File not found on server. Please re-upload.",
                    })
                    continue

                # Validate
                try:
                    self.validate(input_path)
                except ValueError as e:
                    results.append({
                        "original_filename": filename,
                        "status": "error",
                        "message": str(e),
                    })
                    continue

                # Subdirectory per file to avoid name collisions
                file_temp_dir = temp_dir / Path(filename).stem
                file_temp_dir.mkdir(parents=True, exist_ok=True)

                try:
                    await self._run_libreoffice(input_path, file_temp_dir)

                    expected_pdf = file_temp_dir / (Path(filename).stem + ".pdf")
                    if not expected_pdf.exists() or expected_pdf.stat().st_size == 0:
                        raise RuntimeError(
                            "PDF was not created. The XPS file may be corrupted "
                            "or unsupported by LibreOffice."
                        )

                    # Validate the generated PDF
                    pdf_info = self._validate_pdf(expected_pdf)
                    total_pages = pdf_info["page_count"]

                    # Determine final output name
                    pdf_filename = Path(filename).stem + ".pdf"
                    final_path = output_dir / pdf_filename

                    # Post-process with pypdf for page selection and/or metadata
                    needs_post = bool(page_range.strip()) or pdf_title or pdf_author or pdf_subject

                    if needs_post and PdfReader and PdfWriter:
                        try:
                            reader = PdfReader(str(expected_pdf))
                            writer = PdfWriter()

                            actual_total = len(reader.pages)

                            # Validate page selection
                            if page_range.strip():
                                err = self._validate_page_selection(page_range, actual_total)
                                if err:
                                    raise ValueError(err)

                            selected = self._parse_page_range(page_range, actual_total)
                            for idx in selected:
                                writer.add_page(reader.pages[idx])

                            # Apply metadata
                            meta: Dict[str, str] = {}
                            if pdf_title:
                                meta["/Title"] = pdf_title
                            if pdf_author:
                                meta["/Author"] = pdf_author
                            if pdf_subject:
                                meta["/Subject"] = pdf_subject
                            if meta:
                                writer.add_metadata(meta)

                            with open(str(final_path), "wb") as f_out:
                                writer.write(f_out)

                            # Re-validate after post-processing
                            post_info = self._validate_pdf(final_path)
                            total_pages = post_info["page_count"]

                        except (ValueError, RuntimeError):
                            raise
                        except Exception as e:
                            logger.warning(f"pypdf post-processing failed, using raw output: {e}")
                            shutil.move(str(expected_pdf), str(final_path))
                    else:
                        shutil.move(str(expected_pdf), str(final_path))

                    # Final output validation
                    if not final_path.exists() or final_path.stat().st_size == 0:
                        raise RuntimeError("Output PDF is missing or empty.")

                    results.append({
                        "original_filename": filename,
                        "pdf_filename": pdf_filename,
                        "status": "success",
                        "page_count": total_pages,
                        "download_url": f"/api/convert-to-pdf/xps-to-pdf/download/{request_id}/{pdf_filename}",
                        "view_url": f"/api/convert-to-pdf/xps-to-pdf/view/{request_id}/{pdf_filename}",
                    })

                except (ValueError, RuntimeError) as e:
                    logger.error(f"Error converting {filename}: {e}")
                    results.append({
                        "original_filename": filename,
                        "status": "error",
                        "message": str(e),
                    })
                except Exception as e:
                    logger.error(f"Unexpected error converting {filename}: {e}")
                    results.append({
                        "original_filename": filename,
                        "status": "error",
                        "message": f"An unexpected error occurred: {str(e)}",
                    })

        finally:
            # Always cleanup temporary processing directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

        if not results:
            raise ValueError("No files were processed.")

        successful = [r for r in results if r.get("status") == "success"]

        return {
            "success": len(successful) > 0,
            "request_id": request_id,
            "results": results,
            "total_files": len(filenames),
            "successful_files": len(successful),
            "failed_files": len(filenames) - len(successful),
        }


xps_to_pdf_service = XpsToPdfService()
