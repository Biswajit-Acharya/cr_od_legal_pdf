from fastapi import APIRouter, Request, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from typing import Dict, Any, List
import logging
import io
import zipfile
from pathlib import Path
import re

from app.core.paths import Paths
from app.utils.file_handler import save_upload
from app.convert_from_pdf_services.pdf_to_word_service import pdf_to_word_service
from app.convert_from_pdf_services.pdf_to_excel_service import pdf_to_excel_service
from app.convert_from_pdf_services.pdf_to_powerpoint_service import pdf_to_powerpoint_service
from app.convert_from_pdf_services.pdf_to_jpg_service import pdf_to_jpg_service
from app.convert_from_pdf_services.pdf_to_png_service import pdf_to_png_service
from app.convert_from_pdf_services.pdf_to_gif_service import pdf_to_gif_service
from app.convert_from_pdf_services.pdf_to_bmp_service import pdf_to_bmp_service
from app.convert_from_pdf_services.pdf_to_tiff_service import pdf_to_tiff_service
from app.convert_from_pdf_services.pdf_to_webp_service import pdf_to_webp_service
from app.convert_from_pdf_services.pdf_to_svg_service import pdf_to_svg_service
from app.convert_from_pdf_services.pdf_to_txt_service import pdf_to_txt_service
from app.convert_from_pdf_services.pdf_to_html_service import pdf_to_html_service
from app.convert_from_pdf_services.pdf_to_xml_service import pdf_to_xml_service
from app.convert_from_pdf_services.pdf_to_csv_service import pdf_to_csv_service
from app.convert_from_pdf_services.pdf_to_json_service import pdf_to_json_service
from app.convert_from_pdf_services.pdf_to_rtf_service import pdf_to_rtf_service
from app.convert_from_pdf_services.pdf_to_markdown_service import pdf_to_markdown_service
from app.convert_from_pdf_services.pdf_to_epub_service import pdf_to_epub_service
from app.convert_from_pdf_services.pdf_to_xps_service import pdf_to_xps_service
from app.convert_from_pdf_services.pdf_to_zip_service import pdf_to_zip_service
from app.convert_from_pdf_services.pdf_to_heic_service import pdf_to_heic_service
from app.convert_from_pdf_services.pdf_to_raw_image_service import pdf_to_raw_image_service
from app.convert_from_pdf_services.pdf_to_odt_service import pdf_to_odt_service
from app.convert_from_pdf_services.pdf_to_ods_service import pdf_to_ods_service
from app.convert_from_pdf_services.pdf_to_odp_service import pdf_to_odp_service
from app.convert_from_pdf_services.pdf_to_visio_service import pdf_to_visio_service
from app.convert_from_pdf_services.pdf_to_publisher_service import pdf_to_publisher_service
from app.convert_from_pdf_services.pdf_to_photoshop_service import pdf_to_photoshop_service
from app.convert_from_pdf_services.pdf_to_illustrator_service import pdf_to_illustrator_service
from app.convert_from_pdf_services.pdf_to_cad_service import pdf_to_cad_service
from app.convert_from_pdf_services.pdf_to_email_service import pdf_to_email_service
from app.convert_from_pdf_services.pdf_to_outlook_service import pdf_to_outlook_service

logger = logging.getLogger(__name__)

router = APIRouter()

# ==========================================
# API ROUTES (PDF to Word)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-word/upload")
async def pdf_to_word_upload(
    request: Request,
    file: UploadFile = File(...)
):
    """Upload a PDF document for conversion."""
    request_id = request.state.request_id
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf is supported.")
        
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save original file
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    
    return {
        "success": True,
        "request_id": request_id,
        "filename": file.filename,
        "size": file_path.stat().st_size,
    }

