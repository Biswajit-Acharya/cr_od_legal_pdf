"""
Duplicate PDF Pages Service.

Provides complete PDF validation, deep analysis, and memory-efficient
page duplication with configurable insert positions.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz

from app.core.paths import Paths
from app.utils.filename import output_filename
from app.pdf_security_services.protect_pdf_service import protect_pdf_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

class PDFAnalysis:
    """Holds analysis details of a PDF before duplication."""

    def __init__(self) -> None:
        self.page_count: int = 0
        self.file_size: int = 0
        self.pdf_version: str = ""
        self.has_bookmarks: bool = False
        self.has_metadata: bool = False
        self.has_annotations: bool = False
        self.has_digital_signature: bool = False
        self.is_encrypted: bool = False
        self.is_corrupted: bool = False
        self.metadata_title: str = ""
        self.metadata_author: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_count": self.page_count,
            "file_size": self.file_size,
            "pdf_version": self.pdf_version,
            "has_bookmarks": self.has_bookmarks,
            "has_metadata": self.has_metadata,
            "has_annotations": self.has_annotations,
            "has_digital_signature": self.has_digital_signature,
            "is_encrypted": self.is_encrypted,
            "is_corrupted": self.is_corrupted,
            "metadata_title": self.metadata_title,
            "metadata_author": self.metadata_author,
        }


class DuplicateResult:
    """Holds final results of a duplication run."""

    def __init__(self) -> None:
        self.success: bool = False
        self.message: str = ""
        self.request_id: str = ""
        self.filename: str = ""
        self.download_url: str = ""
        self.original_pages: int = 0
        self.selected_pages: int = 0
        self.copies: int = 0
        self.total_output_pages: int = 0
        self.processed_size: int = 0
        self.processing_time: float = 0.0
        self.analysis: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "request_id": self.request_id,
            "filename": self.filename,
            "download_url": self.download_url,
            "original_pages": self.original_pages,
            "selected_pages": self.selected_pages,
            "copies": self.copies,
            "total_output_pages": self.total_output_pages,
            "processed_size": self.processed_size,
            "processing_time": self.processing_time,
            "analysis": self.analysis,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DuplicatePDFPagesService:
    """
    Production-ready page duplication engine utilizing PyMuPDF for memory-efficient
    object copying and reference updates.
    """

    # ------------------------------------------------------------------
    # Public Entry Points
    # ------------------------------------------------------------------

    async def analyze(self, input_pdf: Path) -> PDFAnalysis:
        """Analyze document structure and return metadata and stats."""
        logger.info("Analyzing PDF for page duplication: %s", input_pdf.name)
        analysis = PDFAnalysis()
        analysis.file_size = input_pdf.stat().st_size

        self._validate_pdf(input_pdf, analysis)
        if analysis.is_corrupted or analysis.is_encrypted:
            return analysis

        self._deep_analyze(input_pdf, analysis)
        return analysis

    async def process(
        self,
        input_pdf: Path,
        request_id: str,
        page_selection: str,
        copies: int = 1,
        insert_mode: str = "after",  # before, after, beginning, end, custom
        custom_position: int = 1,
        preserve_bookmarks: bool = True,
        preserve_annotations: bool = True,
        preserve_metadata: bool = True,
    ) -> DuplicateResult:
        """
        Duplicate selected pages in-place/copy and return the output path/download URL.
        """
        start = time.perf_counter()
        logger.info(
            "Duplicating pages [request_id=%s] selection=%s copies=%d insert=%s pos=%d",
            request_id, page_selection, copies, insert_mode, custom_position,
        )

        result = DuplicateResult()
        result.request_id = request_id

        # 1. Validation
        analysis = PDFAnalysis()
        analysis.file_size = input_pdf.stat().st_size
        
        try:
            protect_pdf_service.check_extraction_permission(input_pdf)
        except Exception as e:
            raise ValueError(str(e))
            
        self._validate_pdf(input_pdf, analysis)

        if analysis.is_corrupted:
            raise ValueError("Corrupted PDF: cannot open document structure.")
        if analysis.is_encrypted:
            raise ValueError("Password-protected PDF: cannot duplicate pages without password.")

        self._deep_analyze(input_pdf, analysis)
        result.analysis = analysis.to_dict()
        result.original_pages = analysis.page_count
        result.copies = copies

        # 2. Parse selected pages (1-based from user)
        selected_pages = self._parse_page_selection(page_selection, analysis.page_count)
        result.selected_pages = len(selected_pages)

        if not selected_pages:
            raise ValueError("Please select at least one page to duplicate.")

        if copies < 1:
            raise ValueError("Number of copies must be at least 1.")

        # Convert to 0-based page indices
        selected_indices = [p - 1 for p in selected_pages]

        # 3. Determine final page sequence order
        final_sequence = self._get_final_page_sequence(
            total_pages=analysis.page_count,
            selected_indices=selected_indices,
            copies=copies,
            insert_mode=insert_mode,
            custom_position=custom_position,
        )
        result.total_output_pages = len(final_sequence)

        # 4. Generate optimized output document
        tmp_out = Path(tempfile.mktemp(suffix=".pdf"))
        try:
            with fitz.open(str(input_pdf)) as src_doc:
                out_doc = fitz.open()

                # Insert pages according to target sequence
                for src_page_idx in final_sequence:
                    out_doc.insert_pdf(
                        src_doc,
                        from_page=src_page_idx,
                        to_page=src_page_idx,
                        links=True,
                        annots=preserve_annotations,
                        widgets=True,
                    )

                # Preserve Bookmarks / Outline
                if preserve_bookmarks:
                    try:
                        toc = src_doc.get_toc()
                        if toc:
                            # Adjust bookmark page references to match new sequence
                            adjusted_toc = self._adjust_toc_references(toc, final_sequence)
                            out_doc.set_toc(adjusted_toc)
                    except Exception as exc:
                        logger.warning("Could not preserve bookmarks: %s", exc)

                # Preserve Metadata
                if preserve_metadata:
                    out_doc.set_metadata(src_doc.metadata)

                out_doc.save(
                    str(tmp_out),
                    garbage=4,
                    deflate=True,
                )
                out_doc.close()

            # 5. Output Verification
            self._validate_output(tmp_out, len(final_sequence))

            # 6. Save to final destination
            out_dir = Paths.request_output(request_id)
            out_name = output_filename(prefix="duplicated_")
            out_path = out_dir / out_name
            shutil.move(str(tmp_out), str(out_path))

            processed_size = out_path.stat().st_size
            proc_time = round(time.perf_counter() - start, 2)

            result.success = True
            result.message = (
                f"Successfully duplicated pages. Document increased from "
                f"{result.original_pages} to {result.total_output_pages} pages."
            )
            result.filename = out_name
            result.download_url = f"/api/pdf/duplicate-pages/download/{request_id}/{out_name}"
            result.processed_size = processed_size
            result.processing_time = proc_time

            logger.info(
                "Duplication complete [request_id=%s] output size=%d pages=%d in %.2fs",
                request_id, processed_size, result.total_output_pages, proc_time,
            )
            return result

        except Exception:
            logger.exception("Duplication failed [request_id=%s]", request_id)
            raise
        finally:
            if tmp_out.exists():
                try:
                    tmp_out.unlink()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Validation & Analysis
    # ------------------------------------------------------------------

    def _validate_pdf(self, path: Path, analysis: PDFAnalysis) -> None:
        """Validate PDF magic bytes, corruption, and encryption status."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(path, "rb") as fh:
            header = fh.read(5)
        if header != b"%PDF-":
            analysis.is_corrupted = True
            raise ValueError("Invalid file format. Upload a valid PDF.")

        try:
            with fitz.open(str(path)) as doc:
                if doc.needs_pass:
                    analysis.is_encrypted = True
                    return
                _ = doc.page_count
        except fitz.FileDataError:
            analysis.is_corrupted = True
            raise ValueError("Corrupted PDF: file data is unreadable.")
        except Exception as exc:
            analysis.is_corrupted = True
            raise ValueError(f"PDF validation failed: {exc}") from exc

    def _deep_analyze(self, path: Path, analysis: PDFAnalysis) -> None:
        """Deep inspect bookmarks, annotations, and metadata fields."""
        with fitz.open(str(path)) as doc:
            analysis.page_count = doc.page_count
            fmt = (doc.metadata or {}).get("format", "")
            analysis.pdf_version = fmt if fmt else "Unknown"

            # Bookmarks
            try:
                toc = doc.get_toc()
                analysis.has_bookmarks = bool(toc)
            except Exception:
                analysis.has_bookmarks = False

            # Annotations
            has_annots = False
            for p_idx in range(doc.page_count):
                try:
                    annots = doc[p_idx].annots()
                    if annots:
                        has_annots = True
                        break
                except Exception:
                    continue
            analysis.has_annotations = has_annots

            # Metadata details
            meta = doc.metadata or {}
            filled = [v for v in meta.values() if v]
            analysis.has_metadata = bool(filled)
            analysis.metadata_title = meta.get("title", "")
            analysis.metadata_author = meta.get("author", "")

            # Signatures
            try:
                for i in range(1, min(doc.xref_length(), 5000)):
                    try:
                        obj_str = doc.xref_object(i)
                        if "/Sig" in obj_str and "/ByteRange" in obj_str:
                            analysis.has_digital_signature = True
                            break
                    except Exception:
                        continue
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Selection Parsing
    # ------------------------------------------------------------------

    def _parse_page_selection(self, selection: str, total_pages: int) -> List[int]:
        """
        Parse user selection string (e.g. '3,8,15', '20-40', 'Entire Document')
        and return sorted list of 1-based page numbers.
        """
        sel = selection.strip().lower()
        if not sel or sel in ("entire", "entire document", "*", "all"):
            return list(range(1, total_pages + 1))

        pages: set[int] = set()
        parts = sel.split(",")
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

                    # Bind to bounds
                    start = max(1, start)
                    end = min(total_pages, end)
                    for p in range(start, end + 1):
                        pages.add(p)
                except ValueError:
                    raise ValueError(f"Invalid page range: '{part}'. Format should be like '20-40'.")
            else:
                try:
                    p = int(part)
                    if 1 <= p <= total_pages:
                        pages.add(p)
                    else:
                        raise ValueError(f"Page number {p} is outside the document (total pages: {total_pages}).")
                except ValueError as exc:
                    if "outside the document" in str(exc):
                        raise
                    raise ValueError(f"Invalid page identifier: '{part}'. Must be a number or range.")

        return sorted(list(pages))

    # ------------------------------------------------------------------
    # Page Sequence Generator
    # ------------------------------------------------------------------

    def _get_final_page_sequence(
        self,
        total_pages: int,
        selected_indices: List[int],
        copies: int,
        insert_mode: str,
        custom_position: int,
    ) -> List[int]:
        """
        Construct the final 0-based page sequence.
        """
        selected_set = set(selected_indices)

        # Global insertion: beginning, end, custom
        if insert_mode in ("beginning", "end", "custom"):
            copies_bundle = []
            for idx in selected_indices:
                copies_bundle.extend([idx] * copies)

            if insert_mode == "beginning":
                insert_idx = 0
            elif insert_mode == "end":
                insert_idx = total_pages
            else:
                # custom_position is 1-based, maps to insertion index between 0 and total_pages
                insert_idx = max(0, min(total_pages, custom_position - 1))

            original = list(range(total_pages))
            return original[:insert_idx] + copies_bundle + original[insert_idx:]

        # Relative insertion: before or after selected pages
        final_seq = []
        for idx in range(total_pages):
            if idx in selected_set:
                if insert_mode == "before":
                    final_seq.extend([idx] * copies)
                    final_seq.append(idx)
                else:  # after
                    final_seq.append(idx)
                    final_seq.extend([idx] * copies)
            else:
                final_seq.append(idx)

        return final_seq

    # ------------------------------------------------------------------
    # Bookmark / TOC Realignment
    # ------------------------------------------------------------------

    def _adjust_toc_references(
        self,
        toc: List[List[Any]],
        final_sequence: List[int],
    ) -> List[List[Any]]:
        """
        Remap TOC bookmarks to align with new page sequence layout.
        Maps the original 1-based page reference to the new matching page number.
        """
        # Create map from original page (0-based) to its first occurrence in final sequence (1-based)
        # Note: bookmarks generally link to the start of a page, so pointing to the first occurrence
        # or duplicated copy is the standard.
        orig_to_new_map: Dict[int, int] = {}
        for new_idx, orig_idx in enumerate(final_sequence):
            if orig_idx not in orig_to_new_map:
                orig_to_new_map[orig_idx] = new_idx + 1

        adjusted = []
        for item in toc:
            # item format: [level, title, page, ...]
            if len(item) >= 3:
                level, title, page = item[0], item[1], item[2]
                if page > 0:
                    orig_page_idx = page - 1
                    # Get new page index, default to same page index if not mapped
                    new_page = orig_to_new_map.get(orig_page_idx, page)
                    new_item = list(item)
                    new_item[2] = new_page
                    adjusted.append(new_item)
                else:
                    adjusted.append(item)
            else:
                adjusted.append(item)

        return adjusted

    # ------------------------------------------------------------------
    # Output Validation
    # ------------------------------------------------------------------

    def _validate_output(self, path: Path, expected_pages: int) -> None:
        """Verify optimized output structure and page count."""
        if not path.exists() or path.stat().st_size < 64:
            raise ValueError("Page duplication failed: output file is empty or missing.")

        try:
            with fitz.open(str(path)) as doc:
                if doc.page_count != expected_pages:
                    raise ValueError(
                        f"Output validation failed: expected {expected_pages} pages, "
                        f"but generated PDF has {doc.page_count} pages."
                    )
                # Test render first page
                _ = doc[0].get_text()
        except Exception as exc:
            raise ValueError(f"Output verification failed: {exc}") from exc


# Singleton instance
_duplicate_pages_service = DuplicatePDFPagesService()
