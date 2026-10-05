"""
Find & Replace Service — Document Management Section.

Allows users to search for specific words, phrases, or text patterns in PDF documents
and replace them automatically across specific pages or the entire document.

Features:
  - Exact & case-sensitive search options
  - Whole-word matching option
  - Context snippet generation around matches
  - Selective or bulk replacement ("Replace All")
  - Automatic redaction and clean text overlay using PyMuPDF (fitz)
  - Secure temporary output generation and file lifecycle cleanup
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# Set path for Windows installations (UB-Mannheim installer default)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from app.core.paths import Paths

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


class FindReplaceService:
    """Enterprise service for PDF text search and bulk find-and-replace."""

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and unsafe characters."""
        if not filename:
            return "document.pdf"
        clean = Path(filename).name
        clean = re.sub(r'[\\/:*?"<>|]', "_", clean)
        clean = re.sub(r"\s+", " ", clean).strip(" ._")
        return clean or "document.pdf"

    def validate_pdf_bytes(self, pdf_bytes: bytes) -> Tuple[bool, str, int]:
        """Validate input PDF bytes for size, magic header, encryption, and page count."""
        if not pdf_bytes or len(pdf_bytes) == 0:
            return False, "Uploaded file is empty.", 0
        if len(pdf_bytes) > MAX_FILE_SIZE_BYTES:
            return False, "File size exceeds maximum limit of 100 MB.", 0
        if not pdf_bytes.startswith(b"%PDF"):
            return False, "Invalid PDF document (missing %PDF header).", 0

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if doc.is_encrypted:
                doc.close()
                return False, "PDF document is encrypted or password-protected.", 0
            page_count = len(doc)
            doc.close()
            if page_count == 0:
                return False, "PDF document contains 0 pages.", 0
            return True, "", page_count
        except Exception as exc:
            return False, f"Failed to parse PDF document: {str(exc)}", 0

    def search_text(
        self,
        pdf_bytes: bytes,
        search_query: str,
        case_sensitive: bool = False,
        match_whole_word: bool = False,
    ) -> Dict[str, Any]:
        """
        Search PDF document for occurrences of search_query.
        Returns match locations, page numbers, bounding boxes, and context snippets.
        """
        is_valid, err_msg, total_pages = self.validate_pdf_bytes(pdf_bytes)
        if not is_valid:
            raise ValueError(err_msg)

        if not search_query or not search_query.strip():
            raise ValueError("Search text query cannot be empty.")

        query = search_query.strip()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        matches: List[Dict[str, Any]] = []
        match_id = 1

        for page_idx in range(len(doc)):
            page = doc[page_idx]

            # Search page rectangles
            quads = page.search_for(query)
            if not quads:
                continue

            for quad in quads:
                # Verify case-sensitivity & whole-word boundaries
                rect_text = page.get_text("text", clip=quad).strip()

                if case_sensitive and query not in rect_text:
                    continue

                if match_whole_word:
                    # Check left boundary
                    left_rect = fitz.Rect(quad.x0 - 3, quad.y0, quad.x0, quad.y1)
                    left_text = page.get_text("text", clip=left_rect).strip()
                    if left_text and left_text[-1].isalnum():
                        continue

                    # Check right boundary
                    right_rect = fitz.Rect(quad.x1, quad.y0, quad.x1 + 3, quad.y1)
                    right_text = page.get_text("text", clip=right_rect).strip()
                    if right_text and right_text[0].isalnum():
                        continue

                # Generate snippet for this specific quad by expanding the clip area horizontally
                clip_rect = fitz.Rect(0, quad.y0 - 2, page.rect.width, quad.y1 + 2)
                line_text = page.get_text("text", clip=clip_rect).strip().replace("\n", " ")

                if len(line_text) > 100:
                    idx = line_text.lower().find(query.lower())
                    if idx != -1:
                        start = max(0, idx - 40)
                        end = min(len(line_text), idx + len(query) + 40)
                        snippet = line_text[start:end]
                        if start > 0:
                            snippet = "..." + snippet
                        if end < len(line_text):
                            snippet = snippet + "..."
                    else:
                        snippet = line_text[:100] + "..."
                else:
                    snippet = line_text

                rect = list(quad)
                matches.append({
                    "id": match_id,
                    "page": page_idx + 1,
                    "rect": [round(c, 2) for c in rect],
                    "snippet": snippet or f"Match found on page {page_idx + 1}",
                })
                match_id += 1

            # OCR Fallback if no digital text matches
            if not quads:
                try:
                    pix = page.get_pixmap(dpi=150)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    
                    scale_x = page.rect.width / pix.width
                    scale_y = page.rect.height / pix.height
                    
                    for i, text in enumerate(ocr_data['text']):
                        if text and text.strip():
                            is_match = False
                            if case_sensitive:
                                is_match = (query in text)
                            else:
                                is_match = (query.lower() in text.lower())
                                
                            if is_match:
                                x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                                x0, y0 = x * scale_x, y * scale_y
                                x1, y1 = (x + w) * scale_x, (y + h) * scale_y
                                
                                matches.append({
                                    "id": match_id,
                                    "page": page_idx + 1,
                                    "rect": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                                    "snippet": f"...{text}...",
                                    "ocr": True
                                })
                                match_id += 1
                except Exception as e:
                    logger.warning(f"OCR search fallback failed on page {page_idx}: {e}")

        doc.close()

        return {
            "success": True,
            "total_matches": len(matches),
            "query": query,
            "matches": matches,
        }

    def _extract_snippet(self, page_text: str, query: str, case_sensitive: bool) -> str:
        """Extract a short context snippet around the matched query."""
        if not page_text:
            return ""
        flags = 0 if case_sensitive else re.IGNORECASE
        match = re.search(re.escape(query), page_text, flags=flags)
        if not match:
            return page_text[:100].strip().replace("\n", " ")

        start = max(0, match.start() - 40)
        end = min(len(page_text), match.end() + 40)
        snippet = page_text[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(page_text):
            snippet = snippet + "..."
        return snippet

    def replace_text(
        self,
        session_id: str,
        pdf_bytes: bytes,
        original_filename: str,
        search_query: str,
        replacement_text: str,
        replace_all: bool = True,
        target_page: Optional[int] = None,
        case_sensitive: bool = False,
        match_whole_word: bool = False,
    ) -> Dict[str, Any]:
        """
        Replace search_query with replacement_text in the PDF document.
        Applies PyMuPDF redaction and text insertion.
        """
        is_valid, err_msg, total_pages = self.validate_pdf_bytes(pdf_bytes)
        if not is_valid:
            raise ValueError(err_msg)

        if not search_query or not search_query.strip():
            raise ValueError("Search text query cannot be empty.")

        query = search_query.strip()
        replace_val = replacement_text if replacement_text is not None else ""

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_replacements = 0

        for page_idx in range(len(doc)):
            if not replace_all and target_page is not None and (page_idx + 1) != target_page:
                continue

            page = doc[page_idx]
            quads = page.search_for(query)
            if not quads:
                continue

            valid_quads = []
            for quad in quads:
                if case_sensitive:
                    rect_text = page.get_text("text", clip=quad).strip()
                    if query not in rect_text:
                        continue

                if match_whole_word:
                    # Check left boundary
                    left_rect = fitz.Rect(quad.x0 - 3, quad.y0, quad.x0, quad.y1)
                    left_text = page.get_text("text", clip=left_rect).strip()
                    if left_text and left_text[-1].isalnum():
                        continue

                    # Check right boundary
                    right_rect = fitz.Rect(quad.x1, quad.y0, quad.x1 + 3, quad.y1)
                    right_text = page.get_text("text", clip=right_rect).strip()
                    if right_text and right_text[0].isalnum():
                        continue

                valid_quads.append(quad)

            # OCR Fallback for replacement
            if not valid_quads:
                try:
                    pix = page.get_pixmap(dpi=150)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    
                    scale_x = page.rect.width / pix.width
                    scale_y = page.rect.height / pix.height
                    
                    for i, text in enumerate(ocr_data['text']):
                        if text and text.strip():
                            is_match = False
                            if case_sensitive:
                                is_match = (query in text)
                            else:
                                is_match = (query.lower() in text.lower())
                                
                            if is_match:
                                x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                                x0, y0 = x * scale_x, y * scale_y
                                x1, y1 = (x + w) * scale_x, (y + h) * scale_y
                                quad = fitz.Quad(fitz.Point(x0, y0), fitz.Point(x1, y0), fitz.Point(x0, y1), fitz.Point(x1, y1))
                                valid_quads.append(quad)
                except Exception as e:
                    logger.warning(f"OCR replace fallback failed on page {page_idx}: {e}")

            if not valid_quads:
                continue

            for quad in valid_quads:
                # Add redaction annotation over match area
                page.add_redact_annot(quad, fill=(1, 1, 1))
                total_replacements += 1
                if not replace_all and total_replacements >= 1:
                    break

            # Apply redactions to clean text
            page.apply_redactions()

            # Re-insert replacement text at redacted rectangles
            for quad in valid_quads:
                fontsize = max(9, min(14, quad.height * 0.75))
                page.insert_textbox(
                    quad,
                    replace_val,
                    fontsize=fontsize,
                    color=(0, 0, 0),
                    align=0,
                )
                if not replace_all:
                    break

            if not replace_all and total_replacements >= 1:
                break

        out_dir = Paths.request_output(session_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        clean_filename = self.sanitize_filename(original_filename)
        out_filename = f"find_replace_{clean_filename}"
        out_path = out_dir / out_filename

        output_bytes = doc.write()
        doc.close()

        out_path.write_bytes(output_bytes)

        return {
            "success": True,
            "session_id": session_id,
            "original_filename": clean_filename,
            "saved_filename": out_filename,
            "total_replacements": total_replacements,
            "search_query": query,
            "replacement_text": replace_val,
            "download_url": f"/document-management/find-replace/download/{session_id}",
        }

    def get_replaced_file_for_download(self, session_id: str) -> Tuple[Path, str]:
        """Retrieve output PDF for download."""
        out_dir = Paths.request_output(session_id)
        files = [f for f in out_dir.glob("*.pdf") if f.is_file()] if out_dir.exists() else []
        if not files:
            raise ValueError("Replaced PDF file not found for this session.")
        return files[0], files[0].name


find_replace_service = FindReplaceService()
