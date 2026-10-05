"""
PDF-related API endpoints.

All PDF operations (merge, split, remove, extract, compress) are
exposed here under the ``/pdf`` prefix.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, HTTPException
from fastapi.responses import FileResponse, Response

from app.core.config import settings
from app.core.constants import MAX_FILE_SIZE_BYTES, MAX_UPLOAD_FILES, PDF_CONTENT_TYPE, DEFAULT_ZIP_NAME
from app.core.paths import Paths
from app.schemas.pdf_schema import (
    WebOptimizationResponse,
    CompressPDFResponse,
    ExtractPagesResponse,
    MergePDFResponse,
    RemovePagesResponse,
    SplitPDFResponse,
    RotatePDFResponse,
)
from app.organize_pdf_services.compress_service import CompressPDFService
from app.organize_pdf_services.extract_service import ExtractPagesService
from app.organize_pdf_services.merge_service import MergePDFService
from app.organize_pdf_services.remove_service import RemovePDFPagesService
from app.organize_pdf_services.split_service import SplitPDFService
from app.organize_pdf_services.rotate_services import RotatePDFService
from app.organize_pdf_services.watermark_services import AddWatermarkService
from app.organize_pdf_services.add_page_number_service import AddPageNumberService
from app.organize_pdf_services.merge_pdf_into_1_page_service import MergeContinuousService
from app.organize_pdf_services.pdf_to_image_collection_service import PDFToImageCollectionService
from app.organize_pdf_services.crop_pdf_service import CropPDFService
from app.organize_pdf_services.repair_pdf_service import RepairPDFService
from app.organize_pdf_services.flatten_pdf_service import FlattenPDFService
from app.organize_pdf_services.pdf_to_individual_pages_service import PDFToIndividualPagesService
from app.organize_pdf_services.edit_pdf_service import EditPDFService
from app.organize_pdf_services.background_management_service import _background_management_service
from app.organize_pdf_services.web_optimization_service import _web_optimization_service
from app.organize_pdf_services.linearization_service import _linearization_service
from app.organize_pdf_services.download_optimized_pdf_service import _download_optimized_service
from app.organize_pdf_services.duplicate_pdf_pages_service import _duplicate_pages_service
from app.organize_pdf_services.insert_blank_page_service import _insert_blank_page_service
from app.organize_pdf_services.replace_pdf_pages_service import _replace_pdf_pages_service
from app.organize_pdf_services.pdf_to_searchable_service import _pdf_to_searchable_service
from app.organize_pdf_services.reorder_bookmarks_after_page_changes_service import _reorder_bookmarks_service
from app.organize_pdf_services.page_label_management_service import _page_label_service
from app.organize_pdf_services.page_size_normalization_service import _page_size_normalization_service
from app.organize_pdf_services.scan_to_pdf_service import scan_to_pdf_service
from app.organize_pdf_services.rich_media_service import rich_media_service
from app.organize_pdf_services.pdf_to_long_image_service import pdf_to_long_image_service
from app.utils.file_handler import save_upload
from app.utils.validators import (
    validate_file_size,
    validate_pdf_content_type,
    validate_pdf_extension,
    validate_pdf_extension,
)
from app.pdf_security_services.file_expiration_service import file_expiration_service

logger = logging.getLogger(__name__)

router = APIRouter()

_merge_service = MergePDFService()
_split_service = SplitPDFService()
_remove_service = RemovePDFPagesService()
_extract_service = ExtractPagesService()
_compress_service = CompressPDFService()
_rotate_service = RotatePDFService()
_watermark_service = AddWatermarkService()
_page_number_service = AddPageNumberService()
_merge_continuous_service = MergeContinuousService()
_pdf_to_image_collection_service = PDFToImageCollectionService()
_crop_pdf_service = CropPDFService()
_repair_pdf_service = RepairPDFService()
_flatten_pdf_service = FlattenPDFService()
_pdf_to_individual_pages_service = PDFToIndividualPagesService()
_edit_pdf_service = EditPDFService()


async def _validate_upload(file: UploadFile) -> None:
    """Run common upload validations."""
    if file.filename is None:
        raise ValueError("Filename is missing.")

    if not validate_pdf_extension(file.filename):
        raise ValueError("Only PDF files are allowed.")

    if file.content_type and not validate_pdf_content_type(file.content_type):
        raise ValueError("Invalid content type. Only application/pdf is allowed.")


async def _save_uploads(
    files: List[UploadFile],
    request_id: str,
) -> List[Path]:
    """Save uploaded files and return their paths."""
    upload_dir = Paths.request_upload(request_id)
    saved: List[Path] = []

    for file in files:
        if file.size is not None and not validate_file_size(file.size):
            raise ValueError(
                f"File '{file.filename}' exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit."
            )

        dest = upload_dir / (file.filename or "upload.pdf")
        await save_upload(file.file, dest)
        saved.append(dest)

    return saved


@router.post("/merge", response_model=MergePDFResponse)
async def merge_pdfs(
    request: Request,
    files: List[UploadFile] = File(..., description="PDF files to merge"),
) -> MergePDFResponse:
    """Merge multiple PDF files into one."""
    request_id: str = request.state.request_id

    if len(files) > MAX_UPLOAD_FILES:
        raise ValueError(f"Maximum {MAX_UPLOAD_FILES} files allowed.")

    try:
        saved_files = await _save_uploads(files, request_id)
        result = await _merge_service.merge(saved_files, request_id)
        return result
    except Exception as exc:
        logger.exception("Merge failed [request_id=%s]", request_id)
        raise


@router.post("/split", response_model=SplitPDFResponse)
async def split_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF to split"),
    split_every: int = Query(..., gt=0, description="Split every N pages"),
) -> SplitPDFResponse:
    """Split a PDF into multiple files of N pages each."""
    request_id: str = request.state.request_id

    try:
        saved = await _save_uploads([file], request_id)
        result = await _split_service.split(saved[0], split_every, request_id)
        return result
    except Exception as exc:
        logger.exception("Split failed [request_id=%s]", request_id)
        raise


@router.post("/remove", response_model=RemovePagesResponse)
async def remove_pages(
    request: Request,
    file: UploadFile = File(..., description="PDF to modify"),
    pages: str = Query(..., description="Pages to remove, e.g. '1,3,5-8'"),
) -> RemovePagesResponse:
    """Remove specified pages from a PDF."""
    request_id: str = request.state.request_id

    try:
        saved = await _save_uploads([file], request_id)
        result = await _remove_service.remove_pages(saved[0], pages, request_id)
        return result
    except Exception as exc:
        logger.exception("Remove pages failed [request_id=%s]", request_id)
        raise


@router.post("/extract", response_model=ExtractPagesResponse)
async def extract_pages(
    request: Request,
    file: UploadFile = File(..., description="PDF to extract from"),
    pages: str = Query(..., description="Pages to extract, e.g. '1,3,5-8'"),
) -> ExtractPagesResponse:
    """Extract specified pages from a PDF into a new file."""
    request_id: str = request.state.request_id

    try:
        saved = await _save_uploads([file], request_id)
        result = await _extract_service.extract(saved[0], pages, request_id)
        return result
    except ValueError as exc:
        logger.warning("Extract validation failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        logger.warning("Extract validation failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Extract failed [request_id=%s]", request_id)
        raise


@router.post("/compress", response_model=CompressPDFResponse)
async def compress_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF to compress"),
    compression_level: str = Query("recommended", description="Compression level: 'extreme', 'recommended', 'less' or 'custom'"),
    target_size: int = Query(None, description="Target size for custom mode"),
    target_size_unit: str = Query("KB", description="Unit for target size: 'KB' or 'MB'"),
) -> CompressPDFResponse:
    """Compress a PDF."""
    request_id: str = request.state.request_id

    try:
        saved = await _save_uploads([file], request_id)
        result = await _compress_service.compress(
            input_pdf=saved[0],
            compression_level=compression_level,
            target_size=target_size,
            target_size_unit=target_size_unit,
            request_id=request_id
        )
        return result
    except Exception as exc:
        logger.exception("Compress failed [request_id=%s]", request_id)
        raise


@router.post("/rotate", response_model=RotatePDFResponse)
async def rotate_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF to rotate"),
    rotation: int = Form(90, description="Rotation angle in degrees"),
    pages: str = Form("all", description="Pages to apply rotation to ('all', 'odd', 'even', or '1,3,5-7')"),
) -> RotatePDFResponse:
    """Rotate a PDF."""
    request_id: str = request.state.request_id

    try:
        saved = await _save_uploads([file], request_id)
        result = await _rotate_service.rotate(
            input_pdf=saved[0],
            rotation=rotation,
            pages=pages,
            request_id=request_id,
        )
        return result
    except Exception as e:
        logger.exception("PDF rotation failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/watermark")
async def watermark_pdf(
    request: Request,
    file: UploadFile = File(...),
    watermark_type: str = Form("text"),
    text: Optional[str] = Form(None),
    font_family: str = Form("Helvetica"),
    font_size: float = Form(36.0),
    font_color: str = Form("#000000"),
    bold: bool = Form(False),
    italic: bool = Form(False),
    underline: bool = Form(False),
    image_file: Optional[UploadFile] = File(None),
    opacity: float = Form(100.0),
    rotation: float = Form(0.0),
    scale: float = Form(1.0),
    margin: float = Form(0.0),
    foreground: bool = Form(True),
    x_pos: Optional[float] = Form(None),
    y_pos: Optional[float] = Form(None),
    preset_position: str = Form("Center"),
    pages_selection: str = Form("all"),
    rules_json: Optional[str] = Form(None),
    repeat_mode: str = Form("single"),
    h_spacing: float = Form(50.0),
    v_spacing: float = Form(50.0)
):
    """
    Watermark a PDF file using text or image.
    """
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    input_dir = Paths.request_upload(request_id)
    input_path = input_dir / file.filename
    await save_upload(file.file, input_path)
    
    image_path = None
    if watermark_type == "image" and image_file and image_file.filename:
        # Save watermark image temporarily
        img_id = str(uuid.uuid4())
        img_dir = Paths.request_upload(img_id)
        image_path = img_dir / image_file.filename
        await save_upload(image_file.file, image_path)

    try:
        response = await _watermark_service.add_watermark(
            input_pdf=input_path,
            request_id=request_id,
            watermark_type=watermark_type,
            text=text,
            font_family=font_family,
            font_size=font_size,
            font_color=font_color,
            bold=bold,
            italic=italic,
            underline=underline,
            image_path=image_path,
            opacity=opacity,
            rotation=rotation,
            scale=scale,
            margin=margin,
            foreground=foreground,
            x_pos=x_pos,
            y_pos=y_pos,
            preset_position=preset_position,
            pages_selection=pages_selection,
            rules_json=rules_json,
            repeat_mode=repeat_mode,
            h_spacing=h_spacing,
            v_spacing=v_spacing
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("PDF watermarking failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/page_number")
async def add_page_numbers(
    request: Request,
    file: UploadFile = File(...),
    page_mode: str = Form("single"),
    format_text: str = Form("{n}"),
    start_number: int = Form(1),
    font_family: str = Form("Helvetica"),
    font_size: float = Form(14.0),
    font_color: str = Form("#000000"),
    bold: bool = Form(False),
    italic: bool = Form(False),
    underline: bool = Form(False),
    preset_position: str = Form("Bottom Right"),
    margin_type: str = Form("Recommended"),
    pages_selection: str = Form("all")
):
    """
    Add page numbers to a PDF file.
    """
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    input_dir = Paths.request_upload(request_id)
    input_path = input_dir / file.filename
    await save_upload(file.file, input_path)
    
    try:
        response = await _page_number_service.add_page_numbers(
            input_pdf=input_path,
            request_id=request_id,
            page_mode=page_mode,
            format_text=format_text,
            start_number=start_number,
            font_family=font_family,
            font_size=font_size,
            font_color=font_color,
            bold=bold,
            italic=italic,
            underline=underline,
            preset_position=preset_position,
            margin_type=margin_type,
            pages_selection=pages_selection
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("PDF page numbering failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{request_id}/{filename}")
async def download_file(request_id: str, filename: str):
    """Download a processed PDF file."""
    output_dir = Paths.request_output(request_id)
    file_path = output_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    # Check if the file has expired
    file_expiration_service.check_file_expiration(output_dir)

    return FileResponse(
        path=str(file_path),
        media_type=PDF_CONTENT_TYPE,
        filename=filename,
    )


@router.get("/download/{request_id}")
async def download_zip(request_id: str):
    """Download all output files as a zip."""
    import zipfile
    import tempfile

    output_dir = Paths.request_output(request_id)

    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="No files found")

    files = list(output_dir.glob("*.pdf"))

    if not files:
        raise HTTPException(status_code=404, detail="No PDF files found")

    zip_path = Path(tempfile.gettempdir()) / f"{request_id}.zip"

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(str(f), f.name)

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=DEFAULT_ZIP_NAME,
    )
@router.post("/merge_continuous")
async def merge_continuous(
    request: Request,
    file: UploadFile = File(...),
    direction: str = Form("vertical"),
    remove_gaps: bool = Form(False),
    pages_selection: str = Form("all")
):
    """
    Merge multiple pages into a single continuous PDF page.
    """
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    input_dir = Paths.request_upload(request_id)
    input_path = input_dir / file.filename
    await save_upload(file.file, input_path)
    
    try:
        response = await _merge_continuous_service.merge_continuous(
            input_pdf=input_path,
            request_id=request_id,
            direction=direction,
            remove_gaps=remove_gaps,
            pages_selection=pages_selection
        )
        return response
    except ValueError as e:
        logger.error(f"Validation error in continuous merge: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in continuous merge: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to merge continuous PDF")

@router.post("/pdf_to_image")
async def pdf_to_image(
    request: Request,
    file: UploadFile = File(...),
    output_format: str = Form("jpg"),
    dpi: int = Form(150),
    quality: str = Form("High"),
    pages_selection: str = Form("all")
):
    """
    Convert PDF pages to image collection.
    """
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    input_dir = Paths.request_upload(request_id)
    input_path = input_dir / file.filename
    await save_upload(file.file, input_path)
    
    try:
        response = await _pdf_to_image_collection_service.convert_to_images(
            input_pdf=input_path,
            request_id=request_id,
            output_format=output_format,
            dpi=dpi,
            quality=quality,
            pages_selection=pages_selection
        )
        return response
    except ValueError as e:
        logger.error(f"Validation error in PDF to image: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in PDF to image: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to convert PDF to images")

@router.post("/crop_pdf")
async def crop_pdf(
    request: Request,
    file: UploadFile = File(...),
    mode: str = Form("manual"),
    left: float = Form(0.0),
    top: float = Form(0.0),
    right: float = Form(0.0),
    bottom: float = Form(0.0),
    pages_selection: str = Form("all")
):
    """
    Crop PDF pages by updating the CropBox.
    """
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    input_dir = Paths.request_upload(request_id)
    input_path = input_dir / file.filename
    await save_upload(file.file, input_path)
    
    try:
        response = await _crop_pdf_service.crop_pdf(
            input_pdf=input_path,
            request_id=request_id,
            mode=mode,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            pages_selection=pages_selection
        )
        return response
    except ValueError as e:
        logger.error(f"Validation error in crop PDF: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in crop PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to crop PDF")

@router.post("/repair_pdf")
async def repair_pdf(
    request: Request,
    file: UploadFile = File(..., description="Corrupted PDF to repair")
):
    """
    Attempt to repair a corrupted or damaged PDF.
    """
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    input_dir = Paths.request_upload(request_id)
    input_path = input_dir / file.filename
    await save_upload(file.file, input_path)
    
    try:
        response = await _repair_pdf_service.repair(
            input_pdf=input_path,
            request_id=request_id
        )
        return response
    except ValueError as e:
        logger.error(f"Validation error in repair PDF: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in repair PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to repair PDF")

@router.post("/pdf_to_individual_pages", response_model=SplitPDFResponse)
async def pdf_to_individual_pages(
    request: Request,
    file: UploadFile = File(...),
    custom_name: str = Form("Page")
):
    """
    Extract every page of a PDF into individual PDF files.
    """
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    input_dir = Paths.request_upload(request_id)
    input_path = input_dir / file.filename
    await save_upload(file.file, input_path)
    
    try:
        response = await _pdf_to_individual_pages_service.split_to_individual_pages(
            input_pdf=input_path,
            request_id=request_id,
            custom_name=custom_name
        )
        return response
    except ValueError as e:
        logger.error(f"Validation error in PDF to individual pages: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in PDF to individual pages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to extract individual pages")

@router.post("/edit_pdf")
async def edit_pdf(
    request: Request,
    file: UploadFile = File(...),
    edits: str = Form(..., description="JSON string containing edit coordinates and objects")
):
    """
    Apply visual edits (text, images, shapes) to a PDF document.
    """
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    input_dir = Paths.request_upload(request_id)
    input_path = input_dir / file.filename
    await save_upload(file.file, input_path)
    
    try:
        response = await _edit_pdf_service.apply_edits(
            input_pdf=input_path,
            edits_json_str=edits,
            request_id=request_id
        )
        return response
    except ValueError as e:
        logger.error(f"Validation error in edit PDF: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in edit PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to apply PDF edits")

@router.post("/flatten_pdf")
async def flatten_pdf(
    request: Request,
    file: UploadFile = File(...),
    flatten_forms: bool = Form(True),
    flatten_comments: bool = Form(True),
    flatten_highlights: bool = Form(True),
    flatten_annotations: bool = Form(True),
    flatten_stamps: bool = Form(True),
    flatten_signature: bool = Form(True),
    flatten_entire_document: bool = Form(False)
):
    """
    Flatten PDF by removing interactivity while preserving text/quality.
    """
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    input_dir = Paths.request_upload(request_id)
    input_path = input_dir / file.filename
    await save_upload(file.file, input_path)
    
    try:
        response = await _flatten_pdf_service.flatten(
            input_pdf=input_path,
            request_id=request_id,
            flatten_forms=flatten_forms,
            flatten_comments=flatten_comments,
            flatten_highlights=flatten_highlights,
            flatten_annotations=flatten_annotations,
            flatten_stamps=flatten_stamps,
            flatten_signature=flatten_signature,
            flatten_entire_document=flatten_entire_document
        )
        return response
    except ValueError as e:
        logger.error(f"Validation error in flatten PDF: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in flatten PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to flatten PDF")


@router.post("/background")
async def process_background(
    request: Request,
    file: UploadFile = File(...),
    action: str = Form("add"),
    bg_type: str = Form("color"),
    pages_selection: str = Form("all"),
    color: str = Form("#FFFFFF"),
    image_file: Optional[UploadFile] = File(None),
    pdf_file: Optional[UploadFile] = File(None),
    opacity: float = Form(100.0),
    rotation: float = Form(0.0),
    scale: float = Form(1.0),
    fit_mode: str = Form("fill"),
    pos_x: float = Form(0.5),
    pos_y: float = Form(0.5),
    erase_areas_json: str = Form("[]")
):
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    input_dir = Paths.request_upload(request_id)
    input_path = input_dir / file.filename
    await save_upload(file.file, input_path)
    
    image_path = None
    if action == "add" and bg_type == "image" and image_file and image_file.filename:
        img_dir = Paths.request_upload(request_id)
        image_path = img_dir / image_file.filename
        await save_upload(image_file.file, image_path)
        
    bg_pdf_path = None
    if action == "add" and bg_type == "pdf" and pdf_file and pdf_file.filename:
        pdf_dir = Paths.request_upload(request_id)
        bg_pdf_path = pdf_dir / pdf_file.filename
        await save_upload(pdf_file.file, bg_pdf_path)

    try:
        response = await _background_management_service.process_background(
            input_pdf=input_path,
            request_id=request_id,
            action=action,
            bg_type=bg_type,
            pages_selection=pages_selection,
            color=color,
            image_path=image_path,
            bg_pdf_path=bg_pdf_path,
            opacity=opacity,
            rotation=rotation,
            scale=scale,
            fit_mode=fit_mode,
            pos_x=pos_x,
            pos_y=pos_y,
            erase_areas_json=erase_areas_json
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Background processing failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web-optimization", response_model=WebOptimizationResponse)
async def optimize_pdf_for_web(
    request: Request,
    file: UploadFile = File(...),
    level: str = Form("medium"),
    compress_images: bool = Form(True),
    remove_metadata_flag: bool = Form(True),
    optimize_fonts_flag: bool = Form(True),
    remove_unused: bool = Form(True),
    compress_object_streams: bool = Form(True),
    optimize_color: bool = Form(False),
    remove_duplicates: bool = Form(True)
):
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        result = await _web_optimization_service.optimize(
            input_pdf=saved[0],
            request_id=request_id,
            level=level,
            compress_images=compress_images,
            remove_metadata_flag=remove_metadata_flag,
            optimize_fonts_flag=optimize_fonts_flag,
            remove_unused=remove_unused,
            compress_object_streams=compress_object_streams,
            optimize_color=optimize_color,
            remove_duplicates=remove_duplicates
        )
        return result
    except Exception as e:
        import logging
        logging.exception("Web Optimization Failed")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/linearization/analyze")
async def analyze_pdf_linearization(
    request: Request,
    file: UploadFile = File(...),
):
    """Analyze PDF structure and return linearization properties."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        analysis = await _linearization_service.analyze(saved[0])
        return {
            "success": True,
            "message": "Analysis complete.",
            "request_id": request_id,
            **analysis.to_dict(),
        }
    except Exception as exc:
        logger.exception("Linearization analysis failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/linearization/process")
