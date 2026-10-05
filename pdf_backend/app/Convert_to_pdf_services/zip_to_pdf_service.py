"""
ZIP to PDF conversion service.

Orchestrates secure extraction, scanning, format detection, conversion, and merging
of ZIP archive contents into a single merged PDF.

Workflow:
  1. save_and_analyze() — securely extract ZIP, analyze contents, build manifest & tree
  2. process() — convert selected supported files (reusing format services), merge into single PDF
"""

from __future__ import annotations

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

# ── Limits & Constraints ──────────────────────────────────────────────────
MAX_ZIP_SIZE_BYTES = 100 * 1024 * 1024         # 100 MB zip upload
MAX_UNCOMPRESSED_SIZE_BYTES = 300 * 1024 * 1024 # 300 MB total uncompressed
MAX_FILE_COUNT = 500                           # 500 files max
MAX_SINGLE_FILE_BYTES = 100 * 1024 * 1024      # 100 MB per file
MAX_RECURSION_DEPTH = 10

# ── File Categories ───────────────────────────────────────────────────────
CATEGORY_PDF = "pdf"
CATEGORY_IMAGE = "image"
CATEGORY_DOCUMENT = "document"
CATEGORY_SPREADSHEET = "spreadsheet"
CATEGORY_PRESENTATION = "presentation"
CATEGORY_DATA = "data"
CATEGORY_WEB = "web"
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
}

CATEGORY_LABELS: Dict[str, str] = {
    CATEGORY_PDF: "PDF", CATEGORY_IMAGE: "Image", CATEGORY_DOCUMENT: "Document",
    CATEGORY_SPREADSHEET: "Spreadsheet", CATEGORY_PRESENTATION: "Presentation",
    CATEGORY_DATA: "Data", CATEGORY_WEB: "Web", CATEGORY_UNSUPPORTED: "Unsupported",
}


