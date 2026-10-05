"""
GIF to PDF conversion service.
Supports animated and static GIFs, frame extraction, duplication removal, and PDF assembly.
"""

from __future__ import annotations

import logging
import os
import io
import math
import zipfile
from pathlib import Path
from typing import Dict, Any, List

from PIL import Image, ImageSequence, ImageChops, ImageEnhance
from pypdf import PdfWriter, PdfReader

from app.core.paths import Paths
from app.Convert_to_pdf_services.jpg_to_pdf_service import (
    _resolve_page_size,
    _resolve_margins,
    _fit_image,
    _sanitize_filename,
    _to_rgb
)
import fitz

logger = logging.getLogger(__name__)

class GifToPdfService:
    
    async def analyze_gif(self, request_id: str, filename: str) -> Dict[str, Any]:
        """
        Analyzes a GIF file, counts frames, calculates duration, 
        and creates thumbnails for frontend preview.
        """
        upload_dir = Paths.request_upload(request_id)
        file_path = upload_dir / filename
        
        if not file_path.exists():
            raise ValueError("Uploaded GIF file not found.")
            
        try:
            with Image.open(file_path) as img:
                if img.format != 'GIF':
                    raise ValueError("File is not a valid GIF.")
                
                frames = []
                frame_count = 0
                total_duration = 0
                width, height = img.size
                
                # Create directory for thumbnails
                thumb_dir = upload_dir / f"thumbs_{filename}"
                thumb_dir.mkdir(parents=True, exist_ok=True)
                
                is_animated = getattr(img, "is_animated", False)
                n_frames = getattr(img, "n_frames", 1)
                
                for i in range(n_frames):
                    img.seek(i)
                    # Convert to RGB with white bg safely to avoid transparency glitches
                    rgb_frame = _to_rgb(img, bg_color=(255,255,255))
                    
                    # Generate small thumbnail
                    rgb_frame.thumbnail((250, 250))
                    thumb_filename = f"frame_{i}.jpg"
                    rgb_frame.save(thumb_dir / thumb_filename, "JPEG", quality=75)
                    
                    dur = img.info.get('duration', 100) / 1000.0 # Convert ms to sec
                    
                    frames.append({
                        "index": i,
                        "duration": dur,
                        "url": f"/api/convert-to-pdf/gif-to-pdf/frame/{request_id}/{filename}/{i}"
                    })
                    
                    frame_count += 1
                    total_duration += dur
                    
                return {
                    "filename": filename,
                    "width": width,
                    "height": height,
                    "frame_count": frame_count,
                    "duration_sec": round(total_duration, 2),
                    "is_animated": is_animated,
                    "frames": frames
                }
        except Exception as e:
            logger.error(f"Error analyzing GIF: {e}")
            raise ValueError(f"Failed to analyze GIF: {str(e)}")

    def _frames_are_duplicate(self, img1: Image.Image, img2: Image.Image) -> bool:
        """Check if two frames are effectively identical."""
        diff = ImageChops.difference(img1, img2)
        if not diff.getbbox():
            return True
        return False

    async def process(
        self,
        request_id: str,
        files_config: List[Dict[str, Any]], # [{"filename": "...", "frames": [0,1,2]}, ...]
        page_size: str,
        orientation: str,
        margin_preset: str,
        fit_mode: str,
        remove_duplicates: bool,
        background_color: str, # "white", "black"
        quality: str, # "high", "balanced", "small"
        dpi: int,
        output_mode: str, # "single", "separate"
        custom_w_str: str = "",
        custom_h_str: str = "",
        custom_unit: str = "pt",
        custom_margin_top: str = "0",
        custom_margin_right: str = "0",
        custom_margin_bottom: str = "0",
        custom_margin_left: str = "0",
        password: str = "",
        title: str = "",
        author: str = "",
        subject: str = "",
        keywords: str = "",
        output_filename: str = "animation.pdf"
    ) -> Dict[str, Any]:
        """Process one or more GIFs into PDF."""
        upload_dir = Paths.request_upload(request_id)
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        bg_rgb = (255, 255, 255) if background_color.lower() == "white" else (0, 0, 0)
        
        # Calculate DPI compression ratio
        # Best quality = 100, Balanced = 75, Small = 50
        jpeg_quality = 95
        if quality == "balanced": jpeg_quality = 75
        elif quality == "small": jpeg_quality = 50

        pdf_paths = []
        writer = PdfWriter()
        
        for file_conf in files_config:
            filename = file_conf["filename"]
            selected_frames = file_conf.get("frames", [])
            file_path = upload_dir / filename
            
            if not file_path.exists():
                raise ValueError(f"File {filename} not found.")
                
            file_writer = PdfWriter() if output_mode == "separate" else writer
            
            try:
                with Image.open(file_path) as img:
                    if not selected_frames:
                        selected_frames = list(range(getattr(img, "n_frames", 1)))
                        
                    last_processed_frame = None
                    
                    for f_idx in selected_frames:
                        img.seek(f_idx)
                        
                        rgb_frame = _to_rgb(img, bg_color=bg_rgb)
                        
                        if remove_duplicates and last_processed_frame:
                            if self._frames_are_duplicate(last_processed_frame, rgb_frame):
                                continue # Skip duplicate
                                
                        last_processed_frame = rgb_frame.copy()
                        
                        # Generate PDF page for this frame using ReportLab/pypdf logic
                        # Re-use jpg_to_pdf page logic
                        w_px, h_px = rgb_frame.size
                        page_w_pt, page_h_pt = _resolve_page_size(
                            page_size, orientation, w_px, h_px, dpi,
                            custom_w_str, custom_h_str, custom_unit
                        )
                        mt, mr, mb, ml = _resolve_margins(
                            margin_preset, custom_margin_top, custom_margin_right,
                            custom_margin_bottom, custom_margin_left
                        )
                        usable_w = page_w_pt - ml - mr
                        usable_h = page_h_pt - mt - mb
                        
                        if usable_w <= 0 or usable_h <= 0:
                            raise ValueError("Margins are too large for the page size.")
                            
                        x_offset, y_offset, draw_w, draw_h = _fit_image(
                            w_px, h_px, usable_w, usable_h, fit_mode
                        )
                        
                        # Use fitz (PyMuPDF) for creating a quick page in-memory as it's very reliable
                        # We convert the PIL image to bytes, then insert into an empty fitz PDF
                        img_byte_arr = io.BytesIO()
                        rgb_frame.save(img_byte_arr, format='JPEG', quality=jpeg_quality, dpi=(dpi,dpi))
                        img_bytes = img_byte_arr.getvalue()
                        
                        temp_doc = fitz.Document()
                        page = temp_doc.new_page(width=page_w_pt, height=page_h_pt)
                        
                        # Fill background if requested black
                        if bg_rgb == (0,0,0):
                            page.draw_rect(page.rect, color=(0,0,0), fill=(0,0,0))
                            
                        rect = fitz.Rect(
                            ml + x_offset, 
                            mt + y_offset, 
                            ml + x_offset + draw_w, 
                            mt + y_offset + draw_h
                        )
                        page.insert_image(rect, stream=img_bytes)
                        
                        temp_pdf_bytes = temp_doc.write()
                        temp_doc.close()
                        
                        # Add to pypdf writer
                        reader = PdfReader(io.BytesIO(temp_pdf_bytes))
                        file_writer.add_page(reader.pages[0])
                        
            except Exception as e:
                logger.error(f"Error processing GIF {filename}: {e}")
                raise ValueError(f"Failed to process GIF {filename}: {str(e)}")
                
            if output_mode == "separate":
                out_name = f"{_sanitize_filename(Path(filename).stem)}.pdf"
                out_path = output_dir / out_name
                with open(out_path, "wb") as f:
                    file_writer.write(f)
                pdf_paths.append(out_path)

        if output_mode == "single":
            final_filename = _sanitize_filename(output_filename)
            if not final_filename.endswith(".pdf"):
                final_filename += ".pdf"
            out_path = output_dir / final_filename
            with open(out_path, "wb") as f:
                writer.write(f)
            pdf_paths = [out_path]

        # Apply metadata and password if requested
        processed_paths = []
        for p in pdf_paths:
            doc = fitz.open(p)
            if title or author or subject or keywords:
                meta = doc.metadata
                if title: meta["title"] = title
                if author: meta["author"] = author
                if subject: meta["subject"] = subject
                if keywords: meta["keywords"] = keywords
                doc.set_metadata(meta)
            
            save_kwargs = {"garbage": 3, "deflate": True}
            if password:
                save_kwargs["encryption"] = fitz.PDF_ENCRYPT_AES_256
                save_kwargs["owner_pw"] = password
                save_kwargs["user_pw"] = password
                
            doc.saveIncr() if not password else doc.save(p.with_suffix('.sec.pdf'), **save_kwargs)
            doc.close()
            
            if password:
                os.replace(p.with_suffix('.sec.pdf'), p)
                
            processed_paths.append(p)
            
        # If separate mode and >1 files, zip them
        if output_mode == "separate" and len(processed_paths) > 1:
            zip_filename = "converted_gifs.zip"
            zip_path = output_dir / zip_filename
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for pp in processed_paths:
                    zf.write(pp, pp.name)
            
            return {
                "success": True,
                "request_id": request_id,
                "filename": zip_filename,
                "download_url": f"/api/convert-to-pdf/gif-to-pdf/download/{request_id}/{zip_filename}"
            }
        else:
            final_p = processed_paths[0]
            return {
                "success": True,
                "request_id": request_id,
                "filename": final_p.name,
                "download_url": f"/api/convert-to-pdf/gif-to-pdf/download/{request_id}/{final_p.name}"
            }

gif_to_pdf_service = GifToPdfService()