async def process_pdf_linearization(
    request: Request,
    file: Optional[UploadFile] = File(None),
    request_id: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    enable_fast_web_view: bool = Form(True),
    preserve_metadata: bool = Form(True),
    optimize_object_streams: bool = Form(True),
    preserve_bookmarks: bool = Form(True),
    keep_digital_signatures: bool = Form(True),
    force_rebuild: bool = Form(False),
):
    """Process and linearize the uploaded PDF for Fast Web View."""
    req_id = request_id or getattr(request.state, "request_id", uuid.uuid4().hex[:8])
    try:
        if file and file.filename:
            saved = await _save_uploads([file], req_id)
            input_pdf = saved[0]
        elif req_id:
            input_pdf = None
            upload_dir = Paths.request_upload(req_id)
            if filename and (upload_dir / filename).exists():
                input_pdf = upload_dir / filename
            else:
                files = list(upload_dir.glob("*.pdf"))
                if files:
                    input_pdf = files[0]
            if not input_pdf or not input_pdf.exists():
                raise HTTPException(status_code=404, detail="Uploaded file not found.")
        else:
            raise HTTPException(status_code=400, detail="Missing file or request_id")

        result = await _linearization_service.process(
            input_pdf=input_pdf,
            request_id=req_id,
            enable_fast_web_view=enable_fast_web_view,
            preserve_metadata=preserve_metadata,
            optimize_object_streams=optimize_object_streams,
            preserve_bookmarks=preserve_bookmarks,
            keep_digital_signatures=keep_digital_signatures,
            force_rebuild=force_rebuild,
        )
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Linearization processing failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/download-optimized/analyze")
async def analyze_optimized_pdf(
    request: Request,
    file: UploadFile = File(...),
):
    """Analyze a PDF and return structural information for display."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        analysis = await _download_optimized_service.analyze(saved[0])
        return {"success": True, "request_id": request_id, **analysis.to_dict()}
    except Exception as exc:
        logger.exception("Download-optimized analysis failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/download-optimized/process")
async def process_optimized_pdf(
    request: Request,
    file: UploadFile = File(...),
    compress_images: bool = Form(True),
    optimize_fonts: bool = Form(True),
    remove_metadata: bool = Form(True),
    compress_streams: bool = Form(True),
    optimize_resources: bool = Form(True),
    remove_duplicates: bool = Form(True),
    preserve_quality: bool = Form(False),
):
    """Optimize a PDF and return a download URL."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        result = await _download_optimized_service.process(
            input_pdf=saved[0],
            request_id=request_id,
            compress_images=compress_images,
            optimize_fonts=optimize_fonts,
            remove_metadata=remove_metadata,
            compress_streams=compress_streams,
            optimize_resources=optimize_resources,
            remove_duplicates=remove_duplicates,
            preserve_quality=preserve_quality,
        )
        return result.to_dict()
    except Exception as exc:
        logger.exception("Download-optimized processing failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/duplicate-pages/upload")
