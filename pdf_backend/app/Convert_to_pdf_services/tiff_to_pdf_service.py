"""
TIFF to PDF conversion service.
Supports multi-frame TIFFs, image enhancements, and PDF/A generation.
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

import cv2
import numpy as np
import fitz
from PIL import Image, ImageSequence, ImageEnhance
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

ALLOWED_EXTENSIONS = {".tif", ".tiff"}
MAX_IMAGE_BYTES = 100 * 1024 * 1024  # 100MB limit for TIFFs

class TiffToPdfService:
    
    async def analyze_tiff(self, request_id: str, filename: str) -> Dict[str, Any]:
        """
        Analyzes a TIFF file, counts frames, 
        and creates thumbnails for frontend preview.
        """
        upload_dir = Paths.request_upload(request_id)
        file_path = upload_dir / filename
        
        if not file_path.exists():
            raise ValueError("Uploaded TIFF file not found.")
            
        try:
            with Image.open(file_path) as img:
                if img.format != 'TIFF' and file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                    raise ValueError("File is not a valid TIFF.")
                
                frames = []
                frame_count = 0
                width, height = img.size
                
                thumb_dir = upload_dir / f"thumbs_{filename}"
                thumb_dir.mkdir(parents=True, exist_ok=True)
                
                n_frames = getattr(img, "n_frames", 1)
                
                for i in range(n_frames):
                    img.seek(i)
                    rgb_frame = _to_rgb(img, bg_color=(255, 255, 255))
                    
                    # Generate small thumbnail
                    rgb_frame.thumbnail((250, 250))
                    thumb_filename = f"frame_{i}.jpg"
                    rgb_frame.save(thumb_dir / thumb_filename, "JPEG", quality=75)
                    
                    frames.append({
                        "index": i,
                        "url": f"/api/convert-to-pdf/tiff-to-pdf/frame/{request_id}/{filename}/{i}"
                    })
                    
                    frame_count += 1
                    
                return {
                    "filename": filename,
                    "width": width,
                    "height": height,
                    "frame_count": frame_count,
                    "frames": frames
                }
        except Exception as e:
            logger.error(f"Error analyzing TIFF: {e}")
            raise ValueError(f"Failed to analyze TIFF: {str(e)}")

    def _apply_cv2_enhancements(self, img_pil: Image.Image, config: Dict[str, Any]) -> Image.Image:
        """Apply requested scanned document enhancements via OpenCV or Pillow."""
        # Check if any enhancement is requested
        has_enhancement = (
            config.get("auto_contrast") or 
            config.get("brightness", 100) != 100 or 
            config.get("sharpness", 100) != 100 or 
            config.get("grayscale") or 
            config.get("noise_reduction") or
            config.get("bg_cleanup") or
            config.get("deskew") or
            config.get("auto_crop")
        )
        if not has_enhancement:
            return img_pil
            
        # First, apply Pillow-based basic enhancements
        if config.get("brightness", 100) != 100:
            enhancer = ImageEnhance.Brightness(img_pil)
            img_pil = enhancer.enhance(config.get("brightness", 100) / 100.0)
            
        if config.get("sharpness", 100) != 100:
            enhancer = ImageEnhance.Sharpness(img_pil)
            img_pil = enhancer.enhance(config.get("sharpness", 100) / 100.0)
            
        if config.get("auto_contrast"):
            from PIL import ImageOps
            img_pil = ImageOps.autocontrast(img_pil, cutoff=1)
            
        if config.get("grayscale"):
            img_pil = img_pil.convert("L").convert("RGB")
            
        # Convert to cv2 numpy array for advanced enhancements
        cv_img = np.array(img_pil)
        # Convert RGB to BGR for OpenCV
        if len(cv_img.shape) == 3 and cv_img.shape[2] == 3:
            cv_img = cv_img[:, :, ::-1]
            
        if config.get("noise_reduction"):
            cv_img = cv2.fastNlMeansDenoisingColored(cv_img, None, 6, 6, 7, 21)
            
        if config.get("bg_cleanup"):
            # Simple adaptive thresholding-like background cleanup
            lab = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            cv_img = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
        if config.get("deskew"):
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
            if lines is not None:
                angles = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                    if -45 < angle < 45:
                        angles.append(angle)
                if angles:
                    median_angle = np.median(angles)
                    if abs(median_angle) > 0.5:
                        h, w = cv_img.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                        cv_img = cv2.warpAffine(
                            cv_img, M, (w, h),
                            flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_REPLICATE
                        )

        if config.get("auto_crop"):
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            coords = cv2.findNonZero(thresh)
            if coords is not None:
                x, y, w, h = cv2.boundingRect(coords)
                margin = 5
                y1 = max(0, y - margin)
                y2 = min(cv_img.shape[0], y + h + margin)
                x1 = max(0, x - margin)
                x2 = min(cv_img.shape[1], x + w + margin)
                cv_img = cv_img[y1:y2, x1:x2]

        # Convert back to PIL
        if len(cv_img.shape) == 3 and cv_img.shape[2] == 3:
            cv_img = cv_img[:, :, ::-1] # BGR to RGB
            return Image.fromarray(cv_img)
        else:
            return Image.fromarray(cv_img).convert("RGB")

    async def process(
        self,
        request_id: str,
        files_config: List[Dict[str, Any]], 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process one or more TIFF files/frames into PDF.
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
        color_mode = config.get("color_mode", "preserve").lower()
        output_mode = config.get("output_mode", "single").lower()
        
        bg_hex = config.get("bg_color", "#ffffff").lstrip("#")
        try:
            bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
        except:
            bg_rgb = (255, 255, 255)
            
        jpeg_quality = 95
        if quality == "medium": jpeg_quality = 75
        elif quality == "low": jpeg_quality = 50
        
        # Determine format based on compression
        save_format = "JPEG" if compression == "jpeg" else "PNG"
        
        writer = PdfWriter()
        generated_pdfs = []
        
        for file_conf in files_config:
            filename = file_conf["filename"]
            selected_frames = file_conf.get("frames", [])
            file_path = upload_dir / filename
            
            if not file_path.exists():
                logger.warning(f"File {filename} not found.")
                continue
                
            file_writer = PdfWriter() if output_mode == "separate" else writer
            
            try:
                with Image.open(file_path) as img:
                    if not selected_frames:
                        selected_frames = list(range(getattr(img, "n_frames", 1)))
                    
                    # TIFF might have DPI in info dict
                    original_dpi = img.info.get("dpi", (dpi_val, dpi_val))
                    if not isinstance(original_dpi, tuple):
                        original_dpi = (dpi_val, dpi_val)
                    if config.get("preserve_dpi") and original_dpi[0] > 0:
                        used_dpi = float(original_dpi[0])
                    else:
                        used_dpi = float(dpi_val)
                        
                    for f_idx in selected_frames:
                        img.seek(f_idx)
                        
                        rgb_frame = _to_rgb(img, bg_color=bg_rgb)
                        
                        # Apply enhancements
                        rgb_frame = self._apply_cv2_enhancements(rgb_frame, config)
                        
                        # Color Mode
                        if color_mode == "grayscale":
                            rgb_frame = rgb_frame.convert("L").convert("RGB")
                        elif color_mode == "black_white":
                            rgb_frame = rgb_frame.convert("1").convert("RGB")
                            
                        # Layout onto canvas
                        w_px, h_px = rgb_frame.size
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
                        # TIFF can support lossless PNG encoding in fitz insertion
                        rgb_frame.save(img_byte_arr, format=save_format, quality=jpeg_quality, dpi=(used_dpi, used_dpi))
                        
                        rect = fitz.Rect(ml + x_pt, mt + y_pt, ml + x_pt + draw_w_pt, mt + y_pt + draw_h_pt)
                        page.insert_image(rect, stream=img_byte_arr.getvalue())
                        
                        pdf_bytes = temp_doc.write()
                        temp_doc.close()
                        
                        reader = PdfReader(io.BytesIO(pdf_bytes))
                        file_writer.add_page(reader.pages[0])
                        
            except Exception as e:
                import traceback
                with open("tiff_error_log.txt", "w") as err_f:
                    err_f.write(traceback.format_exc())
                logger.error(f"Error processing {filename}: {e}\n{traceback.format_exc()}")
                continue
                
            if output_mode == "separate":
                # Save individual file
                safe_name = _sanitize_filename(filename.rsplit('.', 1)[0]) + ".pdf"
                out_path = output_dir / safe_name
                
                # Apply Security and Metadata
                self._apply_pdf_metadata_security(file_writer, config)
                
                with open(out_path, "wb") as f:
                    file_writer.write(f)
                    
                # Apply PDF/A if requested
                if config.get("pdf_a"):
                    out_path = self._apply_pdfa(out_path, config.get("pdf_a"))
                    
                generated_pdfs.append(out_path.name)
                
        if output_mode == "single":
            if not writer.pages:
                raise ValueError("No pages were successfully processed.")
                
            raw_name = config.get("output_filename", "converted_tiffs")
            safe_name = _sanitize_filename(raw_name)
            if not safe_name.lower().endswith(".pdf"):
                safe_name += ".pdf"
                
            out_path = output_dir / safe_name
            self._apply_pdf_metadata_security(writer, config)
            
            with open(out_path, "wb") as f:
                writer.write(f)
                
            if config.get("pdf_a"):
                out_path = self._apply_pdfa(out_path, config.get("pdf_a"))
                safe_name = out_path.name
                
            generated_pdfs.append(safe_name)
            
        if not generated_pdfs:
            raise ValueError("Failed to generate any PDFs.")
            
        # Return success with either single file or a zip if multiple separate PDFs
        if len(generated_pdfs) == 1:
            return {
                "success": True,
                "pdf_filename": generated_pdfs[0],
                "page_count": len(writer.pages) if output_mode == "single" else "Unknown"
            }
        else:
            zip_filename = "converted_tiffs.zip"
            zip_path = output_dir / zip_filename
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for pdf_file in generated_pdfs:
                    zf.write(output_dir / pdf_file, pdf_file)
            return {
                "success": True,
                "pdf_filename": zip_filename,
                "page_count": "Multiple"
            }

    def _apply_pdf_metadata_security(self, writer: PdfWriter, config: Dict[str, Any]):
        metadata = {}
        if config.get("pdf_title"): metadata["/Title"] = config.get("pdf_title")
        if config.get("pdf_author"): metadata["/Author"] = config.get("pdf_author")
        if config.get("pdf_subject"): metadata["/Subject"] = config.get("pdf_subject")
        if config.get("pdf_keywords"): metadata["/Keywords"] = config.get("pdf_keywords")
        if config.get("pdf_creator"): metadata["/Creator"] = config.get("pdf_creator")
        if metadata:
            writer.add_metadata(metadata)
            
        if config.get("password"):
            writer.encrypt(
                user_password=config.get("password"),
                owner_password=config.get("password"),
                permissions_flag=0b0100  # basic print allowed
            )

    def _apply_pdfa(self, pdf_path: Path, standard: str) -> Path:
        """Call ocrmypdf to enforce PDF/A if requested."""
        standard_map = {
            "pdf/a-1b": "pdfa-1",
            "pdf/a-2b": "pdfa-2",
            "pdf/a-3b": "pdfa-3"
        }
        ocr_profile = standard_map.get(standard.lower(), "pdfa-2")
        
        output_filename = f"{pdf_path.stem}_pdfa.pdf"
        output_path = pdf_path.parent / output_filename
        
        cmd = [
            "ocrmypdf",
            "--skip-text",
            "--output-type", ocr_profile,
            "--optimize", "1",
            str(pdf_path.resolve()),
            str(output_path.resolve())
        ]
        
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if process.returncode == 0 and output_path.exists():
                return output_path
            else:
                logger.warning(f"PDF/A conversion failed: {process.stderr}")
                return pdf_path # Return original if failed
        except Exception as e:
            logger.warning(f"PDF/A conversion error: {e}")
            return pdf_path

tiff_to_pdf_service = TiffToPdfService()