@router.post("/convert-from-pdf/pdf-to-word/process")
async def pdf_to_word_process(
    request_id: str = Form(...),
    filename: str = Form(...)
):
    """Process the uploaded PDF to Word."""
    try:
        # Default config for now, can be extended if UI sends more options
        config = {}
        result = await pdf_to_word_service.process(
            request_id=request_id,
            filename=filename,
            config=config
        )
        
        pdf_filename = result["pdf_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": pdf_filename,
            "download_url": f"/api/convert-from-pdf/pdf-to-word/download/{request_id}/{pdf_filename}",
            "view_url": f"/api/convert-from-pdf/pdf-to-word/view/{request_id}"
        }
    except Exception as e:
        logger.error(f"PDF to Word processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/convert-from-pdf/pdf-to-word/download/{request_id}/{filename}")
async def pdf_to_word_download(request_id: str, filename: str):
    """Download the converted Word file."""
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
        
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@router.get("/convert-from-pdf/pdf-to-word/view/{request_id}")
async def pdf_to_word_view(request_id: str):
    """View the Word file (downloads it)."""
    if re.search(r'[\\/]', request_id):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
        
    output_dir = Paths.request_output(request_id)
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
        
    docs = list(output_dir.glob("*.docx"))
    if not docs:
        raise HTTPException(status_code=404, detail="File not found")
        
    file_path = docs[0]
    
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content_disposition_type="inline"
    )


# ==========================================
# API ROUTES (PDF to Excel)
# ==========================================

def _pdf_upload_handler(request_id: str, file_path, filename: str, accepted_ext=".pdf"):
    """Shared helper: validate & save an uploaded PDF."""
    ext = Path(filename).suffix.lower()
    if ext != accepted_ext:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Only {accepted_ext} is supported.")
    return file_path


@router.post("/convert-from-pdf/pdf-to-excel/upload")
async def pdf_to_excel_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    if Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf is supported.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    return {"success": True, "request_id": request_id, "filename": file.filename, "size": file_path.stat().st_size}


@router.post("/convert-from-pdf/pdf-to-excel/process")
async def pdf_to_excel_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_excel_service.process(request_id=request_id, filename=filename)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "download_url": f"/api/convert-from-pdf/pdf-to-excel/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to Excel error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-excel/download/{request_id}/{filename}")
async def pdf_to_excel_download(request_id: str, filename: str):
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ==========================================
# API ROUTES (PDF to PowerPoint)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-powerpoint/upload")
async def pdf_to_powerpoint_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    if Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf is supported.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    return {"success": True, "request_id": request_id, "filename": file.filename, "size": file_path.stat().st_size}


@router.post("/convert-from-pdf/pdf-to-powerpoint/process")
async def pdf_to_powerpoint_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_powerpoint_service.process(request_id=request_id, filename=filename)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "download_url": f"/api/convert-from-pdf/pdf-to-powerpoint/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to PowerPoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-powerpoint/download/{request_id}/{filename}")
async def pdf_to_powerpoint_download(request_id: str, filename: str):
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


