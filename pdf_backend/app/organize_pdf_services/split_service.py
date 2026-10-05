"""
Service for splitting a PDF into multiple smaller files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from pypdf import PdfReader, PdfWriter

from app.core.constants import SPLIT_OUTPUT_PREFIX
from app.core.paths import Paths
from app.schemas.pdf_schema import SplitPDFResponse
from app.utils.filename import output_filename
from app.pdf_security_services.protect_pdf_service import protect_pdf_service

logger = logging.getLogger(__name__)


class SplitPDFService:
    """Split a PDF into chunks of N pages each."""

    async def split(
        self,
        input_pdf: Path,
        split_every: int,
        request_id: str,
    ) -> SplitPDFResponse:
        """
        Split ``input_pdf`` into files of ``split_every`` pages each.

        Args:
            input_pdf: Path to the uploaded PDF.
            split_every: Number of pages per output file.
            request_id: Unique request identifier.

        Returns:
            SplitPDFResponse with list of output filenames.
        """
        output_dir = Paths.request_output(request_id)

        try:
            protect_pdf_service.check_extraction_permission(input_pdf)
        except Exception as e:
            raise ValueError(str(e))

        reader = PdfReader(str(input_pdf))
        total_pages = len(reader.pages)

        if split_every < 1:
            raise ValueError("split_every must be at least 1.")

        output_files: List[str] = []
        chunk_index = 0

        for start in range(0, total_pages, split_every):
            end = min(start + split_every, total_pages)
            writer = PdfWriter()

            for page in reader.pages[start:end]:
                writer.add_page(page)

            if reader.metadata:
                writer.add_metadata(reader.metadata)

            out_name = output_filename(prefix=SPLIT_OUTPUT_PREFIX)
            out_path = output_dir / out_name

            with open(out_path, "wb") as f:
                writer.write(f)

            output_files.append(out_name)
            chunk_index += 1

        logger.info(
            "Split PDF into %d file(s) (every %d pages).",
            len(output_files),
            split_every,
        )

        return SplitPDFResponse(
            success=True,
            message=f"PDF split into {len(output_files)} file(s).",
            request_id=request_id,
            files=output_files,
            download_url=f"/api/pdf/download/{request_id}",
            total_files=len(output_files),
        )
