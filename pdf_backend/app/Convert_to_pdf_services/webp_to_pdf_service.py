"""
WebP to PDF conversion service.
Supports strict WebP validation, transparency compositing, cropping, and PDF layout features.
"""

from __future__ import annotations

import logging
import os
import io
import math
import subprocess
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Tuple

import fitz
from PIL import Image
from pypdf import PdfWriter, PdfReader

from app.core.paths import Paths
from app.Convert_to_pdf_services.jpg_to_pdf_service import (
    _resolve_page_size,
    _resolve_margins,
    _fit_image,
    _sanitize_filename,
    _to_rgb
)

logger = logging.getLogger(__name__)

# Only .webp is allowed
ALLOWED_EXTENSIONS = {".webp"}
MAX_IMAGE_BYTES = 100 * 1024 * 1024  # 100MB limit

class WebpToPdfService:
    
    async def analyze_webp(self, request_id: str, filename: str) -> Dict[str, Any]:
        """
        Analyzes a WebP file with strict validation and creates a thumbnail.
        """
        upload_dir = Paths.request_upload(request_id)
        file_path = upload_dir / filename
        
        if not file_path.exists():
            raise ValueError("Uploaded file not found.")
            
        ext = file_path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("Only WebP (.webp) images are supported.")
            
        try:
            with Image.open(file_path) as img:
                if img.format != 'WEBP':
                    raise ValueError(f"{filename} could not be processed because the file is invalid or corrupted (Not a true WebP).")
                
                width, height = img.size
                
                thumb_dir = upload_dir / f"thumbs_{filename}"
                thumb_dir.mkdir(parents=True, exist_ok=True)
                
                # Create thumbnail with white background if transparent
                rgb_frame = _to_rgb(img, bg_color=(255, 255, 255))
                rgb_frame.thumbnail((250, 250))
                thumb_filename = "thumb.jpg"
                rgb_frame.save(thumb_dir / thumb_filename, "JPEG", quality=75)
                
                return {
                    "filename": filename,
                    "width": width,
                    "height": height,
                    "url": f"/api/convert-to-pdf/webp-to-pdf/frame/{request_id}/{filename}"
                }
        except Exception as e:
            logger.error(f"Error analyzing WebP: {e}")
            raise ValueError(f"{filename} could not be processed because the file is invalid or corrupted.")

    def _apply_crop_rotate(self, img_pil: Image.Image, config: Dict[str, Any], file_conf: Dict[str, Any]) -> Image.Image:
        """Apply requested crop and rotation."""
        # Check individual file rotation first
        rotation = int(file_conf.get("rotation", 0))
        if rotation:
            if rotation == 90:
                img_pil = img_pil.transpose(Image.ROTATE_270) # PIL rotates counter-clockwise
            elif rotation == 180:
                img_pil = img_pil.transpose(Image.ROTATE_180)
            elif rotation == 270:
                img_pil = img_pil.transpose(Image.ROTATE_90)
                
        # 1. Apply Manual Crop if provided by the Cropper UI (percentages)
        crop_data = file_conf.get("crop")
        if crop_data:
            w, h = img_pil.size
            cx = float(crop_data.get("x", 0))
            cy = float(crop_data.get("y", 0))
            cw = float(crop_data.get("width", 100))
            ch = float(crop_data.get("height", 100))
            
            left = int(w * (cx / 100.0))
            top = int(h * (cy / 100.0))
            right = int(left + (w * (cw / 100.0)))
            bottom = int(top + (h * (ch / 100.0)))
            
            # Ensure valid bounds
            left = max(0, min(left, w - 1))
            top = max(0, min(top, h - 1))
            right = max(left + 1, min(right, w))
            bottom = max(top + 1, min(bottom, h))
            
            img_pil = img_pil.crop((left, top, right, bottom))
            
        # 2. Apply Auto Crop if enabled
        if config.get("auto_crop") in [True, "true", "True", "1"]:
            # getbbox() finds the bounding box of non-zero alpha in RGBA
            # Convert to RGBA just to find bbox of non-transparent areas safely
            if img_pil.mode != 'RGBA':
                tmp = img_pil.convert('RGBA')
            else:
                tmp = img_pil
            bbox = tmp.getbbox()
            if bbox:
                img_pil = img_pil.crop(bbox)
                
        return img_pil

    async def process(
        self,
        request_id: str,
        files_config: List[Dict[str, Any]], 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process one or more WebP files into PDF.
        """
        upload_dir = Paths.request_upload(request_id)
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # --- Config Extraction ---
        page_size = config.get("page_size", "a4").lower()
        orientation = config.get("orientation", "auto").lower()
        fit_mode = config.get("fit_mode", "fit").lower()
        margin_preset = config.get("margin_preset", "medium").lower()
        custom_m_top = config.get("custom_margin_top", "10")
        custom_m_right = config.get("custom_margin_right", "10")
        custom_m_bottom = config.get("custom_margin_bottom", "10")
        custom_m_left = config.get("custom_margin_left", "10")
        custom_pw = config.get("custom_page_width", "210")
        custom_ph = config.get("custom_page_height", "297")
        custom_pu = config.get("custom_page_unit", "mm")
        dpi_val = float(config.get("dpi", 150) or 150)
        quality = config.get("quality", "high").lower()
        compression = config.get("compression", "jpeg").lower()
        output_mode = config.get("output_mode", "single").lower()
        
        bg_hex = config.get("bg_color", "#ffffff").lstrip("#")
        try:
            bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
        except:
            bg_rgb = (255, 255, 255)
            
        jpeg_quality = 95
        if quality == "maximum": jpeg_quality = 100
        elif quality == "medium": jpeg_quality = 75
        elif quality == "low": jpeg_quality = 50
        
        # Determine format based on compression
        save_format = "JPEG" if compression == "jpeg" else "PNG"
        
        writer = PdfWriter()
        generated_pdfs = []
        
        if not files_config:
            raise ValueError("No valid WebP files provided.")
            
        for file_conf in files_config:
            filename = file_conf["filename"]
            file_path = upload_dir / filename
            
            if not file_path.exists():
                logger.warning(f"File {filename} not found.")
                continue
                
            file_writer = PdfWriter() if output_mode == "separate" else writer
            
            try:
                with Image.open(file_path) as img:
                    if img.format != 'WEBP':
                        raise ValueError("Invalid WebP format.")
                        
                    # Apply rotation and crop
                    img_proc = self._apply_crop_rotate(img, config, file_conf)
                    
                    # Convert to RGB compositing against background
                    rgb_frame = _to_rgb(img_proc, bg_color=bg_rgb)
                    
                    original_dpi = img.info.get("dpi", (dpi_val, dpi_val))
                    if not isinstance(original_dpi, tuple):
                        original_dpi = (dpi_val, dpi_val)
                    if config.get("preserve_dpi") and original_dpi[0] > 0:
                        used_dpi = float(original_dpi[0])
                    else:
                        used_dpi = float(dpi_val)
                        
                    # Layout onto canvas
                    w_px, h_px = rgb_frame.size
                    
                    if page_size == "original":
                        # Convert pixel dimensions to points based on DPI
                        page_w_pt = (w_px / used_dpi) * 72
                        page_h_pt = (h_px / used_dpi) * 72
                        mt = mr = mb = ml = 0
                        x_pt = y_pt = 0
                        draw_w_pt, draw_h_pt = page_w_pt, page_h_pt
                    else:
                        page_w_pt, page_h_pt = _resolve_page_size(
                            page_size, orientation, w_px, h_px, used_dpi,
                            custom_pw, custom_ph, custom_pu
                        )
                        mt, mr, mb, ml = _resolve_margins(
                            margin_preset, custom_m_top, custom_m_right,
                            custom_m_bottom, custom_m_left
                        )
                        
                        usable_w = page_w_pt - ml - mr
                        usable_h = page_h_pt - mt - mb
                        
                        if usable_w <= 0 or usable_h <= 0:
                            usable_w, usable_h = page_w_pt, page_h_pt
                            ml = mt = 0
                            
                        x_pt, y_pt, draw_w_pt, draw_h_pt = _fit_image(
                            w_px, h_px, usable_w, usable_h, fit_mode
                        )
                        
                    # Generate fitz page
                    temp_doc = fitz.Document()
                    page = temp_doc.new_page(width=page_w_pt, height=page_h_pt)
                    
                    # Background
                    page.draw_rect(fitz.Rect(0, 0, page_w_pt, page_h_pt), color=None, fill=(bg_rgb[0]/255, bg_rgb[1]/255, bg_rgb[2]/255))
                    
                    img_byte_arr = io.BytesIO()
                    rgb_frame.save(img_byte_arr, format=save_format, quality=jpeg_quality, dpi=(used_dpi, used_dpi))
                    
                    rect = fitz.Rect(ml + x_pt, mt + y_pt, ml + x_pt + draw_w_pt, mt + y_pt + draw_h_pt)
                    page.insert_image(rect, stream=img_byte_arr.getvalue())
                    
                    pdf_bytes = temp_doc.write()
                    temp_doc.close()
                    
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    file_writer.add_page(reader.pages[0])
                    
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                # We do not crash the whole process, but if all fail, it will be caught later
                continue
                
            if output_mode == "separate":
                # Save individual file
                safe_name = _sanitize_filename(filename.rsplit('.', 1)[0]) + ".pdf"
                out_path = output_dir / safe_name
                
                with open(out_path, "wb") as f:
                    file_writer.write(f)
                    
                generated_pdfs.append(out_path.name)
                
        if output_mode == "single":
            if not writer.pages:
                raise ValueError("PDF generation failed. No pages were successfully processed. Ensure files are valid WebPs.")
                
            raw_name = config.get("output_filename", "webp_to_pdf")
            safe_name = _sanitize_filename(raw_name)
            if not safe_name.lower().endswith(".pdf"):
                safe_name += ".pdf"
                
            out_path = output_dir / safe_name
            
            with open(out_path, "wb") as f:
                writer.write(f)
                
            generated_pdfs.append(safe_name)
            
        if not generated_pdfs:
            raise ValueError("Failed to generate any PDFs.")
            
        # Return success with either single file or a zip if multiple separate PDFs
        if len(generated_pdfs) == 1:
            return {
                "success": True,
                "pdf_filename": generated_pdfs[0],
                "page_count": len(writer.pages) if output_mode == "single" else 1
            }
        else:
            zip_filename = "converted_webps.zip"
            zip_path = output_dir / zip_filename
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for pdf_file in generated_pdfs:
                    zf.write(output_dir / pdf_file, pdf_file)
            return {
                "success": True,
                "pdf_filename": zip_filename,
                "page_count": len(generated_pdfs)
            }

webp_to_pdf_service = WebpToPdfService()
