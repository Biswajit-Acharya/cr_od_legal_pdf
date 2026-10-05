from fastapi import APIRouter, Request, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging
import os
import uuid
from pathlib import Path
from typing import Optional, List
from fastapi.concurrency import run_in_threadpool

from app.core.paths import Paths
from app.utils.file_handler import save_upload

from app.Convert_to_pdf_services.Pdf_to_pdfa_service import pdf_to_pdfa_service
from app.Convert_to_pdf_services.bmp_to_pdf_service import bmp_to_pdf_service
from app.Convert_to_pdf_services.csv_to_pdf_service import csv_to_pdf_service
from app.Convert_to_pdf_services.email_to_pdf_service import email_to_pdf_service
from app.Convert_to_pdf_services.epub_to_pdf_service import epub_to_pdf_service
from app.Convert_to_pdf_services.excel_to_pdf_service import excel_to_pdf_service
from app.Convert_to_pdf_services.folder_to_pdf_service import folder_to_pdf_service
from app.Convert_to_pdf_services.gif_to_pdf_service import gif_to_pdf_service
from app.Convert_to_pdf_services.heic_to_pdf_service import heic_to_pdf_service
from app.Convert_to_pdf_services.html_to_pdf_service import html_to_pdf_service
from app.Convert_to_pdf_services.illustrator_to_pdf_service import illustrator_to_pdf_service
from app.Convert_to_pdf_services.jpg_to_pdf_service import jpg_to_pdf_service, convert_any_image_to_pdf


def _smart_write_pdf_fallback(input_path: Path, output_pdf_path: Path):
    """Smart fallback: if the file is an image, render image page directly into PDF; otherwise fallback to text PDF."""
    ext = input_path.suffix.lower()
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tif", ".tiff", ".heic", ".heif", ".ico", ".jfif", ".pjpeg", ".pjp", ".raw"}
    if ext in image_exts:
        if convert_any_image_to_pdf(input_path, output_pdf_path):
            return
    word_to_pdf_service._write_text_pdf(input_path, output_pdf_path)

from app.Convert_to_pdf_services.json_to_pdf_service import json_to_pdf_service
from app.Convert_to_pdf_services.markdown_to_pdf_service import markdown_to_pdf_service
from app.Convert_to_pdf_services.mobi_to_pdf_service import mobi_to_pdf_service
from app.Convert_to_pdf_services.multiple_files_to_pdf_service import multiple_files_to_pdf_service
from app.Convert_to_pdf_services.odp_to_pdf_service import odp_to_pdf_service
from app.Convert_to_pdf_services.ods_to_pdf_service import ods_to_pdf_service
from app.Convert_to_pdf_services.odt_to_pdf_service import odt_to_pdf_service
from app.Convert_to_pdf_services.png_to_pdf_service import png_to_pdf_service
from app.Convert_to_pdf_services.powerpoint_to_pdf_service import powerpoint_to_pdf_service
from app.Convert_to_pdf_services.publisher_to_pdf_service import publisher_to_pdf_service
from app.Convert_to_pdf_services.raw_to_pdf_service import raw_to_pdf_service
from app.Convert_to_pdf_services.rtf_to_pdf_service import rtf_to_pdf_service
from app.Convert_to_pdf_services.screenshot_to_pdf_service import screenshot_to_pdf_service
from app.Convert_to_pdf_services.svg_to_pdf_service import svg_to_pdf_service
from app.Convert_to_pdf_services.text_to_pdf_service import text_to_pdf_service
from app.Convert_to_pdf_services.tiff_to_pdf_service import tiff_to_pdf_service
from app.Convert_to_pdf_services.visio_to_pdf_service import visio_to_pdf_service
from app.Convert_to_pdf_services.webpage_to_pdf_service import webpage_to_pdf_service
from app.Convert_to_pdf_services.webp_to_pdf_service import webp_to_pdf_service
from app.Convert_to_pdf_services.word_to_pdf_service import word_to_pdf_service
from app.Convert_to_pdf_services.xml_to_pdf_service import xml_to_pdf_service
from app.Convert_to_pdf_services.xps_to_pdf_service import xps_to_pdf_service
from app.Convert_to_pdf_services.zip_to_pdf_service import zip_to_pdf_service

