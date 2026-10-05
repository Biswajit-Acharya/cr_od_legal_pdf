"""
HTML and URL to PDF conversion service using Playwright.
Supports modern website rendering, CSS, JS, and full PDF settings.
"""

from __future__ import annotations

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.parse
import os

from playwright.sync_api import sync_playwright
import fitz

from app.core.paths import Paths
from app.utils.validators import validate_safe_url
from app.Convert_to_pdf_services.jpg_to_pdf_service import _resolve_margins

logger = logging.getLogger(__name__)

class HtmlToPdfService:
    
    async def process(
        self,
        request_id: str,
        input_type: str,
        content: str,
        page_size: str,
        orientation: str,
        margin_preset: str,
        custom_margin_top: str,
        custom_margin_right: str,
        custom_margin_bottom: str,
        custom_margin_left: str,
        custom_page_width: str,
        custom_page_height: str,
        custom_page_unit: str,
        print_background: bool,
        header_text: str,
        footer_text: str,
        page_numbers: bool,
        title: str,
        author: str,
        subject: str,
        keywords: str,
        password: str,
        output_filename: str
    ) -> Dict[str, Any]:
        """Process HTML or URL to PDF."""
        # Run the synchronous blocking operation in a threadpool
        return await asyncio.to_thread(
            self._process_sync,
            request_id, input_type, content, page_size, orientation, margin_preset,
            custom_margin_top, custom_margin_right, custom_margin_bottom, custom_margin_left,
            custom_page_width, custom_page_height, custom_page_unit, print_background,
            header_text, footer_text, page_numbers, title, author, subject, keywords,
            password, output_filename
        )

    def _process_sync(
        self,
        request_id: str,
        input_type: str,
        content: str,
        page_size: str,
        orientation: str,
        margin_preset: str,
        custom_margin_top: str,
        custom_margin_right: str,
        custom_margin_bottom: str,
        custom_margin_left: str,
        custom_page_width: str,
        custom_page_height: str,
        custom_page_unit: str,
        print_background: bool,
        header_text: str,
        footer_text: str,
        page_numbers: bool,
        title: str,
        author: str,
        subject: str,
        keywords: str,
        password: str,
        output_filename: str
    ) -> Dict[str, Any]:
        
        # 1. Validation
        if input_type == "url":
            if not validate_safe_url(content):
                raise ValueError("Invalid or unsafe URL provided.")
        
        # 2. Page Options
        pdf_kwargs = {
            "print_background": print_background,
            "landscape": (orientation.lower() == "landscape")
        }

        # Size
        if page_size.lower() == "custom":
            pdf_kwargs["width"] = f"{custom_page_width}{custom_page_unit}"
            pdf_kwargs["height"] = f"{custom_page_height}{custom_page_unit}"
        elif page_size.lower() != "original":
            pdf_kwargs["format"] = page_size.upper()

        # Margins
        mt, mr, mb, ml = _resolve_margins(
            margin_preset, custom_margin_top, custom_margin_right,
            custom_margin_bottom, custom_margin_left
        )
        pdf_kwargs["margin"] = {
            "top": f"{mt}px",
            "right": f"{mr}px",
            "bottom": f"{mb}px",
            "left": f"{ml}px"
        }

        # Header and Footer
        display_header_footer = False
        header_template = "<span></span>"
        footer_template = "<span></span>"
        
        if header_text:
            display_header_footer = True
            header_template = f'<div style="font-size: 10px; width: 100%; text-align: center; color: #666;">{header_text}</div>'
            
        if footer_text or page_numbers:
            display_header_footer = True
            footer_html = ""
            if footer_text:
                footer_html += f'<span>{footer_text}</span>'
            if page_numbers:
                if footer_html:
                    footer_html += '<span style="margin: 0 10px;">|</span>'
                footer_html += '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>'
            
            footer_template = f'<div style="font-size: 10px; width: 100%; text-align: center; color: #666;">{footer_html}</div>'

        if display_header_footer:
            pdf_kwargs["display_header_footer"] = True
            pdf_kwargs["header_template"] = header_template
            pdf_kwargs["footer_template"] = footer_template
            
            # Ensure margins exist for header/footer
            if mt < 20: pdf_kwargs["margin"]["top"] = "30px"
            if mb < 20: pdf_kwargs["margin"]["bottom"] = "30px"

        # 3. Render PDF using Playwright
        raw_pdf_bytes = b""
        
        temp_html_path = None
        if input_type == "html":
            temp_html_path = Paths.request_upload(request_id) / "temp.html"
            temp_html_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Windows compatibility for Playwright inside FastAPI thread
        import sys
        import asyncio
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    ignore_https_errors=True,
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()
                
                if input_type == "url":
                    page.goto(content, wait_until="networkidle", timeout=30000)
                else:
                    page.goto(temp_html_path.resolve().as_uri(), wait_until="networkidle", timeout=30000)
                
                raw_pdf_bytes = page.pdf(**pdf_kwargs)
                browser.close()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Playwright rendering failed: {e}\n{tb}")
            raise ValueError(f"Failed to render the website/HTML:\n{tb}")
        finally:
            if temp_html_path and temp_html_path.exists():
                try:
                    os.remove(temp_html_path)
                except Exception:
                    pass

        # 4. Post-process with PyMuPDF for Metadata and Security
        doc = fitz.Document(stream=raw_pdf_bytes, filetype="pdf")
        
        meta = doc.metadata
        if title: meta["title"] = title
        if author: meta["author"] = author
        if subject: meta["subject"] = subject
        if keywords: meta["keywords"] = keywords
        meta["creator"] = "PDF Backend (Playwright)"
        doc.set_metadata(meta)

        save_kwargs = {
            "garbage": 3,
            "deflate": True
        }
        
        if password:
            save_kwargs["encryption"] = fitz.PDF_ENCRYPT_AES_256
            save_kwargs["owner_pw"] = password
            save_kwargs["user_pw"] = password
            
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        final_filename = output_filename if output_filename.endswith(".pdf") else f"{output_filename}.pdf"
        output_path = output_dir / final_filename
        
        doc.save(output_path, **save_kwargs)
        doc.close()
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ValueError("Generated PDF is invalid or empty.")
            
        return {
            "success": True,
            "request_id": request_id,
            "filename": final_filename,
            "download_url": f"/api/convert-to-pdf/html-to-pdf/download/{request_id}/{final_filename}"
        }

html_to_pdf_service = HtmlToPdfService()
