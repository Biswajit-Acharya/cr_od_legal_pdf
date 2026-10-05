"""
Webpage / URL to PDF conversion service.

Dedicated Playwright-based renderer for converting web URLs to high-quality PDFs.
Supports viewport presets, element hiding, custom headers/footers, batch conversion,
and comprehensive rendering options.

Uses synchronous Playwright wrapped in asyncio.to_thread() for FastAPI compatibility.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import fitz  # PyMuPDF
from playwright.sync_api import sync_playwright

from app.core.paths import Paths
from app.utils.validators import validate_safe_url

logger = logging.getLogger(__name__)

# ── Viewport presets ──────────────────────────────────────────────────────
VIEWPORT_PRESETS: Dict[str, Dict[str, int]] = {
    "desktop": {"width": 1280, "height": 800},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 375, "height": 812},
}

# ── Limits ────────────────────────────────────────────────────────────────
MAX_URL_LENGTH = 2048
PAGE_LOAD_TIMEOUT_MS = 60_000
MAX_RENDER_TIMEOUT_MS = 120_000
MAX_BATCH_URLS = 10


def _safe_filename(name: str) -> str:
    """Remove unsafe filesystem characters."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_. ')
    return name[:120] if name else "webpage"


def _url_to_filename(url: str, title: str = "") -> str:
    """Generate a safe filename from URL and optional page title."""
    if title:
        base = _safe_filename(title)
    else:
        parsed = urlparse(url)
        base = _safe_filename(parsed.netloc + parsed.path.replace("/", "_"))
    if not base:
        base = "webpage"
    return f"{base}.pdf"


