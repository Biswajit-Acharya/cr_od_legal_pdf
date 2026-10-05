"""
Visio to PDF conversion service.
Uses LibreOffice (soffice) in headless mode (via libvisio) for native fidelity.
Uses pypdf for specific page selection extraction.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import os
import zipfile
from pathlib import Path
from typing import Dict, Any

from app.core.paths import Paths

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    pass

logger = logging.getLogger(__name__)

class VisioToPdfService:
    
    def validate(self, file_path: Path, request_id: str) -> Dict[str, Any]:
        """
        Validate that the file is a proper Visio file.
        """
        if not file_path.exists():
            raise ValueError("File not found.")
            
        if file_path.stat().st_size == 0:
            raise ValueError("The uploaded Visio file is empty.")
            
        ext = file_path.suffix.lower()
        if ext not in ['.vsd', '.vsdx']:
            raise ValueError("Unsupported format. Only .vsd and .vsdx are allowed.")
            
        # Basic .vsdx structure validation (it's a ZIP archive containing a [Content_Types].xml file)
        if ext == '.vsdx':
            try:
                with zipfile.ZipFile(file_path, 'r') as zf:
                    if '[Content_Types].xml' not in zf.namelist():
                        logger.warning("Visio file might be corrupted: Missing [Content_Types].xml")
            except zipfile.BadZipFile:
                raise ValueError("The .vsdx file appears to be corrupted or unreadable.")
            except Exception as e:
                logger.warning(f"Visio validation warning: {e}")
                pass

        # Return minimal data for preview
        return {
            "filename": file_path.name,
            "size_bytes": file_path.stat().st_size,
            "format": "Visio Diagram"
        }
        
    def _parse_page_range(self, range_str: str, total_pages: int) -> list[int]:
        """
        Parse a string like '1,3,5-8' into a list of zero-indexed page numbers.
        """
        if not range_str or not range_str.strip():
            return list(range(total_pages))
            
        pages = set()
        parts = range_str.strip().split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                try:
                    start_str, end_str = part.split('-')
                    start = int(start_str)
                    end = int(end_str)
                    if start > end:
                        start, end = end, start
                    for p in range(start, end + 1):
                        pages.add(p - 1)
                except ValueError:
                    pass
            else:
                try:
                    p = int(part)
                    pages.add(p - 1)
                except ValueError:
                    pass
                    
        # Filter valid pages and sort
        valid_pages = sorted([p for p in pages if 0 <= p < total_pages])
        if not valid_pages:
            return list(range(total_pages))
        return valid_pages

    async def process(
        self,
        request_id: str,
        filename: str,
        page_range: str = ""
    ) -> Dict[str, Any]:
        """
        Convert Visio to PDF using LibreOffice headless mode.
        Optionally apply page selection using pypdf.
        """
        input_file = Paths.request_upload(request_id) / filename
        if not input_file.exists():
            raise ValueError("Visio file not found.")

        output_dir = Paths.request_output(request_id)
        temp_dir = Paths.request_temp(request_id) / "visio_processing"
        
        try:
            # Create isolated temp dir for LibreOffice processing
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy input file to temp dir to avoid modifying original upload
            safe_input = temp_dir / filename
            shutil.copy2(input_file, safe_input)
            
            # Determine LibreOffice executable
            soffice_cmd = "soffice"
            if os.name == 'nt':
                # Check common Windows paths in case it's installed but not in PATH
                common_paths = [
                    r"C:\Program Files\LibreOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
                ]
                for p in common_paths:
                    if os.path.exists(p):
                        soffice_cmd = p
                        break
            
            command = [
                soffice_cmd,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_dir),
                str(safe_input)
            ]
            
            # Execute LibreOffice
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                
                def run_soffice():
                    return subprocess.run(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False
                    )
                
                process = await loop.run_in_executor(None, run_soffice)
                
                if process.returncode != 0:
                    err_msg = process.stderr.decode('utf-8', errors='ignore')
                    logger.error(f"LibreOffice conversion failed: {err_msg}")
                    raise ValueError(f"Visio to PDF conversion failed during processing. LibreOffice error: {err_msg}")
            except FileNotFoundError:
                logger.error("LibreOffice (soffice) executable not found in PATH.")
                raise ValueError("LibreOffice is not installed or unavailable. Please install LibreOffice and ensure 'soffice' is in PATH.")
            except Exception as e:
                logger.error(f"Unexpected error executing LibreOffice: {e}")
                raise ValueError(f"An unexpected error occurred during Visio to PDF conversion: {str(e)}")
            
            # Verify output
            expected_pdf_name = filename.rsplit(".", 1)[0] + ".pdf"
            temp_pdf_path = temp_dir / expected_pdf_name
            
            if not temp_pdf_path.exists() or temp_pdf_path.stat().st_size == 0:
                raise ValueError("PDF generation failed. The output file is missing or empty. Ensure the file is a valid Visio diagram.")
                
            # Post-Processing with pypdf
            final_pdf_path = output_dir / expected_pdf_name
            
            needs_post_processing = bool(page_range.strip())
            
            if needs_post_processing:
                try:
                    reader = PdfReader(str(temp_pdf_path))
                    writer = PdfWriter()
                    
                    total_pages = len(reader.pages)
                    
                    # Page Selection
                    selected_indices = self._parse_page_range(page_range, total_pages)
                    for idx in selected_indices:
                        writer.add_page(reader.pages[idx])
                        
                    # Write to final destination
                    with open(str(final_pdf_path), "wb") as f_out:
                        writer.write(f_out)
                        
                except Exception as e:
                    logger.error(f"pypdf post-processing failed: {e}")
                    raise ValueError(f"Failed to apply specific page extraction: {str(e)}")
            else:
                # No post-processing needed, just move the file
                shutil.move(str(temp_pdf_path), str(final_pdf_path))
            
            return {
                "success": True,
                "request_id": request_id,
                "filename": expected_pdf_name,
                "download_url": f"/api/convert-to-pdf/visio-to-pdf/download/{request_id}/{expected_pdf_name}",
                "view_url": f"/api/convert-to-pdf/visio-to-pdf/view/{request_id}"
            }
            
        finally:
            # Always cleanup temporary processing directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

visio_to_pdf_service = VisioToPdfService()