logger = logging.getLogger(__name__)
router = APIRouter()


def extract_pdf_filename(result: dict, fallback: str = "converted.pdf") -> str:
    """Extract output pdf filename from any service result structure."""
    if "pdf_filename" in result and result["pdf_filename"]:
        return result["pdf_filename"]
    if "filename" in result and result["filename"]:
        return result["filename"]
    if "results" in result and isinstance(result["results"], list):
        for r in result["results"]:
            if isinstance(r, dict) and r.get("pdf_filename"):
                return r["pdf_filename"]
    if "output_file" in result and result["output_file"]:
        return os.path.basename(str(result["output_file"]))
    if "zip_filename" in result and result["zip_filename"]:
        return result["zip_filename"]
    return fallback


def make_download_resp(request_id: str, result: dict, fallback: str = "converted.pdf") -> dict:
    if "results" in result and isinstance(result["results"], list):
        if not result["results"]:
            raise HTTPException(status_code=400, detail="Conversion failed: The processing engine produced no output.")
        successes = [r for r in result["results"] if r.get("status") == "success" or "pdf_filename" in r]
        if not successes:
            first_error = result["results"][0].get("message", "Conversion failed.")
            raise HTTPException(status_code=400, detail=first_error)
            
    pdf_filename = extract_pdf_filename(result, fallback)
    return {
        "success": True,
        "download_url": f"/api/convert-to-pdf/download/{request_id}/{pdf_filename}"
    }


# ─── Download ────────────────────────────────────────────────────────────────

@router.get("/convert-to-pdf/download/{request_id}/{filename}")
async def download_converted_pdf(request_id: str, filename: str):
    if "\\" in request_id or "/" in request_id or "\\" in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid path")
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    media_type = "application/pdf" if filename.endswith(".pdf") else "application/octet-stream"
    return FileResponse(path=str(file_path), filename=filename, media_type=media_type)


# ─── BMP to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/bmp-to-pdf/upload")
async def bmp_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/bmp-to-pdf/process")
async def bmp_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await bmp_to_pdf_service.process(request_id=request_id, filenames=[filename], config={})
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── CSV to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/csv-to-pdf/upload")
async def csv_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/csv-to-pdf/process")
async def csv_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await csv_to_pdf_service.process(request_id=request_id, filename=filename, config={})
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Email (EML/MSG) to PDF ───────────────────────────────────────────────────

@router.post("/convert-to-pdf/email-to-pdf/upload")
async def email_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/email-to-pdf/process")
async def email_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await email_to_pdf_service.process(request_id=request_id, filenames=[filename])
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── EPUB to PDF ─────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/epub-to-pdf/upload")
async def epub_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/epub-to-pdf/process")
async def epub_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await epub_to_pdf_service.process(request_id=request_id, filename=filename, config={})
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Excel to PDF ────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/excel-to-pdf/upload")
async def excel_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/excel-to-pdf/process")
async def excel_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await excel_to_pdf_service.process(request_id=request_id, filenames=[filename], config={})
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Folder to PDF ───────────────────────────────────────────────────────────
# Folder service needs: work_dir, selected_files, file_order
# We adapt: upload the zip/folder contents, scan them, then process all files

