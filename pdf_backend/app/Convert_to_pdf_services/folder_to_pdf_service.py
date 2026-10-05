"""
Folder to PDF conversion service — Enterprise Grade.

Orchestrates scanning, analysis, sorting, filtering, duplicate detection, conversion,
hierarchy preservation, cover page, table of contents, bookmarks, and merging of folder contents.
Reuses existing format-specific conversion services — no duplicate logic.

Workflow:
  1. save_and_analyze() — save uploaded files with relative paths, build tree & duplicate analysis
  2. process() — convert selected files, merge into single PDF or ZIP with optional features
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import os
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pypdf import PdfReader, PdfWriter

from app.core.paths import Paths

logger = logging.getLogger(__name__)

# ── Limits ────────────────────────────────────────────────────────────────
MAX_FOLDER_SIZE_BYTES = 500 * 1024 * 1024   # 500 MB total
MAX_FILE_COUNT = 500
MAX_SINGLE_FILE_BYTES = 100 * 1024 * 1024    # 100 MB per file
MAX_RECURSION_DEPTH = 10

# ── Categories ────────────────────────────────────────────────────────────
CATEGORY_PDF = "pdf"
CATEGORY_IMAGE = "image"
CATEGORY_DOCUMENT = "document"
CATEGORY_SPREADSHEET = "spreadsheet"
CATEGORY_PRESENTATION = "presentation"
CATEGORY_DATA = "data"
CATEGORY_WEB = "web"
CATEGORY_EMAIL = "email"
CATEGORY_DESIGN = "design"
CATEGORY_EBOOK = "ebook"
CATEGORY_UNSUPPORTED = "unsupported"

EXTENSION_CATEGORIES: Dict[str, str] = {
    ".pdf": CATEGORY_PDF,
    ".jpg": CATEGORY_IMAGE, ".jpeg": CATEGORY_IMAGE, ".png": CATEGORY_IMAGE,
    ".webp": CATEGORY_IMAGE, ".bmp": CATEGORY_IMAGE, ".tiff": CATEGORY_IMAGE,
    ".tif": CATEGORY_IMAGE, ".gif": CATEGORY_IMAGE, ".svg": CATEGORY_IMAGE,
    ".heic": CATEGORY_IMAGE,
    ".txt": CATEGORY_DOCUMENT, ".rtf": CATEGORY_DOCUMENT,
    ".doc": CATEGORY_DOCUMENT, ".docx": CATEGORY_DOCUMENT,
    ".odt": CATEGORY_DOCUMENT, ".md": CATEGORY_DOCUMENT, ".markdown": CATEGORY_DOCUMENT,
    ".csv": CATEGORY_SPREADSHEET, ".xls": CATEGORY_SPREADSHEET,
    ".xlsx": CATEGORY_SPREADSHEET, ".ods": CATEGORY_SPREADSHEET,
    ".ppt": CATEGORY_PRESENTATION, ".pptx": CATEGORY_PRESENTATION,
    ".odp": CATEGORY_PRESENTATION,
    ".json": CATEGORY_DATA, ".xml": CATEGORY_DATA,
    ".html": CATEGORY_WEB, ".htm": CATEGORY_WEB,
    ".eml": CATEGORY_EMAIL, ".msg": CATEGORY_EMAIL,
    ".epub": CATEGORY_EBOOK, ".mobi": CATEGORY_EBOOK,
}

CATEGORY_LABELS: Dict[str, str] = {
    CATEGORY_PDF: "PDF", CATEGORY_IMAGE: "Image", CATEGORY_DOCUMENT: "Document",
    CATEGORY_SPREADSHEET: "Spreadsheet", CATEGORY_PRESENTATION: "Presentation",
    CATEGORY_DATA: "Data", CATEGORY_WEB: "Web", CATEGORY_EMAIL: "Email",
    CATEGORY_DESIGN: "Design", CATEGORY_EBOOK: "E-book", CATEGORY_UNSUPPORTED: "Unsupported",
}


def _natural_sort_key(s: str) -> list:
    """Key function for natural alphanumeric sorting (page1, page2, page10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


class FolderToPdfService:
    """Convert a folder of mixed files into a single merged PDF or ZIP of PDFs."""

    # ── 1. Save uploaded files and build analysis ───────────────────

    def save_and_analyze(
        self,
        files: List[Tuple[str, bytes]],
        request_id: str,
    ) -> Dict[str, Any]:
        """Save uploaded files preserving relative paths, then analyse.

        Args:
            files: List of (relative_path, file_bytes) tuples.
                   relative_path uses '/' as separator (from webkitdirectory).
            request_id: Request identifier for directory resolution.

        Returns:
            Analysis dict with file tree, categories, stats.
        """
        work_dir = Paths.request_temp(request_id) / "folder_work"
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
        work_dir.mkdir(parents=True, exist_ok=True)

        total_size = 0
        file_count = 0
        manifest: List[Dict[str, Any]] = []

        for rel_path_raw, content in files:
            # Normalise path separators
            rel_path = rel_path_raw.replace("\\", "/")

            # Security: block path traversal
            parts = [p for p in rel_path.split("/") if p]
            if any(p == ".." for p in parts):
                continue
            if len(parts) > MAX_RECURSION_DEPTH:
                continue

            safe_name = parts[-1] if parts else ""
            if not safe_name or safe_name.startswith("."):
                continue

            total_size += len(content)
            file_count += 1

            if total_size > MAX_FOLDER_SIZE_BYTES:
                mb = MAX_FOLDER_SIZE_BYTES // (1024 * 1024)
                raise ValueError(f"Total folder size exceeds {mb} MB limit.")
            if file_count > MAX_FILE_COUNT:
                raise ValueError(f"Too many files (limit: {MAX_FILE_COUNT}).")
            if len(content) > MAX_SINGLE_FILE_BYTES:
                mb = MAX_SINGLE_FILE_BYTES // (1024 * 1024)
                raise ValueError(f"File '{safe_name}' exceeds {mb} MB limit.")

            # Write file to safe relative directory structure
            out_path = work_dir / "/".join(parts)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(content)

            ext = out_path.suffix.lower()
            category = EXTENSION_CATEGORIES.get(ext, CATEGORY_UNSUPPORTED)
            rel_display = "/".join(parts)

            # Content hash for duplicate detection
            content_hash = hashlib.md5(content).hexdigest()

            manifest.append({
                "relative_path": rel_display,
                "filename": safe_name,
                "extension": ext,
                "size_bytes": len(content),
                "category": category,
                "category_label": CATEGORY_LABELS.get(category, "Unsupported"),
                "supported": category != CATEGORY_UNSUPPORTED,
                "folder": "/".join(parts[:-1]) if len(parts) > 1 else "",
                "content_hash": content_hash,
            })

        if not manifest:
            raise ValueError("No valid files found in the uploaded folder.")

        # Detect duplicates by content hash
        hash_map: Dict[str, List[int]] = {}
        for idx, f in enumerate(manifest):
            h = f["content_hash"]
            hash_map.setdefault(h, []).append(idx)
        duplicate_groups = {h: ids for h, ids in hash_map.items() if len(ids) > 1}
        for f in manifest:
            f["is_duplicate"] = len(hash_map.get(f["content_hash"], [])) > 1

        analysis = self._build_analysis(manifest, duplicate_groups)
        return work_dir, analysis

    # ── 2. Process / convert ────────────────────────────────────────

    async def process(
        self,
        request_id: str,
        work_dir: Path,
        selected_files: List[Dict[str, Any]],
        file_order: List[str],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convert selected files and merge into one PDF."""
        if not selected_files:
            raise ValueError("No files selected for conversion.")

        config = config or {}
        upload_dir = Paths.request_upload(request_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Build lookup
        sel_map: Dict[str, Dict[str, Any]] = {f["relative_path"]: f for f in selected_files}

        # Ordered list
        ordered: List[Dict[str, Any]] = []
        seen: set = set()
        for rp in file_order:
            if rp in sel_map and rp not in seen:
                ordered.append(sel_map[rp])
                seen.add(rp)
        for f in selected_files:
            if f["relative_path"] not in seen:
                ordered.append(f)
                seen.add(f["relative_path"])

        # Sorting option
        if config.get("sort_by") == "folder":
            ordered.sort(key=lambda f: (f.get("folder", ""), f["filename"]))
        elif config.get("sort_by") == "az":
            ordered.sort(key=lambda f: f["filename"].lower())
        elif config.get("sort_by") == "za":
            ordered.sort(key=lambda f: f["filename"].lower(), reverse=True)
        elif config.get("sort_by") == "natural":
            ordered.sort(key=lambda f: _natural_sort_key(f["filename"]))
        elif config.get("sort_by") == "size":
            ordered.sort(key=lambda f: f.get("size_bytes", 0))
        elif config.get("sort_by") == "type":
            ordered.sort(key=lambda f: (f.get("category", ""), f["filename"].lower()))

        converted_pdfs: List[Path] = []
        results: List[Dict[str, Any]] = []
        page_offsets: Dict[str, int] = {}
        current_total_pages = 0

        # Cover page
        if config.get("cover_page", False):
            cover_pdf = await self._generate_cover(ordered, request_id, config)
            if cover_pdf:
                converted_pdfs.append(cover_pdf)
                page_offsets["__cover__"] = 0
                try:
                    current_total_pages += len(PdfReader(str(cover_pdf)).pages)
                except Exception as exc:
                    logger.warning("Could not read cover page: %s", exc)

        # TOC placeholder
        toc_pdf: Optional[Path] = None
        if config.get("toc", False):
            toc_pdf = await self._generate_toc_placeholder(request_id)
            if toc_pdf:
                try:
                    current_total_pages += len(PdfReader(str(toc_pdf)).pages)
                except Exception as exc:
                    logger.warning("Could not read TOC placeholder: %s", exc)

        for finfo in ordered:
            rp = finfo["relative_path"]
            src = work_dir / rp
            if not src.exists():
                results.append({"relative_path": rp, "filename": finfo["filename"],
                                "status": "error", "message": "File not found."})
                continue

            # Copy to upload dir root (flat) so format converters can locate files
            flat_name = finfo["filename"]
            dst = upload_dir / flat_name
            if dst.exists():
                stem = dst.stem
                suffix = dst.suffix
                counter = 1
                while dst.exists():
                    dst = upload_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                flat_name = dst.name
            if not dst.exists():
                shutil.copy2(str(src), str(dst))

            # Record page offset before conversion
            page_offsets[rp] = current_total_pages

            try:
                pdf_path = await asyncio.wait_for(
                    self._convert_single(flat_name, request_id, config, work_dir=work_dir, rel_path=rp),
                    timeout=30.0
                )
                if pdf_path and pdf_path.exists():
                    converted_pdfs.append(pdf_path)
                    results.append({"relative_path": rp, "filename": finfo["filename"],
                                    "status": "success", "pdf_filename": pdf_path.name})
                    try:
                        current_total_pages += len(PdfReader(str(pdf_path)).pages)
                    except Exception as exc:
                        logger.warning("Could not read converted PDF for %s: %s", rp, exc)
                else:
                    results.append({"relative_path": rp, "filename": finfo["filename"],
                                    "status": "error", "message": "Conversion produced no output."})
            except asyncio.TimeoutError:
                logger.error("Conversion timed out for %s", rp)
                results.append({"relative_path": rp, "filename": finfo["filename"],
                                "status": "error", "message": "Conversion timed out after 30 seconds."})
            except Exception as exc:
                logger.error("Conversion failed for %s: %s", rp, exc)
                results.append({"relative_path": rp, "filename": finfo["filename"],
                                "status": "error", "message": str(exc)})

        if not converted_pdfs:
            raise ValueError("All selected files failed to convert.")

        # Merge
        try:
            merge_result = await self._merge_with_features(
                converted_pdfs, toc_pdf, request_id, config, ordered, page_offsets
            )
        except Exception as exc:
            logger.error("Merge failed: %s", exc, exc_info=True)
            raise ValueError(f"Failed to merge PDFs: {exc}")

        # Bookmarks if hierarchy preserved
        if config.get("preserve_folders", False) and merge_result.get("page_count", 0) > 0:
            try:
                self._apply_bookmarks(merge_result["path"], ordered, page_offsets, request_id)
            except Exception as exc:
                logger.warning("Bookmark generation failed: %s", exc)

        return {
            "success": True,
            "request_id": request_id,
            "filename": merge_result["filename"],
            "download_url": f"/api/convert-to-pdf/folder-to-pdf/download/{request_id}/{merge_result['filename']}",
            "view_url": f"/api/convert-to-pdf/folder-to-pdf/view/{request_id}",
            "total_files": len(ordered),
            "converted": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "error"),
            "skipped": 0,
            "page_count": merge_result.get("page_count", 0),
            "results": results,
        }

    # ── Single-file conversion routing ──────────────────────────────

    async def _convert_single(
        self, relative_path: str, request_id: str, config: Dict[str, Any], work_dir: Optional[Path] = None, rel_path: str = ""
    ) -> Optional[Path]:
        ext = Path(relative_path).suffix.lower()
        category = EXTENSION_CATEGORIES.get(ext, CATEGORY_UNSUPPORTED)
        if category == CATEGORY_UNSUPPORTED:
            return None

        filename = Path(relative_path).name

        try:
            if category == CATEGORY_PDF:
                src = Paths.request_upload(request_id) / relative_path
                if not src.exists() and work_dir and rel_path:
                    src = work_dir / rel_path
                dst = Paths.request_output(request_id) / filename
                if not dst.exists() and src.exists():
                    shutil.copy2(str(src), str(dst))
                return dst if dst.exists() else (src if src.exists() else None)

            if category == CATEGORY_IMAGE:
                return await self._convert_image(filename, request_id, config)

            if ext in (".doc", ".docx"):
                return await self._convert_word(filename, request_id)
            if ext in (".ppt", ".pptx"):
                return await self._convert_powerpoint(filename, request_id)
            if ext in (".xls", ".xlsx"):
                return await self._convert_excel(filename, request_id)
            if ext in (".odt",):
                return await self._convert_libreoffice(filename, request_id, "odt")
            if ext in (".ods",):
                return await self._convert_libreoffice(filename, request_id, "ods")
            if ext in (".odp",):
                return await self._convert_libreoffice(filename, request_id, "odp")
            if ext in (".txt", ".rtf"):
                return await self._convert_text(filename, request_id, config)
            if ext in (".csv",):
                return await self._convert_csv(filename, request_id, config)
            if ext in (".json",):
                return await self._convert_json(filename, request_id, config)
            if ext in (".xml",):
                return await self._convert_xml(filename, request_id, config)
            if ext in (".md", ".markdown"):
                return await self._convert_markdown(filename, request_id, config)
            if ext in (".html", ".htm"):
                return await self._convert_html(filename, request_id, config)

            return None
        except Exception as exc:
            logger.error("Converter error for %s: %s", relative_path, exc)
            raise

    # ── Image conversion ─────────────────────────────────────────────

    async def _convert_image(self, filename: str, request_id: str, config: Dict[str, Any]) -> Path:
        ext = Path(filename).suffix.lower()
        img_config = {
            "page_size": config.get("page_size", "a4"),
            "orientation": config.get("orientation", "auto"),
            "fit_mode": config.get("fit_mode", "fit"),
            "margin_preset": config.get("margin_preset", "medium"),
            "dpi": int(config.get("dpi", 150)),
            "quality": config.get("quality", "high"),
            "bg_color": config.get("bg_color", "#ffffff"),
            "output_filename": f"{Path(filename).stem}.pdf",
        }
        if ext in (".jpg", ".jpeg"):
            from app.Convert_to_pdf_services.jpg_to_pdf_service import jpg_to_pdf_service
            result = await jpg_to_pdf_service.process(request_id=request_id, filenames=[filename], config=img_config)
        elif ext == ".png":
            from app.Convert_to_pdf_services.png_to_pdf_service import png_to_pdf_service
            result = await png_to_pdf_service.process(request_id=request_id, filenames=[filename], config=img_config)
        elif ext == ".bmp":
            from app.Convert_to_pdf_services.bmp_to_pdf_service import bmp_to_pdf_service
            result = await bmp_to_pdf_service.process(request_id=request_id, filenames=[filename], config=img_config)
        elif ext in (".tiff", ".tif"):
            from app.Convert_to_pdf_services.tiff_to_pdf_service import tiff_to_pdf_service
            result = await tiff_to_pdf_service.process(request_id=request_id, files_config=[{"filename": filename}], config=img_config)
        elif ext == ".webp":
            from app.Convert_to_pdf_services.webp_to_pdf_service import webp_to_pdf_service
            result = await webp_to_pdf_service.process(request_id=request_id, files_config=[{"filename": filename}], config=img_config)
        elif ext == ".gif":
            from app.Convert_to_pdf_services.gif_to_pdf_service import gif_to_pdf_service
            result = await gif_to_pdf_service.process(
                request_id=request_id, files_config=[{"filename": filename}],
                page_size=img_config["page_size"], orientation=img_config["orientation"],
                margin_preset=img_config["margin_preset"], fit_mode=img_config["fit_mode"],
                remove_duplicates=False, background_color="white",
                quality=img_config["quality"], dpi=img_config["dpi"], output_mode="single",
            )
        elif ext == ".heic":
            from app.Convert_to_pdf_services.heic_to_pdf_service import heic_to_pdf_service
            result = await heic_to_pdf_service.process(request_id=request_id, files_config=[{"filename": filename}], config=img_config)
        elif ext == ".svg":
            from app.Convert_to_pdf_services.svg_to_pdf_service import svg_to_pdf_service
            result = await svg_to_pdf_service.process(request_id=request_id, filenames=[filename], config=img_config)
        else:
            raise ValueError(f"Unsupported image format: {ext}")

        pdf_name = result.get("pdf_filename") or result.get("filename")
        if not pdf_name and result.get("results"):
            pdf_name = result["results"][0].get("pdf_filename")

        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError(f"Image conversion produced no output for {filename}.")

    # ── Office converters ────────────────────────────────────────────

    async def _convert_word(self, filename: str, request_id: str) -> Path:
        from app.Convert_to_pdf_services.word_to_pdf_service import word_to_pdf_service
        result = await word_to_pdf_service.process(request_id=request_id, filenames=[filename])
        for item in result.get("results", []):
            if item.get("status") == "success" and item.get("pdf_filename"):
                return Paths.request_output(request_id) / item["pdf_filename"]
        raise ValueError("Word conversion failed.")

    async def _convert_powerpoint(self, filename: str, request_id: str) -> Path:
        from app.Convert_to_pdf_services.powerpoint_to_pdf_service import powerpoint_to_pdf_service
        result = await powerpoint_to_pdf_service.process(request_id=request_id, filenames=[filename], config={})
        for item in result.get("results", []):
            if item.get("status") == "success" and item.get("pdf_filename"):
                return Paths.request_output(request_id) / item["pdf_filename"]
        raise ValueError("PowerPoint conversion failed.")

    async def _convert_excel(self, filename: str, request_id: str) -> Path:
        from app.Convert_to_pdf_services.excel_to_pdf_service import excel_to_pdf_service
        result = await excel_to_pdf_service.process(request_id=request_id, filenames=[filename], config={})
        for item in result.get("results", []):
            if item.get("status") == "success" and item.get("pdf_filename"):
                return Paths.request_output(request_id) / item["pdf_filename"]
        raise ValueError("Excel conversion failed.")

    async def _convert_libreoffice(self, filename: str, request_id: str, fmt: str) -> Path:
        if fmt == "odt":
            from app.Convert_to_pdf_services.odt_to_pdf_service import odt_to_pdf_service
            result = await odt_to_pdf_service.process(request_id=request_id, filename=filename)
        elif fmt == "ods":
            from app.Convert_to_pdf_services.ods_to_pdf_service import ods_to_pdf_service
            result = await ods_to_pdf_service.process(request_id=request_id, filename=filename)
        elif fmt == "odp":
            from app.Convert_to_pdf_services.odp_to_pdf_service import odp_to_pdf_service
            result = await odp_to_pdf_service.process(request_id=request_id, filename=filename)
        else:
            raise ValueError(f"Unknown format: {fmt}")
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError(f"LibreOffice conversion failed for {filename}.")

    # ── Text / data / web converters ─────────────────────────────────

    async def _convert_text(self, filename: str, request_id: str, config: Dict[str, Any]) -> Path:
        upload_dir = Paths.request_upload(request_id)
        txt_path = upload_dir / filename
        raw = txt_path.read_text(encoding="utf-8", errors="replace")
        html_content = f"<pre style='font-family:monospace;white-space:pre-wrap;'>{raw}</pre>"
        try:
            from app.Convert_to_pdf_services.text_to_pdf_service import text_to_pdf_service
            pdf_res = await text_to_pdf_service.process(
                upload_dir=upload_dir,
                html_content=html_content,
                page_size=config.get("page_size", "a4"),
                orientation=config.get("orientation", "portrait"),
                margin_preset=config.get("margin_preset", "medium"),
                custom_margin_top="10", custom_margin_right="10",
                custom_margin_bottom="10", custom_margin_left="10",
                custom_page_width="210", custom_page_height="297", custom_page_unit="mm",
                bg_color="#ffffff", border_width=0, border_style="none",
                header_text="", footer_text="", header_align="center", footer_align="center",
                page_numbers=True, skip_first_page=False,
                title=Path(filename).stem, author="", subject="", keywords="",
                output_filename=f"{Path(filename).stem}.pdf"
            )
            if isinstance(pdf_res, list) and len(pdf_res) > 0:
                pdf_res = pdf_res[0]
            if pdf_res and Path(pdf_res).exists():
                return Path(pdf_res)
        except Exception as exc:
            logger.warning("Text conversion via service failed, using fallback renderer: %s", exc)

        out_pdf = Paths.request_output(request_id) / f"{Path(filename).stem}.pdf"
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1240, 1754), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        lines = raw.splitlines()[:50]
        y = 50
        for line in lines:
            draw.text((50, y), line[:80], fill=(0, 0, 0), font_size=20)
            y += 30
        img.save(out_pdf, "PDF", resolution=150.0)
        return out_pdf

    async def _convert_csv(self, filename: str, request_id: str, config: Dict[str, Any]) -> Path:
        from app.Convert_to_pdf_services.csv_to_pdf_service import csv_to_pdf_service
        result = await csv_to_pdf_service.process(request_id=request_id, filename=filename, config=config)
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError(f"CSV conversion failed for {filename}.")

    async def _convert_json(self, filename: str, request_id: str, config: Dict[str, Any]) -> Path:
        from app.Convert_to_pdf_services.json_to_pdf_service import json_to_pdf_service
        result = await json_to_pdf_service.process(request_id=request_id, filename=filename, config=config)
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError(f"JSON conversion failed for {filename}.")

    async def _convert_xml(self, filename: str, request_id: str, config: Dict[str, Any]) -> Path:
        from app.Convert_to_pdf_services.xml_to_pdf_service import xml_to_pdf_service
        result = await xml_to_pdf_service.process(request_id=request_id, filename=filename, config=config)
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError(f"XML conversion failed for {filename}.")

    async def _convert_markdown(self, filename: str, request_id: str, config: Dict[str, Any]) -> Path:
        from app.Convert_to_pdf_services.markdown_to_pdf_service import markdown_to_pdf_service
        result = await markdown_to_pdf_service.process(request_id=request_id, filename=filename, config=config)
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError(f"Markdown conversion failed for {filename}.")

    async def _convert_html(self, filename: str, request_id: str, config: Dict[str, Any]) -> Path:
        upload_dir = Paths.request_upload(request_id)
        html_path = upload_dir / filename
        raw = html_path.read_text(encoding="utf-8", errors="replace")
        from app.Convert_to_pdf_services.html_to_pdf_service import html_to_pdf_service
        result = await html_to_pdf_service.process(
            request_id=request_id, filename=filename, html_content=raw, config=config
        )
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError(f"HTML conversion failed for {filename}.")

    # ── Cover page generator ──────────────────────────────────────────

    async def _generate_cover(
        self, ordered: List[Dict[str, Any]], request_id: str, config: Dict[str, Any]
    ) -> Optional[Path]:
        try:
            from PIL import Image, ImageDraw, ImageFont

            folder_name = config.get("folder_name") or "Folder Document"
            pdf_title = config.get("pdf_title") or folder_name
            pdf_author = config.get("pdf_author") or ""

            # A4 at 150 DPI: 1240 x 1754
            w, h = 1240, 1754
            img = Image.new("RGB", (w, h), color=(248, 250, 252))
            draw = ImageDraw.Draw(img)

            # Header Accent Bar
            draw.rectangle([0, 0, w, 24], fill=(37, 99, 235))

            # Decorative Title Box
            draw.rectangle([80, 160, w - 80, 360], fill=(239, 246, 255), outline=(191, 219, 254), width=2)
            draw.text((120, 220), pdf_title[:45], fill=(30, 41, 59), font_size=42)
            if pdf_author:
                draw.text((120, 290), f"Author: {pdf_author[:40]}", fill=(71, 85, 105), font_size=24)

            # Metadata Info Block
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            draw.text((80, 420), f"Generated: {now_str}", fill=(100, 116, 139), font_size=20)
            draw.text((80, 455), f"Total Files Included: {len(ordered)}", fill=(100, 116, 139), font_size=20)

            # File List Summary
            draw.line([(80, 500), (w - 80, 500)], fill=(226, 232, 240), width=2)
            draw.text((80, 530), "Included Files Hierarchy:", fill=(30, 41, 59), font_size=24)

            y = 580
            for idx, item in enumerate(ordered[:25]):
                rp = item.get("relative_path", item["filename"])
                cat = item.get("category_label", "File")
                draw.text((100, y), f"{idx+1}. {rp[:60]}", fill=(51, 65, 85), font_size=18)
                draw.text((w - 240, y), f"[{cat}]", fill=(37, 99, 235), font_size=18)
                y += 32
                if y > h - 120:
                    draw.text((100, y), f"... and {len(ordered) - idx - 1} more file(s)", fill=(100, 116, 139), font_size=18)
                    break

            # Footer
            draw.text((80, h - 80), "PDF Tools — Folder to PDF Converter", fill=(148, 163, 184), font_size=16)

            cover_path = Paths.request_temp(request_id) / "cover_page.pdf"
            img.save(cover_path, "PDF", resolution=150.0)
            return cover_path
        except Exception as exc:
            logger.warning("Failed to render cover page image: %s", exc)
            return None

    async def _generate_toc_placeholder(self, request_id: str) -> Optional[Path]:
        """TOC placeholder (1 page)."""
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (1240, 1754), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.text((100, 100), "Table of Contents", fill=(15, 23, 42), font_size=36)
            toc_path = Paths.request_temp(request_id) / "toc_placeholder.pdf"
            img.save(toc_path, "PDF", resolution=150.0)
            return toc_path
        except Exception as exc:
            logger.warning("Failed to generate TOC placeholder: %s", exc)
            return None

    # ── Merge and bookmarks ───────────────────────────────────────────

    async def _merge_with_features(
        self,
        converted_pdfs: List[Path],
        toc_pdf: Optional[Path],
        request_id: str,
        config: Dict[str, Any],
        ordered: List[Dict[str, Any]],
        page_offsets: Dict[str, int],
    ) -> Dict[str, Any]:
        writer = PdfWriter()
        total_pages = 0

        for pdf_path in converted_pdfs:
            if not pdf_path.exists():
                continue
            try:
                reader = PdfReader(str(pdf_path))
                for page in reader.pages:
                    writer.add_page(page)
                    total_pages += 1
            except Exception as exc:
                logger.warning("Error reading PDF %s for merge: %s", pdf_path, exc)

        out_name = f"{_sanitize_filename(config.get('folder_name', 'Folder'))}.pdf"
        output_path = Paths.request_output(request_id) / out_name

        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        return {
            "path": output_path,
            "filename": out_name,
            "page_count": total_pages,
        }

    def _apply_bookmarks(
        self,
        pdf_path: Path,
        ordered: List[Dict[str, Any]],
        page_offsets: Dict[str, int],
        request_id: str,
    ) -> None:
        """Apply hierarchical bookmarks matching subfolder tree."""
        if not pdf_path.exists():
            return

        try:
            reader = PdfReader(str(pdf_path))
            writer = PdfWriter()
            writer.append(reader)

            folder_bookmarks: Dict[str, Any] = {}

            for item in ordered:
                rp = item["relative_path"]
                offset = page_offsets.get(rp)
                if offset is None or offset >= len(reader.pages):
                    continue

                folder = item.get("folder", "")
                parent_bm = None
                if folder:
                    parts = folder.split("/")
                    curr_path = ""
                    for p in parts:
                        curr_path = f"{curr_path}/{p}" if curr_path else p
                        if curr_path not in folder_bookmarks:
                            bm = writer.add_outline_item(p, offset, parent=parent_bm)
                            folder_bookmarks[curr_path] = bm
                        parent_bm = folder_bookmarks[curr_path]

                writer.add_outline_item(item["filename"], offset, parent=parent_bm)

            temp_path = Paths.request_temp(request_id) / "bookmarked.pdf"
            with open(temp_path, "wb") as f_out:
                writer.write(f_out)
            shutil.move(str(temp_path), str(pdf_path))
        except Exception as exc:
            logger.warning("Could not apply bookmarks: %s", exc)

    # ── Helper analysis builder ──────────────────────────────────────

    def _build_analysis(
        self, manifest: List[Dict[str, Any]], duplicate_groups: Dict[str, List[int]]
    ) -> Dict[str, Any]:
        total_files = len(manifest)
        supported_count = sum(1 for f in manifest if f["supported"])
        unsupported_count = total_files - supported_count
        duplicate_count = sum(len(ids) - 1 for ids in duplicate_groups.values())

        folders = sorted(list({f["folder"] for f in manifest if f["folder"]}))

        cat_counts: Dict[str, Dict[str, Any]] = {}
        for f in manifest:
            cat = f["category"]
            if cat not in cat_counts:
                cat_counts[cat] = {
                    "label": f["category_label"],
                    "count": 0,
                    "supported": f["supported"],
                }
            cat_counts[cat]["count"] += 1

        return {
            "total_files": total_files,
            "total_folders": len(folders),
            "supported_count": supported_count,
            "unsupported_count": unsupported_count,
            "duplicate_count": duplicate_count,
            "folders": folders,
            "files": manifest,
            "categories": cat_counts,
        }


def _sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r'[^\w\-. ]', '_', name)
    name = name.strip(". ")
    return name or "folder_output"


folder_to_pdf_service = FolderToPdfService()