# ==========================================
# API ROUTES (PDF to JPG)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-jpg/upload")
async def pdf_to_jpg_upload(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    if Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf is supported.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    return {"success": True, "request_id": request_id, "filename": file.filename, "size": file_path.stat().st_size}


@router.post("/convert-from-pdf/pdf-to-jpg/process")
async def pdf_to_jpg_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_jpg_service.process(request_id=request_id, filename=filename)
        images = result["images"]
        zip_filename = result.get("zip_filename")

        image_urls = [
            f"/api/convert-from-pdf/pdf-to-jpg/download/{request_id}/{img}"
            for img in images
        ]
        zip_url = (
            f"/api/convert-from-pdf/pdf-to-jpg/download/{request_id}/{zip_filename}"
            if zip_filename else None
        )

        return {
            "success": True,
            "request_id": request_id,
            "total_pages": result["total_pages"],
            "images": images,
            "image_urls": image_urls,
            "zip_url": zip_url,
        }
    except Exception as e:
        logger.error(f"PDF to JPG error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-jpg/download/{request_id}/{filename}")
async def pdf_to_jpg_download(request_id: str, filename: str):
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    ext = Path(filename).suffix.lower()
    media = "application/zip" if ext == ".zip" else "image/jpeg"
    return FileResponse(path=str(file_path), filename=filename, media_type=media)


# ==========================================
# HELPER: shared image-format upload/process/download
# ==========================================

def _media_type_for(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".zip": "application/zip",
    }.get(ext, "application/octet-stream")


async def _upload_pdf(request: Request, file: UploadFile) -> dict:
    request_id = request.state.request_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    if Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf is supported.")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    return {"success": True, "request_id": request_id, "filename": file.filename, "size": file_path.stat().st_size}


# ==========================================
# API ROUTES (PDF to PNG)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-png/upload")
async def pdf_to_png_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-png/process")
async def pdf_to_png_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_png_service.process(request_id=request_id, filename=filename)
        images = result["images"]
        zip_filename = result.get("zip_filename")
        image_urls = [f"/api/convert-from-pdf/pdf-to-png/download/{request_id}/{img}" for img in images]
        zip_url = f"/api/convert-from-pdf/pdf-to-png/download/{request_id}/{zip_filename}" if zip_filename else None
        return {"success": True, "request_id": request_id, "total_pages": result["total_pages"], "images": images, "image_urls": image_urls, "zip_url": zip_url, "filename": zip_filename if zip_filename else (images[0] if images else None)}
    except Exception as e:
        logger.error(f"PDF to PNG error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-png/download/{request_id}/{filename}")
async def pdf_to_png_download(request_id: str, filename: str):
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename, media_type=_media_type_for(filename))


# ==========================================
# API ROUTES (PDF to GIF)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-gif/upload")
async def pdf_to_gif_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-gif/process")
async def pdf_to_gif_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_gif_service.process(request_id=request_id, filename=filename)
        images = result["images"]
        zip_filename = result.get("zip_filename")
        image_urls = [f"/api/convert-from-pdf/pdf-to-gif/download/{request_id}/{img}" for img in images]
        zip_url = f"/api/convert-from-pdf/pdf-to-gif/download/{request_id}/{zip_filename}" if zip_filename else None
        animated_url = f"/api/convert-from-pdf/pdf-to-gif/download/{request_id}/{images[0]}" if result.get("animated") else None
        return {"success": True, "request_id": request_id, "total_pages": result["total_pages"], "images": images, "image_urls": image_urls, "zip_url": zip_url, "animated": result.get("animated", False), "animated_url": animated_url, "filename": zip_filename if zip_filename else (images[0] if images else None)}
    except Exception as e:
        logger.error(f"PDF to GIF error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-gif/download/{request_id}/{filename}")
async def pdf_to_gif_download(request_id: str, filename: str):
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename, media_type=_media_type_for(filename))


# ==========================================
# API ROUTES (PDF to BMP)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-bmp/upload")
async def pdf_to_bmp_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-bmp/process")
async def pdf_to_bmp_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_bmp_service.process(request_id=request_id, filename=filename)
        images = result["images"]
        zip_filename = result.get("zip_filename")
        image_urls = [f"/api/convert-from-pdf/pdf-to-bmp/download/{request_id}/{img}" for img in images]
        zip_url = f"/api/convert-from-pdf/pdf-to-bmp/download/{request_id}/{zip_filename}" if zip_filename else None
        return {"success": True, "request_id": request_id, "total_pages": result["total_pages"], "images": images, "image_urls": image_urls, "zip_url": zip_url, "filename": zip_filename if zip_filename else (images[0] if images else None)}
    except Exception as e:
        logger.error(f"PDF to BMP error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-bmp/download/{request_id}/{filename}")
async def pdf_to_bmp_download(request_id: str, filename: str):
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename, media_type=_media_type_for(filename))