class WebpageToPdfService:
    """Convert web URLs to PDF using Playwright Chromium."""

    # ── Single URL conversion ──────────────────────────────────────

    async def convert_url(
        self,
        request_id: str,
        url: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convert a single URL to PDF.

        Args:
            request_id: Unique request identifier.
            url: The webpage URL to convert.
            config: Rendering and output options.

        Returns:
            Dict with success, filename, download_url, view_url, etc.
        """
        config = config or {}

        # Validate URL
        if not url or not url.strip():
            raise ValueError("No URL provided.")
        url = url.strip()
        if len(url) > MAX_URL_LENGTH:
            raise ValueError(f"URL exceeds maximum length of {MAX_URL_LENGTH} characters.")

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only HTTP and HTTPS URLs are supported.")
        if not parsed.netloc:
            raise ValueError("Invalid URL: no hostname found.")

        if not validate_safe_url(url):
            raise ValueError(
                "This URL is blocked for security reasons. "
                "Private networks, localhost, and internal addresses are not allowed."
            )

        # Run synchronous Playwright in threadpool
        return await asyncio.to_thread(self._convert_sync, request_id, url, config)

    def _convert_sync(
        self, request_id: str, url: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synchronous conversion using Playwright."""
        # Windows compatibility
        if os.name == "nt":
            import asyncio as _a
            try:
                _a.set_event_loop_policy(_a.WindowsProactorEventLoopPolicy())
            except Exception:
                pass

        viewport_name = config.get("viewport", "desktop")
        viewport = VIEWPORT_PRESETS.get(viewport_name, VIEWPORT_PRESETS["desktop"])
        if config.get("viewport_width"):
            viewport["width"] = int(config["viewport_width"])
        if config.get("viewport_height"):
            viewport["height"] = int(config["viewport_height"])

        wait_until = config.get("wait_until", "networkidle")
        custom_delay_ms = int(config.get("custom_delay_ms", 0) or 0)
        scale = float(config.get("scale", 1.0) or 1.0)
        hide_selectors = config.get("hide_selectors", "")
        page_size = config.get("page_size", "a4")
        orientation = config.get("orientation", "portrait")
        print_background = config.get("print_background", True)
        prefer_css_page_size = config.get("prefer_css_page_size", False)

        # Margins
        mt = config.get("margin_top", "1cm")
        mr = config.get("margin_right", "1cm")
        mb = config.get("margin_bottom", "1cm")
        ml = config.get("margin_left", "1cm")

        # Header / Footer
        display_hf = False
        header_template = "<span></span>"
        footer_template = "<span></span>"

        if config.get("header_enabled", False):
            display_hf = True
            header_template = self._build_header_template(config)

        if config.get("footer_enabled", False):
            display_hf = True
            footer_template = self._build_footer_template(config)

        # Build pdf_kwargs
        pdf_kwargs: Dict[str, Any] = {
            "print_background": print_background,
            "landscape": (orientation.lower() == "landscape"),
            "scale": max(0.1, min(scale, 5.0)),
            "margin": {"top": mt, "right": mr, "bottom": mb, "left": ml},
        }

        if page_size.lower() == "custom":
            cw = config.get("custom_page_width", "210")
            ch = config.get("custom_page_height", "297")
            unit = config.get("custom_page_unit", "mm")
            pdf_kwargs["width"] = f"{cw}{unit}"
            pdf_kwargs["height"] = f"{ch}{unit}"
        elif page_size.lower() != "original":
            pdf_kwargs["format"] = page_size.upper()

        if prefer_css_page_size:
            pdf_kwargs["prefer_css_page_size"] = True

        if display_hf:
            pdf_kwargs["display_header_footer"] = True
            pdf_kwargs["header_template"] = header_template
            pdf_kwargs["footer_template"] = footer_template
            # Ensure enough margin for header/footer
            if pdf_kwargs["margin"]["top"] in ("0", "0px", "0cm", "0mm"):
                pdf_kwargs["margin"]["top"] = "30px"
            if pdf_kwargs["margin"]["bottom"] in ("0", "0px", "0cm", "0mm"):
                pdf_kwargs["margin"]["bottom"] = "30px"

        # Playwright execution
        raw_pdf_bytes = b""
        page_title = ""

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    ignore_https_errors=True,
                    viewport=viewport,
                    user_agent=config.get("user_agent", ""),
                )
                page = context.new_page()

                # Navigate
                page.goto(url, wait_until=wait_until, timeout=PAGE_LOAD_TIMEOUT_MS)

                # Custom delay
                if custom_delay_ms > 0:
                    page.wait_for_timeout(custom_delay_ms)

                # Wait for fonts
                if config.get("wait_for_fonts", True):
                    try:
                        page.wait_for_function("document.fonts.ready", timeout=5000)
                    except Exception:
                        pass

                # Hide elements via CSS selectors
                if hide_selectors:
                    selectors = [s.strip() for s in hide_selectors.split(",") if s.strip()]
                    for sel in selectors:
                        try:
                            page.evaluate(
                                f"""(sel) => {{
                                    document.querySelectorAll(sel).forEach(el => {{
                                        el.style.display = 'none';
                                    }});
                                }}""",
                                sel,
                            )
                        except Exception as exc:
                            logger.warning("Failed to hide selector '%s': %s", sel, exc)

                # Get page title
                try:
                    page_title = page.title() or ""
                except Exception:
                    page_title = ""

                # Generate PDF
                raw_pdf_bytes = page.pdf(**pdf_kwargs)
                browser.close()

        except Exception as exc:
            logger.error("Playwright rendering failed for %s: %s", url, exc)
            raise ValueError(f"Failed to render the webpage: {exc}")

        if not raw_pdf_bytes:
            raise ValueError("PDF generation produced no output.")

        # Post-process with PyMuPDF
        title = config.get("pdf_title", "") or page_title
        filename = _url_to_filename(url, page_title)
        output_path = self._postprocess_pdf(
            raw_pdf_bytes, request_id, filename, config, title=title
        )

        return {
            "success": True,
            "request_id": request_id,
            "filename": filename,
            "page_title": page_title,
            "download_url": f"/api/convert-to-pdf/webpage-to-pdf/download/{request_id}/{filename}",
            "view_url": f"/api/convert-to-pdf/webpage-to-pdf/view/{request_id}",
        }

    # ── Batch conversion ───────────────────────────────────────────

    async def convert_batch(
        self,
        request_id: str,
        urls: List[str],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convert multiple URLs to individual PDFs, then zip them."""
        if not urls:
            raise ValueError("No URLs provided.")
        if len(urls) > MAX_BATCH_URLS:
            raise ValueError(f"Maximum {MAX_BATCH_URLS} URLs per batch.")

        # Validate all URLs first
        for i, url in enumerate(urls):
            url = url.strip()
            if not url:
                raise ValueError(f"URL #{i + 1} is empty.")
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"URL #{i + 1} must use HTTP or HTTPS.")
            if not validate_safe_url(url):
                raise ValueError(f"URL #{i + 1} is blocked for security reasons.")

        results: List[Dict[str, Any]] = []
        success_count = 0
        fail_count = 0

        for i, url in enumerate(urls):
            url = url.strip()
            try:
                result = await self.convert_url(request_id, url, config)
                results.append({"url": url, "status": "success", **result})
                success_count += 1
            except Exception as exc:
                logger.warning("Batch URL %d failed: %s", i + 1, exc)
                results.append({"url": url, "status": "error", "message": str(exc)})
                fail_count += 1

        if success_count == 0:
            raise ValueError("All URLs failed to convert.")

        # Create ZIP if multiple successes
        zip_filename = None
        if success_count > 1:
            zip_filename = f"webpage_pdfs_{request_id[:8]}.zip"
            zip_path = Paths.request_output(request_id) / zip_filename
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for r in results:
                    if r["status"] == "success":
                        pdf_path = Paths.request_output(request_id) / r["filename"]
                        if pdf_path.exists():
                            zf.write(str(pdf_path), r["filename"])

        return {
            "success": True,
            "request_id": request_id,
            "total": len(urls),
            "converted": success_count,
            "failed": fail_count,
            "results": results,
            "zip_filename": zip_filename,
            "zip_download_url": (
                f"/api/convert-to-pdf/webpage-to-pdf/download-zip/{request_id}"
                if zip_filename else None
            ),
        }

    # ── Header / Footer templates ──────────────────────────────────

    @staticmethod
    def _build_header_template(config: Dict[str, Any]) -> str:
        """Build Playwright header HTML template."""
        left = config.get("header_left", "")
        center = config.get("header_center", "")
        right = config.get("header_right", "")
        if not left and not center and not right:
            center = config.get("header_text", "")
        return (
            '<div style="font-size:9px;width:100%;display:flex;justify-content:space-between;'
            'padding:0 20px;color:#666;">'
            f'<span>{left}</span>'
            f'<span>{center}</span>'
            f'<span>{right}</span>'
            '</div>'
        )

    @staticmethod
    def _build_footer_template(config: Dict[str, Any]) -> str:
        """Build Playwright footer HTML template with page numbers."""
        left = config.get("footer_left", "")
        center = config.get("footer_center", "")
        right = config.get("footer_right", "")

        if not left and not center and not right:
            center = config.get("footer_text", "")

        # Add page numbers if enabled
        pn_format = config.get("page_number_format", "page_total")
        if config.get("page_numbers", False):
            if pn_format == "page":
                page_part = 'Page <span class="pageNumber"></span>'
            elif pn_format == "page_total":
                page_part = 'Page <span class="pageNumber"></span> of <span class="totalPages"></span>'
            else:
                page_part = '<span class="pageNumber"></span>'

            if center:
                center += " &nbsp;|&nbsp; " + page_part
            else:
                center = page_part

        return (
            '<div style="font-size:9px;width:100%;display:flex;justify-content:space-between;'
            'padding:0 20px;color:#666;">'
            f'<span>{left}</span>'
            f'<span>{center}</span>'
            f'<span>{right}</span>'
            '</div>'
        )

    # ── PDF post-processing ────────────────────────────────────────

    def _postprocess_pdf(
        self,
        raw_bytes: bytes,
        request_id: str,
        filename: str,
        config: Dict[str, Any],
        title: str = "",
    ) -> Path:
        """Add metadata and optionally encrypt the PDF."""
        doc = fitz.Document(stream=raw_bytes, filetype="pdf")

        meta = doc.metadata
        if title:
            meta["title"] = title
        if config.get("pdf_author"):
            meta["author"] = config["pdf_author"]
        if config.get("pdf_subject"):
            meta["subject"] = config["pdf_subject"]
        if config.get("pdf_keywords"):
            meta["keywords"] = config["pdf_keywords"]
        meta["creator"] = "PDF Backend (Playwright)"
        meta["producer"] = "PDF Backend"
        doc.set_metadata(meta)

        save_kwargs: Dict[str, Any] = {"garbage": 3, "deflate": True}

        password = config.get("password", "")
        if password:
            save_kwargs["encryption"] = fitz.PDF_ENCRYPT_AES_256
            save_kwargs["owner_pw"] = password
            save_kwargs["user_pw"] = password

        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not filename.endswith(".pdf"):
            filename = f"{filename}.pdf"

        output_path = output_dir / filename
        doc.save(output_path, **save_kwargs)
        doc.close()

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ValueError("Generated PDF is invalid or empty.")

        return output_path


webpage_to_pdf_service = WebpageToPdfService()