def _natural_sort_key(name: str) -> List[Any]:
    parts = re.split(r"(\d+)", name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def _is_safe_path(base_dir: Path, target_path: Path) -> bool:
    try:
        base_resolved = base_dir.resolve()
        target_resolved = target_path.resolve()
        return str(target_resolved).startswith(str(base_resolved))
    except Exception:
        return False


class ZipToPdfService:
    """Convert a ZIP archive of mixed files into a single merged PDF."""

    # ── 1. Save & Extract ZIP and Build Analysis ─────────────────────

    def save_and_analyze(
        self,
        zip_bytes: bytes,
        zip_filename: str,
        request_id: str,
    ) -> Dict[str, Any]:
        """Securely validate & extract ZIP contents and return content manifest.

        Args:
            zip_bytes: Raw bytes of uploaded ZIP file.
            zip_filename: Original filename of ZIP archive.
            request_id: Unique request identifier.

        Returns:
            Dict containing ZIP manifest, file counts, categories, and tree.
        """
        if len(zip_bytes) == 0:
            raise ValueError("The uploaded ZIP file is empty.")

        if len(zip_bytes) > MAX_ZIP_SIZE_BYTES:
            raise ValueError(f"ZIP file size ({len(zip_bytes) / 1024 / 1024:.1f} MB) exceeds maximum allowed size ({MAX_ZIP_SIZE_BYTES / 1024 / 1024:.0f} MB).")

        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except zipfile.BadZipFile:
            raise ValueError("The uploaded file is corrupted or not a valid ZIP archive.")
        except Exception as e:
            raise ValueError(f"Failed to open ZIP archive: {e}")

        infolist = zf.infolist()
        if not infolist:
            raise ValueError("The ZIP archive contains no files.")

        # Check total file count and uncompressed size
        total_uncompressed = sum(info.file_size for info in infolist if not info.is_dir())
        file_entries = [info for info in infolist if not info.is_dir()]

        if len(file_entries) > MAX_FILE_COUNT:
            raise ValueError(f"ZIP archive contains too many files ({len(file_entries)}). Maximum allowed is {MAX_FILE_COUNT}.")

        if total_uncompressed > MAX_UNCOMPRESSED_SIZE_BYTES:
            raise ValueError(f"Uncompressed ZIP size ({total_uncompressed / 1024 / 1024:.1f} MB) exceeds maximum allowed limit ({MAX_UNCOMPRESSED_SIZE_BYTES / 1024 / 1024:.0f} MB).")

        # Set up work directory and upload directory for existing converters
        work_dir = Paths.request_temp(request_id) / "zip_work"
        upload_dir = Paths.request_upload(request_id)

        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
        work_dir.mkdir(parents=True, exist_ok=True)
        upload_dir.mkdir(parents=True, exist_ok=True)

        manifest: List[Dict[str, Any]] = []

        for idx, info in enumerate(file_entries):
            # Normalize path separators
            rel_path_raw = info.filename.replace("\\", "/").strip("/")

            # Security check: Zip Slip / Path Traversal
            if ".." in rel_path_raw.split("/") or rel_path_raw.startswith("/") or ":" in rel_path_raw:
                logger.warning("Zip Slip attempt detected in path: %s", info.filename)
                continue

            target_work = work_dir / rel_path_raw
            if not _is_safe_path(work_dir, target_work):
                logger.warning("Unsafe extraction path blocked: %s", info.filename)
                continue

            # Extract content safely
            target_work.parent.mkdir(parents=True, exist_ok=True)
            try:
                data = zf.read(info.filename)
            except Exception as e:
                logger.warning("Failed reading file %s from ZIP: %s", info.filename, e)
                continue

            target_work.write_bytes(data)

            # Also save into upload_dir so existing converters can locate files
            target_upload = upload_dir / rel_path_raw
            target_upload.parent.mkdir(parents=True, exist_ok=True)
            target_upload.write_bytes(data)

            ext = target_work.suffix.lower()
            category = EXTENSION_CATEGORIES.get(ext, CATEGORY_UNSUPPORTED)
            supported = category != CATEGORY_UNSUPPORTED
            folder = str(target_work.parent.relative_to(work_dir)).replace("\\", "/")
            if folder == ".":
                folder = ""

            manifest.append({
                "id": f"file_{idx}",
                "filename": target_work.name,
                "relative_path": rel_path_raw,
                "folder": folder,
                "ext": ext,
                "size_bytes": len(data),
                "category": category,
                "category_label": CATEGORY_LABELS.get(category, category.title()),
                "supported": supported,
            })

        zf.close()

        if not manifest:
            raise ValueError("No valid files could be extracted from the ZIP archive.")

        # Default natural sort
        manifest.sort(key=lambda f: _natural_sort_key(f["relative_path"]))

        analysis = self._build_analysis(manifest, zip_filename)
        return analysis

    # ── 2. Process Files & Merge into PDF ───────────────────────────

    async def process(
        self,
        request_id: str,
        work_dir: Path,
        selected_files: List[Dict[str, Any]],
        file_order: List[str],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convert selected files and merge them into a single PDF.

        Args:
            request_id: Request identifier.
            work_dir: Extracted ZIP directory.
            selected_files: List of file dicts selected by user.
            file_order: List of relative paths in desired page order.
            config: Options (page_size, orientation, margin_preset, fit_mode, etc.)

        Returns:
            Dict with filename, page_count, download_url, view_url.
        """
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build lookup table for selected files
        rel_path_to_info = {f["relative_path"]: f for f in selected_files if f.get("supported", True)}

        # Order items according to file_order or config sort_by
        ordered_paths: List[str] = []
        if file_order:
            for rp in file_order:
                if rp in rel_path_to_info and rp not in ordered_paths:
                    ordered_paths.append(rp)

        # Add any selected files not listed in order
        for rp in rel_path_to_info:
            if rp not in ordered_paths:
                ordered_paths.append(rp)

        # Apply sort_by if specified and not 'original'
        sort_by = config.get("sort_by", "original")
        if sort_by == "name_asc":
            ordered_paths.sort(key=lambda rp: Path(rp).name.lower())
        elif sort_by == "name_desc":
            ordered_paths.sort(key=lambda rp: Path(rp).name.lower(), reverse=True)
        elif sort_by == "path_asc":
            ordered_paths.sort(key=lambda rp: rp.lower())
        elif sort_by == "path_desc":
            ordered_paths.sort(key=lambda rp: rp.lower(), reverse=True)
        elif sort_by == "natural":
            ordered_paths.sort(key=_natural_sort_key)

        if not ordered_paths:
            raise ValueError("No supported files were selected for conversion.")

        converted_pdf_paths: List[Path] = []
        errors: List[str] = []

        try:
            for rp in ordered_paths:
                finfo = rel_path_to_info[rp]
                local_file = work_dir / rp
                if not local_file.exists():
                    # Fallback to upload_dir
                    local_file = Paths.request_upload(request_id) / rp

                if not local_file.exists():
                    errors.append(f"File not found: {rp}")
                    continue

                category = finfo.get("category") or EXTENSION_CATEGORIES.get(local_file.suffix.lower(), CATEGORY_UNSUPPORTED)

                try:
                    if category == CATEGORY_PDF:
                        converted_pdf_paths.append(local_file)
                    elif category == CATEGORY_IMAGE:
                        pdf_path = await self._convert_image(local_file.name, rp, request_id, config)
                        converted_pdf_paths.append(pdf_path)
                    elif category == CATEGORY_DOCUMENT:
                        ext = local_file.suffix.lower()
                        if ext in (".txt", ".rtf", ".md", ".markdown"):
                            pdf_path = await self._convert_text_or_md(local_file.name, rp, request_id, config)
                            converted_pdf_paths.append(pdf_path)
                        elif ext in (".doc", ".docx"):
                            pdf_path = await self._convert_word(rp, request_id)
                            converted_pdf_paths.append(pdf_path)
                        elif ext == ".odt":
                            pdf_path = await self._convert_libreoffice(rp, request_id, "odt")
                            converted_pdf_paths.append(pdf_path)
                    elif category == CATEGORY_SPREADSHEET:
                        ext = local_file.suffix.lower()
                        if ext == ".csv":
                            pdf_path = await self._convert_csv(rp, request_id, config)
                            converted_pdf_paths.append(pdf_path)
                        elif ext in (".xls", ".xlsx"):
                            pdf_path = await self._convert_excel(rp, request_id)
                            converted_pdf_paths.append(pdf_path)
                        elif ext == ".ods":
                            pdf_path = await self._convert_libreoffice(rp, request_id, "ods")
                            converted_pdf_paths.append(pdf_path)
                    elif category == CATEGORY_PRESENTATION:
                        ext = local_file.suffix.lower()
                        if ext in (".ppt", ".pptx"):
                            pdf_path = await self._convert_powerpoint(rp, request_id)
                            converted_pdf_paths.append(pdf_path)
                        elif ext == ".odp":
                            pdf_path = await self._convert_libreoffice(rp, request_id, "odp")
                            converted_pdf_paths.append(pdf_path)
                    elif category in (CATEGORY_DATA, CATEGORY_WEB):
                        ext = local_file.suffix.lower()
                        if ext == ".json":
                            pdf_path = await self._convert_json(rp, request_id, config)
                            converted_pdf_paths.append(pdf_path)
                        elif ext == ".xml":
                            pdf_path = await self._convert_xml(rp, request_id, config)
                            converted_pdf_paths.append(pdf_path)
                        elif ext in (".html", ".htm"):
                            pdf_path = await self._convert_html(rp, request_id, config)
                            converted_pdf_paths.append(pdf_path)
                    else:
                        if not config.get("ignore_unsupported", True):
                            errors.append(f"Unsupported format skipped: {rp}")
                except Exception as exc:
                    logger.warning("Conversion failed for %s: %s", rp, exc)
                    errors.append(f"Failed to convert {rp}: {exc}")

            if not converted_pdf_paths:
                err_msg = "; ".join(errors) if errors else "No files could be converted to PDF."
                raise ValueError(err_msg)

            # Merge all converted & original PDFs
            out_filename = config.get("output_filename", "").strip()
            if not out_filename:
                out_filename = "converted_from_zip.pdf"
            if not out_filename.endswith(".pdf"):
                out_filename += ".pdf"

            # Sanitize filename
            out_filename = re.sub(r'[^\w\.-]', '_', out_filename)

            merged_result = self._merge_pdfs(converted_pdf_paths, output_dir / out_filename, config)

            return {
                "success": True,
                "request_id": request_id,
                "filename": out_filename,
                "pdf_filename": out_filename,
                "page_count": merged_result["page_count"],
                "download_url": f"/api/convert-to-pdf/zip-to-pdf/download/{request_id}/{out_filename}",
                "view_url": f"/api/convert-to-pdf/zip-to-pdf/view/{request_id}",
                "converted_count": len(converted_pdf_paths),
                "warnings": errors,
            }
        finally:
            # Cleanup temporary work directory
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

    # ── Format Converters Delegation ──────────────────────────────────

    async def _convert_image(self, filename: str, rel_path: str, request_id: str, config: Dict[str, Any]) -> Path:
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
            result = await jpg_to_pdf_service.process(request_id=request_id, filenames=[rel_path], config=img_config)
        elif ext == ".png":
            from app.Convert_to_pdf_services.png_to_pdf_service import png_to_pdf_service
            result = await png_to_pdf_service.process(request_id=request_id, filenames=[rel_path], config=img_config)
        elif ext == ".bmp":
            from app.Convert_to_pdf_services.bmp_to_pdf_service import bmp_to_pdf_service
            result = await bmp_to_pdf_service.process(request_id=request_id, filenames=[rel_path], config=img_config)
        elif ext in (".tiff", ".tif"):
            from app.Convert_to_pdf_services.tiff_to_pdf_service import tiff_to_pdf_service
            result = await tiff_to_pdf_service.process(request_id=request_id, files_config=[{"filename": rel_path}], config=img_config)
        elif ext == ".webp":
            from app.Convert_to_pdf_services.webp_to_pdf_service import webp_to_pdf_service
            result = await webp_to_pdf_service.process(request_id=request_id, files_config=[{"filename": rel_path}], config=img_config)
        elif ext == ".gif":
            from app.Convert_to_pdf_services.gif_to_pdf_service import gif_to_pdf_service
            result = await gif_to_pdf_service.process(
                request_id=request_id, files_config=[{"filename": rel_path}],
                page_size=img_config["page_size"], orientation=img_config["orientation"],
                margin_preset=img_config["margin_preset"], fit_mode=img_config["fit_mode"],
                remove_duplicates=False, background_color="white",
                quality=img_config["quality"], dpi=img_config["dpi"], output_mode="single",
            )
        elif ext == ".heic":
            from app.Convert_to_pdf_services.heic_to_pdf_service import heic_to_pdf_service
            result = await heic_to_pdf_service.process(request_id=request_id, files_config=[{"filename": rel_path}], config=img_config)
        elif ext == ".svg":
            from app.Convert_to_pdf_services.svg_to_pdf_service import svg_to_pdf_service
            result = await svg_to_pdf_service.process(request_id=request_id, filenames=[rel_path], config=img_config)
        else:
            raise ValueError(f"Unsupported image format: {ext}")

        pdf_name = result.get("pdf_filename") or result.get("filename")
        if not pdf_name and result.get("results"):
            pdf_name = result["results"][0].get("pdf_filename")

        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError(f"Image conversion produced no output for {rel_path}.")

    async def _convert_word(self, rel_path: str, request_id: str) -> Path:
        from app.Convert_to_pdf_services.word_to_pdf_service import word_to_pdf_service
        result = await word_to_pdf_service.process(request_id=request_id, filenames=[rel_path])
        for item in result.get("results", []):
            if item.get("status") == "success" and item.get("pdf_filename"):
                return Paths.request_output(request_id) / item["pdf_filename"]
        raise ValueError("Word conversion failed.")

    async def _convert_powerpoint(self, rel_path: str, request_id: str) -> Path:
        from app.Convert_to_pdf_services.powerpoint_to_pdf_service import powerpoint_to_pdf_service
        result = await powerpoint_to_pdf_service.process(request_id=request_id, filenames=[rel_path], config={})
        for item in result.get("results", []):
            if item.get("status") == "success" and item.get("pdf_filename"):
                return Paths.request_output(request_id) / item["pdf_filename"]
        raise ValueError("PowerPoint conversion failed.")

    async def _convert_excel(self, rel_path: str, request_id: str) -> Path:
        from app.Convert_to_pdf_services.excel_to_pdf_service import excel_to_pdf_service
        result = await excel_to_pdf_service.process(request_id=request_id, filenames=[rel_path], config={})
        for item in result.get("results", []):
            if item.get("status") == "success" and item.get("pdf_filename"):
                return Paths.request_output(request_id) / item["pdf_filename"]
        raise ValueError("Excel conversion failed.")

    async def _convert_libreoffice(self, rel_path: str, request_id: str, fmt: str) -> Path:
        if fmt == "odt":
            from app.Convert_to_pdf_services.odt_to_pdf_service import odt_to_pdf_service
            result = await odt_to_pdf_service.process(request_id=request_id, filename=rel_path)
        elif fmt == "ods":
            from app.Convert_to_pdf_services.ods_to_pdf_service import ods_to_pdf_service
            result = await ods_to_pdf_service.process(request_id=request_id, filename=rel_path)
        elif fmt == "odp":
            from app.Convert_to_pdf_services.odp_to_pdf_service import odp_to_pdf_service
            result = await odp_to_pdf_service.process(request_id=request_id, filename=rel_path)
        else:
            raise ValueError(f"Unknown format: {fmt}")
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError(f"LibreOffice conversion failed for {rel_path}.")

    async def _convert_text_or_md(self, filename: str, rel_path: str, request_id: str, config: Dict[str, Any]) -> Path:
        ext = Path(filename).suffix.lower()
        if ext in (".md", ".markdown"):
            from app.Convert_to_pdf_services.markdown_to_pdf_service import markdown_to_pdf_service
            result = await markdown_to_pdf_service.process(request_id=request_id, files_config=[{"filename": rel_path}], config={
                "theme": "default", "page_size": config.get("page_size", "a4"),
                "orientation": config.get("orientation", "portrait"),
                "margin_preset": config.get("margin_preset", "medium"),
            })
            for item in result.get("results", []):
                if item.get("status") == "success" and item.get("pdf_filename"):
                    return Paths.request_output(request_id) / item["pdf_filename"]
            raise ValueError("Markdown conversion failed.")

        # Text / RTF to HTML to PDF
        txt_path = Paths.request_upload(request_id) / rel_path
        if not txt_path.exists():
            txt_path = Paths.request_temp(request_id) / "zip_work" / rel_path

        raw = txt_path.read_text(encoding="utf-8", errors="replace")
        import html as _html
        escaped = _html.escape(raw)
        html_content = (
            f"<html><head><meta charset='utf-8'>"
            f"<style>body{{font-family:monospace;white-space:pre-wrap;margin:40px;}}</style>"
            f"</head><body><pre>{escaped}</pre></body></html>"
        )
        from app.Convert_to_pdf_services.html_to_pdf_service import html_to_pdf_service
        result = await html_to_pdf_service.process(
            request_id=request_id, input_type="html", content=html_content,
            page_size=config.get("page_size", "a4"), orientation=config.get("orientation", "portrait"),
            margin_preset=config.get("margin_preset", "medium"),
            custom_margin_top="10", custom_margin_right="10", custom_margin_bottom="10", custom_margin_left="10",
            custom_page_width="210", custom_page_height="297", custom_page_unit="mm",
            print_background=False, header_text="", footer_text="", page_numbers=False,
            title=filename, author="", subject="", keywords="", password="",
            output_filename=Path(filename).stem,
        )
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError("Text conversion failed.")

    async def _convert_csv(self, rel_path: str, request_id: str, config: Dict[str, Any]) -> Path:
        from app.Convert_to_pdf_services.csv_to_pdf_service import csv_to_pdf_service
        result = await csv_to_pdf_service.process(request_id=request_id, filename=rel_path, config={
            "page_size": config.get("page_size", "a4"), "orientation": config.get("orientation", "portrait"),
            "margin_preset": config.get("margin_preset", "medium"),
        })
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError("CSV conversion failed.")

    async def _convert_json(self, rel_path: str, request_id: str, config: Dict[str, Any]) -> Path:
        from app.Convert_to_pdf_services.json_to_pdf_service import json_to_pdf_service
        p = Paths.request_upload(request_id) / rel_path
        if not p.exists():
            p = Paths.request_temp(request_id) / "zip_work" / rel_path
        content = p.read_text(encoding="utf-8", errors="replace")
        result = await json_to_pdf_service.process(request_id=request_id, filename=rel_path, content=content, config={
            "mode": "table", "page_size": config.get("page_size", "a4"),
            "orientation": config.get("orientation", "portrait"),
            "margin_preset": config.get("margin_preset", "medium"),
        })
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError("JSON conversion failed.")

    async def _convert_xml(self, rel_path: str, request_id: str, config: Dict[str, Any]) -> Path:
        from app.Convert_to_pdf_services.xml_to_pdf_service import xml_to_pdf_service
        result = await xml_to_pdf_service.process(request_id=request_id, files_config=[{"filename": rel_path}], config={
            "page_size": config.get("page_size", "a4"), "orientation": config.get("orientation", "portrait"),
            "margin_preset": config.get("margin_preset", "medium"),
        })
        for item in result.get("results", []):
            if item.get("status") == "success" and item.get("pdf_filename"):
                return Paths.request_output(request_id) / item["pdf_filename"]
        raise ValueError("XML conversion failed.")

    async def _convert_html(self, rel_path: str, request_id: str, config: Dict[str, Any]) -> Path:
        from app.Convert_to_pdf_services.html_to_pdf_service import html_to_pdf_service
        p = Paths.request_upload(request_id) / rel_path
        if not p.exists():
            p = Paths.request_temp(request_id) / "zip_work" / rel_path
        content = p.read_text(encoding="utf-8", errors="replace")
        result = await html_to_pdf_service.process(
            request_id=request_id, input_type="html", content=content,
            page_size=config.get("page_size", "a4"), orientation=config.get("orientation", "portrait"),
            margin_preset=config.get("margin_preset", "medium"),
            custom_margin_top="10", custom_margin_right="10", custom_margin_bottom="10", custom_margin_left="10",
            custom_page_width="210", custom_page_height="297", custom_page_unit="mm",
            print_background=True, header_text="", footer_text="", page_numbers=False,
            title=Path(rel_path).name, author="", subject="", keywords="", password="",
            output_filename=Path(rel_path).stem,
        )
        pdf_name = result.get("filename")
        if pdf_name:
            return Paths.request_output(request_id) / pdf_name
        raise ValueError("HTML conversion failed.")

    # ── PDF Merging ───────────────────────────────────────────────────

    def _merge_pdfs(self, pdf_paths: List[Path], output_file: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge a list of PDF files into a single output PDF."""
        writer = PdfWriter()
        total_pages = 0

        for pdf_path in pdf_paths:
            try:
                reader = PdfReader(str(pdf_path))
                for page in reader.pages:
                    writer.add_page(page)
                    total_pages += 1
            except Exception as exc:
                logger.warning("Skipping unreadable PDF %s: %s", pdf_path.name, exc)

        if total_pages == 0:
            raise ValueError("No valid pages were found in converted files.")

        title = config.get("pdf_title", "") or "Converted ZIP Document"
        author = config.get("pdf_author", "")
        writer.add_metadata({
            "/Title": title,
            "/Author": author,
            "/Producer": "PDF Backend - ZIP to PDF",
        })

        with open(output_file, "wb") as fh:
            writer.write(fh)

        return {
            "path": output_file,
            "page_count": total_pages,
        }

    # ── Analysis Summary Builder ──────────────────────────────────────

    @staticmethod
    def _build_analysis(manifest: List[Dict], zip_filename: str) -> Dict[str, Any]:
        categories: Dict[str, List[Dict]] = {}
        folders: Dict[str, int] = {}

        for f in manifest:
            cat = f["category"]
            categories.setdefault(cat, []).append(f)
            folder = f.get("folder", "")
            if folder:
                folders[folder] = folders.get(folder, 0) + 1

        total = len(manifest)
        supported = sum(1 for f in manifest if f["supported"])
        unsupported = total - supported

        summary_by_cat = {}
        for cat, cat_files in categories.items():
            summary_by_cat[cat] = {
                "label": CATEGORY_LABELS.get(cat, cat),
                "count": len(cat_files),
                "supported": cat != CATEGORY_UNSUPPORTED,
            }

        zip_stem = Path(zip_filename).stem
        default_out_name = f"{zip_stem}.pdf" if zip_stem else "converted_from_zip.pdf"

        return {
            "zip_filename": zip_filename,
            "default_output_filename": default_out_name,
            "total_files": total,
            "total_folders": len(folders),
            "supported_count": supported,
            "unsupported_count": unsupported,
            "folders": list(folders.keys()),
            "files": manifest,
            "categories": summary_by_cat,
        }


zip_to_pdf_service = ZipToPdfService()