async def upload_duplicate_pages(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload PDF and run analysis for page duplication."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        analysis = await _duplicate_pages_service.analyze(saved[0])
        return {"success": True, "request_id": request_id, **analysis.to_dict()}
    except Exception as exc:
        logger.exception("Duplicate pages upload/analysis failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/duplicate-pages/process")
async def process_duplicate_pages(
    request: Request,
    file: UploadFile = File(...),
    page_selection: str = Form(...),
    copies: int = Form(1),
    insert_mode: str = Form("after"),
    custom_position: int = Form(1),
    preserve_bookmarks: bool = Form(True),
    preserve_annotations: bool = Form(True),
    preserve_metadata: bool = Form(True),
):
    """Process PDF page duplication."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        result = await _duplicate_pages_service.process(
            input_pdf=saved[0],
            request_id=request_id,
            page_selection=page_selection,
            copies=copies,
            insert_mode=insert_mode,
            custom_position=custom_position,
            preserve_bookmarks=preserve_bookmarks,
            preserve_annotations=preserve_annotations,
            preserve_metadata=preserve_metadata,
        )
        return result.to_dict()
    except Exception as exc:
        logger.exception("Duplicate pages processing failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/duplicate-pages/download/{request_id}/{filename}")
async def download_duplicate_pages_file(
    request_id: str,
    filename: str,
):
    """Securely download duplicated PDF."""
    path = Paths.request_output(request_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Duplicated PDF file not found or expired.")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=filename,
    )


# --- Insert Blank Page Endpoints ---


@router.post("/insert-blank-page/upload")
async def upload_insert_blank_page(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload PDF and run analysis for blank page insertion."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        analysis = await _insert_blank_page_service.analyze(saved[0])
        return {"success": True, "request_id": request_id, **analysis.to_dict()}
    except Exception as exc:
        logger.exception("Insert blank page upload/analysis failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/insert-blank-page/process")
async def process_insert_blank_page(
    request: Request,
    file: UploadFile = File(...),
    insert_mode: str = Form("after"),
    target_page: int = Form(1),
    target_page_end: Optional[int] = Form(None),
    blank_page_count: int = Form(1),
    page_size_name: str = Form("a4"),
    custom_width: float = Form(595.27),
    custom_height: float = Form(841.89),
    orientation: str = Form("portrait"),
    bg_color_hex: str = Form("#ffffff"),
    margin_preset: str = Form("standard"),
    margin_top: float = Form(36.0),
    margin_bottom: float = Form(36.0),
    margin_left: float = Form(36.0),
    margin_right: float = Form(36.0),
    page_label_prefix: str = Form(""),
    placeholder_text: str = Form(""),
    preserve_metadata: bool = Form(True),
    preserve_bookmarks: bool = Form(True),
):
    """Process PDF blank page insertion."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        result = await _insert_blank_page_service.process(
            input_pdf=saved[0],
            request_id=request_id,
            insert_mode=insert_mode,
            target_page=target_page,
            target_page_end=target_page_end,
            blank_page_count=blank_page_count,
            page_size_name=page_size_name,
            custom_width=custom_width,
            custom_height=custom_height,
            orientation=orientation,
            bg_color_hex=bg_color_hex,
            margin_preset=margin_preset,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
            margin_left=margin_left,
            margin_right=margin_right,
            page_label_prefix=page_label_prefix,
            placeholder_text=placeholder_text,
            preserve_metadata=preserve_metadata,
            preserve_bookmarks=preserve_bookmarks,
        )
        return result.to_dict()
    except Exception as exc:
        logger.exception("Insert blank page processing failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/insert-blank-page/download/{request_id}/{filename}")
