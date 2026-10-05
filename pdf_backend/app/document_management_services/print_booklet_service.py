"""
Print Booklet Service — Document Management Section.

PDF booklet imposition tool:
  - Rearrange pages for booklet printing (fold + staple)
  - Auto-pad to multiple of 4 (blank pages)
  - Correct imposition: last+first, second+second-last, inward
  - Front/back sides for duplex printing
  - Long-edge / short-edge binding
  - Left / right / top binding options
  - A4, A3, Letter, Legal, custom paper size
  - Portrait / Landscape handling
  - Inner/outer margins, gutter/binding margin
  - Fit-to-area scaling preserving aspect ratio
  - Optional page borders, crop marks, bleed area
  - Sheet-by-sheet preview
  - Generate print-ready booklet PDF
  - Download generated PDF
"""

from __future__ import annotations

import logging
import math
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

import fitz  # PyMuPDF

from app.core.paths import Paths

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

PAPER_SIZES_MM = {
    "a4": (210, 297),
    "a3": (297, 420),
    "letter": (215.9, 279.4),
    "legal": (215.9, 355.6),
    "a5": (148, 210),
    "tabloid": (279.4, 431.8),
}

MM_TO_PT = 72 / 25.4


def _mm_to_pt(mm: float) -> float:
    return mm * MM_TO_PT