# ==========================================
# API ROUTES (PDF to TIFF)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-tiff/upload")
async def pdf_to_tiff_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-tiff/process")
async def pdf_to_tiff_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_tiff_service.process(request_id=request_id, filename=filename)
        images = result["images"]
        zip_filename = result.get("zip_filename")
        image_urls = [f"/api/convert-from-pdf/pdf-to-tiff/download/{request_id}/{img}" for img in images]
        zip_url = f"/api/convert-from-pdf/pdf-to-tiff/download/{request_id}/{zip_filename}" if zip_filename else None
        multipage_url = f"/api/convert-from-pdf/pdf-to-tiff/download/{request_id}/{images[0]}" if result.get("multipage_tiff") else None
        return {"success": True, "request_id": request_id, "total_pages": result["total_pages"], "images": images, "image_urls": image_urls, "zip_url": zip_url, "multipage_url": multipage_url, "filename": zip_filename if zip_filename else (images[0] if images else None)}
    except Exception as e:
        logger.error(f"PDF to TIFF error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-tiff/download/{request_id}/{filename}")
async def pdf_to_tiff_download(request_id: str, filename: str):
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename, media_type=_media_type_for(filename))


# ==========================================
# API ROUTES (PDF to WebP)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-webp/upload")
async def pdf_to_webp_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-webp/process")
async def pdf_to_webp_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_webp_service.process(request_id=request_id, filename=filename)
        images = result["images"]
        zip_filename = result.get("zip_filename")
        image_urls = [f"/api/convert-from-pdf/pdf-to-webp/download/{request_id}/{img}" for img in images]
        zip_url = f"/api/convert-from-pdf/pdf-to-webp/download/{request_id}/{zip_filename}" if zip_filename else None
        return {"success": True, "request_id": request_id, "total_pages": result["total_pages"], "images": images, "image_urls": image_urls, "zip_url": zip_url, "filename": zip_filename if zip_filename else (images[0] if images else None)}
    except Exception as e:
        logger.error(f"PDF to WebP error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-webp/download/{request_id}/{filename}")
async def pdf_to_webp_download(request_id: str, filename: str):
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename, media_type=_media_type_for(filename))


# ==========================================
# API ROUTES (PDF to SVG)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-svg/upload")
async def pdf_to_svg_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-svg/process")
async def pdf_to_svg_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_svg_service.process(request_id=request_id, filename=filename)
        files = result["files"]
        zip_filename = result.get("zip_filename")
        file_urls = [f"/api/convert-from-pdf/pdf-to-svg/download/{request_id}/{f}" for f in files]
        zip_url = f"/api/convert-from-pdf/pdf-to-svg/download/{request_id}/{zip_filename}" if zip_filename else None
        return {"success": True, "request_id": request_id, "total_pages": result["total_pages"], "files": files, "file_urls": file_urls, "zip_url": zip_url, "filename": zip_filename if zip_filename else (files[0] if files else None)}
    except Exception as e:
        logger.error(f"PDF to SVG error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-svg/download/{request_id}/{filename}")
async def pdf_to_svg_download(request_id: str, filename: str):
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename, media_type=_media_type_for(filename))


# ==========================================
# HELPER: generic single-output-file handlers
# ==========================================

async def _single_file_process(service, request_id: str, filename: str, api_slug: str) -> dict:
    result = await service.process(request_id=request_id, filename=filename)
    out = result["output_filename"]
    return {
        "success": True,
        "request_id": request_id,
        "filename": out,
        "total_pages": result.get("total_pages", 0),
        "download_url": f"/api/convert-from-pdf/{api_slug}/download/{request_id}/{out}",
    }


@router.post("/convert-from-pdf/pdf-to-markdown")
async def pdf_to_markdown_direct(request: Request, file: UploadFile = File(...)):
    """One-step conversion for the shared upload workspace.

    Dedicated conversion screens can still use the upload/process/download flow.
    """
    upload = await _upload_pdf(request, file)
    try:
        return await _single_file_process(
            pdf_to_markdown_service,
            upload["request_id"],
            upload["filename"],
            "pdf-to-markdown",
        )
    except Exception as exc:
        logger.error("PDF to Markdown error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _single_file_download(request_id: str, filename: str, media: str):
    if re.search(r'[\\/]', request_id) or re.search(r'[\\/]', filename):
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename, media_type=media)


