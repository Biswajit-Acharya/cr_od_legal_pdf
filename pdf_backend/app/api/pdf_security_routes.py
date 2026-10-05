"""
API Routes for PDF Security features.
"""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.paths import Paths
from app.utils.file_handler import save_upload
from app.pdf_security_services.security_service import pdf_security_service
from app.pdf_security_services.protect_pdf_service import protect_pdf_service
from app.pdf_security_services.unlock_pdf_service import unlock_pdf_service
from app.pdf_security_services.digital_signature_verification_service import (
    digital_signature_verification_service,
)
from app.pdf_security_services.document_integrity_verification_service import (
    document_integrity_verification_service,
)
from app.pdf_security_services.watermark_protection_service import watermark_protection_service
from app.pdf_security_services.file_expiration_service import file_expiration_service
from app.pdf_security_services.secure_sharing_service import SecureSharingService
from app.pdf_security_services.malware_scan_service import malware_scan_service
from app.pdf_security_services.unsafe_link_detection_service import unsafe_link_detection_service
from app.pdf_security_services.security_score_service import security_score_service
from app.pdf_security_services.pdf_security_policy_templates_service import (
    pdf_security_policy_template_service,
)
from app.pdf_security_services.remove_javascript_service import remove_javascript_service
from app.pdf_security_services.atomic_server_timestamping_service import atomic_server_timestamping_service
from app.pdf_security_services.pdf_metadata_protection_service import pdf_metadata_protection_service
from app.pdf_security_services.pdf_sanitization_service import pdf_sanitization_service
from app.pdf_security_services.pdf_forensic_analysis_service import pdf_forensic_analysis_service
from app.pdf_security_services.embedded_media_detection_service import embedded_media_detection_service
from app.pdf_security_services.pdf_version_security_check_service import pdf_version_security_check_service
from app.pdf_security_services.restrict_accessibility_copy_service import restrict_accessibility_copy_service
from app.pdf_security_services.trusted_certificates_service import trusted_certificates_service
from app.pdf_security_services.pdfa_validation_service import pdfa_validation_service
from app.pdf_security_services.blackout_areas_service import blackout_areas_service
from app.pdf_security_services.hide_sensitive_information_service import hide_sensitive_information_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ── HELPERS ──────────────────────────────────────────────────────────────

def _get_request_id(request: Request) -> str:
    rid = request.headers.get("X-Request-ID")
    if not rid:
        rid = getattr(request.state, "request_id", uuid.uuid4().hex[:16])
    return rid


def _save_upload_to_request(file: UploadFile, request_id: str) -> tuple[Path, str]:
    """Save an uploaded file to the request upload directory and return (path, filename)."""
    filename = Path(file.filename or f"upload_{uuid.uuid4().hex[:8]}.pdf").name
    upload_dir = Paths.request_upload(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    import shutil
    file.file.seek(0)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return dest, filename


def _output_path(request_id: str, filename: str) -> Path:
    return Paths.request_output(request_id) / filename


def _download_url(request_id: str, filename: str) -> str:
    return f"/api/pdf/download/{request_id}/{filename}"


def _signature_verification_dir() -> Path:
    path = Paths.outputs() / "digital_signature_verifications"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _document_integrity_dir() -> Path:
    path = Paths.outputs() / "document_integrity_verifications"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _security_score_dir() -> Path:
    path = Paths.outputs() / "security_score_reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_upload_name(upload_file: UploadFile, default_suffix: str = ".pdf") -> str:
    suffix = Path(upload_file.filename or default_suffix).suffix.lower() or default_suffix
    if suffix != ".pdf":
        suffix = default_suffix
    return f"{uuid.uuid4().hex}{suffix}"


# ── 1. PROTECT PDF ──────────────────────────────────────────────────────

@router.post("/security/protect")
async def protect_pdf(
    request: Request,
    file: UploadFile = File(...),
    user_password: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    confirm_password: Optional[str] = Form(None),
    owner_password: Optional[str] = Form(None),
    encryption: str = Form("aes-256"),
    allow_print: bool = Form(False),
    allow_high_quality_print: bool = Form(False),
    allow_copy: bool = Form(False),
    allow_edit: bool = Form(False),
    allow_form_fill: bool = Form(False),
    allow_comment: bool = Form(False),
    allow_accessibility: bool = Form(True),
    allow_page_extraction: bool = Form(False),
    allow_document_assembly: bool = Form(False),
):
    """Password protect a PDF with AES encryption and permission controls."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")
    open_password = user_password if user_password is not None else password
    if not open_password:
        raise HTTPException(status_code=400, detail="Password is required.")

    try:
        filename = file.filename or f"upload_{uuid.uuid4().hex[:8]}.pdf"
        upload_path = Paths.request_upload(request_id) / filename
        await save_upload(file.file, upload_path)
        output_file = f"protected_{filename}"
        out_path = _output_path(request_id, output_file)

        result = protect_pdf_service.protect_pdf(
            input_path=str(upload_path),
            output_path=str(out_path),
            user_password=open_password,
            confirm_password=confirm_password,
            owner_password=owner_password,
            encryption=encryption,
            allow_print=allow_print,
            allow_high_quality_print=allow_high_quality_print,
            allow_copy=allow_copy,
            allow_edit=allow_edit,
            allow_form_fill=allow_form_fill,
            allow_comment=allow_comment,
            allow_accessibility=allow_accessibility,
            allow_page_extraction=allow_page_extraction,
            allow_document_assembly=allow_document_assembly,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Protection failed."))

        return {
            **result,
            "download_url": _download_url(request_id, output_file),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"protect_pdf error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 2. UNLOCK PDF ───────────────────────────────────────────────────────

@router.post("/security/unlock")
async def unlock_pdf(
    request: Request,
    file: UploadFile = File(...),
    password: str = Form(...),
):
    """Remove password protection from a PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required.")

    try:
        filename = file.filename or f"upload_{uuid.uuid4().hex[:8]}.pdf"
        upload_path = Paths.request_upload(request_id) / filename
        await save_upload(file.file, upload_path)
        output_file = f"unlocked_{filename}"
        out_path = _output_path(request_id, output_file)

        result = unlock_pdf_service.unlock_pdf(str(upload_path), str(out_path), password)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unlock failed."))

        return {
            **result,
            "download_url": _download_url(request_id, output_file),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"unlock_pdf error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 3. REMOVE JAVASCRIPT ───────────────────────────────────────────────

@router.post("/security/remove-javascript")
async def remove_javascript(
    request: Request,
    file: UploadFile = File(...),
):
    """Remove embedded JavaScript from a PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = remove_javascript_service.remove_javascript(str(upload_path), request_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "JavaScript removal failed."))

        return result
    except ValueError as e:
        logger.warning(f"remove_javascript validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"remove_javascript error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred during JavaScript sanitization.")


# ============================================================
# SUB SECTION-7 — REMOVE FORM DATA
# ============================================================

@router.post("/security/remove-form-data")
async def remove_form_data(
    request: Request,
    file: UploadFile = File(...),
):
    """Remove entered values from PDF form fields and restore the form to a blank reusable state."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")

        upload_path, filename = _save_upload_to_request(file, request_id)

        from app.pdf_security_services.remove_form_data_service import process as rfd_process
        result = rfd_process(str(upload_path), request_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Form data removal failed."))

        output_file = result.get("output_file")
        if output_file:
            result["download_url"] = _download_url(request_id, output_file)

        return {
            **result,
            "original_filename": filename,
        }
    except ValueError as e:
        logger.warning(f"remove_form_data validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"remove_form_data error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred during form data removal.")


# ============================================================
# SUB SECTION-6 — REMOVE HIDDEN DATA
# ============================================================

@router.post("/security/remove-hidden-data")
async def remove_hidden_data(
    request: Request,
    file: UploadFile = File(...),
):
    """Remove hidden data, metadata, and attachments from a PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")

        upload_path, filename = _save_upload_to_request(file, request_id)

        from app.pdf_security_services.remove_hidden_data_service import process as rhd_process
        result = rhd_process(str(upload_path), request_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Hidden data removal failed."))

        return {
            **result,
            "original_filename": filename
        }
    except ValueError as e:
        logger.warning(f"remove_hidden_data validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"remove_hidden_data error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred during sanitization.")


# ── 6. RESTRICT EXTRACTION ─────────────────────────────────────────────

@router.post("/security/restrict-extraction")
async def restrict_extraction(
    request: Request,
    file: UploadFile = File(...),
):
    """Restrict page extraction from a PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)
        output_file = f"no_extract_{filename}"
        out_path = _output_path(request_id, output_file)

        result = pdf_security_service.restrict_extraction(str(upload_path), str(out_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Extraction restriction failed."))

        return {
            **result,
            "download_url": _download_url(request_id, output_file),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"restrict_extraction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 7. RESTRICT COPY ───────────────────────────────────────────────────

@router.post("/security/restrict-copy")
async def restrict_copy(
    request: Request,
    file: UploadFile = File(...),
):
    """Restrict text copying and accessibility."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)
        output_file = f"no_copy_{filename}"
        out_path = _output_path(request_id, output_file)

        result = pdf_security_service.restrict_copy(str(upload_path), str(out_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Copy restriction failed."))

        return {
            **result,
            "download_url": _download_url(request_id, output_file),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"restrict_copy error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 8. SECURITY SCORE ──────────────────────────────────────────────────

@router.post("/security/security-score")
async def security_score(
    request: Request,
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
):
    """Analyze a PDF and return a transparent deterministic security score."""
    request_id = _get_request_id(request)
    upload_path: Optional[Path] = None

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path = Paths.request_upload(request_id) / _safe_upload_name(file)
        await save_upload(file.file, upload_path)
        result = security_score_service.analyze_pdf(
            str(upload_path),
            original_filename=file.filename,
            mime_type=file.content_type,
            password=password,
            output_dir=_security_score_dir(),
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Security score failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"security_score error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Security analysis could not be completed. Please try again.")
    finally:
        if upload_path is not None:
            try:
                upload_path.unlink(missing_ok=True)
            except Exception:
                logger.warning("Could not clean security score upload: %s", upload_path)


@router.get("/security/security-score/result/{analysis_id}")
async def security_score_result(analysis_id: str):
    """Return a stored security score result."""
    try:
        return security_score_service.load_result(_security_score_dir(), analysis_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as e:
        logger.error(f"security_score_result error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load security score result.")


@router.get("/security/security-score/report/{analysis_id}")
async def security_score_report(analysis_id: str):
    """Download a stored security score report."""
    try:
        report_path = security_score_service.report_path(_security_score_dir(), analysis_id)
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Security score report not found.")
        return FileResponse(path=str(report_path), media_type="application/pdf", filename=report_path.name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"security_score_report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download security score report.")


# ── 9. MALWARE SCAN ────────────────────────────────────────────────────

@router.post("/security/malware-scan")
async def malware_scan(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Scans a PDF for malware using local ClamAV and performs static structure analysis.
    """
    request_id = _get_request_id(request)
    upload_path, filename = _save_upload_to_request(file, request_id)

    try:
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")

        result = await malware_scan_service.scan_pdf(upload_path, filename, request_id)
        # Note: Do not return {"success": True, **result} here if it breaks frontend.
        # But actually we can return success since our new frontend parses result.clamav
        return {"success": True, **result}

    finally:
        # Secure cleanup
        try:
            if upload_path.exists():
                upload_path.unlink()
        except Exception as e:
            logger.error(f"Failed to cleanup temp file {upload_path}: {e}")


# ── 10. PDF/A VALIDATION ───────────────────────────────────────────────

@router.post("/security/pdfa-validation")
async def pdfa_validation(
    request: Request,
    file: UploadFile = File(...),
):
    """Validate PDF/A compliance of a document."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.validate_pdfa(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "PDF/A validation failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"pdfa_validation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 11. DIGITAL SIGNATURE VERIFY ───────────────────────────────────────

@router.post("/security/digital-signature-verify")
@router.post("/digital-signature-verification/verify")
async def digital_signature_verify(
    request: Request,
    file: UploadFile = File(...),
):
    """Verify digital signatures in a PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        filename = file.filename or f"upload_{uuid.uuid4().hex[:8]}.pdf"
        upload_path = Paths.request_upload(request_id) / filename
        await save_upload(file.file, upload_path)
        result = digital_signature_verification_service.verify_pdf(
            str(upload_path),
            original_filename=filename,
            output_dir=_signature_verification_dir(),
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Signature verification failed."))

        verification_id = result.get("verification_id")
        if verification_id:
            result["result_url"] = f"/api/pdf/security/digital-signature-verify/result/{verification_id}"
            result["report_url"] = f"/api/pdf/security/digital-signature-verify/report/{verification_id}"

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"digital_signature_verify error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security/digital-signature-verify/result/{verification_id}")
@router.get("/digital-signature-verification/result/{verification_id}")
async def digital_signature_result(verification_id: str):
    """Return a stored digital signature verification result."""
    try:
        return digital_signature_verification_service.load_result(
            _signature_verification_dir(),
            verification_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as e:
        logger.error(f"digital_signature_result error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load verification result.")


@router.get("/security/digital-signature-verify/report/{verification_id}")
@router.get("/digital-signature-verification/report/{verification_id}")
async def digital_signature_report(verification_id: str):
    """Download a stored digital signature verification report."""
    try:
        report_path = digital_signature_verification_service.report_path(
            _signature_verification_dir(),
            verification_id,
        )
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Verification report not found.")
        return FileResponse(
            path=str(report_path),
            media_type="application/pdf",
            filename=report_path.name,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"digital_signature_report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download verification report.")


# ── 12. DOCUMENT INTEGRITY ─────────────────────────────────────────────

@router.post(
    "/security/document-integrity",
    summary="Document Integrity Verification",
    description=(
        "Validate an uploaded PDF, calculate SHA-256/SHA-512 fingerprints, analyze PDF structure, "
        "detect digital signatures and incremental updates, extract metadata, and optionally compare "
        "against a trusted reference PDF. Hashes alone are fingerprints and do not prove authenticity "
        "without a trusted reference or validated signature."
    ),
)
@router.post(
    "/document-integrity/verify",
    summary="Document Integrity Verification",
    description="Verify PDF integrity indicators and optionally compare with a trusted reference PDF.",
)
async def document_integrity(
    request: Request,
    file: UploadFile = File(..., description="PDF document to verify."),
    reference_file: Optional[UploadFile] = File(None, description="Optional trusted reference PDF for byte-level comparison."),
):
    """Verify document integrity without claiming authenticity from hashes alone."""
    request_id = _get_request_id(request)
    upload_path: Optional[Path] = None
    reference_path: Optional[Path] = None

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_dir = Paths.request_upload(request_id)
        upload_filename = _safe_upload_name(file)
        upload_path = upload_dir / upload_filename
        await save_upload(file.file, upload_path)

        if reference_file and reference_file.filename:
            reference_filename = f"reference_{_safe_upload_name(reference_file)}"
            reference_path = upload_dir / reference_filename
            await save_upload(reference_file.file, reference_path)

        result = document_integrity_verification_service.verify_document(
            str(upload_path),
            original_filename=file.filename,
            mime_type=file.content_type,
            reference_path=str(reference_path) if reference_path else None,
            reference_filename=reference_file.filename if reference_file else None,
            reference_mime_type=reference_file.content_type if reference_file else None,
            output_dir=_document_integrity_dir(),
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Integrity check failed."))

        verification_id = result.get("verification_id")
        if verification_id:
            result["result_url"] = f"/api/pdf/document-integrity/result/{verification_id}"
            result["report_url"] = f"/api/pdf/document-integrity/report/{verification_id}"

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"document_integrity error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to verify document integrity.")
    finally:
        document_integrity_verification_service.cleanup_temporary_files(
            [path for path in [upload_path, reference_path] if path is not None]
        )


@router.get("/security/document-integrity/result/{verification_id}")
@router.get("/document-integrity/result/{verification_id}")
async def document_integrity_result(verification_id: str):
    """Return a stored document integrity verification result."""
    try:
        return document_integrity_verification_service.load_result(
            _document_integrity_dir(),
            verification_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as e:
        logger.error(f"document_integrity_result error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load verification result.")


@router.get("/security/document-integrity/report/{verification_id}")
@router.get("/document-integrity/report/{verification_id}")
async def document_integrity_report(verification_id: str):
    """Download a stored document integrity verification report."""
    try:
        report_path = document_integrity_verification_service.report_path(
            _document_integrity_dir(),
            verification_id,
        )
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Verification report not found.")
        return FileResponse(
            path=str(report_path),
            media_type="application/pdf",
            filename=report_path.name,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"document_integrity_report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download verification report.")


# ── 13. EMBEDDED FILE DETECT ───────────────────────────────────────────

@router.post("/security/embedded-file-detect")
async def embedded_file_detect(
    request: Request,
    file: UploadFile = File(...),
):
    """Detect embedded files and attachments in a PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.detect_embedded_files(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Embedded file detection failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"embedded_file_detect error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 14. EMBEDDED MEDIA DETECT ──────────────────────────────────────────

@router.post("/security/embedded-media-detect")
async def embedded_media_detect(
    request: Request,
    file: UploadFile = File(...),
):
    """Detect embedded media (images, audio, video) in a PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.detect_embedded_media(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Embedded media detection failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"embedded_media_detect error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 15. FILE EXPIRATION ────────────────────────────────────────────────

@router.post("/security/file-expiration")
async def file_expiration(
    request: Request,
    file: UploadFile = File(...),
    expiration_type: str = Form(...),
    expires_at: Optional[str] = Form(None),
    duration_seconds: Optional[int] = Form(None),
):
    """
    Applies a file expiration policy to a PDF.
    """
    request_id = _get_request_id(request)
    
    try:
        if not file or not file.filename:
            raise ValueError("PDF file is required.")
            
        input_path, filename = _save_upload_to_request(file, request_id)
        
        output_dir = Paths.request_output(request_id)
        output_file = f"expiring_{filename}"
        output_path = output_dir / output_file
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import shutil
        shutil.copy2(input_path, output_path)
        
        policy = file_expiration_service.apply_expiration_policy(
            output_dir=output_dir,
            expiration_type=expiration_type,
            expires_at=expires_at,
            duration_seconds=duration_seconds,
        )
        
        return {
            "success": True,
            "message": "Expiration policy applied successfully.",
            "output_file": output_file,
            "download_url": _download_url(request_id, output_file),
            "policy": policy,
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"file_expiration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to apply expiration policy.")


# ── 16. HIDE SENSITIVE INFORMATION ─────────────────────────────────────

@router.post("/security/hide-sensitive")
async def hide_sensitive(
    request: Request,
    file: UploadFile = File(...),
):
    """Redact detected sensitive information patterns from the PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)
        output_file = f"redacted_{filename}"
        out_path = _output_path(request_id, output_file)

        result = pdf_security_service.hide_sensitive_info(str(upload_path), str(out_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Sensitive data redaction failed."))

        return {
            **result,
            "download_url": _download_url(request_id, output_file),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"hide_sensitive error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 17. BLACKOUT AREAS ─────────────────────────────────────────────────

@router.post("/security/blackout-areas")
async def blackout_areas(
    request: Request,
    file: UploadFile = File(...),
    areas: str = Form(...),
):
    """Blackout/redact specific rectangular areas in the PDF.

    `areas` is a JSON string: [{"page": 1, "x0": 10, "y0": 10, "x1": 200, "y1": 50}]
    """
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        import json
        area_list = json.loads(areas)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid areas JSON format.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)
        output_file = f"blackout_{filename}"
        out_path = _output_path(request_id, output_file)

        result = pdf_security_service.blackout_areas(str(upload_path), str(out_path), area_list)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Blackout failed."))

        return {
            **result,
            "download_url": _download_url(request_id, output_file),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"blackout_areas error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 18. METADATA PROTECTION ────────────────────────────────────────────

@router.post("/security/metadata-protection/analyze")
async def metadata_protection_analyze(
    request: Request,
    file: UploadFile = File(...)
):
    """Analyze PDF metadata before protection."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = await pdf_metadata_protection_service.analyze_metadata(
            filepath=upload_path,
            original_filename=filename
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Metadata analysis failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"metadata_protection_analyze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/security/metadata-protection")
async def metadata_protection(
    request: Request,
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
):
    """Remove or protect PDF metadata to prevent information leakage."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = await pdf_metadata_protection_service.protect_metadata(
            filepath=upload_path,
            original_filename=filename,
            request_id=request_id,
            owner_password=password
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Metadata protection failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"metadata_protection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── SUB SECTION-28 – PDF SANITIZATION ───────────────────────────────────

@router.post("/security/sanitization/analyze")
async def analyze_pdf_for_sanitization(
    request: Request,
    file: UploadFile = File(...)
):
    """Analyzes a PDF to find elements that can be sanitized."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = await pdf_sanitization_service.analyze_pdf(
            filepath=upload_path,
            original_filename=filename
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Analysis failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"analyze_pdf_for_sanitization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/security/sanitization/process")
async def process_pdf_sanitization(
    request: Request,
    file: UploadFile = File(...)
):
    """Actually sanitizes a PDF and verifies the output."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = await pdf_sanitization_service.sanitize_pdf(
            filepath=upload_path,
            original_filename=filename,
            request_id=request_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Sanitization failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"process_pdf_sanitization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SUB SECTION 29 - PDF FORENSIC ANALYSIS
# ============================================================

@router.post("/security/forensic-analysis")
async def forensic_analysis(
    request: Request,
    file: UploadFile = File(...)
):
    """Performs a detailed static forensic examination of the uploaded PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = await pdf_forensic_analysis_service.analyze(
            filepath=upload_path,
            original_filename=filename
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Forensic analysis failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"forensic_analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to analyze this PDF because the document is corrupted or uses an unsupported structure.")


# ============================================================
# SUB SECTION 30 - EMBEDDED MEDIA DETECTION
# ============================================================

@router.post("/security/embedded-media")
async def embedded_media_detection(
    request: Request,
    file: UploadFile = File(...)
):
    """Inspects the PDF for media and embedded content."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = await embedded_media_detection_service.analyze(
            filepath=upload_path,
            original_filename=filename
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Media detection failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"embedded_media_detection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to analyze this PDF because the document is corrupted or uses an unsupported structure.")


# ============================================================
# SUB SECTION 31 - PDF VERSION SECURITY CHECK
# ============================================================

@router.post("/security/version-check")
async def version_security_check(
    request: Request,
    file: UploadFile = File(...)
):
    """Identifies the PDF version and provides a compatibility/security assessment."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = await pdf_version_security_check_service.analyze(
            filepath=upload_path,
            original_filename=filename
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Version check failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"version_security_check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to analyze this PDF because the document is corrupted or uses an unsupported structure.")

# ── 18.5 ATOMIC SERVER TIMESTAMPING ────────────────────────────────────

@router.post("/security/atomic-server-timestamping")
async def atomic_server_timestamping(
    request: Request,
    file: UploadFile = File(...)
):
    """Apply a trusted server timestamp to the PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = await atomic_server_timestamping_service.apply_timestamp(
            filepath=upload_path,
            original_filename=filename,
            request_id=request_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Atomic server timestamping failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"atomic_server_timestamping error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 19. SANITIZE PDF ───────────────────────────────────────────────────

@router.post("/security/sanitize")
async def sanitize_pdf(
    request: Request,
    file: UploadFile = File(...),
):
    """Perform full PDF sanitization: remove JS, forms, metadata, attachments."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)
        output_file = f"sanitized_{filename}"
        out_path = _output_path(request_id, output_file)

        result = pdf_security_service.sanitize_pdf(str(upload_path), str(out_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Sanitization failed."))

        return {
            **result,
            "download_url": _download_url(request_id, output_file),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"sanitize_pdf error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 20. POLICY TEMPLATES ───────────────────────────────────────────────

@router.post("/security/policy-templates")
async def policy_templates(request: Request):
    """Compatibility endpoint: list available security policy templates."""
    try:
        return pdf_security_policy_template_service.list_templates()
    except Exception as e:
        logger.error(f"policy_templates error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security/security-policy-templates")
async def list_security_policy_templates():
    """List predefined PDF security policy templates."""
    try:
        return pdf_security_policy_template_service.list_templates()
    except Exception as e:
        logger.error(f"list_security_policy_templates error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load security policy templates.")


@router.get("/security/security-policy-templates/{template_id}")
async def get_security_policy_template(template_id: str):
    """Return one predefined PDF security policy template."""
    try:
        return pdf_security_policy_template_service.get_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as e:
        logger.error(f"get_security_policy_template error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load security policy template.")


@router.post("/security/security-policy-templates/apply")
async def apply_security_policy_template(
    request: Request,
    file: UploadFile = File(...),
    template_id: str = Form(...),
    password: Optional[str] = Form(None),
    confirm_password: Optional[str] = Form(None),
):
    """Apply a selected security policy template to a PDF and return a secured download."""
    request_id = _get_request_id(request)
    upload_path: Optional[Path] = None

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path = Paths.request_upload(request_id) / _safe_upload_name(file)
        await save_upload(file.file, upload_path)

        clean_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(file.filename or "document").stem).strip("._-")
        if not clean_stem:
            clean_stem = "document"
        clean_template = re.sub(r"[^A-Za-z0-9_-]+", "_", template_id).strip("_-") or "policy"
        output_file = f"{clean_stem}_{clean_template}_secured.pdf"
        out_path = _output_path(request_id, output_file)

        result = pdf_security_policy_template_service.apply_template(
            input_path=upload_path,
            output_path=out_path,
            template_id=template_id,
            password=password,
            confirm_password=confirm_password,
            original_filename=file.filename,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Security policy could not be applied."))

        return {
            **result,
            "download_url": _download_url(request_id, result["output_file"]),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"apply_security_policy_template error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to apply security policy template.")
    finally:
        pdf_security_policy_template_service.cleanup_temporary_files([upload_path])


# ── 21. VERSION SECURITY ───────────────────────────────────────────────

@router.post("/security/version-check")
async def version_check(
    request: Request,
    file: UploadFile = File(...),
):
    """Check PDF version for known security issues."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.check_version_security(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Version check failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"version_check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 22. SECURE SHARING ─────────────────────────────────────────────────

@router.post("/security/secure-sharing")
async def secure_sharing(
    request: Request,
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    expires_at: Optional[str] = Form(None),
    allow_download: Optional[bool] = Form(False),
    allow_print: Optional[bool] = Form(False),
):
    """Create a secure sharing link for a PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = SecureSharingService.create_share(
            source_file_path=upload_path,
            original_filename=file.filename,
            password=password,
            expires_at=expires_at,
            allow_download=allow_download,
            allow_print=allow_print
        )
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"secure_sharing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/security/secure-sharing/{token}/validate")
async def validate_secure_share(token: str):
    """Validate a secure share link status."""
    try:
        share_data = SecureSharingService.validate_share_access(token)
        return {
            "success": True,
            "filename": share_data.get("filename"),
            "has_password": bool(share_data.get("password_hash")),
            "allow_download": share_data.get("allow_download"),
            "allow_print": share_data.get("allow_print"),
        }
    except HTTPException as e:
        if e.status_code == 403:
            return {"success": False, "status": "access_denied", "detail": e.detail}
        raise

@router.post("/security/secure-sharing/{token}/verify")
async def verify_secure_share_password(token: str, password: str = Form(...)):
    """Verify password for a secure share."""
    SecureSharingService.verify_password(token, password)
    return {"success": True}

@router.get("/security/secure-sharing/{token}/access")
async def access_secure_share(token: str, password: Optional[str] = None):
    """Access the actual PDF file."""
    SecureSharingService.verify_password(token, password)
    SecureSharingService.record_access(token)
    
    file_path = SecureSharingService.get_shared_file_path(token)
    share_data = SecureSharingService.validate_share_access(token)
    
    return FileResponse(
        path=file_path,
        filename=share_data.get("filename"),
        media_type="application/pdf"
    )

@router.post("/security/secure-sharing/manage")
async def list_secure_shares(management_tokens: str = Form(...)):
    """List all secure shares given a comma-separated list of management tokens."""
    tokens = [t.strip() for t in management_tokens.split(",") if t.strip()]
    shares = SecureSharingService.get_shares_by_management_tokens(tokens)
    return {"success": True, "shares": shares}

@router.post("/security/secure-sharing/{token}/revoke")
async def revoke_secure_share(token: str, management_token: str = Form(...)):
    """Revoke a secure share."""
    result = SecureSharingService.revoke_share(token, management_token)
    return {"success": True, **result}


# ── 23. AUDIT REPORT ───────────────────────────────────────────────────

@router.post("/security/audit-report")
async def audit_report(
    request: Request,
    file: UploadFile = File(...),
):
    """Generate a comprehensive security audit report."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.generate_audit_report(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Audit report failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"audit_report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 24. TRUSTED CERTS ──────────────────────────────────────────────────

@router.post("/security/trusted-certs")
async def trusted_certs(request: Request):
    """Get the list of trusted root certificates."""
    try:
        return pdf_security_service.get_trusted_certs()
    except Exception as e:
        logger.error(f"trusted_certs error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 25. UNSAFE LINK DETECT ─────────────────────────────────────────────

@router.post("/security/unsafe-link-detect")
async def unsafe_link_detect(
    request: Request,
    file: UploadFile = File(...),
):
    """Detect and analyse all URLs embedded in the PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.detect_unsafe_links(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Link detection failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"unsafe_link_detect error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SUB SECTION 8 - TRUSTED CERTIFICATES
# ============================================================

@router.post("/security/trusted-certificates")
async def trusted_certificates(
    request: Request,
    file: UploadFile = File(...)
):
    """Analyzes digitally signed PDFs and validates certificates."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = await trusted_certificates_service.analyze(
            filepath=upload_path,
            original_filename=filename
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to validate certificates."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"trusted_certificates error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing the document.")


# ── SUB SECTION-3 – RESTRICT ACCESSIBILITY COPY ─────────────────────────────────

@router.post("/security/restrict-accessibility-copy")
async def restrict_accessibility_copy(
    request: Request,
    file: UploadFile = File(...)
):
    """Restricts content extraction and accessibility copy by applying PDF security permissions."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)

        result = await restrict_accessibility_copy_service.process_pdf(
            filepath=upload_path,
            original_filename=filename,
            request_id=request_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to restrict accessibility copy."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"restrict_accessibility_copy error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing the document.")


# ── 26. WATERMARK PROTECTION ───────────────────────────────────────────

@router.post("/security/watermark-protection")
async def watermark_protection(
    request: Request,
    file: UploadFile = File(...),
    watermark_text: str = Form("CONFIDENTIAL"),
):
    """Add a protective diagonal watermark to all pages."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)
        output_file = f"watermarked_{filename}"
        out_path = _output_path(request_id, output_file)

        result = pdf_security_service.add_watermark_protection(
            str(upload_path), str(out_path), watermark_text
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Watermark failed."))

        return {
            **result,
            "download_url": _download_url(request_id, output_file),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"watermark_protection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 27. AI CLASSIFICATION ──────────────────────────────────────────────

@router.post("/security/ai-classification")
async def ai_classification(
    request: Request,
    file: UploadFile = File(...),
):
    """AI-based document type classification."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.ai_classify_document(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "AI classification failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ai_classification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 28. AI RECOMMENDATIONS ─────────────────────────────────────────────

@router.post("/security/ai-recommendations")
async def ai_recommendations(
    request: Request,
    file: UploadFile = File(...),
):
    """AI-driven security recommendations."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.ai_security_recommendations(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "AI recommendations failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ai_recommendations error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 29. AI RISK DETECTION ──────────────────────────────────────────────

@router.post("/security/ai-risk-detection")
async def ai_risk_detection(
    request: Request,
    file: UploadFile = File(...),
):
    """AI-based security risk detection."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.ai_risk_detection(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "AI risk detection failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ai_risk_detection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 30. AI SENSITIVE DETECTION ─────────────────────────────────────────

@router.post("/security/ai-sensitive-detect")
async def ai_sensitive_detect(
    request: Request,
    file: UploadFile = File(...),
):
    """AI-based PII and sensitive data detection."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.ai_sensitive_detection(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "AI sensitive detection failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ai_sensitive_detect error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── 31. FORENSIC ANALYSIS ──────────────────────────────────────────────

@router.post("/security/forensic-analysis")
async def forensic_analysis(
    request: Request,
    file: UploadFile = File(...),
):
    """Deep forensic analysis of PDF internal structure."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, _ = _save_upload_to_request(file, request_id)
        result = pdf_security_service.forensic_analysis(str(upload_path))

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Forensic analysis failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"forensic_analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ── WATERMARK PROTECTION ────────────────────────────────────────────────

@router.post("/security/watermark")
async def watermark_pdf(
    request: Request,
    file: UploadFile = File(...),
    watermark_type: str = Form("text"),
    pages: str = Form("all"),
    position: str = Form("center"),
    rotation: int = Form(0),
    opacity: int = Form(100),
    pos_x: Optional[float] = Form(None),
    pos_y: Optional[float] = Form(None),
    # Text
    text: Optional[str] = Form(None),
    font_color: Optional[str] = Form("#000000"),
    font_size: Optional[int] = Form(48),
    # Image
    image_file: Optional[UploadFile] = File(None),
    scale: Optional[int] = Form(100),
):
    """Apply a text or image watermark to a PDF."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        filename = file.filename or f"upload_{uuid.uuid4().hex[:8]}.pdf"
        upload_path = Paths.request_upload(request_id) / filename
        await save_upload(file.file, upload_path)

        image_path = None
        if watermark_type == "image" and image_file and image_file.filename:
            image_filename = image_file.filename or f"img_{uuid.uuid4().hex[:8]}.png"
            image_path = Paths.request_upload(request_id) / image_filename
            await save_upload(image_file.file, image_path)

        output_file = f"watermarked_{filename}"
        out_path = _output_path(request_id, output_file)

        result = watermark_protection_service.apply_watermark(
            input_path=upload_path,
            output_path=out_path,
            watermark_type=watermark_type,
            pages=pages,
            position=position,
            rotation=rotation,
            opacity=opacity,
            pos_x=pos_x,
            pos_y=pos_y,
            text=text,
            font_color=font_color,
            font_size=font_size,
            image_path=image_path,
            scale=scale,
        )

        return {
            "success": True,
            "message": result.get("message", "Watermark applied successfully."),
            "output_file": output_file,
            "download_url": _download_url(request_id, output_file),
            "result": result,
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"watermark_pdf error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to apply watermark.")

# ============================================================
# SUB SECTION-4: RESTRICT PAGE EXTRACTION
# ============================================================

@router.post("/security/restrict-page-extraction")
async def restrict_page_extraction(
    request: Request,
    file: UploadFile = File(...),
):
    """Restrict page extraction by setting a PDF permission flag."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        filename = file.filename or f"upload_{uuid.uuid4().hex[:8]}.pdf"
        upload_path = Paths.request_upload(request_id) / filename
        await save_upload(file.file, upload_path)
        output_file = f"restricted_{filename}"
        out_path = _output_path(request_id, output_file)

        result = protect_pdf_service.restrict_page_extraction(
            input_path=str(upload_path),
            output_path=str(out_path)
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to restrict page extraction."))

        result["download_url"] = _download_url(request_id, result["output_file"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"restrict_page_extraction error: {e}\n{tb}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unable to restrict page extraction. Error: {str(e)}\n{tb}")

# ============================================================
# 13. AI Sensitive Data Detection
# ============================================================

from app.pdf_security_services.ai_sensitive_data_detection_service import ai_sensitive_data_detection_service

@router.post("/security/ai-sensitive-data-detection")
async def ai_sensitive_data_detection(
    request: Request,
    file: UploadFile = File(...),
):
    """Analyze a PDF for sensitive data using AI and hybrid heuristics."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path = Paths.request_upload(request_id) / _safe_upload_name(file)
        await save_upload(file.file, upload_path)

        result = await ai_sensitive_data_detection_service.scan_pdf(
            filepath=upload_path,
            original_filename=file.filename,
            request_id=request_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "AI Sensitive Data Detection failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"ai_sensitive_data_detection error: {e}\n{tb}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unable to perform AI Sensitive Data Detection. Error: {str(e)}\n{tb}")

# ============================================================
# 14. AI Document Classification
# ============================================================

from app.pdf_security_services.ai_document_classification_service import ai_document_classification_service

@router.post("/security/ai-document-classification")
async def ai_document_classification(
    request: Request,
    file: UploadFile = File(...),
):
    """Analyze a PDF to automatically classify it into an appropriate document category."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path = Paths.request_upload(request_id) / _safe_upload_name(file)
        await save_upload(file.file, upload_path)

        result = await ai_document_classification_service.classify_pdf(
            filepath=upload_path,
            original_filename=file.filename,
            request_id=request_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "AI Document Classification failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"ai_document_classification error: {e}\n{tb}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unable to perform AI Document Classification. Error: {str(e)}\n{tb}")

# ============================================================
# AI SECURITY RISK DETECTION
# ============================================================

from app.pdf_security_services.ai_security_risk_detection_service import ai_security_risk_detection_service

@router.post("/security/ai-security-risk-detection")
async def ai_security_risk_detection(
    request: Request,
    file: UploadFile = File(...),
):
    """Analyze a PDF for security risks using deterministic checks combined with malware and link scanning services."""
    request_id = _get_request_id(request)

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path = Paths.request_upload(request_id) / _safe_upload_name(file)
        await save_upload(file.file, upload_path)

        result = await ai_security_risk_detection_service.analyze_pdf(
            filepath=upload_path,
            original_filename=file.filename,
            request_id=request_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "AI Security Risk Detection failed."))

        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"ai_security_risk_detection error: {e}\n{tb}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unable to perform AI Security Risk Detection. Error: {str(e)}")

# ============================================================
# SUB SECTION-10 — PDF/A VALIDATION
# ============================================================

@router.post("/security/pdfa-validate")
async def pdfa_validate(
    request: Request,
    file: UploadFile = File(...)
):
    """Validate if a PDF meets PDF/A requirements."""
    request_id = _get_request_id(request)
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)
        result = pdfa_validation_service.validate_pdfa(str(upload_path))
        return result
    except Exception as e:
        logger.error(f"PDF/A validation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate PDF/A: {str(e)}")


# ============================================================
# SUB SECTION-32 — BLACKOUT AREAS
# ============================================================

@router.post("/security/blackout-areas")
async def blackout_areas(
    request: Request,
    file: UploadFile = File(...),
    areas: str = Form(...)  # JSON string of areas
):
    """Apply permanent blackout redaction to specific areas."""
    request_id = _get_request_id(request)
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        import json
        areas_data = json.loads(areas)
        upload_path, filename = _save_upload_to_request(file, request_id)
        output_file = f"blackout_{filename}"
        out_path = _output_path(request_id, output_file)

        result = blackout_areas_service.apply_blackout(str(upload_path), str(out_path), areas_data)
        return {
            "success": True,
            "message": result["message"],
            "downloadUrl": _download_url(request_id, output_file)
        }
    except Exception as e:
        logger.error(f"Blackout areas error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to apply blackout: {str(e)}")


# ============================================================
# SUB SECTION-G — HIDE SENSITIVE INFORMATION
# ============================================================

@router.post("/security/hide-sensitive-detect")
async def hide_sensitive_detect(
    request: Request,
    file: UploadFile = File(...)
):
    """Detect sensitive information in PDF."""
    request_id = _get_request_id(request)
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        upload_path, filename = _save_upload_to_request(file, request_id)
        result = hide_sensitive_information_service.detect_sensitive_info(str(upload_path))
        return result
    except Exception as e:
        logger.error(f"Hide sensitive detect error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to detect sensitive info: {str(e)}")

@router.post("/security/hide-sensitive-apply")
async def hide_sensitive_apply(
    request: Request,
    file: UploadFile = File(...),
    areas: str = Form(...)  # JSON string of areas to redact
):
    """Apply redaction to detected sensitive information."""
    request_id = _get_request_id(request)
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="PDF file is required.")

    try:
        import json
        areas_data = json.loads(areas)
        upload_path, filename = _save_upload_to_request(file, request_id)
        output_file = f"redacted_{filename}"
        out_path = _output_path(request_id, output_file)

        # We can reuse blackout service since it does the exact same PyMuPDF redaction
        result = blackout_areas_service.apply_blackout(str(upload_path), str(out_path), areas_data)
        return {
            "success": True,
            "message": result["message"],
            "downloadUrl": _download_url(request_id, output_file)
        }
    except Exception as e:
        logger.error(f"Hide sensitive apply error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to apply redaction: {str(e)}")