class PrintBookletService:
    """Service for PDF booklet imposition."""

    def validate_pdf(self, pdf_bytes: bytes) -> fitz.Document:
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise ValueError("Uploaded file is empty.")
        if len(pdf_bytes) > MAX_FILE_SIZE_BYTES:
            size_mb = len(pdf_bytes) / (1024 * 1024)
            raise ValueError(f"File size ({size_mb:.1f} MB) exceeds 100 MB limit.")
        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("Invalid PDF document (missing %PDF header).")
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception:
            raise ValueError("Corrupted or unreadable PDF document.")
        if doc.is_encrypted:
            doc.close()
            raise ValueError("PDF is encrypted or password-protected.")
        return doc

    def parse_page_range(self, page_range: str, total_pages: int) -> List[int]:
        if not page_range or not page_range.strip():
            return list(range(total_pages))
        pages = set()
        for part in page_range.split(","):
            part = part.strip()
            if "-" in part:
                start_s, end_s = part.split("-", 1)
                try:
                    start = int(start_s.strip())
                    end = int(end_s.strip())
                except ValueError:
                    continue
                for p in range(max(1, start), min(total_pages, end) + 1):
                    pages.add(p - 1)
            else:
                try:
                    p = int(part.strip())
                    if 1 <= p <= total_pages:
                        pages.add(p - 1)
                except ValueError:
                    continue
        return sorted(pages)

    def _pad_to_multiple_of_4(self, page_indices: List[int]) -> List[int]:
        """Pad page list to length divisible by 4 using -1 as blank marker."""
        remainder = len(page_indices) % 4
        if remainder != 0:
            pad_count = 4 - remainder
            page_indices = page_indices + ([-1] * pad_count)
        return page_indices

    def compute_booklet_order(self, page_indices: List[int]) -> Dict[str, Any]:
        """Compute booklet imposition order.

        Returns sheet layout info with front/back pages for each sheet.
        """
        padded = self._pad_to_multiple_of_4(list(page_indices))
        total = len(padded)
        sheets = total // 4

        sheet_layouts = []
        for s in range(sheets):
            # Standard booklet imposition
            front_left = padded[total - 1 - 2 * s]     # last pages work inward
            front_right = padded[2 * s]                  # first pages work inward
            back_left = padded[2 * s + 1]                # second pages work inward
            back_right = padded[total - 2 - 2 * s]      # second-last work inward

            sheet_layouts.append({
                "sheet_number": s + 1,
                "front": {
                    "left": front_left,
                    "right": front_right,
                },
                "back": {
                    "left": back_left,
                    "right": back_right,
                },
            })

        return {
            "original_pages": len(page_indices),
            "padded_pages": total,
            "blank_pages": total - len(page_indices),
            "sheets": sheets,
            "sheet_layouts": sheet_layouts,
        }

    def _get_paper_dims(self, paper_size: str, custom_w: float, custom_h: float) -> Tuple[float, float]:
        if paper_size == "custom":
            if custom_w <= 0 or custom_h <= 0:
                raise ValueError("Custom paper size requires positive width and height in mm.")
            return _mm_to_pt(custom_w), _mm_to_pt(custom_h)
        if paper_size not in PAPER_SIZES_MM:
            raise ValueError(f"Unknown paper size: {paper_size}.")
        w, h = PAPER_SIZES_MM[paper_size]
        return _mm_to_pt(w), _mm_to_pt(h)

    def _resolve_orientation(self, orientation: str, paper_w: float, paper_h: float) -> Tuple[float, float]:
        if orientation == "landscape":
            return (max(paper_w, paper_h), min(paper_w, paper_h))
        return (min(paper_w, paper_h), max(paper_w, paper_h))

    def preview(
        self,
        pdf_bytes: bytes,
        page_range: str = "",
        paper_size: str = "a4",
        orientation: str = "portrait",
        binding: str = "left",
        duplex: str = "long-edge",
        margin_inner_mm: float = 15,
        margin_outer_mm: float = 10,
        gutter_mm: float = 8,
        bleed_mm: float = 0,
        custom_w: float = 0,
        custom_h: float = 0,
    ) -> Dict[str, Any]:
        """Return booklet preview info."""
        doc = self.validate_pdf(pdf_bytes)
        page_indices = self.parse_page_range(page_range, doc.page_count)
        total_doc_pages = doc.page_count

        if len(page_indices) == 0:
            doc.close()
            raise ValueError("No valid pages in the specified range.")

        sample_page = doc[page_indices[0]]
        page_rect = sample_page.rect
        page_aspect = page_rect.width / page_rect.height
        doc.close()

        booklet = self.compute_booklet_order(page_indices)
        paper_w, paper_h = self._get_paper_dims(paper_size, custom_w, custom_h)
        sheet_w, sheet_h = self._resolve_orientation(orientation, paper_w, paper_h)

        margin_inner = _mm_to_pt(margin_inner_mm)
        margin_outer = _mm_to_pt(margin_outer_mm)
        gutter = _mm_to_pt(gutter_mm)
        bleed = _mm_to_pt(bleed_mm)

        # Each side of a sheet has 2 pages side by side
        # After folding: inner pages near gutter, outer pages near margin_outer
        side_w = (sheet_w - gutter - 2 * margin_inner - 2 * margin_outer - 2 * bleed) / 2
        side_h = sheet_h - 2 * margin_outer - 2 * bleed

        # Fit page into side preserving aspect ratio
        side_aspect = side_w / side_h
        if page_aspect > side_aspect:
            display_w = side_w
            display_h = side_w / page_aspect
        else:
            display_h = side_h
            display_w = side_h * page_aspect

        return {
            "success": True,
            "booklet": booklet,
            "sheet_width_pt": round(sheet_w, 1),
            "sheet_height_pt": round(sheet_h, 1),
            "side_width_pt": round(side_w, 1),
            "side_height_pt": round(side_h, 1),
            "display_width_pt": round(display_w, 1),
            "display_height_pt": round(display_h, 1),
            "margin_inner_pt": round(margin_inner, 1),
            "margin_outer_pt": round(margin_outer, 1),
            "gutter_pt": round(gutter, 1),
            "bleed_pt": round(bleed, 1),
            "paper_size": paper_size,
            "orientation": orientation,
            "binding": binding,
            "duplex": duplex,
            "page_range": page_range or f"1-{total_doc_pages}",
        }

    def generate(
        self,
        pdf_bytes: bytes,
        session_id: str,
        page_range: str = "",
        paper_size: str = "a4",
        orientation: str = "portrait",
        binding: str = "left",
        duplex: str = "long-edge",
        margin_inner_mm: float = 15,
        margin_outer_mm: float = 10,
        gutter_mm: float = 8,
        bleed_mm: float = 0,
        show_borders: bool = False,
        show_crop_marks: bool = False,
        custom_w: float = 0,
        custom_h: float = 0,
        output_name: str = "",
    ) -> Dict[str, Any]:
        """Generate booklet PDF."""
        src_doc = self.validate_pdf(pdf_bytes)
        page_indices = self.parse_page_range(page_range, src_doc.page_count)

        if len(page_indices) == 0:
            src_doc.close()
            raise ValueError("No valid pages in the specified range.")

        booklet = self.compute_booklet_order(page_indices)
        paper_w, paper_h = self._get_paper_dims(paper_size, custom_w, custom_h)
        sheet_w, sheet_h = self._resolve_orientation(orientation, paper_w, paper_h)

        margin_inner = _mm_to_pt(margin_inner_mm)
        margin_outer = _mm_to_pt(margin_outer_mm)
        gutter = _mm_to_pt(gutter_mm)
        bleed = _mm_to_pt(bleed_mm)

        side_w = (sheet_w - gutter - 2 * margin_inner - 2 * margin_outer - 2 * bleed) / 2
        side_h = sheet_h - 2 * margin_outer - 2 * bleed

        # Blank page placeholder
        blank_page = fitz.open()
        blank_page.new_page(width=612, height=792)
        blank_bytes = blank_page.write()
        blank_page.close()

        out_doc = fitz.open()

        for sheet in booklet["sheet_layouts"]:
            front = sheet["front"]
            back = sheet["back"]

            # Create front side sheet
            front_page = out_doc.new_page(width=sheet_w, height=sheet_h)
            self._draw_sheet_side(
                front_page, src_doc, blank_bytes,
                front["left"], front["right"],
                sheet_w, sheet_h, side_w, side_h,
                margin_inner, margin_outer, gutter, bleed,
                binding, show_borders,
            )
            if show_crop_marks:
                self._draw_crop_marks(front_page, sheet_w, sheet_h, margin_outer, bleed)

            # Create back side sheet (mirrored for duplex)
            back_page = out_doc.new_page(width=sheet_w, height=sheet_h)
            self._draw_sheet_side(
                back_page, src_doc, blank_bytes,
                back["left"], back["right"],
                sheet_w, sheet_h, side_w, side_h,
                margin_inner, margin_outer, gutter, bleed,
                binding, show_borders,
                is_back=True,
            )
            if show_crop_marks:
                self._draw_crop_marks(back_page, sheet_w, sheet_h, margin_outer, bleed)

        src_doc.close()

        # Save
        out_dir = Paths.request_output(session_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        if not output_name:
            output_name = "booklet.pdf"
        if not output_name.lower().endswith(".pdf"):
            output_name += ".pdf"

        out_path = out_dir / output_name
        output_bytes = out_doc.write()
        out_doc.close()
        out_path.write_bytes(output_bytes)

        return {
            "success": True,
            "output_filename": output_name,
            "original_pages": booklet["original_pages"],
            "padded_pages": booklet["padded_pages"],
            "blank_pages": booklet["blank_pages"],
            "sheets": booklet["sheets"],
            "total_output_pages": booklet["sheets"] * 2,  # front + back per sheet
            "file_size": len(output_bytes),
            "download_url": f"/document-management/print-booklet/download/{session_id}",
        }

    def _draw_sheet_side(
        self,
        page: fitz.Page,
        src_doc: fitz.Document,
        blank_bytes: bytes,
        left_page_idx: int,
        right_page_idx: int,
        sheet_w: float,
        sheet_h: float,
        side_w: float,
        side_h: float,
        margin_inner: float,
        margin_outer: float,
        gutter: float,
        bleed: float,
        binding: str,
        show_borders: bool,
        is_back: bool = False,
    ) -> None:
        """Draw two pages on one side of a booklet sheet."""
        # Determine left/right placement based on binding
        if binding == "right":
            # For right binding, flip sides
            left_page_idx, right_page_idx = right_page_idx, left_page_idx

        # For back side, pages are mirrored (reading order preserved after flip)
        if is_back:
            left_page_idx, right_page_idx = right_page_idx, left_page_idx

        # Calculate positions
        x_left = margin_outer + bleed
        x_right = margin_outer + bleed + side_w + gutter + 2 * margin_inner
        y_top = margin_outer + bleed

        # Place left page
        self._place_page(page, src_doc, blank_bytes, left_page_idx, x_left, y_top, side_w, side_h, show_borders)

        # Place right page
        self._place_page(page, src_doc, blank_bytes, right_page_idx, x_right, y_top, side_w, side_h, show_borders)

        # Draw gutter line
        shape = page.new_shape()
        gutter_x = margin_outer + bleed + side_w + margin_inner
        shape.draw_line(fitz.Point(gutter_x, margin_outer + bleed), fitz.Point(gutter_x, sheet_h - margin_outer - bleed))
        shape.finish(color=(0.85, 0.85, 0.85), width=0.3)
        shape.commit()

    def _place_page(
        self,
        page: fitz.Page,
        src_doc: fitz.Document,
        blank_bytes: bytes,
        page_idx: int,
        x: float,
        y: float,
        cell_w: float,
        cell_h: float,
        show_borders: bool,
    ) -> None:
        """Place a single page into the sheet, fitting to cell."""
        if page_idx < 0:
            # Blank page
            if show_borders:
                shape = page.new_shape()
                shape.draw_rect(fitz.Rect(x, y, x + cell_w, y + cell_h))
                shape.finish(color=(0.8, 0.8, 0.8), width=0.3, dashes="[2 2]")
                shape.commit()
            return

        src_page = src_doc[page_idx]
        src_rect = src_page.rect

        # Fit preserving aspect ratio
        src_aspect = src_rect.width / src_rect.height
        cell_aspect = cell_w / cell_h
        if src_aspect > cell_aspect:
            draw_w = cell_w
            draw_h = cell_w / src_aspect
        else:
            draw_h = cell_h
            draw_w = cell_h * src_aspect

        # Center in cell
        cx = x + (cell_w - draw_w) / 2
        cy = y + (cell_h - draw_h) / 2
        dest_rect = fitz.Rect(cx, cy, cx + draw_w, cy + draw_h)

        page.show_pdf_page(dest_rect, src_doc, page_idx, fitz.Matrix(1, 1))

        if show_borders:
            shape = page.new_shape()
            shape.draw_rect(fitz.Rect(x, y, x + cell_w, y + cell_h))
            shape.finish(color=(0.6, 0.6, 0.6), width=0.5)
            shape.commit()

    def _draw_crop_marks(
        self, page: fitz.Page, sheet_w: float, sheet_h: float,
        margin: float, bleed: float,
    ) -> None:
        """Draw crop marks at sheet corners."""
        shape = page.new_shape()
        mark_len = 8
        offset = 3

        corners = [
            (margin + bleed, margin + bleed),
            (sheet_w - margin - bleed, margin + bleed),
            (margin + bleed, sheet_h - margin - bleed),
            (sheet_w - margin - bleed, sheet_h - margin - bleed),
        ]

        for cx, cy in corners:
            # Horizontal
            if cx < sheet_w / 2:
                shape.draw_line(fitz.Point(cx - mark_len, cy), fitz.Point(cx - offset, cy))
            else:
                shape.draw_line(fitz.Point(cx + offset, cy), fitz.Point(cx + mark_len, cy))
            # Vertical
            if cy < sheet_h / 2:
                shape.draw_line(fitz.Point(cx, cy - mark_len), fitz.Point(cx, cy - offset))
            else:
                shape.draw_line(fitz.Point(cx, cy + offset), fitz.Point(cx, cy + mark_len))

        shape.finish(color=(0, 0, 0), width=0.3)
        shape.commit()

    def get_file_for_download(self, session_id: str) -> Tuple[Path, str]:
        out_dir = Paths.request_output(session_id)
        if not out_dir.exists():
            raise ValueError("Session data not found or expired.")
        files = [f for f in out_dir.glob("*.pdf") if f.is_file()]
        if not files:
            raise ValueError("Output PDF not found for this session.")
        return files[0], files[0].name


print_booklet_service = PrintBookletService()