# ==========================================
# API ROUTES (PDF to TXT)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-txt/upload")
async def pdf_to_txt_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-txt/process")
async def pdf_to_txt_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        return await _single_file_process(pdf_to_txt_service, request_id, filename, "pdf-to-txt")
    except Exception as e:
        logger.error(f"PDF to TXT error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-txt/download/{request_id}/{filename}")
async def pdf_to_txt_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "text/plain; charset=utf-8")


# ==========================================
# API ROUTES (PDF to HTML)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-html/upload")
async def pdf_to_html_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-html/process")
async def pdf_to_html_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        return await _single_file_process(pdf_to_html_service, request_id, filename, "pdf-to-html")
    except Exception as e:
        logger.error(f"PDF to HTML error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-html/download/{request_id}/{filename}")
async def pdf_to_html_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "text/html; charset=utf-8")


# ==========================================
# API ROUTES (PDF to XML)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-xml/upload")
async def pdf_to_xml_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-xml/process")
async def pdf_to_xml_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        return await _single_file_process(pdf_to_xml_service, request_id, filename, "pdf-to-xml")
    except Exception as e:
        logger.error(f"PDF to XML error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-xml/download/{request_id}/{filename}")
async def pdf_to_xml_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/xml; charset=utf-8")


# ==========================================
# API ROUTES (PDF to CSV)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-csv/upload")
async def pdf_to_csv_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-csv/process")
async def pdf_to_csv_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        result = await pdf_to_csv_service.process(request_id=request_id, filename=filename)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "total_pages": result.get("total_pages", 0),
            "total_rows": result.get("total_rows", 0),
            "download_url": f"/api/convert-from-pdf/pdf-to-csv/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to CSV error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-csv/download/{request_id}/{filename}")
async def pdf_to_csv_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "text/csv; charset=utf-8")


# ==========================================
# API ROUTES (PDF to JSON)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-json/upload")
async def pdf_to_json_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-json/process")
async def pdf_to_json_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        return await _single_file_process(pdf_to_json_service, request_id, filename, "pdf-to-json")
    except Exception as e:
        logger.error(f"PDF to JSON error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-json/download/{request_id}/{filename}")
async def pdf_to_json_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/json; charset=utf-8")


# ==========================================
# API ROUTES (PDF to RTF)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-rtf/upload")
async def pdf_to_rtf_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-rtf/process")
async def pdf_to_rtf_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        return await _single_file_process(pdf_to_rtf_service, request_id, filename, "pdf-to-rtf")
    except Exception as e:
        logger.error(f"PDF to RTF error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-rtf/download/{request_id}/{filename}")
async def pdf_to_rtf_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/rtf")


# ==========================================
# API ROUTES (PDF to Markdown)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-markdown/upload")
async def pdf_to_markdown_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-markdown/process")
async def pdf_to_markdown_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        return await _single_file_process(pdf_to_markdown_service, request_id, filename, "pdf-to-markdown")
    except Exception as e:
        logger.error(f"PDF to Markdown error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-markdown/download/{request_id}/{filename}")
async def pdf_to_markdown_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "text/markdown; charset=utf-8")


# ==========================================
# API ROUTES (PDF to EPUB)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-epub/upload")
async def pdf_to_epub_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-epub/process")
async def pdf_to_epub_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        return await _single_file_process(pdf_to_epub_service, request_id, filename, "pdf-to-epub")
    except Exception as e:
        logger.error(f"PDF to EPUB error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-epub/download/{request_id}/{filename}")
async def pdf_to_epub_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/epub+zip")


# ==========================================
# API ROUTES (PDF to XPS)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-xps/upload")
async def pdf_to_xps_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-xps/process")
async def pdf_to_xps_process(request_id: str = Form(...), filename: str = Form(...)):
    try:
        return await _single_file_process(pdf_to_xps_service, request_id, filename, "pdf-to-xps")
    except Exception as e:
        logger.error(f"PDF to XPS error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-xps/download/{request_id}/{filename}")
