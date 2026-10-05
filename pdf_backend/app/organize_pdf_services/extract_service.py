"""
Service for extracting specific pages from a PDF.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.core.constants import EXTRACT_OUTPUT_PREFIX
from app.core.paths import Paths
from app.schemas.pdf_schema import ExtractPagesResponse
from app.utils.filename import output_filename
from app.utils.page_parser import parse_page_range
from app.pdf_security_services.protect_pdf_service import protect_pdf_service

logger = logging.getLogger(__name__)


class ExtractPagesService:
    """Extract selected pages from a PDF into a new file."""

    async def extract(
        self,
        input_pdf: Path,
        page_string: str,
        request_id: str,
    ) -> ExtractPagesResponse:
        """
        Extract pages specified by ``page_string`` from ``input_pdf``.

        Args:
            input_pdf: Path to the uploaded PDF.
            page_string: Comma/range string, e.g. ``"1,3,5-8"``.
            request_id: Unique request identifier.

        Returns:
            ExtractPagesResponse with output filename and download URL.
        """
        output_dir = Paths.request_output(request_id)

        try:
            protect_pdf_service.check_extraction_permission(input_pdf)
        except Exception as e:
            raise ValueError(str(e))

        reader = PdfReader(str(input_pdf))
        total_pages = len(reader.pages)

        page_indexes = parse_page_range(page_string, total_pages)

        writer = PdfWriter()

        for idx in page_indexes:
            writer.add_page(reader.pages[idx - 1])

        if reader.metadata:
            writer.add_metadata(reader.metadata)

        out_name = output_filename(prefix=EXTRACT_OUTPUT_PREFIX)
        out_path = output_dir / out_name

        with open(out_path, "wb") as f:
            writer.write(f)

        logger.info(
            "Extracted %d page(s) → %s", len(page_indexes), out_name
        )

        file_size = out_path.stat().st_size

        return ExtractPagesResponse(
            success=True,
            message=f"Successfully extracted {len(page_indexes)} page(s).",
            request_id=request_id,
            filename=out_name,
            download_url=f"/api/pdf/download/{request_id}/{out_name}",
            file_size=file_size,
        )
