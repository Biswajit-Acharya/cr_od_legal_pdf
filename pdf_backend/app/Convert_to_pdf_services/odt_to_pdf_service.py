"""
ODT to PDF conversion service.
Uses LibreOffice (soffice) in headless mode for maximum fidelity.
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

logger = logging.getLogger(__name__)

class OdtToPdfService:
    
    def validate(self, file_path: Path, request_id: str) -> Dict[str, Any]:
        """
        Validate that the file is a proper ODT file.
        Returns basic file stats for the preview.
        """
        if not file_path.exists():
            raise ValueError("File not found.")
            
        if file_path.stat().st_size == 0:
            raise ValueError("The uploaded ODT file is empty.")
            
        # Basic ODT structure validation (it's a ZIP archive containing a 'mimetype' file)
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                if 'mimetype' in zf.namelist():
                    mimetype_content = zf.read('mimetype').decode('utf-8').strip()
                    if mimetype_content != 'application/vnd.oasis.opendocument.text':
                        logger.warning(f"Unexpected mimetype in ODT: {mimetype_content}")
                        # We don't strictly fail here in case some generators produce weird mimetypes,
                        # but it's a good sanity check.
        except zipfile.BadZipFile:
            raise ValueError("The ODT file appears to be corrupted or unreadable.")
        except Exception as e:
            logger.warning(f"ODT validation warning: {e}")
            # Do not block conversion on minor validation errors
            pass

        # Return minimal data for preview
        return {
            "filename": file_path.name,
            "size_bytes": file_path.stat().st_size
        }

    async def process(
        self,
        request_id: str,
        filename: str
    ) -> Dict[str, Any]:
        """
        Convert ODT to PDF using LibreOffice headless mode.
        """
        input_file = Paths.request_upload(request_id) / filename
        if not input_file.exists():
            raise ValueError("ODT file not found.")

        output_dir = Paths.request_output(request_id)
        temp_dir = Paths.request_temp(request_id) / "odt_processing"
        
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
                # We use subprocess.run via executor to avoid Windows asyncio subprocess issues
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
                    raise ValueError(f"ODT to PDF conversion failed during processing. LibreOffice error: {err_msg}")
            except FileNotFoundError:
                logger.error("LibreOffice (soffice) executable not found in PATH.")
                raise ValueError("LibreOffice is not installed or unavailable. Please install LibreOffice and ensure 'soffice' is in PATH.")
            except Exception as e:
                logger.error(f"Unexpected error executing LibreOffice: {e}")
                raise ValueError(f"An unexpected error occurred during ODT to PDF conversion: {str(e)}")
            
            # Verify output
            expected_pdf_name = filename.rsplit(".", 1)[0] + ".pdf"
            temp_pdf_path = temp_dir / expected_pdf_name
            
            if not temp_pdf_path.exists() or temp_pdf_path.stat().st_size == 0:
                raise ValueError("PDF generation failed. The output file is missing or empty.")
                
            # Move to final output directory
            final_pdf_path = output_dir / expected_pdf_name
            shutil.move(str(temp_pdf_path), str(final_pdf_path))
            
            return {
                "success": True,
                "request_id": request_id,
                "filename": expected_pdf_name,
                "download_url": f"/api/convert-to-pdf/odt-to-pdf/download/{request_id}/{expected_pdf_name}",
                "view_url": f"/api/convert-to-pdf/odt-to-pdf/view/{request_id}"
            }
            
        finally:
            # Always cleanup temporary processing directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

odt_to_pdf_service = OdtToPdfService()