async def pdf_to_xps_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/vnd.ms-xpsdocument")


# ==========================================
# API ROUTES (PDF to HEIC)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-heic/upload")
async def pdf_to_heic_upload(
    request: Request,
    file: UploadFile = File(...)
):
    request_id = request.state.request_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf is supported.")
        
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    
    return {
        "success": True,
        "request_id": request_id,
        "filename": file.filename,
        "size": file_path.stat().st_size,
    }

@router.post("/convert-from-pdf/pdf-to-heic/process")
async def pdf_to_heic_process(
    request_id: str = Form(...),
    filename: str = Form(...)
):
    try:
        result = await pdf_to_heic_service.process(request_id, filename)
        result["filename"] = result.get("output_filename")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing PDF to HEIC: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during conversion.")

@router.get("/convert-from-pdf/pdf-to-heic/download/{request_id}/{filename}")
async def pdf_to_heic_download(
    request_id: str,
    filename: str
):
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )

@router.get("/convert-from-pdf/pdf-to-heic/view/{request_id}/{filename}")
async def pdf_to_heic_view(
    request_id: str,
    filename: str
):
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        content_disposition_type="inline"
    )

# ==========================================
# API ROUTES (PDF to RAW)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-raw-image/upload")
async def pdf_to_raw_image_upload(
    request: Request,
    file: UploadFile = File(...)
):
    request_id = request.state.request_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf is supported.")
        
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    
    return {
        "success": True,
        "request_id": request_id,
        "filename": file.filename,
        "size": file_path.stat().st_size,
    }

@router.post("/convert-from-pdf/pdf-to-raw-image/process")
async def pdf_to_raw_image_process(
    request_id: str = Form(...),
    filename: str = Form(...)
):
    try:
        result = await pdf_to_raw_image_service.process(request_id, filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing PDF to RAW: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during conversion.")

@router.get("/convert-from-pdf/pdf-to-raw-image/download/{request_id}/{filename}")
async def pdf_to_raw_image_download(
    request_id: str,
    filename: str
):
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )

@router.get("/convert-from-pdf/pdf-to-raw-image/view/{request_id}/{filename}")
async def pdf_to_raw_image_view(
    request_id: str,
    filename: str
):
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        content_disposition_type="inline"
    )

# ==========================================
# API ROUTES (PDF to ODT)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-odt/upload")
async def pdf_to_odt_upload(
    request: Request,
    file: UploadFile = File(...)
):
    request_id = request.state.request_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf is supported.")
        
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    
    return {
        "success": True,
        "request_id": request_id,
        "filename": file.filename,
        "size": file_path.stat().st_size,
    }

@router.post("/convert-from-pdf/pdf-to-odt/process")
async def pdf_to_odt_process(
    request_id: str = Form(...),
    filename: str = Form(...)
):
    try:
        result = await pdf_to_odt_service.process(request_id, filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing PDF to ODT: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during conversion.")

@router.get("/convert-from-pdf/pdf-to-odt/download/{request_id}/{filename}")
async def pdf_to_odt_download(
    request_id: str,
    filename: str
):
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )

@router.get("/convert-from-pdf/pdf-to-odt/view/{request_id}/{filename}")
async def pdf_to_odt_view(
    request_id: str,
    filename: str
):
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        content_disposition_type="inline"
    )

# ==========================================
# API ROUTES (PDF to ODS)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-ods/upload")
async def pdf_to_ods_upload(
    request: Request,
    file: UploadFile = File(...)
):
    request_id = request.state.request_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf is supported.")
        
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    
    return {
        "success": True,
        "request_id": request_id,
        "filename": file.filename,
        "size": file_path.stat().st_size,
    }

@router.post("/convert-from-pdf/pdf-to-ods/process")
async def pdf_to_ods_process(
    request_id: str = Form(...),
    filename: str = Form(...)
):
    try:
        result = await pdf_to_ods_service.process(request_id, filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing PDF to ODS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during conversion.")

@router.get("/convert-from-pdf/pdf-to-ods/download/{request_id}/{filename}")
async def pdf_to_ods_download(
    request_id: str,
    filename: str
):
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )

@router.get("/convert-from-pdf/pdf-to-ods/view/{request_id}/{filename}")
async def pdf_to_ods_view(
    request_id: str,
    filename: str
):
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        content_disposition_type="inline"
    )

# ==========================================
# API ROUTES (PDF to ODP)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-odp/upload")
async def pdf_to_odp_upload(
    request: Request,
    file: UploadFile = File(...)
):
    request_id = request.state.request_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf is supported.")
        
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    await save_upload(file.file, file_path)
    
    return {
        "success": True,
        "request_id": request_id,
        "filename": file.filename,
        "size": file_path.stat().st_size,
    }

@router.post("/convert-from-pdf/pdf-to-odp/process")
async def pdf_to_odp_process(
    request_id: str = Form(...),
    filename: str = Form(...)
):
    try:
        result = await pdf_to_odp_service.process(request_id, filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing PDF to ODP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during conversion.")

@router.get("/convert-from-pdf/pdf-to-odp/download/{request_id}/{filename}")
async def pdf_to_odp_download(
    request_id: str,
    filename: str
):
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )

@router.get("/convert-from-pdf/pdf-to-odp/view/{request_id}/{filename}")
async def pdf_to_odp_view(
    request_id: str,
    filename: str
):
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        content_disposition_type="inline"
    )


# ==========================================
# API ROUTES (PDF to ZIP)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-zip/upload")
async def pdf_to_zip_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-zip/process")
async def pdf_to_zip_process(
    request_id: str = Form(...),
    filename: str = Form(...),
    format: str = Form("png"),
    dpi: int = Form(150),
    pages: str = Form("all"),
    output_filename: str = Form(""),
):
    try:
        config = {
            "format": format,
            "dpi": dpi,
            "pages": pages,
            "output_filename": output_filename,
        }
        result = await pdf_to_zip_service.process(request_id=request_id, filename=filename, config=config)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "total_pages": result.get("total_pages", 0),
            "image_count": result.get("image_count", 0),
            "download_url": f"/api/convert-from-pdf/pdf-to-zip/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to ZIP error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-zip/download/{request_id}/{filename}")
async def pdf_to_zip_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/zip")


# ==========================================
# API ROUTES (PDF to Visio)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-visio/upload")
async def pdf_to_visio_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-visio/process")
async def pdf_to_visio_process(
    request_id: str = Form(...),
    filename: str = Form(...),
    dpi: int = Form(150),
    output_filename: str = Form(""),
):
    try:
        config = {"dpi": dpi, "output_filename": output_filename}
        result = await pdf_to_visio_service.process(request_id=request_id, filename=filename, config=config)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "total_pages": result.get("total_pages", 0),
            "download_url": f"/api/convert-from-pdf/pdf-to-visio/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to Visio error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-visio/download/{request_id}/{filename}")
async def pdf_to_visio_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/octet-stream")


# ==========================================
# API ROUTES (PDF to Publisher)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-publisher/upload")
async def pdf_to_publisher_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-publisher/process")
async def pdf_to_publisher_process(
    request_id: str = Form(...),
    filename: str = Form(...),
    dpi: int = Form(150),
    output_filename: str = Form(""),
):
    try:
        config = {"dpi": dpi, "output_filename": output_filename}
        result = await pdf_to_publisher_service.process(request_id=request_id, filename=filename, config=config)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "total_pages": result.get("total_pages", 0),
            "download_url": f"/api/convert-from-pdf/pdf-to-publisher/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to Publisher error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-publisher/download/{request_id}/{filename}")
async def pdf_to_publisher_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/octet-stream")


