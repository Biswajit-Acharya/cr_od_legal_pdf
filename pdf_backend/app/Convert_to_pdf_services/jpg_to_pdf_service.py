"""
JPG / PNG to PDF conversion service.

Uses Pillow (already in requirements) for image handling and pypdf for
PDF assembly. No new dependencies required.
"""

from __future__ import annotations

import io
import logging
import math
import os
import re
import shutil
import struct
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS
from pypdf import PdfWriter, PdfReader
from pypdf.generic import NameObject

from app.core.paths import Paths

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Standard page sizes in points (1 pt = 1/72 inch)
PAGE_SIZES_PT: Dict[str, Tuple[float, float]] = {
    "a4":     (595.28, 841.89),
    "a3":     (841.89, 1190.55),
    "a5":     (419.53, 595.28),
    "letter": (612.00, 792.00),
    "legal":  (612.00, 1008.00),
}

# Margin presets in points
MARGIN_PRESETS: Dict[str, float] = {
    "none":   0.0,
    "small":  14.17,   # ~5 mm
    "medium": 28.35,   # ~10 mm
    "large":  56.69,   # ~20 mm
}

# EXIF orientation tag
EXIF_ORIENTATION_TAG = 274

# Allowed extensions
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tif", ".tiff", ".heic", ".heif", ".ico", ".jfif", ".pjpeg", ".pjp"
}


def convert_any_image_to_pdf(input_path: Path, output_pdf_path: Path) -> bool:
    """Convert any image file (JPG, PNG, Screenshot, WEBP, BMP, etc.) directly into a clean PDF page."""
    try:
        with Image.open(input_path) as img:
            img = _apply_exif_orientation(img)
            rgb_img = _to_rgb(img)
            output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            rgb_img.save(str(output_pdf_path), "PDF", resolution=100.0)
            return True
    except Exception as e:
        logger.error(f"Failed to convert image {input_path} to PDF: {e}")
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_filename(name: str) -> str:
    """Remove unsafe characters from a filename."""
    name = os.path.basename(name)          # strip any path component
    name = re.sub(r'[^\w\-. ]', '_', name) # keep word chars, dash, dot, space
    name = name.strip(". ")
    return name or "converted_images"


def _apply_exif_orientation(img: Image.Image) -> Image.Image:
    """Rotate / flip image to match EXIF orientation tag."""
    try:
        exif_data = img._getexif()  # type: ignore[attr-defined]
        if exif_data is None:
            return img
        orientation = exif_data.get(EXIF_ORIENTATION_TAG)
        if orientation == 2:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            img = img.rotate(180, expand=True)
        elif orientation == 4:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        elif orientation == 5:
            img = img.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 6:
            img = img.rotate(-90, expand=True)
        elif orientation == 7:
            img = img.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 8:
            img = img.rotate(90, expand=True)
    except Exception:
        pass
    return img