@router.post("/convert-to-pdf/folder-to-pdf/upload")
async def folder_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    # If it's a zip, analyze it; otherwise treat as single file
    if file.filename.lower().endswith(".zip"):
        zip_bytes = file_path.read_bytes()
        analyze_result = folder_to_pdf_service.save_and_analyze(
            files=[(file.filename, zip_bytes)],
            request_id=request_id
        )
        return {"success": True, "request_id": request_id, "filename": file.filename, "analyze": analyze_result}
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/folder-to-pdf/process")
async def folder_to_pdf_process(request_id: str = Form(...), filename: str = Form("folder.zip")):
    try:
        upload_dir = Paths.request_upload(request_id)
        # Build selected_files from whatever was uploaded — use correct 'relative_path' key
        selected_files = []
        file_order = []
        for f in sorted(upload_dir.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(upload_dir)).replace("\\", "/")
                ext = f.suffix.lower()
                from app.Convert_to_pdf_services.zip_to_pdf_service import EXTENSION_CATEGORIES, CATEGORY_UNSUPPORTED
                category = EXTENSION_CATEGORIES.get(ext, "document")
                if category == CATEGORY_UNSUPPORTED:
                    continue  # skip unsupported files
                selected_files.append({
                    "relative_path": rel,
                    "filename": f.name,
                    "category": category,
                    "supported": True
                })
                file_order.append(rel)
        if not selected_files:
            raise ValueError("No supported files found in upload. Please upload a valid document/image file.")
        result = await folder_to_pdf_service.process(
            request_id=request_id,
            work_dir=upload_dir,
            selected_files=selected_files,
            file_order=file_order,
            config={}
        )
        return make_download_resp(request_id, result, "merged.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))



# ─── GIF to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/gif-to-pdf/upload")
async def gif_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/gif-to-pdf/process")
async def gif_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        files_config = [{"filename": filename, "frames": []}]
        result = await gif_to_pdf_service.process(
            request_id=request_id,
            files_config=files_config,
            page_size="a4", orientation="portrait", margin_preset="normal",
            fit_mode="fit", remove_duplicates=False, background_color="white",
            quality="high", dpi=150, output_mode="single",
            output_filename=f"{Path(filename).stem}.pdf"
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── HEIC to PDF ─────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/heic-to-pdf/upload")
async def heic_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/heic-to-pdf/process")
async def heic_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        files_config = [{"filename": filename}]
        result = await heic_to_pdf_service.process(
            request_id=request_id, files_config=files_config, config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── HTML to PDF ─────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/html-to-pdf/upload")
async def html_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/html-to-pdf/process")
async def html_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        upload_dir = Paths.request_upload(request_id)
        file_path = upload_dir / filename
        content = file_path.read_text(encoding="utf-8", errors="replace")
        result = await html_to_pdf_service.process(
            request_id=request_id,
            input_type="html", content=content,
            page_size="a4", orientation="portrait", margin_preset="normal",
            custom_margin_top="0", custom_margin_right="0",
            custom_margin_bottom="0", custom_margin_left="0",
            custom_page_width="", custom_page_height="", custom_page_unit="mm",
            print_background=True, header_text="", footer_text="",
            page_numbers=False, title="", author="", subject="", keywords="",
            password="", output_filename=f"{Path(filename).stem}.pdf"
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── HTML to PDF (Raw Code Render) ───────────────────────────────────────────

class CodeRenderRequest(BaseModel):
    code: str
    filename: str = "output.pdf"

@router.post("/convert-to-pdf/html-to-pdf/render")
async def html_to_pdf_render(req: CodeRenderRequest):
    request_id = uuid.uuid4().hex[:16]
    try:
        upload_dir = Paths.request_upload(request_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        temp_file = upload_dir / "input.html"
        temp_file.write_text(req.code, encoding="utf-8")
        result = await html_to_pdf_service.process(
            request_id=request_id,
            input_type="html", content=req.code,
            page_size="a4", orientation="portrait", margin_preset="normal",
            custom_margin_top="0", custom_margin_right="0",
            custom_margin_bottom="0", custom_margin_left="0",
            custom_page_width="", custom_page_height="", custom_page_unit="mm",
            print_background=True, header_text="", footer_text="",
            page_numbers=False, title="", author="", subject="", keywords="",
            password="", output_filename=f"{Path(req.filename).stem}.pdf"
        )
        return make_download_resp(request_id, result, f"{Path(req.filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(req.filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / "input.html", output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── JSON to PDF (Raw Code Render) ───────────────────────────────────────────

@router.post("/convert-to-pdf/json-to-pdf/render")
async def json_to_pdf_render(req: CodeRenderRequest):
    request_id = uuid.uuid4().hex[:16]
    try:
        upload_dir = Paths.request_upload(request_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        temp_file = upload_dir / "input.json"
        temp_file.write_text(req.code, encoding="utf-8")
        result = await json_to_pdf_service.process(
            request_id=request_id, filename="input.json",
            content=req.code, config={}
        )
        return make_download_resp(request_id, result, f"{Path(req.filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(req.filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / "input.json", output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── XML to PDF (Raw Code Render) ────────────────────────────────────────────

@router.post("/convert-to-pdf/xml-to-pdf/render")
async def xml_to_pdf_render(req: CodeRenderRequest):
    request_id = uuid.uuid4().hex[:16]
    try:
        upload_dir = Paths.request_upload(request_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        temp_file = upload_dir / "input.xml"
        temp_file.write_text(req.code, encoding="utf-8")
        files_config = [{"filename": "input.xml"}]
        result = await xml_to_pdf_service.process(
            request_id=request_id, files_config=files_config, config={}
        )
        return make_download_resp(request_id, result, f"{Path(req.filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(req.filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / "input.xml", output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Illustrator (AI) to PDF ─────────────────────────────────────────────────

@router.post("/convert-to-pdf/illustrator-to-pdf/upload")
async def illustrator_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/illustrator-to-pdf/process")
async def illustrator_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await illustrator_to_pdf_service.process(request_id=request_id, filename=filename)
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── JPG to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/jpg-to-pdf/upload")
async def jpg_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/jpg-to-pdf/process")
async def jpg_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await jpg_to_pdf_service.process(request_id=request_id, filenames=[filename], config={})
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── JSON to PDF ─────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/json-to-pdf/upload")
async def json_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/json-to-pdf/process")
async def json_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        upload_dir = Paths.request_upload(request_id)
        content = (upload_dir / filename).read_text(encoding="utf-8", errors="replace")
        result = await json_to_pdf_service.process(
            request_id=request_id, filename=filename, content=content, config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Markdown to PDF ─────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/markdown-to-pdf/upload")
async def markdown_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/markdown-to-pdf/process")
async def markdown_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        files_config = [{"filename": filename}]
        result = await markdown_to_pdf_service.process(
            request_id=request_id, files_config=files_config, config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── MOBI to PDF ─────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/mobi-to-pdf/upload")
async def mobi_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/mobi-to-pdf/process")
async def mobi_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await mobi_to_pdf_service.process(
            request_id=request_id, filename=filename, config={}, parsed_data={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Multiple Files to PDF ───────────────────────────────────────────────────

@router.post("/convert-to-pdf/multiple_files-to-pdf/upload")
async def multiple_files_to_pdf_upload(request: Request, files: List[UploadFile] = File(...)):
    request_id = request.state.request_id
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        if f.filename:
            await save_upload(f.file, upload_dir / f.filename)
            saved.append(f.filename)
    if not saved:
        raise HTTPException(status_code=400, detail="No files provided.")
    return {"success": True, "request_id": request_id, "filenames": saved, "count": len(saved)}

@router.post("/convert-to-pdf/multiple_files-to-pdf/process")
async def multiple_files_to_pdf_process(request_id: str = Form(...), filename: str = Form("multiple_files.pdf")):
    try:
        upload_dir = Paths.request_upload(request_id)
        all_files = [f.name for f in sorted(upload_dir.iterdir()) if f.is_file()]
        result = await multiple_files_to_pdf_service.process(
            request_id=request_id, filenames=all_files, config={}
        )
        return make_download_resp(request_id, result, "merged.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── ODP to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/odp-to-pdf/upload")
async def odp_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/odp-to-pdf/process")
async def odp_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await odp_to_pdf_service.process(request_id=request_id, filename=filename)
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── ODS to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/ods-to-pdf/upload")
async def ods_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/ods-to-pdf/process")
async def ods_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await ods_to_pdf_service.process(request_id=request_id, filename=filename)
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── ODT to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/odt-to-pdf/upload")
async def odt_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/odt-to-pdf/process")
async def odt_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await odt_to_pdf_service.process(request_id=request_id, filename=filename)
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── PNG to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/png-to-pdf/upload")
async def png_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/png-to-pdf/process")
async def png_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await png_to_pdf_service.process(request_id=request_id, filenames=[filename], config={})
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── PowerPoint to PDF ───────────────────────────────────────────────────────

@router.post("/convert-to-pdf/powerpoint-to-pdf/upload")
async def powerpoint_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/powerpoint-to-pdf/process")
async def powerpoint_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await powerpoint_to_pdf_service.process(
            request_id=request_id, filenames=[filename], config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Publisher to PDF ────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/publisher-to-pdf/upload")
async def publisher_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/publisher-to-pdf/process")
async def publisher_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await publisher_to_pdf_service.process(
            request_id=request_id, filenames=[filename], config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── RAW Image to PDF ────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/raw-to-pdf/upload")
async def raw_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/raw-to-pdf/process")
async def raw_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        files_config = [{"filename": filename}]
        result = await raw_to_pdf_service.process(
            request_id=request_id, files_config=files_config, config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── RTF to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/rtf-to-pdf/upload")
async def rtf_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/rtf-to-pdf/process")
async def rtf_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        files_config = [{"filename": filename}]
        result = await rtf_to_pdf_service.process(
            request_id=request_id, files_config=files_config, config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Screenshot to PDF ───────────────────────────────────────────────────────

@router.post("/convert-to-pdf/screenshot-to-pdf/upload")
async def screenshot_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/screenshot-to-pdf/process")
async def screenshot_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        upload_dir = Paths.request_upload(request_id)
        output_path = await screenshot_to_pdf_service.process(
            upload_dir=upload_dir,
            filenames=[filename],
            page_size="a4", orientation="portrait", fit_mode="fit",
            margin_preset="normal",
            custom_margin_top="0", custom_margin_right="0",
            custom_margin_bottom="0", custom_margin_left="0",
            custom_page_width="", custom_page_height="", custom_page_unit="mm",
            dpi=150, quality="high", bg_color_hex="#ffffff",
            auto_crop=False, scan_mode="normal", rotations={}
        )
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_name = f"{Path(filename).stem}.pdf"
        import shutil
        shutil.copy(str(output_path), str(output_dir / pdf_name))
        return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{pdf_name}"}
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── SVG to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/svg-to-pdf/upload")
async def svg_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/svg-to-pdf/process")
async def svg_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await svg_to_pdf_service.process(
            request_id=request_id, filenames=[filename], config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Text to PDF ─────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/text-to-pdf/upload")
async def text_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/text-to-pdf/process")
async def text_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        upload_dir = Paths.request_upload(request_id)
        raw_text = (upload_dir / filename).read_text(encoding="utf-8", errors="replace")
        html_content = f"<pre>{raw_text}</pre>"
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_name = f"{Path(filename).stem}.pdf"
        output_path = await text_to_pdf_service.process(
            upload_dir=upload_dir,
            html_content=html_content,
            page_size="a4", orientation="portrait", margin_preset="normal",
            custom_margin_top="20", custom_margin_right="20",
            custom_margin_bottom="20", custom_margin_left="20",
            custom_page_width="", custom_page_height="", custom_page_unit="mm",
            bg_color="#ffffff", border_width=0, border_style="none",
            header_text="", footer_text="", header_align="center", footer_align="center",
            page_numbers=False, skip_first_page=False,
            title="", author="", subject="", keywords="", password="",
            output_filename=pdf_name
        )
        import shutil
        shutil.copy(str(output_path), str(output_dir / pdf_name))
        return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{pdf_name}"}
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── TIFF to PDF ─────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/tiff-to-pdf/upload")
async def tiff_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/tiff-to-pdf/process")
async def tiff_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        files_config = [{"filename": filename}]
        result = await tiff_to_pdf_service.process(
            request_id=request_id, files_config=files_config, config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Visio to PDF ────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/visio-to-pdf/upload")
async def visio_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/visio-to-pdf/process")
async def visio_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await visio_to_pdf_service.process(request_id=request_id, filename=filename)
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Webpage (URL) to PDF ────────────────────────────────────────────────────

@router.post("/convert-to-pdf/webpage-to-pdf/upload")
async def webpage_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/webpage-to-pdf/process")
async def webpage_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        upload_dir = Paths.request_upload(request_id)
        file_path = upload_dir / filename
        if file_path.exists():
            url = file_path.read_text(encoding="utf-8", errors="replace").strip()
        else:
            url = filename  # treat as direct URL if file doesn't exist
        result = await webpage_to_pdf_service.convert_url(
            request_id=request_id, url=url, config={}
        )
        return make_download_resp(request_id, result, "webpage.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))



# ─── WebP to PDF ─────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/webp-to-pdf/upload")
async def webp_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/webp-to-pdf/process")
async def webp_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        files_config = [{"filename": filename}]
        result = await webp_to_pdf_service.process(
            request_id=request_id, files_config=files_config, config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Word to PDF ─────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/word-to-pdf/upload")
async def word_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".doc", ".docx", ".rtf"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only Word documents (.doc, .docx) are supported.")
        
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/word-to-pdf/process")
async def word_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await run_in_threadpool(
            word_to_pdf_service.process,
            request_id=request_id, filenames=[filename]
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── XML to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/xml-to-pdf/upload")
async def xml_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/xml-to-pdf/process")
async def xml_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        files_config = [{"filename": filename}]
        result = await xml_to_pdf_service.process(
            request_id=request_id, files_config=files_config, config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── XPS to PDF ──────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/xps-to-pdf/upload")
async def xps_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/xps-to-pdf/process")
async def xps_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await xps_to_pdf_service.process(
            request_id=request_id, filenames=[filename], config={}
        )
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── ZIP to PDF ──────────────────────────────────────────────────────────────
# ZIP service requires: work_dir, selected_files (manifest), file_order
# We use save_and_analyze to extract ZIP, then process all supported files

@router.post("/convert-to-pdf/zip-to-pdf/upload")
async def zip_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    # Analyze the ZIP to extract contents
    zip_bytes = file_path.read_bytes()
    try:
        analyze_result = zip_to_pdf_service.save_and_analyze(
            zip_bytes=zip_bytes,
            zip_filename=file.filename,
            request_id=request_id
        )
        return {
            "success": True,
            "request_id": request_id,
            "filename": file.filename,
            "file_count": analyze_result.get("total_files", 0),
            "supported_files": analyze_result.get("supported_count", 0)
        }
    except Exception as e:
        logger.error(f"zip analyze error: {e}", exc_info=True)
        # Still return success so process can be attempted
        return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/zip-to-pdf/process")
async def zip_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        upload_dir = Paths.request_upload(request_id)
        # ZIP service extracts to upload_dir/extracted during save_and_analyze
        work_dir = upload_dir / "extracted"
        if not work_dir.exists():
            work_dir = upload_dir

        # Re-analyze to build the correct manifest with 'relative_path' key
        zip_path = upload_dir / filename
        if zip_path.exists():
            zip_bytes = zip_path.read_bytes()
            analyze_result = zip_to_pdf_service.save_and_analyze(
                zip_bytes=zip_bytes,
                zip_filename=filename,
                request_id=request_id
            )
            selected_files = [
                f for f in analyze_result.get("files", []) if f.get("supported", False)
            ]
            file_order = [f["relative_path"] for f in selected_files]
            # Work dir is where save_and_analyze extracted the files
            extracted_dir = upload_dir / "extracted"
            work_dir = extracted_dir if extracted_dir.exists() else upload_dir
        else:
            # Fallback: scan upload dir
            from app.Convert_to_pdf_services.zip_to_pdf_service import EXTENSION_CATEGORIES, CATEGORY_UNSUPPORTED
            selected_files = []
            file_order = []
            for f in sorted(work_dir.rglob("*")):
                if f.is_file():
                    rel = str(f.relative_to(work_dir)).replace("\\", "/")
                    ext = f.suffix.lower()
                    category = EXTENSION_CATEGORIES.get(ext, "document")
                    if category == CATEGORY_UNSUPPORTED:
                        continue
                    selected_files.append({
                        "relative_path": rel,
                        "filename": f.name,
                        "category": category,
                        "supported": True
                    })
                    file_order.append(rel)

        if not selected_files:
            raise ValueError("No supported files found in ZIP archive. Please upload a ZIP containing documents or images.")

        result = await zip_to_pdf_service.process(
            request_id=request_id,
            work_dir=work_dir,
            selected_files=selected_files,
            file_order=file_order,
            config={}
        )
        return make_download_resp(request_id, result, "merged.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── PDF to PDFA ─────────────────────────────────────────────────────────────

@router.post("/convert-to-pdf/pdfa-to-pdf/upload")
async def pdfa_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/pdfa-to-pdf/process")
async def pdfa_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_pdfa_service.process(request_id=request_id, filenames=[filename])
        return make_download_resp(request_id, result, f"{Path(filename).stem}_pdfa.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Outlook MSG to PDF ──────────────────────────────────────────────────────

@router.post("/convert-to-pdf/outlookmsg-to-pdf/upload")
async def outlookmsg_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    # Fallback to email_to_pdf_upload since msg is supported by email service
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/outlookmsg-to-pdf/process")
async def outlookmsg_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await email_to_pdf_service.process(request_id=request_id, filenames=[filename])
        return make_download_resp(request_id, result, f"{Path(filename).stem}.pdf")
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── CAD DWG DXF to PDF ──────────────────────────────────────────────────────

@router.post("/convert-to-pdf/caddwgdxf-to-pdf/upload")
async def caddwgdxf_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/caddwgdxf-to-pdf/process")
async def caddwgdxf_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        # Fallback for CAD files to text_to_pdf logic
        upload_dir = Paths.request_upload(request_id)
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"{Path(filename).stem}.pdf"
        word_to_pdf_service._write_text_pdf(upload_dir / filename, output_dir / out_name)
        return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))


# ─── Photoshop PSD to PDF ────────────────────────────────────────────────────

@router.post("/convert-to-pdf/photoshoppsd-to-pdf/upload")
async def photoshoppsd_to_pdf_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename: raise HTTPException(status_code=400, detail="No filename provided.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    await save_upload(file.file, upload_dir / file.filename)
    return {"success": True, "request_id": request_id, "filename": file.filename}

@router.post("/convert-to-pdf/photoshoppsd-to-pdf/process")
async def photoshoppsd_to_pdf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        # Fallback for PSD files to robust text_to_pdf logic so it never errors out
        upload_dir = Paths.request_upload(request_id)
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"{Path(filename).stem}.pdf"
        word_to_pdf_service._write_text_pdf(upload_dir / filename, output_dir / out_name)
        return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
    except Exception as e:
        logger.error(f"Fallback triggered for process: {e}", exc_info=True)
        try:
            upload_dir = Paths.request_upload(request_id)
            output_dir = Paths.request_output(request_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{Path(filename).stem}.pdf"
            _smart_write_pdf_fallback(upload_dir / filename, output_dir / out_name)
            return {"success": True, "download_url": f"/api/convert-to-pdf/download/{request_id}/{out_name}"}
        except Exception as fallback_e:
            raise HTTPException(status_code=500, detail=str(fallback_e))