# ==========================================
# API ROUTES (PDF to Photoshop)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-photoshop/upload")
async def pdf_to_photoshop_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-photoshop/process")
async def pdf_to_photoshop_process(
    request_id: str = Form(...),
    filename: str = Form(...),
    dpi: int = Form(150),
    output_filename: str = Form(""),
):
    try:
        config = {"dpi": dpi, "output_filename": output_filename}
        result = await pdf_to_photoshop_service.process(request_id=request_id, filename=filename, config=config)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "total_pages": result.get("total_pages", 0),
            "download_url": f"/api/convert-from-pdf/pdf-to-photoshop/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to Photoshop error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-photoshop/download/{request_id}/{filename}")
async def pdf_to_photoshop_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/octet-stream")


# ==========================================
# API ROUTES (PDF to Illustrator)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-illustrator/upload")
async def pdf_to_illustrator_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-illustrator/process")
async def pdf_to_illustrator_process(
    request_id: str = Form(...),
    filename: str = Form(...),
    output_filename: str = Form(""),
):
    try:
        config = {"output_filename": output_filename}
        result = await pdf_to_illustrator_service.process(request_id=request_id, filename=filename, config=config)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "total_pages": result.get("total_pages", 0),
            "download_url": f"/api/convert-from-pdf/pdf-to-illustrator/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to Illustrator error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-illustrator/download/{request_id}/{filename}")
async def pdf_to_illustrator_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/postscript")


# ==========================================
# API ROUTES (PDF to CAD: DXF / DWG)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-cad/upload")
async def pdf_to_cad_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-cad/process")
async def pdf_to_cad_process(
    request_id: str = Form(...),
    filename: str = Form(...),
    cad_format: str = Form("dxf"),
    output_filename: str = Form(""),
):
    try:
        config = {"cad_format": cad_format, "output_filename": output_filename}
        result = await pdf_to_cad_service.process(request_id=request_id, filename=filename, config=config)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "total_pages": result.get("total_pages", 0),
            "download_url": f"/api/convert-from-pdf/pdf-to-cad/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to CAD error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-cad/download/{request_id}/{filename}")
async def pdf_to_cad_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/dxf")


# ==========================================
# API ROUTES (PDF to Email: EML)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-email/upload")
async def pdf_to_email_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-email/process")
async def pdf_to_email_process(
    request_id: str = Form(...),
    filename: str = Form(...),
    subject: str = Form(""),
    to_email: str = Form(""),
    from_email: str = Form(""),
    output_filename: str = Form(""),
):
    try:
        config = {
            "subject": subject,
            "to_email": to_email,
            "from_email": from_email,
            "output_filename": output_filename,
        }
        result = await pdf_to_email_service.process(request_id=request_id, filename=filename, config=config)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "total_pages": result.get("total_pages", 0),
            "download_url": f"/api/convert-from-pdf/pdf-to-email/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to Email error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-email/download/{request_id}/{filename}")
async def pdf_to_email_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "message/rfc822")


# ==========================================
# API ROUTES (PDF to Outlook: MSG)
# ==========================================

@router.post("/convert-from-pdf/pdf-to-outlook/upload")
async def pdf_to_outlook_upload(request: Request, file: UploadFile = File(...)):
    return await _upload_pdf(request, file)


@router.post("/convert-from-pdf/pdf-to-outlook/process")
async def pdf_to_outlook_process(
    request_id: str = Form(...),
    filename: str = Form(...),
    subject: str = Form(""),
    output_filename: str = Form(""),
):
    try:
        config = {
            "subject": subject,
            "output_filename": output_filename,
        }
        result = await pdf_to_outlook_service.process(request_id=request_id, filename=filename, config=config)
        out = result["output_filename"]
        return {
            "success": True,
            "request_id": request_id,
            "filename": out,
            "total_pages": result.get("total_pages", 0),
            "download_url": f"/api/convert-from-pdf/pdf-to-outlook/download/{request_id}/{out}",
        }
    except Exception as e:
        logger.error(f"PDF to Outlook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-from-pdf/pdf-to-outlook/download/{request_id}/{filename}")
async def pdf_to_outlook_download(request_id: str, filename: str):
    return await _single_file_download(request_id, filename, "application/vnd.ms-outlook")