def _to_rgb(img: Image.Image, bg_color: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """Convert any PIL image mode to RGB, handling transparency safely."""
    if img.mode == "RGB":
        return img
    if img.mode in ("RGBA", "LA", "PA"):
        background = Image.new("RGB", img.size, bg_color)
        mask = img.split()[-1] if img.mode in ("RGBA", "LA") else None
        if img.mode == "PA":
            img = img.convert("RGBA")
            mask = img.split()[-1]
        if mask:
            background.paste(img.convert("RGB"), mask=mask)
        else:
            background.paste(img.convert("RGB"))
        return background
    return img.convert("RGB")


def _parse_custom_dims(width_str: str, height_str: str, unit: str) -> Tuple[float, float]:
    """Parse custom page dimensions and return (width_pt, height_pt)."""
    try:
        w = float(width_str)
        h = float(height_str)
    except (ValueError, TypeError):
        raise ValueError("Custom page dimensions must be valid numbers.")

    if w <= 0 or h <= 0:
        raise ValueError("Custom page dimensions must be positive.")
    if unit == "mm":
        w = w * 72 / 25.4
        h = h * 72 / 25.4
    elif unit == "inch":
        w = w * 72
        h = h * 72
    elif unit == "pt":
        pass
    else:
        raise ValueError(f"Unknown unit '{unit}'. Use mm, inch, or pt.")

    if w > 14400 or h > 14400:  # 200 inch max
        raise ValueError("Custom page dimensions are too large.")
    return w, h


def _resolve_page_size(
    page_size: str,
    orientation: str,
    img_w: int,
    img_h: int,
    dpi: float,
    custom_w_str: str = "",
    custom_h_str: str = "",
    custom_unit: str = "mm",
) -> Tuple[float, float]:
    """Return (page_width_pt, page_height_pt) for given settings."""

    if page_size == "original":
        # Physical size based on image DPI
        eff_dpi = dpi if dpi > 0 else 96.0
        w_pt = img_w * 72.0 / eff_dpi
        h_pt = img_h * 72.0 / eff_dpi
    elif page_size == "custom":
        w_pt, h_pt = _parse_custom_dims(custom_w_str, custom_h_str, custom_unit)
    else:
        size_key = page_size.lower()
        if size_key not in PAGE_SIZES_PT:
            raise ValueError(f"Unknown page size '{page_size}'.")
        w_pt, h_pt = PAGE_SIZES_PT[size_key]

    # Apply orientation
    if orientation == "portrait":
        if w_pt > h_pt:
            w_pt, h_pt = h_pt, w_pt
    elif orientation == "landscape":
        if h_pt > w_pt:
            w_pt, h_pt = h_pt, w_pt
    elif orientation == "auto":
        # Match image shape
        if img_w > img_h and h_pt > w_pt:
            w_pt, h_pt = h_pt, w_pt
        elif img_h >= img_w and w_pt > h_pt:
            w_pt, h_pt = h_pt, w_pt

    return w_pt, h_pt


def _resolve_margins(
    margin_preset: str,
    custom_top: str = "0",
    custom_right: str = "0",
    custom_bottom: str = "0",
    custom_left: str = "0",
) -> Tuple[float, float, float, float]:
    """Return (top, right, bottom, left) margin in points."""
    if margin_preset == "custom":
        try:
            top    = float(custom_top)    * 72 / 25.4  # treat as mm
            right  = float(custom_right)  * 72 / 25.4
            bottom = float(custom_bottom) * 72 / 25.4
            left   = float(custom_left)   * 72 / 25.4
        except (ValueError, TypeError):
            raise ValueError("Custom margin values must be valid numbers (in mm).")
        if any(v < 0 for v in (top, right, bottom, left)):
            raise ValueError("Margin values cannot be negative.")
        return top, right, bottom, left
    m = MARGIN_PRESETS.get(margin_preset, 0.0)
    return m, m, m, m


def _fit_image(
    img_w: int, img_h: int,
    area_w: float, area_h: float,
    fit_mode: str,
) -> Tuple[float, float, float, float]:
    """
    Return (x, y, draw_w, draw_h) in points inside the area box.
    area origin is (0,0), positive Y down.
    """
    img_ratio = img_w / img_h
    area_ratio = area_w / area_h

    if fit_mode == "fill":
        # Scale to fill; allow cropping
        if img_ratio > area_ratio:
            draw_h = area_h
            draw_w = draw_h * img_ratio
        else:
            draw_w = area_w
            draw_h = draw_w / img_ratio
        x = (area_w - draw_w) / 2
        y = (area_h - draw_h) / 2

    elif fit_mode == "original":
        # No scaling — use image's natural pt size at 96 dpi reference
        draw_w = img_w * 72.0 / 96.0
        draw_h = img_h * 72.0 / 96.0
        # Cap to area if too large
        if draw_w > area_w or draw_h > area_h:
            scale = min(area_w / draw_w, area_h / draw_h)
            draw_w *= scale
            draw_h *= scale
        x = (area_w - draw_w) / 2
        y = (area_h - draw_h) / 2

    else:  # "fit" (default)
        if img_ratio > area_ratio:
            draw_w = area_w
            draw_h = draw_w / img_ratio
        else:
            draw_h = area_h
            draw_w = draw_h * img_ratio
        x = (area_w - draw_w) / 2
        y = (area_h - draw_h) / 2

    return x, y, draw_w, draw_h


def _quality_to_jpeg_q(quality_preset: str) -> int:
    """Map named quality preset to JPEG quality integer."""
    return {"maximum": 95, "high": 85, "medium": 70, "small": 50}.get(quality_preset, 85)


def _add_watermark_to_page(
    canvas_img: Image.Image,
    text: str,
    opacity: float,
    position: str,
    rotation: float,
) -> Image.Image:
    """Overlay a text watermark on a PIL RGBA canvas."""
    if not text.strip():
        return canvas_img

    # Ensure RGBA for compositing
    canvas_rgba = canvas_img.convert("RGBA")
    w, h = canvas_rgba.size

    # Build watermark layer
    wm_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(wm_layer)

    font_size = max(24, int(min(w, h) / 12))
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    # Measure text
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Determine position
    padding = 20
    if position == "center":
        tx, ty = (w - tw) / 2, (h - th) / 2
    elif position == "top-left":
        tx, ty = padding, padding
    elif position == "top-right":
        tx, ty = w - tw - padding, padding
    elif position == "bottom-left":
        tx, ty = padding, h - th - padding
    else:  # bottom-right / default
        tx, ty = w - tw - padding, h - th - padding

    alpha = max(0, min(255, int(opacity * 255 / 100)))
    draw.text((tx, ty), text, font=font, fill=(128, 128, 128, alpha))

    # Rotate if needed
    if rotation != 0:
        wm_layer = wm_layer.rotate(-rotation, expand=False)

    combined = Image.alpha_composite(canvas_rgba, wm_layer)
    return combined.convert("RGB")


def _add_page_number_to_img(
    canvas_img: Image.Image,
    page_num: int,
    position: str,
    font_size: int = 24,
) -> Image.Image:
    """Draw page number onto a PIL image (RGB)."""
    img = canvas_img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    text = str(page_num)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    w, h = img.size
    padding = max(10, font_size // 2)

    if position == "bottom-center":
        tx = (w - tw) / 2
        ty = h - th - padding
    elif position == "bottom-left":
        tx = padding
        ty = h - th - padding
    else:  # bottom-right
        tx = w - tw - padding
        ty = h - th - padding

    draw.text((tx, ty), text, font=font, fill=(50, 50, 50, 220))
    combined = Image.alpha_composite(img, overlay)
    return combined.convert("RGB")


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class JpgToPdfService:
    """Convert one or more image files into a single PDF document."""

    # Max file size per image (bytes): 50 MB
    MAX_IMAGE_BYTES = 50 * 1024 * 1024

    def validate_image_file(self, path: Path) -> None:
        """Raise ValueError if the file is not a usable image."""
        if not path.exists():
            raise ValueError(f"Image file not found: {path.name}")
        if path.stat().st_size == 0:
            raise ValueError(f"File '{path.name}' is empty.")
        if path.stat().st_size > self.MAX_IMAGE_BYTES:
            raise ValueError(f"File '{path.name}' exceeds the 50 MB size limit.")
        ext = path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File '{path.name}' has an unsupported extension '{ext}'. "
                f"Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        # Verify it is actually an image
        try:
            with Image.open(path) as img:
                img.verify()
        except Exception:
            raise ValueError(f"File '{path.name}' is not a valid image or is corrupted.")

    def _render_page_image(
        self,
        img: Image.Image,
        page_w_pt: float,
        page_h_pt: float,
        margin_top: float,
        margin_right: float,
        margin_bottom: float,
        margin_left: float,
        fit_mode: str,
        bg_color: Tuple[int, int, int],
        dpi: float,
    ) -> Image.Image:
        """
        Render the source image onto a page canvas (PIL Image in RGB).

        The canvas pixel size is computed from page_pt * (dpi/72) so the
        resulting JPEG embedded in the PDF will have the desired DPI.
        """
        scale = dpi / 72.0
        canvas_px_w = max(1, int(round(page_w_pt * scale)))
        canvas_px_h = max(1, int(round(page_h_pt * scale)))

        canvas = Image.new("RGB", (canvas_px_w, canvas_px_h), bg_color)

        # Margin in pixels
        ml = int(round(margin_left  * scale))
        mr = int(round(margin_right * scale))
        mt = int(round(margin_top   * scale))
        mb = int(round(margin_bottom * scale))

        area_px_w = canvas_px_w - ml - mr
        area_px_h = canvas_px_h - mt - mb

        if area_px_w <= 0 or area_px_h <= 0:
            logger.warning("Margins leave no drawable area — using full page.")
            area_px_w = canvas_px_w
            area_px_h = canvas_px_h
            ml = mt = 0

        img_w, img_h = img.size
        # _fit_image returns in points; multiply by scale for pixels
        x_pt, y_pt, draw_w_pt, draw_h_pt = _fit_image(
            img_w, img_h,
            area_px_w / scale,  # convert back to pt for aspect math
            area_px_h / scale,
            fit_mode,
        )

        draw_px_w = max(1, int(round(draw_w_pt * scale)))
        draw_px_h = max(1, int(round(draw_h_pt * scale)))
        x_px = ml + int(round(x_pt * scale))
        y_px = mt + int(round(y_pt * scale))

        # For 'fill', we crop: clamp the paste position
        resized = img.resize((draw_px_w, draw_px_h), Image.LANCZOS)

        if fit_mode == "fill":
            # Crop to area
            crop_x = max(0, -x_px)
            crop_y = max(0, -y_px)
            crop_x2 = crop_x + area_px_w
            crop_y2 = crop_y + area_px_h
            cropped = resized.crop((crop_x, crop_y, crop_x2, crop_y2))
            canvas.paste(cropped, (ml, mt))
        else:
            # Clip to canvas bounds
            paste_x = max(0, x_px)
            paste_y = max(0, y_px)
            canvas.paste(resized, (paste_x, paste_y))

        return canvas

    async def process(
        self,
        request_id: str,
        filenames: List[str],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert images to a single PDF and save to the output directory.

        Returns dict with success, request_id, pdf_filename.
        """
        upload_dir = Paths.request_upload(request_id)
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not filenames:
            raise ValueError("No images were provided for conversion.")

        # --- Extract config ---
        page_size       = config.get("page_size", "a4").lower()
        orientation     = config.get("orientation", "auto").lower()
        fit_mode        = config.get("fit_mode", "fit").lower()
        margin_preset   = config.get("margin_preset", "medium").lower()
        custom_m_top    = config.get("custom_margin_top",    "10")
        custom_m_right  = config.get("custom_margin_right",  "10")
        custom_m_bottom = config.get("custom_margin_bottom", "10")
        custom_m_left   = config.get("custom_margin_left",   "10")
        custom_pw       = config.get("custom_page_width",  "210")
        custom_ph       = config.get("custom_page_height", "297")
        custom_pu       = config.get("custom_page_unit",    "mm")
        dpi_val         = float(config.get("dpi", 150) or 150)
        quality_preset  = config.get("quality", "high").lower()
        jpeg_q          = _quality_to_jpeg_q(quality_preset)

        bg_hex          = config.get("bg_color", "#ffffff").lstrip("#")
        try:
            bg_color = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))  # type: ignore[assignment]
        except Exception:
            bg_color = (255, 255, 255)

        # Watermark
        wm_enabled  = config.get("watermark_enabled", False)
        wm_text     = config.get("watermark_text", "")
        wm_opacity  = float(config.get("watermark_opacity", 30))
        wm_position = config.get("watermark_position", "center").lower()
        wm_rotation = float(config.get("watermark_rotation", 45))

        # Page numbers
        pn_enabled   = config.get("page_numbers_enabled", False)
        pn_start     = int(config.get("page_numbers_start", 1) or 1)
        pn_position  = config.get("page_numbers_position", "bottom-center").lower()

        # PDF metadata
        pdf_title    = config.get("pdf_title", "")
        pdf_author   = config.get("pdf_author", "")
        pdf_subject  = config.get("pdf_subject", "")
        pdf_keywords = config.get("pdf_keywords", "")

        # Output filename
        raw_name = config.get("output_filename", "converted_images")
        safe_name = _sanitize_filename(raw_name)
        if not safe_name.lower().endswith(".pdf"):
            safe_name += ".pdf"

        # Compression
        compress_pdf = config.get("compress_pdf", False)

        # Validate margins
        margin_top, margin_right, margin_bottom, margin_left = _resolve_margins(
            margin_preset, custom_m_top, custom_m_right, custom_m_bottom, custom_m_left
        )

        # Validate DPI
        if dpi_val <= 0:
            dpi_val = 150.0

        # --- Build PDF page by page using pypdf ---
        page_canvases: List[Image.Image] = []

        for idx, filename in enumerate(filenames):
            img_path = upload_dir / filename
            self.validate_image_file(img_path)

            try:
                img = Image.open(img_path)
                img.load()
            except Exception as e:
                raise ValueError(f"Could not open image '{filename}': {e}")

            # EXIF orientation
            img = _apply_exif_orientation(img)

            # Convert to RGB
            img = _to_rgb(img, bg_color=bg_color)  # type: ignore[arg-type]

            img_w, img_h = img.size

            # Resolve page size
            page_w_pt, page_h_pt = _resolve_page_size(
                page_size, orientation,
                img_w, img_h, dpi_val,
                custom_pw, custom_ph, custom_pu,
            )

            # Render page canvas
            canvas = self._render_page_image(
                img,
                page_w_pt, page_h_pt,
                margin_top, margin_right, margin_bottom, margin_left,
                fit_mode,
                bg_color,  # type: ignore[arg-type]
                dpi_val,
            )

            # Watermark
            if wm_enabled and wm_text:
                canvas = _add_watermark_to_page(canvas, wm_text, wm_opacity, wm_position, wm_rotation)

            # Page number
            if pn_enabled:
                page_num_display = pn_start + idx
                font_px = max(18, int(dpi_val / 6))
                canvas = _add_page_number_to_img(canvas, page_num_display, pn_position, font_px)

            page_canvases.append(canvas.convert("RGB"))
            img.close()

        if not page_canvases:
            raise ValueError("No pages were rendered.")

        # Save all pages as a multi-page PDF using Pillow
        output_path = output_dir / safe_name
        first_page = page_canvases[0]
        rest_pages = page_canvases[1:]

        first_page.save(
            output_path,
            format="PDF",
            save_all=True,
            append_images=rest_pages,
            resolution=dpi_val,
        )

        # Close all canvas images
        for c in page_canvases:
            c.close()


        # Inject metadata and optionally compress using pikepdf
        needs_pikepdf = bool(pdf_title or pdf_author or pdf_subject or pdf_keywords or compress_pdf)
        if needs_pikepdf:
            try:
                import pikepdf
                with pikepdf.open(output_path, allow_overwriting_input=True) as pdf:
                    with pdf.open_metadata() as meta:
                        if pdf_title:
                            meta["dc:title"]       = pdf_title
                        if pdf_author:
                            meta["dc:creator"]     = pdf_author
                        if pdf_subject:
                            meta["dc:description"] = pdf_subject
                        if pdf_keywords:
                            meta["pdf:Keywords"]   = pdf_keywords
                        meta["pdf:Producer"] = "PDF Tools"
                    save_kwargs: Dict[str, Any] = {}
                    if compress_pdf:
                        save_kwargs["compress_streams"] = True
                        save_kwargs["object_stream_mode"] = pikepdf.ObjectStreamMode.generate
                    pdf.save(output_path, **save_kwargs)
            except Exception as pe:
                logger.warning(f"pikepdf metadata/compression step failed (PDF still valid): {pe}")

        if not output_path.exists():
            raise RuntimeError("PDF generation failed — output file was not created.")

        logger.info(f"JPG→PDF: {len(filenames)} image(s) → '{safe_name}' [{output_path.stat().st_size} bytes]")

        return {
            "success": True,
            "request_id": request_id,
            "pdf_filename": safe_name,
            "page_count": len(filenames),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _jpeg_bytes_to_pdf_page(jpeg_data: bytes, width_pt: float, height_pt: float) -> bytes:
        """
        Wrap raw JPEG bytes into a minimal valid single-page PDF.
        Uses pypdf's PdfWriter so the result is compatible.
        """
        # We create an in-memory PDF with one JPEG XObject page
        writer = PdfWriter()

        # Build a minimal page using pypdf's low-level API
        from pypdf.generic import (
            ArrayObject, DictionaryObject, DecodedStreamObject,
            FloatObject, NameObject, NumberObject, RectangleObject,
            StreamObject,
        )

        # JPEG stream object
        jpeg_stream = DecodedStreamObject()
        jpeg_stream._data = jpeg_data  # type: ignore[attr-defined]
        jpeg_stream.update({
            NameObject("/Type"):             NameObject("/XObject"),
            NameObject("/Subtype"):          NameObject("/Image"),
            NameObject("/Filter"):           NameObject("/DCTDecode"),
            NameObject("/ColorSpace"):       NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        })

        # Parse JPEG dimensions from header
        img_w_px, img_h_px = _parse_jpeg_dims(jpeg_data)
        jpeg_stream.update({
            NameObject("/Width"):  NumberObject(img_w_px),
            NameObject("/Height"): NumberObject(img_h_px),
            NameObject("/Length"): NumberObject(len(jpeg_data)),
        })

        # Indirect object for the image
        img_obj = writer._add_object(jpeg_stream)

        # Page content stream: paint image over the full page
        content_str = (
            f"q\n"
            f"{width_pt:.4f} 0 0 {height_pt:.4f} 0 0 cm\n"
            f"/Im0 Do\n"
            f"Q\n"
        )
        content_bytes = content_str.encode("latin-1")

        content_stream = DecodedStreamObject()
        content_stream._data = content_bytes  # type: ignore[attr-defined]
        content_stream.update({
            NameObject("/Length"): NumberObject(len(content_bytes)),
        })
        content_obj = writer._add_object(content_stream)

        # Page dictionary
        page_dict = DictionaryObject({
            NameObject("/Type"):      NameObject("/Page"),
            NameObject("/MediaBox"):  ArrayObject([
                FloatObject(0), FloatObject(0),
                FloatObject(width_pt), FloatObject(height_pt),
            ]),
            NameObject("/Contents"): content_obj,
            NameObject("/Resources"): DictionaryObject({
                NameObject("/XObject"): DictionaryObject({
                    NameObject("/Im0"): img_obj,
                }),
            }),
        })

        writer.add_page(page_dict)  # type: ignore[arg-type]

        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()

    @staticmethod
    def _compress_output(pdf_path: Path) -> None:
        """Re-save PDF with pikepdf to compress object streams."""
        import pikepdf
        with pikepdf.open(pdf_path) as pdf:
            pdf.save(
                pdf_path,
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )


# ---------------------------------------------------------------------------
# JPEG dimension parser (fast, no extra deps)
# ---------------------------------------------------------------------------

def _parse_jpeg_dims(data: bytes) -> Tuple[int, int]:
    """Extract (width, height) from raw JPEG bytes."""
    i = 0
    while i < len(data) - 1:
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        i += 2
        if marker in (0xC0, 0xC1, 0xC2):
            # SOF0/SOF1/SOF2
            # length(2) + precision(1) + height(2) + width(2)
            h = struct.unpack(">H", data[i + 3:i + 5])[0]
            w = struct.unpack(">H", data[i + 5:i + 7])[0]
            return w, h
        if marker in (0xD8, 0xD9, 0x01) or (0xD0 <= marker <= 0xD7):
            continue
        # Read segment length
        if i + 2 > len(data):
            break
        seg_len = struct.unpack(">H", data[i:i + 2])[0]
        i += seg_len
    # Fallback
    return 1, 1


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

jpg_to_pdf_service = JpgToPdfService()
