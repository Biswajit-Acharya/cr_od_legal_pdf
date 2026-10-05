"""
Service for compressing PDF files to a target size or recommended size.
"""

from __future__ import annotations

import io
import logging
import shutil
import tempfile
import sys
from pathlib import Path
from typing import Optional

import pikepdf
from pikepdf import Pdf, Name
from fastapi import HTTPException

from app.core.constants import COMPRESSED_OUTPUT_PREFIX
from app.core.paths import Paths
from app.schemas.pdf_schema import CompressPDFResponse
from app.utils.filename import output_filename

logger = logging.getLogger(__name__)


class CompressPDFService:
    """Compress a PDF file to a target size or use recommended settings."""

    async def compress(
        self,
        input_pdf: Path,
        compression_level: str,
        target_size: Optional[int],
        target_size_unit: str,
        request_id: str,
    ) -> CompressPDFResponse:
        output_dir = Paths.request_output(request_id)
        original_size = input_pdf.stat().st_size
        out_name = output_filename(prefix=COMPRESSED_OUTPUT_PREFIX)
        out_path = output_dir / out_name

        target_bytes = 0
        if compression_level == "custom" and target_size:
            target_bytes = target_size * 1024 if target_size_unit.upper() == "KB" else target_size * 1024 * 1024
            if original_size <= target_bytes:
                shutil.copy2(str(input_pdf), str(out_path))
                return self._resp(out_name, out_path, original_size, request_id,
                                  "File is already smaller than or equal to the target size.")

        tmp = Path(tempfile.mktemp(suffix=".pdf"))
        try:
            if compression_level == "extreme":
                quality, scale = 15, 0.3
            elif compression_level == "less":
                quality, scale = 60, 0.9
            elif compression_level == "recommended":
                quality, scale = 35, 0.6
            else:
                reduction_ratio = target_bytes / original_size if original_size > 0 else 1.0
                if reduction_ratio > 0.8:
                    quality, scale = 50, 0.8
                elif reduction_ratio > 0.5:
                    quality, scale = 35, 0.6
                elif reduction_ratio > 0.25:
                    quality, scale = 15, 0.35
                else:
                    quality, scale = 5, 0.2

            try:
                self._compress_to(input_pdf, tmp, quality, scale)
            except Exception as e:
                logger.error(f"Compression failed internally: {e}")
                shutil.copy2(str(input_pdf), str(out_path))
                msg = f"File could not be compressed due to complex structure. Returning original."
                return self._resp(out_name, out_path, original_size, request_id, msg)

            final_size = tmp.stat().st_size
            
            if final_size >= original_size:
                shutil.copy2(str(input_pdf), str(out_path))
                msg = "File could not be compressed further without quality loss. Returning original."
                return self._resp(out_name, out_path, original_size, request_id, msg)
            
            shutil.move(str(tmp), str(out_path))
            
            if compression_level == "custom":
                if final_size <= target_bytes:
                    msg = f"PDF compressed to target size ({self._fmt(final_size)})."
                else:
                    msg = (
                        f"Compressed to {self._fmt(final_size)}. "
                        f"Target {self._fmt(target_bytes)} is too aggressive for this document."
                    )
            else:
                msg = f"PDF compressed successfully with {compression_level} settings."
                
            return self._resp(out_name, out_path, original_size, request_id, msg)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    def _compress_to(self, src: Path, dst: Path, quality: int, scale: float) -> None:
        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(max(old_limit, 5000))
        try:
            with Pdf.open(str(src)) as pdf:
                self._strip_metadata(pdf)

                for page in pdf.pages:
                    self._process_page(page, quality, scale)

                pdf.save(
                    str(dst),
                    compress_streams=True,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate,
                    recompress_flate=True,
                    linearize=False,
                )
        finally:
            sys.setrecursionlimit(old_limit)

    def _strip_metadata(self, pdf: Pdf) -> None:
        try:
            pdf.docinfo = {}
        except Exception:
            pass
        for page in pdf.pages:
            for key in ["/Annots", "/AA", "/Metadata"]:
                if key in page:
                    try:
                        del page[key]
                    except Exception:
                        pass

    def _process_page(self, page, quality: int, scale: float) -> None:
        resources = page.get("/Resources")
        if not resources:
            return
        xobjects = resources.get("/XObject")
        if not xobjects:
            return
        for key in list(xobjects):
            try:
                obj = xobjects[key]
                if not isinstance(obj, pikepdf.Stream):
                    continue
                subtype = obj.get("/Subtype")
                if subtype == pikepdf.Name("/Image"):
                    self._compress_image(obj, quality, scale)
                elif "/XObject" in obj.get("/Resources", {}):
                    self._process_sub_xobject(obj, quality, scale)
            except Exception:
                continue

    def _process_sub_xobject(self, obj, quality: int, scale: float) -> None:
        resources = obj.get("/Resources")
        if not resources:
            return
        xobjects = resources.get("/XObject")
        if not xobjects:
            return
        for key in list(xobjects):
            try:
                child = xobjects[key]
                if not isinstance(child, pikepdf.Stream):
                    continue
                if child.get("/Subtype") == pikepdf.Name("/Image"):
                    self._compress_image(child, quality, scale)
                elif "/XObject" in child.get("/Resources", {}):
                    self._process_sub_xobject(child, quality, scale)
            except Exception:
                continue

    def _compress_image(self, img_obj, quality: int, scale: float) -> None:
        try:
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = None

            width = int(img_obj.get("/Width", 0))
            height = int(img_obj.get("/Height", 0))
            if width == 0 or height == 0:
                return

            new_w = max(1, int(width * scale))
            new_h = max(1, int(height * scale))

            filter_val = str(img_obj.get("/Filter", ""))

            if "/DCTDecode" in filter_val or "/JPXDecode" in filter_val:
                try:
                    raw_data = img_obj.read_raw_bytes()
                    pil_img = Image.open(io.BytesIO(raw_data))
                except Exception:
                    return
            else:
                try:
                    raw_data = img_obj.read_bytes() # Uncompressed data
                except Exception:
                    return
                
                color_space = str(img_obj.get("/ColorSpace", ""))
                try:
                    bpc = int(img_obj.get("/BitsPerComponent", 8))
                except (ValueError, TypeError):
                    bpc = 8

                if "Gray" in color_space or "DeviceGray" in color_space:
                    mode = "L"
                    channels = 1
                elif "CMYK" in color_space:
                    mode = "CMYK"
                    channels = 4
                else:
                    mode = "RGB"
                    channels = 3

                expected_bytes = width * height * channels
                if bpc < 8:
                    expected_bytes = (width * channels * bpc + 7) // 8 * height

                if len(raw_data) < expected_bytes:
                    return

                try:
                    if channels == 1:
                        pil_img = Image.frombytes("L", (width, height), raw_data[:expected_bytes])
                    elif channels == 4:
                        pil_img = Image.frombytes("CMYK", (width, height), raw_data[:expected_bytes])
                    else:
                        pil_img = Image.frombytes("RGB", (width, height), raw_data[:expected_bytes])
                except Exception:
                    return

            if pil_img.mode in ("RGBA", "P", "LA"):
                pil_img = pil_img.convert("RGB")
            elif pil_img.mode == "CMYK":
                pil_img = pil_img.convert("RGB")

            if scale < 1.0:
                pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
            jpeg_data = buf.getvalue()

            img_obj.write(jpeg_data)
            img_obj[Name.Filter] = Name.DCTDecode
            img_obj[Name.Width] = pil_img.width
            img_obj[Name.Height] = pil_img.height
            img_obj[Name.ColorSpace] = Name.DeviceRGB
            img_obj[Name.BitsPerComponent] = 8

        except Exception:
            pass

    def _resp(
        self, out_name: str, out_path: Path, original_size: int,
        request_id: str, message: str,
    ) -> CompressPDFResponse:
        compressed_size = out_path.stat().st_size
        reduction = round((1 - compressed_size / original_size) * 100, 2) if original_size > 0 else 0.0
        reduction = max(reduction, 0.0)

        logger.info("Compressed: %d → %d bytes (%.1f%%)", original_size, compressed_size, reduction)

        return CompressPDFResponse(
            success=True,
            message=message,
            request_id=request_id,
            filename=out_name,
            download_url=f"/api/pdf/download/{request_id}/{out_name}",
            original_size=original_size,
            compressed_size=compressed_size,
            reduction_percent=reduction,
        )

    @staticmethod
    def _fmt(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.2f} MB"