async def download_inserted_blank_page_file(
    request_id: str,
    filename: str,
):
    """Securely download processed PDF."""
    path = Paths.request_output(request_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Processed PDF file not found or expired.")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=filename,
    )


# --- Replace PDF Pages Endpoints ---

@router.post("/replace-pdf-pages/upload")
async def upload_replace_pdf_pages(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload PDF and run structure analysis for page replacement."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        analysis = await _replace_pdf_pages_service.analyze(saved[0])
        return {"success": True, "request_id": request_id, **analysis.to_dict()}
    except Exception as exc:
        logger.exception("Replace PDF Pages upload/analysis failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/replace-pdf-pages/process")
async def process_replace_pdf_pages(
    request: Request,
    orig_file: UploadFile = File(...),
    repl_file: UploadFile = File(...),
    mapping: str = Form(...),  # JSON list string e.g. '[{"orig": 1, "repl": 3}]'
    size_mode: str = Form("fit"),
    preserve_bookmarks: bool = Form(True),
    preserve_metadata: bool = Form(True),
    preserve_labels: bool = Form(True),
    preserve_hyperlinks: bool = Form(True),
    preserve_annotations: bool = Form(True),
):
    """Process page replacements."""
    request_id = request.state.request_id
    try:
        # Save both files
        import json
        mapping_list = json.loads(mapping)

        # Save uploads
        saved_orig = await _save_uploads([orig_file], f"{request_id}_orig")
        saved_repl = await _save_uploads([repl_file], f"{request_id}_repl")

        result = await _replace_pdf_pages_service.process(
            orig_pdf=saved_orig[0],
            repl_pdf=saved_repl[0],
            request_id=request_id,
            mapping=mapping_list,
            size_mode=size_mode,
            preserve_bookmarks=preserve_bookmarks,
            preserve_metadata=preserve_metadata,
            preserve_labels=preserve_labels,
            preserve_hyperlinks=preserve_hyperlinks,
            preserve_annotations=preserve_annotations,
        )
        return result.to_dict()
    except Exception as exc:
        logger.exception("Replace PDF Pages processing failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/replace-pdf-pages/download/{request_id}/{filename}")
async def download_replaced_pdf_file(
    request_id: str,
    filename: str,
):
    """Securely download replaced PDF."""
    path = Paths.request_output(request_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Replaced PDF file not found or expired.")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=filename,
    )


# --- PDF to Searchable (OCR) Endpoints ---

@router.post("/pdf-to-searchable/upload")
async def upload_pdf_to_searchable(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload PDF and analyze standard searchability details."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        analysis = await _pdf_to_searchable_service.analyze(saved[0])
        return {"success": True, "request_id": request_id, **analysis.to_dict()}
    except Exception as exc:
        logger.exception("PDF to Searchable upload/analysis failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/pdf-to-searchable/process")
async def process_pdf_to_searchable(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("english"),
    quality: str = Form("balanced"),
    auto_rotate: bool = Form(True),
    deskew: bool = Form(True),
    clean_noise: bool = Form(True),
    preserve_metadata: bool = Form(True),
    skip_searchable: bool = Form(True),
    force_ocr: bool = Form(False),
):
    """Process PDF to Searchable using OCRmyPDF."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        result = await _pdf_to_searchable_service.process(
            input_pdf=saved[0],
            request_id=request_id,
            language=language,
            quality=quality,
            auto_rotate=auto_rotate,
            deskew=deskew,
            clean_noise=clean_noise,
            preserve_metadata=preserve_metadata,
            skip_searchable=skip_searchable,
            force_ocr=force_ocr,
        )
        return result.to_dict()
    except Exception as exc:
        logger.exception("PDF to Searchable processing failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/pdf-to-searchable/download/{request_id}/{filename}")
async def download_searchable_pdf_file(
    request_id: str,
    filename: str,
):
    """Securely download processed Searchable PDF."""
    path = Paths.request_output(request_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Searchable PDF file not found or expired.")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=filename,
    )


# --- Reorder Bookmarks Endpoints ---

@router.post("/reorder-bookmarks/upload")
async def upload_pdf_for_bookmark_reorder(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload PDF and analyze current bookmarks."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        analysis = await _reorder_bookmarks_service.analyze(saved[0])
        return {"request_id": request_id, **analysis}
    except Exception as exc:
        logger.exception("Bookmark reorder upload/analysis failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/reorder-bookmarks/process")
async def process_bookmark_reorder(
    request: Request,
    file: UploadFile = File(...),
    page_mapping: str = Form(...),
    preserve_hierarchy: bool = Form(True),
    preserve_metadata: bool = Form(True),
    preserve_titles: bool = Form(True),
    preserve_colors: bool = Form(True),
    preserve_bold: bool = Form(True),
    preserve_italic: bool = Form(True),
    preserve_zoom: bool = Form(True),
    preserve_view_mode: bool = Form(True),
    preserve_named_dest: bool = Form(True),
    preserve_page_labels: bool = Form(True),
    preserve_expand_state: bool = Form(True),
    preserve_collapse_state: bool = Form(True),
    update_internal_links: bool = Form(True),
    update_goto_links: bool = Form(True),
    repair_invalid_dests: bool = Form(True),
    repair_broken_refs: bool = Form(True),
    repair_named_dests: bool = Form(True),
    remove_invalid_bookmarks: bool = Form(True),
    skip_unsupported_actions: bool = Form(True),
    validate_after_update: bool = Form(True),
    generate_validation_report: bool = Form(True),
    optimize_output_pdf: bool = Form(True),
):
    """Process bookmark reordering with the given mapping."""
    request_id = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        result = await _reorder_bookmarks_service.process(
            input_pdf=saved[0],
            request_id=request_id,
            page_mapping=page_mapping,
            preserve_hierarchy=preserve_hierarchy,
            preserve_metadata=preserve_metadata,
            preserve_titles=preserve_titles,
            preserve_colors=preserve_colors,
            preserve_bold=preserve_bold,
            preserve_italic=preserve_italic,
            preserve_zoom=preserve_zoom,
            preserve_view_mode=preserve_view_mode,
            preserve_named_dest=preserve_named_dest,
            preserve_page_labels=preserve_page_labels,
            preserve_expand_state=preserve_expand_state,
            preserve_collapse_state=preserve_collapse_state,
            update_internal_links=update_internal_links,
            update_goto_links=update_goto_links,
            repair_invalid_dests=repair_invalid_dests,
            repair_broken_refs=repair_broken_refs,
            repair_named_dests=repair_named_dests,
            remove_invalid_bookmarks=remove_invalid_bookmarks,
            skip_unsupported_actions=skip_unsupported_actions,
            validate_after_update=validate_after_update,
            generate_validation_report=generate_validation_report,
            optimize_output_pdf=optimize_output_pdf
        )
        return result
    except Exception as exc:
        logger.exception("Bookmark reorder processing failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/reorder-bookmarks/download/{request_id}/{filename}")
async def download_reordered_bookmarks_file(
    request_id: str,
    filename: str,
):
    """Securely download processed Bookmark Reordered PDF."""
    path = Paths.request_output(request_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Reordered PDF file not found or expired.")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=filename,
    )


# ==========================================
# PAGE LABEL MANAGEMENT (Sub Section 1.31)
# ==========================================

@router.post("/page-label-management/upload")
async def page_label_upload(file: UploadFile = File(...)):
    """Upload PDF and analyze existing page labels."""
    return await _page_label_service.process_upload(file)

@router.post("/page-label-management/process")
async def page_label_process(
    file: UploadFile = File(...),
    request_id: str = Form(...),
    rules: str = Form(...),
    action: str = Form(...)  # 'apply' or 'remove'
):
    """Process PDF and apply or remove page labels based on rules."""
    return _page_label_service.process_labels(request_id, file.filename, rules, action)

@router.get("/page-label-management/download/{request_id}/{filename}")
async def page_label_download(request_id: str, filename: str):
    """Download the processed PDF with new page labels."""
    from pathlib import Path
    file_path = Path("temp_processing") / f"{request_id}_{filename}"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )

# ==========================================
# PAGE SIZE NORMALIZATION 
# ==========================================

import json
import os

@router.post("/page-size-normalization/upload")
async def page_size_normalization_upload(file: UploadFile = File(...)):
    """Upload PDF and analyze existing page sizes."""
    await _validate_upload(file)
    request_id = str(uuid.uuid4())
    upload_dir = Paths.request_upload(request_id)
    
    input_path = upload_dir / file.filename
    await save_upload(file.file, input_path)
    
    return _page_size_normalization_service.analyze_pdf(input_path, request_id, file.filename)

@router.post("/page-size-normalization/process")
async def page_size_normalization_process(
    file: UploadFile = File(...),
    request_id: str = Form(...),
    settings: str = Form(...)
):
    """Process PDF page sizes based on settings."""
    await _validate_upload(file)
    upload_dir = Paths.request_upload(request_id)
    output_dir = Paths.request_output(request_id)
    
    input_path = upload_dir / file.filename
    # Avoid saving if it already exists from the /upload step
    if not input_path.exists():
        await save_upload(file.file, input_path)
        
    output_filename = f"normalized_{file.filename}"
    output_path = output_dir / output_filename
    
    settings_dict = json.loads(settings)
    
    # Process
    import time
    start_t = time.time()
    processed_pages = _page_size_normalization_service.process_normalization(
        input_path, output_path, settings_dict
    )
    process_time = round(time.time() - start_t, 2)
    output_size = os.path.getsize(output_path)
    
    return {
        "request_id": request_id,
        "filename": output_filename,
        "processed_pages": processed_pages,
        "output_size": output_size,
        "processing_time": f"{process_time}s"
    }

@router.get("/page-size-normalization/download/{request_id}/{filename}")
async def page_size_normalization_download(request_id: str, filename: str):
    """Download the normalized PDF."""
    output_dir = Paths.request_output(request_id)
    output_path = output_dir / filename
    
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Processed file not found.")
        
    from starlette.background import BackgroundTask
    def cleanup():
        # Optional: cleanup directories if needed
        pass
            
    background_task = BackgroundTask(cleanup)
    
    return FileResponse(
        path=str(output_path),
        filename=filename,
        media_type=PDF_CONTENT_TYPE,
        background=background_task
    )


# ==========================================================
# ORGANIZE PDF ENDPOINTS
# ==========================================================

from app.organize_pdf_services.organize_pdf_service import organize_pdf_service


@router.post("/organize/upload")
async def organize_upload(
    request: Request,
    file: UploadFile = File(..., description="PDF to organize"),
):
    """Upload PDF and initialize organize session."""
    request_id: str = request.state.request_id
    try:
        saved = await _save_uploads([file], request_id)
        result = organize_pdf_service.upload_pdf_from_path(
            file_path=saved[0],
            filename=file.filename or "upload.pdf",
            request_id=request_id,
        )
        return result
    except Exception as exc:
        logger.exception("Organize upload failed [request_id=%s]", request_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/organize/process")
async def organize_process(
    request: Request,
    request_id: str = Form(...),
    output_name: str = Form("organized.pdf"),
    preserve_metadata: bool = Form(True),
    preserve_bookmarks: bool = Form(True),
    label_style: str = Form("arabic"),
    label_prefix: str = Form(""),
    label_restart: int = Form(0),
):
    """Process and generate the organized PDF."""
    try:
        result = organize_pdf_service.process_organize(
            request_id=request_id,
            output_name=output_name,
            preserve_metadata=preserve_metadata,
            preserve_bookmarks=preserve_bookmarks,
            label_style=label_style,
            label_prefix=label_prefix,
            label_restart=label_restart,
        )
        return result
    except Exception as exc:
        logger.exception("Organize process failed [request_id=%s]", request_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/organize/thumbnail")
async def organize_thumbnail(
    request: Request,
    request_id: str = Form(...),
    indices: str = Form(""),
    scale: float = Form(0.3),
):
    """Generate thumbnails for specified page indices."""
    try:
        idx_list = [int(i.strip()) for i in indices.split(",") if i.strip()] if indices else None
        result = organize_pdf_service.generate_thumbnails(
            request_id=request_id,
            indices=idx_list,
            scale=scale,
        )
        return result
    except Exception as exc:
        logger.exception("Organize thumbnail failed [request_id=%s]", request_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/organize/preview")
async def organize_preview(
    request: Request,
    request_id: str = Form(...),
    page_index: int = Form(...),
    scale: float = Form(1.0),
):
    """Generate high-quality preview for a single page."""
    try:
        result = organize_pdf_service.generate_preview(
            request_id=request_id,
            page_index=page_index,
            scale=scale,
        )
        return result
    except Exception as exc:
        logger.exception("Organize preview failed [request_id=%s]", request_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/organize/status/{request_id}")
async def organize_status(request_id: str):
    """Get organize session status."""
    return organize_pdf_service.get_status(request_id)


@router.get("/organize/download/{request_id}")
async def organize_download(request_id: str):
    """Download the organized PDF."""
    session = organize_pdf_service._sessions.get(request_id)
    if not session or not session.get("output_filename"):
        raise HTTPException(status_code=404, detail="Organized file not found or not yet processed.")
    filename = session["output_filename"]
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk.")
    return FileResponse(
        path=str(file_path),
        media_type=PDF_CONTENT_TYPE,
        filename=filename,
    )


@router.post("/organize/action")
async def organize_action(
    request: Request,
    action: str = Form(...),
    request_id: str = Form(...),
    params: str = Form("{}"),
):
    """Generic action endpoint for organize operations."""
    try:
        p = json.loads(params) if params else {}
        if action == "reorder":
            result = organize_pdf_service.reorder_pages(request_id, p.get("new_order", []))
        elif action == "rotate":
            result = organize_pdf_service.rotate_pages(request_id, p.get("indices", []), p.get("degrees", 90))
        elif action == "delete":
            result = organize_pdf_service.delete_pages(request_id, p.get("indices", []))
        elif action == "duplicate":
            result = organize_pdf_service.duplicate_pages(request_id, p.get("indices", []), p.get("copies", 1))
        elif action == "insert_blank":
            result = organize_pdf_service.insert_blank_page(request_id, p.get("position", 0), p.get("width", 595.27), p.get("height", 841.89))
        elif action == "move":
            result = organize_pdf_service.move_pages(request_id, p.get("indices", []), p.get("target", 0))
        elif action == "swap":
            result = organize_pdf_service.swap_pages(request_id, p.get("a", 0), p.get("b", 1))
        elif action == "reverse":
            result = organize_pdf_service.reverse_pages(request_id, p.get("indices"))
        elif action == "copy":
            result = organize_pdf_service.copy_to_clipboard(request_id, p.get("indices", []), "copy")
        elif action == "cut":
            result = organize_pdf_service.copy_to_clipboard(request_id, p.get("indices", []), "cut")
        elif action == "paste":
            result = organize_pdf_service.paste_from_clipboard(request_id, p.get("position", 0))
        elif action == "undo":
            result = organize_pdf_service.undo(request_id)
        elif action == "redo":
            result = organize_pdf_service.redo(request_id)
        elif action == "label":
            result = organize_pdf_service.apply_page_labels(request_id, p.get("style", "arabic"), p.get("prefix", ""), p.get("restart", 0), p.get("start", 1))
        elif action == "remove_labels":
            result = organize_pdf_service.remove_page_labels(request_id)
        elif action == "select":
            result_indices = organize_pdf_service.select_pages(request_id, p.get("mode", "all"), **{k: v for k, v in p.items() if k not in ("mode",)})
            result = {"success": True, "selected_indices": result_indices}
        elif action == "analyze":
            result = organize_pdf_service.analyze_pdf(request_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Organize action '%s' failed", action)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Scan to PDF ──────────────────────────────────────────────────────────────

@router.post("/scan/create")
async def scan_create_session(request: Request):
    request_id = request.state.request_id
    return scan_to_pdf_service.create_session(request_id)


@router.post("/scan/upload")
async def scan_upload_images(
    request: Request,
    files: List[UploadFile] = File(...),
    request_id: str = Form(...),
):
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    saved_names = []
    for f in files:
        ext = Path(f.filename or "").suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}:
            continue
        safe_name = f"{uuid.uuid4().hex[:8]}{ext}"
        dest = upload_dir / safe_name
        await save_upload(f.file, dest)
        saved_paths.append(dest)
        saved_names.append(f.filename or safe_name)
    return scan_to_pdf_service.upload_images(saved_paths, saved_names, request_id)


@router.post("/scan/add")
async def scan_add_image(
    request: Request,
    file: UploadFile = File(...),
    request_id: str = Form(...),
    position: Optional[int] = Form(None),
):
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "").suffix.lower()
    safe_name = f"{uuid.uuid4().hex[:8]}{ext}"
    dest = upload_dir / safe_name
    await save_upload(file.file, dest)
    return scan_to_pdf_service.add_image(dest, file.filename or safe_name, request_id, position)


@router.post("/scan/remove")
async def scan_remove_page(
    request: Request,
    page_id: str = Form(...),
    request_id: str = Form(...),
):
    return scan_to_pdf_service.remove_page(request_id, page_id)


@router.post("/scan/duplicate")
async def scan_duplicate_page(
    request: Request,
    page_id: str = Form(...),
    request_id: str = Form(...),
):
    return scan_to_pdf_service.duplicate_page(request_id, page_id)


@router.post("/scan/rotate")
async def scan_rotate_page(
    request: Request,
    page_id: str = Form(...),
    degrees: int = Form(90),
    request_id: str = Form(...),
):
    return scan_to_pdf_service.rotate_page(request_id, page_id, degrees)


@router.post("/scan/reorder")
async def scan_reorder_pages(
    request: Request,
    new_order: str = Form(...),
    request_id: str = Form(...),
):
    import json
    order = json.loads(new_order)
    return scan_to_pdf_service.reorder_pages(request_id, order)


@router.post("/scan/enhance")
async def scan_enhance(
    request: Request,
    request_id: str = Form(...),
    page_id: Optional[str] = Form(None),
):
    if page_id:
        return scan_to_pdf_service.enhance_page(request_id, page_id)
    return scan_to_pdf_service.enhance_all(request_id)


@router.post("/scan/generate")
async def scan_generate_pdf(
    request: Request,
    request_id: str = Form(...),
    page_size: str = Form("a4"),
    orientation: str = Form("auto"),
    quality: str = Form("high"),
    compress: bool = Form(False),
    color_mode: str = Form("color"),
    output_name: Optional[str] = Form(None),
):
    return scan_to_pdf_service.generate_pdf(
        request_id, page_size, orientation, quality, compress, color_mode, output_name
    )


@router.post("/scan/export-zip")
async def scan_export_zip(
    request: Request,
    request_id: str = Form(...),
):
    return scan_to_pdf_service.generate_zip(request_id)


@router.get("/scan/thumbnail/{request_id}/{page_id}")
async def scan_thumbnail(request_id: str, page_id: str, max_size: int = 200):
    data = scan_to_pdf_service.generate_thumbnail(request_id, page_id, max_size)
    if data is None:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return Response(content=data, media_type="image/jpeg")


@router.get("/scan/status/{request_id}")
async def scan_status(request_id: str):
    return scan_to_pdf_service.get_status(request_id)


@router.get("/scan/download/{request_id}/{filename}")
async def scan_download(request_id: str, filename: str):
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "application/pdf" if filename.endswith(".pdf") else "application/zip"
    return FileResponse(path=str(file_path), media_type=media_type, filename=filename)


# ── Rich Media (Embed Audio/Video) ─────────────────────────────────────────

@router.post("/rich-media/create")
async def rich_media_create(request: Request):
    request_id = request.state.request_id
    return rich_media_service.create_session(request_id)


@router.post("/rich-media/upload-pdf")
async def rich_media_upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    request_id: str = Form(...),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".pdf"}:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid.uuid4().hex[:8]}{ext}"
    await save_upload(file.file, dest)
    return rich_media_service.upload_pdf(dest, file.filename or "upload.pdf", request_id)


@router.post("/rich-media/upload-media")
async def rich_media_upload_media(
    request: Request,
    file: UploadFile = File(...),
    request_id: str = Form(...),
):
    ext = Path(file.filename or "").suffix.lower()
    allowed = {".mp4", ".avi", ".mov", ".webm", ".mp3", ".wav", ".gif", ".m4a", ".ogg", ".flac"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported media format: {ext}")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}{ext}"
    dest = upload_dir / safe_name
    await save_upload(file.file, dest)
    return rich_media_service.upload_media(dest, file.filename or safe_name, request_id)


@router.get("/rich-media/preview/{request_id}/{page_index}")
async def rich_media_preview(request_id: str, page_index: int, max_size: int = 800):
    data = rich_media_service.get_page_preview(request_id, page_index, max_size)
    if data is None:
        raise HTTPException(status_code=404, detail="Preview not available")
    return Response(content=data, media_type="image/jpeg")


@router.post("/rich-media/add-placement")
async def rich_media_add_placement(
    request: Request,
    request_id: str = Form(...),
    media_id: str = Form(...),
    page_index: int = Form(0),
    x: float = Form(10.0),
    y: float = Form(10.0),
    width: float = Form(30.0),
    height: float = Form(25.0),
    autoplay: bool = Form(False),
    loop: bool = Form(False),
    muted: bool = Form(False),
    show_controls: bool = Form(True),
    play_on_click: bool = Form(False),
    interaction_mode: str = Form("embedded"),
    start_time: float = Form(0.0),
    end_time: float = Form(0.0),
    volume: float = Form(1.0),
    rotation: float = Form(0.0),
    poster_media_id: Optional[str] = Form(None),
):
    return rich_media_service.add_placement(
        request_id, media_id, page_index, x, y, width, height,
        autoplay, loop, muted, show_controls,
        play_on_click, interaction_mode, start_time, end_time,
        volume, rotation, poster_media_id,
    )


@router.post("/rich-media/update-placement")
async def rich_media_update_placement(
    request: Request,
    request_id: str = Form(...),
    placement_id: str = Form(...),
    x: Optional[float] = Form(None),
    y: Optional[float] = Form(None),
    width: Optional[float] = Form(None),
    height: Optional[float] = Form(None),
    autoplay: Optional[bool] = Form(None),
    loop: Optional[bool] = Form(None),
    muted: Optional[bool] = Form(None),
    show_controls: Optional[bool] = Form(None),
    play_on_click: Optional[bool] = Form(None),
    interaction_mode: Optional[str] = Form(None),
    start_time: Optional[float] = Form(None),
    end_time: Optional[float] = Form(None),
    volume: Optional[float] = Form(None),
    rotation: Optional[float] = Form(None),
):
    kwargs = {}
    if x is not None: kwargs["x"] = x
    if y is not None: kwargs["y"] = y
    if width is not None: kwargs["width"] = width
    if height is not None: kwargs["height"] = height
    if autoplay is not None: kwargs["autoplay"] = autoplay
    if loop is not None: kwargs["loop"] = loop
    if muted is not None: kwargs["muted"] = muted
    if show_controls is not None: kwargs["show_controls"] = show_controls
    if play_on_click is not None: kwargs["play_on_click"] = play_on_click
    if interaction_mode is not None: kwargs["interaction_mode"] = interaction_mode
    if start_time is not None: kwargs["start_time"] = start_time
    if end_time is not None: kwargs["end_time"] = end_time
    if volume is not None: kwargs["volume"] = volume
    if rotation is not None: kwargs["rotation"] = rotation
    return rich_media_service.update_placement(request_id, placement_id, **kwargs)


@router.post("/rich-media/remove-placement")
async def rich_media_remove_placement(
    request: Request,
    request_id: str = Form(...),
    placement_id: str = Form(...),
):
    return rich_media_service.remove_placement(request_id, placement_id)


@router.post("/rich-media/remove-media")
async def rich_media_remove_media(
    request: Request,
    request_id: str = Form(...),
    media_id: str = Form(...),
):
    return rich_media_service.remove_media(request_id, media_id)


@router.post("/rich-media/duplicate-placement")
async def rich_media_duplicate_placement(
    request: Request,
    request_id: str = Form(...),
    placement_id: str = Form(...),
):
    return rich_media_service.duplicate_placement(request_id, placement_id)


@router.post("/rich-media/upload-poster")
async def rich_media_upload_poster(
    request: Request,
    file: UploadFile = File(...),
    request_id: str = Form(...),
    media_id: str = Form(...),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        raise HTTPException(status_code=400, detail="Poster must be JPG, PNG, WebP, or BMP")
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"poster_{uuid.uuid4().hex[:8]}{ext}"
    dest = upload_dir / safe_name
    await save_upload(file.file, dest)
    return rich_media_service.upload_poster(dest, file.filename or safe_name, request_id, media_id)


@router.post("/rich-media/auto-poster")
async def rich_media_auto_poster(
    request: Request,
    request_id: str = Form(...),
    media_id: str = Form(...),
):
    return rich_media_service.auto_generate_poster(request_id, media_id)


@router.post("/rich-media/delete-poster")
async def rich_media_delete_poster(
    request: Request,
    request_id: str = Form(...),
    media_id: str = Form(...),
):
    return rich_media_service.delete_poster(request_id, media_id)


@router.post("/rich-media/process")
async def rich_media_process(
    request: Request,
    request_id: str = Form(...),
    output_name: Optional[str] = Form(None),
):
    return rich_media_service.process(request_id, output_name)


@router.get("/rich-media/status/{request_id}")
async def rich_media_status(request_id: str):
    return rich_media_service.get_status(request_id)


@router.get("/rich-media/download/{request_id}/{filename}")
async def rich_media_download(request_id: str, filename: str):
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
    )


# ── PDF to Single Long Image ────────────────────────────────────────────────

@router.post("/pdf-to-long-image/upload")
async def pdf_to_long_image_upload(
    request: Request,
    file: UploadFile = File(..., description="PDF to convert"),
):
    """Upload PDF and return analysis (page count, dimensions, etc.)."""
    await _validate_upload(file)
    request_id = request.state.request_id
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid.uuid4().hex[:8]}.pdf"
    await save_upload(file.file, dest)
    try:
        analysis = await pdf_to_long_image_service.analyze(dest)
        return {
            "success": True,
            "request_id": request_id,
            "analysis": analysis.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pdf-to-long-image/process")
async def pdf_to_long_image_process(
    request: Request,
    request_id: str = Form(...),
    pages: str = Form("all"),
    output_format: str = Form("png"),
    dpi: int = Form(300),
    quality: str = Form("high"),
    page_gap: int = Form(10),
    bg_color: str = Form("#ffffff"),
    alignment: str = Form("center"),
    max_width: int = Form(0),
):
    """Render PDF pages and stitch into one long image."""
    try:
        # Locate the uploaded PDF
        upload_dir = Paths.request_upload(request_id)
        pdf_files = list(upload_dir.glob("*.pdf"))
        if not pdf_files:
            raise HTTPException(status_code=400, detail="No PDF uploaded. Upload first.")
        input_pdf = pdf_files[0]

        result = await pdf_to_long_image_service.process(
            input_pdf=input_pdf,
            request_id=request_id,
            pages_selection=pages,
            output_format=output_format,
            dpi=dpi,
            quality=quality,
            page_gap=page_gap,
            bg_color=bg_color,
            alignment=alignment,
            max_width=max_width,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("PDF-to-long-image failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pdf-to-long-image/download/{request_id}/{filename}")
async def pdf_to_long_image_download(request_id: str, filename: str):
    """Download the generated long image."""
    file_path = Paths.request_output(request_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    ext = Path(filename).suffix.lower()
    media_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
    }
    media_type = media_map.get(ext, "application/octet-stream")
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )
