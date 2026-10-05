"""
API Routes for Compare PDF & Redaction features.
"""

from __future__ import annotations

import io
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.core.paths import Paths
from app.Compare_and_redaction_services.compare_pdf_service import compare_pdf_service
from app.Compare_and_redaction_services.redact_pdf_service import redact_pdf_service
from app.Compare_and_redaction_services.duplicate_check_service import duplicate_check_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/compare/process")
async def compare_pdf_process(
    request: Request,
    original_file: UploadFile = File(...),
    revised_file: UploadFile = File(...),
    mode: str = Form("smart"),
    ignore_whitespace: Any = Form(False),
    ignore_case: Any = Form(False),
    ignore_formatting: Any = Form(False),
    ignore_metadata: Any = Form(False),
    ignore_headers_footers: Any = Form(False),
    ignore_annotations: Any = Form(False),
    ignore_font_changes: Any = Form(False),
):
    """Upload original and revised PDFs and perform full multi-layer comparison."""
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = getattr(request.state, "request_id", uuid.uuid4().hex[:16])

    if not original_file or not original_file.filename:
        raise HTTPException(status_code=400, detail="Original PDF file is required.")
    if not revised_file or not revised_file.filename:
        raise HTTPException(status_code=400, detail="Revised PDF file is required.")

    orig_bytes = await original_file.read()
    rev_bytes = await revised_file.read()

    if not orig_bytes:
        raise HTTPException(status_code=400, detail="Original PDF file is empty.")
    if not rev_bytes:
        raise HTTPException(status_code=400, detail="Revised PDF file is empty.")

    options = {
        "mode": mode,
        "ignore_whitespace": ignore_whitespace,
        "ignore_case": ignore_case,
        "ignore_formatting": ignore_formatting,
        "ignore_metadata": ignore_metadata,
        "ignore_headers_footers": ignore_headers_footers,
        "ignore_annotations": ignore_annotations,
        "ignore_font_changes": ignore_font_changes,
    }

    try:
        result = await compare_pdf_service.compare(
            request_id=request_id,
            original_bytes=orig_bytes,
            revised_bytes=rev_bytes,
            options=options,
        )
        if not result.get("success") and result.get("is_protected"):
            raise HTTPException(status_code=400, detail=result.get("message", "Document is password protected."))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Compare PDF processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare/view-page/{request_id}/{page_num}")
async def compare_pdf_view_page(
    request_id: str, page_num: int, mode: str = "side_by_side", active_diff: int = -1
):
    """View rendered side-by-side or overlay diff PNG image for a specific page."""
    if re.search(r"[\\/]", request_id) or page_num < 1:
        raise HTTPException(status_code=400, detail="Invalid request.")

    try:
        img_bytes = compare_pdf_service.render_page_diff_image(
            request_id, page_num, mode=mode, active_diff_index=active_diff
        )
        if not img_bytes:
            raise HTTPException(status_code=404, detail="Page image not found.")
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Page render error for request {request_id} page {page_num}: {e}")
        raise HTTPException(status_code=500, detail="Failed to render page comparison.")


@router.get("/compare/download-report/{request_id}")
async def compare_pdf_download_report(request_id: str):
    """Download the summary comparison PDF report."""
    if re.search(r"[\\/]", request_id):
        raise HTTPException(status_code=400, detail="Invalid request.")

    out_dir = Paths.request_output(request_id)
    report_file = out_dir / "comparison_report.pdf"

    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Comparison report not found.")

    return FileResponse(
        path=str(report_file),
        media_type="application/pdf",
        filename=f"Compare_Report_{request_id}.pdf",
    )


@router.get("/compare/download-highlighted/{request_id}")
async def compare_pdf_download_highlighted(request_id: str):
    """Download the color-coded highlighted comparison PDF."""
    if re.search(r"[\\/]", request_id):
        raise HTTPException(status_code=400, detail="Invalid request.")

    out_dir = Paths.request_output(request_id)
    highlighted_file = out_dir / "comparison_highlighted.pdf"

    if not highlighted_file.exists():
        raise HTTPException(status_code=404, detail="Highlighted comparison PDF not found.")

    return FileResponse(
        path=str(highlighted_file),
        media_type="application/pdf",
        filename=f"Highlighted_Comparison_{request_id}.pdf",
    )


# ── REDACT PDF ENDPOINTS ──────────────────────────────────────────────────

class RedactSearchRequest(BaseModel):
    session_id: str
    query: str
    case_sensitive: bool = False
    whole_word: bool = False


class RedactPatternRequest(BaseModel):
    session_id: str
    pattern_keys: Optional[list[str]] = None


class RedactSensitiveRequest(BaseModel):
    session_id: str


class RedactApplyRequest(BaseModel):
    session_id: str
    redactions: list[dict[str, Any]]
    fill_color: str = "#000000"
    label: str = ""
    security_options: Optional[dict[str, bool]] = None


@router.post("/redact/initialize")
async def redact_pdf_initialize(request: Request, file: UploadFile = File(...)):
    """Upload a PDF document and initialize a redaction session."""
    session_id = request.headers.get("X-Request-ID")
    if not session_id:
        session_id = getattr(request.state, "request_id", uuid.uuid4().hex[:16])

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        res = await redact_pdf_service.initialize_session(session_id, pdf_bytes)
        if not res.get("success") and res.get("is_protected"):
            raise HTTPException(status_code=400, detail=res.get("message", "Document is encrypted."))
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Redact initialization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/redact/render-page/{session_id}/{page_num}")
async def redact_pdf_render_page(session_id: str, page_num: int, dpi: int = 150):
    """Render a single PDF page for workspace preview."""
    if re.search(r"[\\/]", session_id) or page_num < 1:
        raise HTTPException(status_code=400, detail="Invalid request parameters.")

    try:
        img_bytes = redact_pdf_service.render_page_image(session_id, page_num, dpi=dpi)
        if not img_bytes:
            raise HTTPException(status_code=404, detail="Page render not found.")
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Redact page render error for session {session_id} page {page_num}: {e}")
        raise HTTPException(status_code=500, detail="Failed to render page image.")


@router.post("/redact/search")
async def redact_pdf_search(payload: RedactSearchRequest):
    """Search text in the document and return match bounding boxes."""
    if not payload.session_id or re.search(r"[\\/]", payload.session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")
    try:
        matches = redact_pdf_service.search_text(
            session_id=payload.session_id,
            query=payload.query,
            case_sensitive=payload.case_sensitive,
            whole_word=payload.whole_word,
        )
        return {"success": True, "count": len(matches), "matches": matches}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Redact search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/redact/detect-patterns")
async def redact_pdf_detect_patterns(payload: RedactPatternRequest):
    """Detect sensitive patterns (Email, Phone, Aadhaar, PAN, Credit Card, etc.) using regex."""
    if not payload.session_id or re.search(r"[\\/]", payload.session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")
    try:
        candidates = redact_pdf_service.detect_patterns(
            session_id=payload.session_id, pattern_keys=payload.pattern_keys
        )
        return {"success": True, "count": len(candidates), "candidates": candidates}
    except Exception as e:
        logger.error(f"Redact pattern detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/redact/detect-sensitive")
async def redact_pdf_detect_sensitive(payload: RedactSensitiveRequest):
    """Run comprehensive sensitive data detection across all categories."""
    if not payload.session_id or re.search(r"[\\/]", payload.session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")
    try:
        candidates = redact_pdf_service.detect_sensitive_data(session_id=payload.session_id)
        return {"success": True, "count": len(candidates), "candidates": candidates}
    except Exception as e:
        logger.error(f"Redact sensitive detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/redact/apply")
async def redact_pdf_apply(payload: RedactApplyRequest):
    """Apply TRUE permanent PyMuPDF redaction and security sanitization."""
    if not payload.session_id or re.search(r"[\\/]", payload.session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")
    if not payload.redactions:
        raise HTTPException(status_code=400, detail="No redaction regions provided.")

    try:
        res = redact_pdf_service.apply_redaction(
            session_id=payload.session_id,
            redactions=payload.redactions,
            fill_color=payload.fill_color,
            label=payload.label,
            security_options=payload.security_options,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Redaction apply error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/redact/download/{session_id}")
async def redact_pdf_download(session_id: str):
    """Download the final sanitized and permanently redacted PDF file."""
    if re.search(r"[\\/]", session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")

    out_dir = Paths.request_output(session_id)
    redacted_file = out_dir / "redacted_output.pdf"

    if not redacted_file.exists():
        raise HTTPException(status_code=404, detail="Redacted PDF file not found.")

    return FileResponse(
        path=str(redacted_file),
        media_type="application/pdf",
        filename=f"Redacted_Document_{session_id}.pdf",
    )


# ── DUPLICATE CHECK ENDPOINTS ─────────────────────────────────────────────

class DuplicateCleanRequest(BaseModel):
    session_id: str
    remove_pages: list[dict[str, Any]]


@router.post("/duplicate/analyze")
async def duplicate_check_analyze(
    request: Request,
    files: list[UploadFile] = File(...),
    mode: str = Form("balanced"),
    threshold: int = Form(85),
    check_pages: Any = Form(True),
    check_text: Any = Form(True),
    check_images: Any = Form(True),
    ignore_headers: Any = Form(True),
    ignore_footers: Any = Form(True),
    ignore_page_numbers: Any = Form(True),
):
    """Analyze single or multiple uploaded PDF files for exact and near duplicates."""
    session_id = request.headers.get("X-Request-ID")
    if not session_id:
        session_id = getattr(request.state, "request_id", uuid.uuid4().hex[:16])

    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file is required.")

    files_map: dict[str, bytes] = {}
    for f in files:
        if not f.filename:
            continue
        content = await f.read()
        if content:
            files_map[f.filename] = content

    if not files_map:
        raise HTTPException(status_code=400, detail="No valid PDF content uploaded.")

    options = {
        "mode": mode,
        "threshold": threshold,
        "check_pages": check_pages,
        "check_text": check_text,
        "check_images": check_images,
        "ignore_headers": ignore_headers,
        "ignore_footers": ignore_footers,
        "ignore_page_numbers": ignore_page_numbers,
    }

    try:
        res = await duplicate_check_service.analyze_duplicates(session_id, files_map, options)
        if not res.get("success") and res.get("is_protected"):
            raise HTTPException(status_code=400, detail=res.get("message", "Document is encrypted."))
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Duplicate check analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/duplicate/clean")
async def duplicate_check_clean(payload: DuplicateCleanRequest):
    """Generate a clean PDF by removing user-selected duplicate pages."""
    if not payload.session_id or re.search(r"[\\/]", payload.session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")
    if not payload.remove_pages:
        raise HTTPException(status_code=400, detail="No pages specified for removal.")

    try:
        res = duplicate_check_service.generate_cleaned_pdf(
            session_id=payload.session_id, remove_specs=payload.remove_pages
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Duplicate clean error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/duplicate/download-cleaned/{session_id}")
async def duplicate_check_download_cleaned(session_id: str):
    """Download the cleaned PDF file with duplicates removed."""
    if re.search(r"[\\/]", session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")

    out_dir = Paths.request_output(session_id)
    cleaned_file = out_dir / "cleaned_document.pdf"

    if not cleaned_file.exists():
        raise HTTPException(status_code=404, detail="Cleaned PDF file not found.")

    return FileResponse(
        path=str(cleaned_file),
        media_type="application/pdf",
        filename=f"Cleaned_Document_{session_id}.pdf",
    )


@router.get("/duplicate/download-report/{session_id}")
async def duplicate_check_download_report(session_id: str):
    """Download the duplicate analysis summary PDF report."""
    if re.search(r"[\\/]", session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")

    out_dir = Paths.request_output(session_id)
    report_file = out_dir / "duplicate_analysis_report.pdf"

    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Duplicate report file not found.")

    return FileResponse(
        path=str(report_file),
        media_type="application/pdf",
        filename=f"Duplicate_Report_{session_id}.pdf",
    )


@router.get("/duplicate/view-page/{session_id}/{doc_idx}/{page_num}")
async def duplicate_check_view_page(
    session_id: str, doc_idx: int, page_num: int, active_group: int = -1
):
    """View high-resolution rendered duplicate page preview with color-coded bounding box highlights."""
    if re.search(r"[\\/]", session_id) or page_num < 1 or doc_idx < 0:
        raise HTTPException(status_code=400, detail="Invalid request parameters.")

    try:
        img_bytes = duplicate_check_service.render_page_duplicate_image(
            session_id=session_id, doc_index=doc_idx, page_num=page_num, active_group_id=active_group
        )
        if not img_bytes:
            raise HTTPException(status_code=404, detail="Duplicate page preview image not found.")
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Duplicate page preview error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



