"""
Watermark Protection service.

Contains the framework-independent business logic for applying text and image
watermarks to PDFs using PyMuPDF (fitz).
"""

from __future__ import annotations

import logging
import math
import io
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz
from PIL import Image

logger = logging.getLogger(__name__)

class WatermarkProtectionService:
    """Apply text and image watermarks to PDF files."""

    @staticmethod
    def _parse_pages(page_range: str, total_pages: int) -> List[int]:
        """Parse user page selection into a list of 0-indexed page numbers."""
        val = page_range.strip().lower()
        if not val or val == "all":
            return list(range(total_pages))
        if val == "first":
            return [0]
        if val == "last":
            return [total_pages - 1]

        pages = set()
        for part in val.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    start_str, end_str = part.split("-", 1)
                    start = int(start_str.strip())
                    end = int(end_str.strip())
                    if start < 1 or end > total_pages or start > end:
                        continue
                    for p in range(start, end + 1):
                        pages.add(p - 1)
                except ValueError:
                    pass
            else:
                try:
                    p = int(part)
                    if 1 <= p <= total_pages:
                        pages.add(p - 1)
                except ValueError:
                    pass
        
        return sorted(list(pages))

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
        """Convert a hex color like #FF0000 to (r, g, b) where each is 0.0-1.0."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        if len(hex_color) != 6:
            return (0.0, 0.0, 0.0)
        try:
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError:
            return (0.0, 0.0, 0.0)

    @staticmethod
    def _calculate_rect(
        page_rect: fitz.Rect,
        w: float,
        h: float,
        position: str,
        margin: float = 30.0,
        pos_x: Optional[float] = None,
        pos_y: Optional[float] = None,
    ) -> fitz.Rect:
        """Calculate bounding box rect based on position."""
        if position.strip().lower() == "custom" and pos_x is not None and pos_y is not None:
            # Map absolute coordinates from frontend to fitz coordinates
            # Note: The frontend sends the center X, Y in PDF points.
            # We must convert center to top-left for PyMuPDF rect.
            x0 = page_rect.x0 + pos_x - (w / 2)
            y0 = page_rect.y0 + pos_y - (h / 2)
            return fitz.Rect(x0, y0, x0 + w, y0 + h)
            
        pos = position.strip().lower()
        
        if pos == "top left":
            x0, y0 = page_rect.x0 + margin, page_rect.y0 + margin
        elif pos == "top center":
            x0, y0 = page_rect.x0 + (page_rect.width - w) / 2, page_rect.y0 + margin
        elif pos == "top right":
            x0, y0 = page_rect.x1 - w - margin, page_rect.y0 + margin
        elif pos == "center left":
            x0, y0 = page_rect.x0 + margin, page_rect.y0 + (page_rect.height - h) / 2
        elif pos == "center":
            x0, y0 = page_rect.x0 + (page_rect.width - w) / 2, page_rect.y0 + (page_rect.height - h) / 2
        elif pos == "center right":
            x0, y0 = page_rect.x1 - w - margin, page_rect.y0 + (page_rect.height - h) / 2
        elif pos == "bottom left":
            x0, y0 = page_rect.x0 + margin, page_rect.y1 - h - margin
        elif pos == "bottom center":
            x0, y0 = page_rect.x0 + (page_rect.width - w) / 2, page_rect.y1 - h - margin
        elif pos == "bottom right":
            x0, y0 = page_rect.x1 - w - margin, page_rect.y1 - h - margin
        else:
            x0, y0 = page_rect.x0 + (page_rect.width - w) / 2, page_rect.y0 + (page_rect.height - h) / 2
            
        return fitz.Rect(x0, y0, x0 + w, y0 + h)

    def apply_watermark(
        self,
        input_path: Path,
        output_path: Path,
        watermark_type: str,
        pages: str,
        position: str,
        rotation: int,
        opacity: int,
        # Position override
        pos_x: Optional[float] = None,
        pos_y: Optional[float] = None,
        # Text specific
        text: Optional[str] = None,
        font_color: Optional[str] = None,
        font_size: Optional[int] = None,
        # Image specific
        image_path: Optional[Path] = None,
        scale: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Applies a watermark and saves it to output_path.
        Returns a dictionary with result metadata.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        watermark_type = watermark_type.strip().lower()
        if watermark_type not in ["text", "image"]:
            raise ValueError("Invalid watermark_type. Must be 'text' or 'image'.")
            
        opacity_float = max(0, min(100, opacity)) / 100.0

        try:
            doc = fitz.open(input_path)
            
            if doc.is_encrypted:
                raise ValueError("PDF is encrypted and cannot be watermarked without a password.")

            target_pages = self._parse_pages(pages, len(doc))
            if not target_pages:
                raise ValueError("No valid pages selected for watermarking.")

            if watermark_type == "text":
                if not text:
                    raise ValueError("Text watermark requires 'text' parameter.")
                color_rgb = self._hex_to_rgb(font_color or "#000000")
                size = font_size or 48
                fontname = "helv"

                # Calculate text dimensions
                tw = fitz.get_text_length(text, fontname=fontname, fontsize=size)
                th = size

                for p_num in target_pages:
                    page = doc[p_num]
                    # Create a transparent shape to insert text if opacity < 1
                    # A robust way is creating a transparent rect/text using shape
                    shape = page.new_shape()
                    rect = self._calculate_rect(page.rect, tw, th, position, pos_x=pos_x, pos_y=pos_y)
                    
                    # We can use insert_text with a rotation matrix if we want to rotate around center.
                    # Wait, Shape.insert_textbox allows rotation!
                    # And Shape allows setting opacity!
                    
                    # If we need arbitrary rotation around the center:
                    cx = rect.x0 + tw / 2
                    cy = rect.y0 + th / 2
                    
                    # Text box approach:
                    # The morph matrix rotates the text.
                    morph = fitz.Matrix(-rotation)  # counter-clockwise rotation
                    
                    # Instead of shape, let's use page.insert_text which accepts morph matrix.
                    # Or we just use `page.insert_text` with `fill_opacity`.
                    p = fitz.Point(rect.x0, rect.y1 - (th * 0.2)) # Baseline approximate
                    
                    # PyMuPDF's morph parameter automatically rotates around the fixpoint
                    # so we just need a simple rotation matrix and set fixpoint to center (cx, cy)
                    mat = fitz.Matrix(-rotation)
                    
                    page.insert_text(
                        p,
                        text,
                        fontsize=size,
                        fontname=fontname,
                        color=color_rgb,
                        fill_opacity=opacity_float,
                        morph=(fitz.Point(cx, cy), mat)
                    )
            
            if watermark_type == "image":
                if not image_path or not image_path.exists():
                    raise ValueError("Image watermark requires a valid 'image_path'.")
                
                # Load image to get dimensions safely and apply opacity
                try:
                    img = Image.open(image_path).convert("RGBA")
                    orig_w, orig_h = img.size
                    
                    if opacity_float < 1.0:
                        alpha = img.split()[3]
                        alpha = alpha.point(lambda p: int(p * opacity_float))
                        img.putalpha(alpha)
                        
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format="PNG")
                    img_bytes = img_byte_arr.getvalue()
                except Exception as e:
                    raise ValueError("Unsupported or invalid image format.") from e
                
                # The frontend assumes a base intrinsic width of 200 PDF points.
                s = (scale or 100) / 100.0
                w = 200.0 * s
                h = orig_h * (w / orig_w) if orig_w > 0 else 200.0 * s
                
                for p_num in target_pages:
                    page = doc[p_num]
                    rect = self._calculate_rect(page.rect, w, h, position, pos_x=pos_x, pos_y=pos_y)
                    
                    page.insert_image(
                        rect,
                        stream=img_bytes,
                        keep_proportion=True,
                        overlay=True,
                        rotate=rotation,
                    )
                    # Note: PyMuPDF doesn't natively expose image opacity directly in insert_image,
                    # but we can apply it using ExtGState if we draw it manually, or the user can upload a transparent image.

            doc.save(output_path, garbage=3, deflate=True)
            doc.close()

            return {
                "success": True,
                "message": "Watermark applied successfully.",
                "watermark_type": watermark_type,
                "pages_processed": len(target_pages),
            }

        except Exception as e:
            logger.error(f"Watermarking failed: {e}", exc_info=True)
            raise ValueError(f"Failed to apply watermark: {str(e)}")

watermark_protection_service = WatermarkProtectionService()
