"""
Service for splitting a PDF into individual pages.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import pikepdf
from pikepdf import Pdf

from app.core.paths import Paths
from app.schemas.pdf_schema import SplitPDFResponse
from app.pdf_security_services.protect_pdf_service import protect_pdf_service

logger = logging.getLogger(__name__)


class PDFToIndividualPagesService:
    """Service to split a PDF into one file per page."""

    async def split_to_individual_pages(
        self,
        input_pdf: Path,
        request_id: str,
        custom_name: str = "Page"
    ) -> SplitPDFResponse:
        """
        Split a PDF into individual pages, preserving quality, size, and orientation.
        """
        output_dir = Paths.request_output(request_id)

        try:
            try:
                protect_pdf_service.check_extraction_permission(input_pdf)
            except Exception as e:
                raise ValueError(str(e))

            with Pdf.open(str(input_pdf)) as pdf:
                if pdf.is_encrypted:
                    raise ValueError("Cannot process password-protected PDF. Please unlock it first.")
                
                total_pages = len(pdf.pages)
                if total_pages == 0:
                    raise ValueError("The uploaded PDF is empty.")

                output_files: List[str] = []
                
                # Format with leading zeros based on total pages (e.g., 001 for 325 pages, 01 for 10 pages)
                zero_padding = len(str(total_pages))
                if zero_padding < 3:
                    zero_padding = 3

                # Ensure custom_name is valid for filesystem
                safe_custom_name = "".join([c for c in custom_name if c.isalpha() or c.isdigit() or c in [' ', '-', '_']]).strip()
                if not safe_custom_name:
                    safe_custom_name = "Page"

                for i, page in enumerate(pdf.pages):
                    page_number = i + 1
                    formatted_number = str(page_number).zfill(zero_padding)
                    out_name = f"{safe_custom_name}_{formatted_number}.pdf"
                    out_path = output_dir / out_name

                    dst = Pdf.new()
                    dst.pages.append(page)
                    
                    # Try to preserve metadata if possible
                    try:
                        if hasattr(pdf, 'docinfo'):
                            with dst.open_metadata() as meta:
                                if hasattr(pdf, 'open_metadata'):
                                    with pdf.open_metadata() as src_meta:
                                        meta.update(src_meta)
                    except Exception:
                        pass # Silently ignore metadata errors to prioritize extraction

                    dst.save(str(out_path))
                    output_files.append(out_name)
                    
                logger.info(
                    "Extracted %d individual pages for request %s",
                    len(output_files),
                    request_id
                )

                return SplitPDFResponse(
                    success=True,
                    message=f"PDF successfully split into {len(output_files)} individual page(s).",
                    request_id=request_id,
                    files=output_files,
                    download_url=f"/api/pdf/download/{request_id}",
                    total_files=len(output_files)
                )

        except pikepdf.PasswordError:
            logger.error("Password protected PDF detected in split_to_individual_pages.")
            raise ValueError("Cannot process password-protected PDF. Please unlock it first.")
        except pikepdf.PdfError as e:
            logger.error(f"Corrupted or invalid PDF detected: {e}")
            raise ValueError(f"Invalid or corrupted PDF file: {str(e)}")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in split_to_individual_pages: {e}")
            raise ValueError(f"Failed to extract pages: {str(e)}")
