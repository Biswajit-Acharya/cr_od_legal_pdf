"""
API Routes for PDF Copyright Protection Section.

Provides endpoints for all 8 copyright protection features.
"""

from __future__ import annotations

import json
import logging

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, File, Form, Query, Request, UploadFile, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse

import uuid

from app.pdf_copyright_protection_services.copyright_registration import copyright_registration_service
from app.pdf_copyright_protection_services.copyright_information_editor import copyright_information_editor_service
from app.pdf_copyright_protection_services.copyright_metadata_management import copyright_metadata_management_service
from app.pdf_copyright_protection_services.copyright_notice import copyright_notice_service
from app.pdf_copyright_protection_services.copyright_watermark import copyright_watermark_service
from app.pdf_copyright_protection_services.invisible_copyright_watermark import invisible_copyright_watermark_service
from app.pdf_copyright_protection_services.digital_copyright_seal import digital_copyright_seal_service
from app.pdf_copyright_protection_services.ownership_certificate import ownership_certificate_service
from app.pdf_copyright_protection_services.author_verification import author_verification_service
from app.pdf_copyright_protection_services.publisher_information import publisher_information_service
from app.pdf_copyright_protection_services.copyright_holder_management import copyright_holder_management_service
from app.pdf_copyright_protection_services.license_management import license_management_service
from app.pdf_copyright_protection_services.license_verification import license_verification_service
from app.pdf_copyright_protection_services.usage_rights_management import usage_rights_management_service
from app.pdf_copyright_protection_services.copyright_policy_templates import copyright_policy_templates_service
from app.pdf_copyright_protection_services.document_ownership_verification import document_ownership_verification_service
from app.pdf_copyright_protection_services.copyright_claim_report import copyright_claim_report_service
from app.pdf_copyright_protection_services.copyright_infringement_detection import copyright_infringement_detection_service
from app.pdf_copyright_protection_services.duplicate_content_detection import duplicate_content_detection_service
from app.pdf_copyright_protection_services.ai_content_similarity import ai_content_similarity_service
from app.pdf_copyright_protection_services.content_ownership_validation import content_ownership_validation_service
from app.pdf_copyright_protection_services.copyright_evidence_report import copyright_evidence_report_service
from app.pdf_copyright_protection_services.copyright_audit_trail import copyright_audit_trail_service
from app.pdf_copyright_protection_services.copyright_history import copyright_history_service
from app.pdf_copyright_protection_services.copyright_transfer_management import copyright_transfer_management_service
from app.pdf_copyright_protection_services.copyright_expiration_tracking import copyright_expiration_tracking_service
from app.pdf_copyright_protection_services.copyright_renewal_reminder import copyright_renewal_reminder_service
from app.pdf_copyright_protection_services.copyright_revocation_record import copyright_revocation_record_service
from app.pdf_copyright_protection_services.document_provenance_tracking import document_provenance_tracking_service
from app.pdf_copyright_protection_services.blockchain_copyright_registration import blockchain_copyright_registration_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Audit Trail Event Logger Helper ──────────────────────────────────────────

def log_audit_event_safe(session_id: str, service, event_type: str, description: str, new_value: dict = None, source: str = "Copyright Service"):
    try:
        file_path, _ = service.get_file_for_download(session_id)
        from pathlib import Path
        path_obj = Path(file_path)
        if path_obj.exists():
            pdf_bytes = path_obj.read_bytes()
            copyright_audit_trail_service.add_event(
                pdf_bytes=pdf_bytes,
                event_type=event_type,
                description=description,
                new_value=new_value,
                action_result="success",
                source=source
            )
    except Exception as e:
        logger.warning(f"Could not log audit event: {e}")


# ── Copyright Registration ──────────────────────────────────────────────────


@router.post("/registration")
async def copyright_registration(
    file: UploadFile = File(...),
    copyright_owner: str = Form(""),
    author: str = Form(""),
    organization: str = Form(""),
    copyright_year: str = Form(""),
    registration_number: str = Form(""),
    registration_date: str = Form(""),
    copyright_notice: str = Form(""),
    notes: str = Form(""),
):
    """Embed copyright registration information into a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = __import__("uuid").uuid4().hex[:16]
        pdf_bytes = await file.read()
        res = copyright_registration_service.register(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            copyright_owner=copyright_owner,
            author=author,
            organization=organization,
            copyright_year=copyright_year,
            registration_number=registration_number,
            registration_date=registration_date,
            copyright_notice=copyright_notice,
            notes=notes,
        )
        log_audit_event_safe(
            session_id=session_id,
            service=copyright_registration_service,
            event_type="Copyright Registration",
            description=f"Copyright registered to owner: {copyright_owner}",
            new_value={"owner": copyright_owner, "author": author, "reg_id": res.get("registration_id")},
            source="Copyright Registration Service"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copyright registration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/registration/check")
async def copyright_registration_check(file: UploadFile = File(...)):
    """Check if a PDF already has a copyright registration record."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_registration_service.check_registration(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copyright registration check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to check registration status.")


@router.get("/registration/download/{session_id}")
async def copyright_registration_download(session_id: str):
    """Download the copyright-registered PDF."""
    try:
        file_path, filename = copyright_registration_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Copyright registration download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Copyright Information Editor ─────────────────────────────────────────────


@router.post("/information-editor/read")
async def copyright_info_read(file: UploadFile = File(...)):
    """Read existing copyright information from a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_information_editor_service.read_copyright_info(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Copyright info read error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/information-editor/update")
async def copyright_info_update(
    file: UploadFile = File(...),
    copyright_owner: str = Form(""),
    author: str = Form(""),
    organization: str = Form(""),
    copyright_year: str = Form(""),
    copyright_notice: str = Form(""),
    registration_number: str = Form(""),
    notes: str = Form(""),
):
    """Update copyright information in a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = __import__("uuid").uuid4().hex[:16]
        pdf_bytes = await file.read()
        return copyright_information_editor_service.update_copyright_info(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            copyright_owner=copyright_owner,
            author=author,
            organization=organization,
            copyright_year=copyright_year,
            copyright_notice=copyright_notice,
            registration_number=registration_number,
            notes=notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copyright info update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/information-editor/download/{session_id}")
async def copyright_info_download(session_id: str):
    """Download the copyright-updated PDF."""
    try:
        file_path, filename = copyright_information_editor_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Copyright info download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Copyright Metadata Management ────────────────────────────────────────────


@router.post("/metadata/read")
async def copyright_metadata_read(file: UploadFile = File(...)):
    """Read copyright-related metadata from a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_metadata_management_service.read_metadata(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Copyright metadata read error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/metadata/update")
async def copyright_metadata_update(
    file: UploadFile = File(...),
    author: str = Form(""),
    copyright_holder: str = Form(""),
    publication_year: str = Form(""),
    copyright_notice: str = Form(""),
    license: str = Form(""),
    license_url: str = Form(""),
    creator: str = Form(""),
    producer: str = Form(""),
    subject: str = Form(""),
    keywords: str = Form(""),
):
    """Update copyright-related metadata in a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = __import__("uuid").uuid4().hex[:16]
        pdf_bytes = await file.read()
        return copyright_metadata_management_service.update_metadata(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            author=author,
            copyright_holder=copyright_holder,
            publication_year=publication_year,
            copyright_notice=copyright_notice,
            license=license,
            license_url=license_url,
            creator=creator,
            producer=producer,
            subject=subject,
            keywords=keywords,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copyright metadata update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/metadata/download/{session_id}")
async def copyright_metadata_download(session_id: str):
    """Download the metadata-updated PDF."""
    try:
        file_path, filename = copyright_metadata_management_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Copyright metadata download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Copyright Notice ─────────────────────────────────────────────────────────


@router.post("/notice/apply")
async def copyright_notice_apply(
    file: UploadFile = File(...),
    notice_text: str = Form(""),
    position: str = Form("bottom"),
    font_size: int = Form(12),
    opacity: float = Form(1.0),
    pages: str = Form("all"),
):
    """Stamp a copyright notice onto PDF pages."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = uuid.uuid4().hex[:16]
        pdf_bytes = await file.read()
        res = copyright_notice_service.apply_notice(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            notice_text=notice_text,
            position=position,
            font_size=font_size,
            opacity=opacity,
            pages=pages,
        )
        log_audit_event_safe(
            session_id=session_id,
            service=copyright_notice_service,
            event_type="Copyright Notice Applied",
            description=f"Stamped copyright notice: '{notice_text}'",
            new_value={"notice_text": notice_text, "position": position, "font_size": font_size},
            source="Copyright Notice Service"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copyright notice error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/notice/download/{session_id}")
async def copyright_notice_download(session_id: str):
    """Download the notice-stamped PDF."""
    try:
        file_path, filename = copyright_notice_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Copyright notice download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Copyright Watermark ──────────────────────────────────────────────────────


@router.post("/watermark/apply")
async def copyright_watermark_apply(
    file: UploadFile = File(...),
    watermark_text: str = Form(""),
    position: str = Form("center"),
    font_size: int = Form(60),
    opacity: float = Form(0.3),
    rotation: float = Form(45.0),
    color: str = Form("#888888"),
    pages: str = Form("all"),
):
    """Apply a visible text watermark to PDF pages."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = uuid.uuid4().hex[:16]
        pdf_bytes = await file.read()
        res = copyright_watermark_service.apply_text_watermark(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            watermark_text=watermark_text,
            position=position,
            font_size=font_size,
            opacity=opacity,
            rotation=rotation,
            color=color,
            pages=pages,
        )
        log_audit_event_safe(
            session_id=session_id,
            service=copyright_watermark_service,
            event_type="Watermark Applied",
            description=f"Applied visible watermark: '{watermark_text}'",
            new_value={"watermark_text": watermark_text, "position": position, "font_size": font_size},
            source="Copyright Watermark Service"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copyright watermark error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/watermark/download/{session_id}")
async def copyright_watermark_download(session_id: str):
    """Download the watermarked PDF."""
    try:
        file_path, filename = copyright_watermark_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Copyright watermark download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Invisible Copyright Watermark ────────────────────────────────────────────


@router.post("/invisible-watermark/embed")
async def invisible_watermark_embed(
    file: UploadFile = File(...),
    owner: str = Form(""),
    reference: str = Form(""),
    year: str = Form(""),
    license_text: str = Form(""),
):
    """Embed invisible copyright watermark into PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = uuid.uuid4().hex[:16]
        pdf_bytes = await file.read()
        res = invisible_copyright_watermark_service.embed_watermark(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            owner=owner,
            reference=reference,
            year=year,
            license_text=license_text,
        )
        log_audit_event_safe(
            session_id=session_id,
            service=invisible_copyright_watermark_service,
            event_type="Invisible Watermark Embedded",
            description=f"Embedded invisible watermark for owner: {owner}",
            new_value={"owner": owner, "fingerprint": res.get("fingerprint")},
            source="Invisible Watermark Service"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invisible watermark embed error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/invisible-watermark/verify")
async def invisible_watermark_verify(file: UploadFile = File(...)):
    """Verify invisible copyright watermark in a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return invisible_copyright_watermark_service.verify_watermark(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Invisible watermark verify error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/invisible-watermark/download/{session_id}")
async def invisible_watermark_download(session_id: str):
    """Download the invisibly watermarked PDF."""
    try:
        file_path, filename = invisible_copyright_watermark_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Invisible watermark download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Digital Copyright Seal ───────────────────────────────────────────────────


@router.post("/digital-seal/generate")
async def digital_seal_generate(
    file: UploadFile = File(...),
    owner: str = Form(""),
    organization: str = Form(""),
    year: str = Form(""),
    seal_info: str = Form(""),
):
    """Generate and apply a digital copyright seal."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = uuid.uuid4().hex[:16]
        pdf_bytes = await file.read()
        res = digital_copyright_seal_service.generate_seal(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            owner=owner,
            organization=organization,
            year=year,
            seal_info=seal_info,
        )
        log_audit_event_safe(
            session_id=session_id,
            service=digital_copyright_seal_service,
            event_type="Digital Copyright Seal Applied",
            description=f"Applied cryptographic SHA-256 seal for owner: {owner}",
            new_value={"owner": owner, "seal_id": res.get("seal_id"), "document_hash": res.get("document_hash")},
            source="Digital Copyright Seal Service"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Digital seal generate error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/digital-seal/verify")
async def digital_seal_verify(file: UploadFile = File(...)):
    """Verify digital copyright seal in a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return digital_copyright_seal_service.verify_seal(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Digital seal verify error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/digital-seal/download/{session_id}")
async def digital_seal_download(session_id: str):
    """Download the sealed PDF."""
    try:
        file_path, filename = digital_copyright_seal_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Digital seal download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Ownership Certificate ────────────────────────────────────────────────────


@router.post("/ownership-certificate/generate")
async def ownership_certificate_generate(
    file: UploadFile = File(...),
    owner: str = Form(""),
    organization: str = Form(""),
    doc_title: str = Form(""),
    pub_date: str = Form(""),
    copyright_info: str = Form(""),
    description: str = Form(""),
    ref_id: str = Form(""),
):
    """Generate an ownership certificate PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = uuid.uuid4().hex[:16]
        pdf_bytes = await file.read()
        res = ownership_certificate_service.generate_certificate(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            owner=owner,
            organization=organization,
            doc_title=doc_title,
            pub_date=pub_date,
            copyright_info=copyright_info,
            description=description,
            ref_id=ref_id,
        )
        log_audit_event_safe(
            session_id=session_id,
            service=ownership_certificate_service,
            event_type="Ownership Certificate Generated",
            description=f"Generated ownership certificate for owner: {owner}",
            new_value={"owner": owner, "certificate_id": res.get("certificate_id"), "document_hash": res.get("document_hash")},
            source="Ownership Certificate Service"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ownership certificate error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/ownership-certificate/download/{session_id}")
async def ownership_certificate_download(session_id: str):
    """Download the ownership certificate PDF."""
    try:
        file_path, filename = ownership_certificate_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Ownership certificate download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Author Verification ──────────────────────────────────────────────────────


@router.post("/author-verification/extract")
async def author_verification_extract(file: UploadFile = File(...)):
    """Extract author metadata from a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return author_verification_service.extract_author_info(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Author verification extract error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/author-verification/verify")
async def author_verification_verify(
    file: UploadFile = File(...),
    claimed_author: str = Form(""),
):
    """Verify claimed author against PDF metadata."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return author_verification_service.verify_author(pdf_bytes, claimed_author)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Author verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


# ── Copyright Holder Management ───────────────────────────────────────────────


@router.post("/holder-management/read")
async def copyright_holder_read(file: UploadFile = File(...)):
    """Read existing copyright holders from a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_holder_management_service.read_holders(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Copyright holder read error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/holder-management/save")
async def copyright_holder_save(
    file: UploadFile = File(...),
    holders_json: str = Form(""),
):
    """Save copyright holders list to the PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = uuid.uuid4().hex[:16]
        pdf_bytes = await file.read()
        return copyright_holder_management_service.save_holders(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            holders_json=holders_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copyright holder save error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/holder-management/verify/{session_id}")
async def copyright_holder_verify(session_id: str):
    """Verify holders are persisted in saved PDF."""
    try:
        return copyright_holder_management_service.verify_saved(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Copyright holder verify error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to verify PDF.")


@router.get("/holder-management/download/{session_id}")
async def copyright_holder_download(session_id: str):
    """Download the holders-saved PDF."""
    try:
        file_path, filename = copyright_holder_management_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Copyright holder download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── License Management ────────────────────────────────────────────────────────


@router.get("/license/presets")
async def license_presets():
    """Return available license presets."""
    try:
        return license_management_service.get_presets()
    except Exception as e:
        logger.error(f"License presets error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load presets.")


@router.post("/license/read")
async def license_read(file: UploadFile = File(...)):
    """Read existing license information from a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return license_management_service.read_license(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"License read error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/license/save")
async def license_save(
    file: UploadFile = File(...),
    license_json: str = Form(""),
):
    """Save license information to the PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = uuid.uuid4().hex[:16]
        pdf_bytes = await file.read()
        return license_management_service.save_license(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            license_json=license_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"License save error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/license/verify/{session_id}")
async def license_verify(session_id: str):
    """Verify license data is persisted in saved PDF."""
    try:
        return license_management_service.verify_saved(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"License verify error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to verify PDF.")


@router.get("/license/download/{session_id}")
async def license_download(session_id: str):
    """Download the license-saved PDF."""
    try:
        file_path, filename = license_management_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"License download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Publisher Information ─────────────────────────────────────────────────────


@router.post("/publisher/read")
async def publisher_read(file: UploadFile = File(...)):
    """Read publisher information from a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return publisher_information_service.read_publisher_info(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Publisher read error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/publisher/update")
async def publisher_update(
    file: UploadFile = File(...),
    publisher_name: str = Form(""),
    organization: str = Form(""),
    publication_date: str = Form(""),
    contact_information: str = Form(""),
    publisher_website: str = Form(""),
    publication_ref_id: str = Form(""),
):
    """Update publisher information in a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = uuid.uuid4().hex[:16]
        pdf_bytes = await file.read()
        return publisher_information_service.update_publisher_info(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            publisher_name=publisher_name,
            organization=organization,
            publication_date=publication_date,
            contact_information=contact_information,
            publisher_website=publisher_website,
            publication_ref_id=publication_ref_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Publisher update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/publisher/download/{session_id}")
async def publisher_download(session_id: str):
    """Download the publisher-updated PDF."""
    try:
        file_path, filename = publisher_information_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Publisher download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── License Verification ──────────────────────────────────────────────────────


@router.post("/license-verify/verify")
async def license_verify_verify(file: UploadFile = File(...)):
    """Verify license information in a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return license_verification_service.verify_license(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"License verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to verify license.")


# ── Usage Rights Management ───────────────────────────────────────────────────


@router.post("/usage-rights/read")
async def usage_rights_read(file: UploadFile = File(...)):
    """Read current permission settings from a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return usage_rights_management_service.read_permissions(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Usage rights read error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/usage-rights/save")
async def usage_rights_save(
    file: UploadFile = File(...),
    permissions_json: str = Form(""),
    password: str = Form(""),
):
    """Save permission settings to the PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = uuid.uuid4().hex[:16]
        pdf_bytes = await file.read()
        return usage_rights_management_service.save_permissions(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            permissions_json=permissions_json,
            password=password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Usage rights save error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/usage-rights/verify/{session_id}")
async def usage_rights_verify(session_id: str):
    """Verify permissions in saved PDF."""
    try:
        return usage_rights_management_service.verify_permissions(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Usage rights verify error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to verify PDF.")


@router.get("/usage-rights/download/{session_id}")
async def usage_rights_download(session_id: str):
    """Download the permissions-saved PDF."""
    try:
        file_path, filename = usage_rights_management_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Usage rights download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Copyright Policy Templates ────────────────────────────────────────────────


@router.get("/policy/templates")
async def policy_templates():
    """Return available policy templates."""
    try:
        return copyright_policy_templates_service.get_templates()
    except Exception as e:
        logger.error(f"Policy templates error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load templates.")


@router.post("/policy/read")
async def policy_read(file: UploadFile = File(...)):
    """Read existing policy from a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_policy_templates_service.read_policy(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Policy read error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.post("/policy/apply")
async def policy_apply(
    file: UploadFile = File(...),
    policy_json: str = Form(""),
):
    """Apply a copyright policy to the PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        session_id = uuid.uuid4().hex[:16]
        pdf_bytes = await file.read()
        return copyright_policy_templates_service.apply_policy(
            pdf_bytes=pdf_bytes,
            original_filename=file.filename,
            session_id=session_id,
            policy_json=policy_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Policy apply error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to process PDF.")


@router.get("/policy/verify/{session_id}")
async def policy_verify(session_id: str):
    """Verify policy persistence in saved PDF."""
    try:
        return copyright_policy_templates_service.verify_saved(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Policy verify error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to verify PDF.")


@router.get("/policy/download/{session_id}")
async def policy_download(session_id: str):
    """Download the policy-applied PDF."""
    try:
        file_path, filename = copyright_policy_templates_service.get_file_for_download(session_id)
        return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Policy download error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to download PDF.")


# ── Document Ownership Verification ───────────────────────────────────────────


@router.post("/ownership-verification/analyze")
async def ownership_verification_analyze(file: UploadFile = File(...)):
    """Analyze PDF for ownership evidence."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return document_ownership_verification_service.verify_ownership(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ownership verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to analyze PDF.")


# ── Copyright Claim Report ────────────────────────────────────────────────────


@router.post("/claim-report/generate")
async def claim_report_generate(file: UploadFile = File(...)):
    """Generate a copyright claim report from a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_claim_report_service.generate_report(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Claim report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate report.")


# ── Copyright Infringement Detection ──────────────────────────────────────────


@router.post("/infringement-detection/analyze")
async def infringement_detection_analyze(file: UploadFile = File(...)):
    """Analyze PDF for potential copyright infringement indicators."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_infringement_detection_service.analyze(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Infringement detection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to analyze PDF.")


# ── Duplicate Content Detection ───────────────────────────────────────────────


@router.post("/duplicate-detection/analyze")
async def duplicate_detection_analyze(file: UploadFile = File(...)):
    """Analyze PDF for duplicate or similar content."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return duplicate_content_detection_service.analyze(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Duplicate detection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to analyze PDF.")


# ── AI Content Similarity Check ───────────────────────────────────────────────


@router.post("/similarity-check/analyze")
async def similarity_check_analyze(file: UploadFile = File(...)):
    """Perform content similarity analysis on a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return ai_content_similarity_service.analyze(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Similarity check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to analyze PDF.")


# ── Content Ownership Validation ─────────────────────────────────────────────


@router.post("/ownership-validation/validate")
async def content_ownership_validate(
    file: UploadFile = File(...),
    claimed_owner: str = Form(""),
):
    """Validate content ownership against PDF metadata and existing records."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return content_ownership_validation_service.validate(pdf_bytes, claimed_owner)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ownership validation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to validate ownership.")


@router.post("/ownership-validation/report")
async def content_ownership_report(file: UploadFile = File(...)):
    """Generate a content ownership validation report."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return content_ownership_validation_service.validate(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ownership report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate ownership report.")


# ── Copyright Evidence Report ────────────────────────────────────────────────


@router.post("/evidence-report/collect")
async def copyright_evidence_collect(file: UploadFile = File(...)):
    """Collect copyright evidence from a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_evidence_report_service.generate_report(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Evidence collection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to collect evidence.")


@router.post("/evidence-report/generate")
async def copyright_evidence_generate(file: UploadFile = File(...)):
    """Generate a copyright evidence report."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_evidence_report_service.generate_report(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Evidence report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate evidence report.")


# ── Copyright Audit Trail ────────────────────────────────────────────────────


@router.post("/audit-trail/add-event")
async def audit_trail_add_event(
    file: UploadFile = File(...),
    event_type: str = Form(""),
    description: str = Form(""),
    previous_value: str = Form(""),
    new_value: str = Form(""),
    action_result: str = Form(""),
):
    """Add an audit event for a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_audit_trail_service.add_event(
            pdf_bytes, event_type, description,
            previous_value or None, new_value or None, action_result,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Audit add event error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to add audit event.")


@router.post("/audit-trail/get-events")
async def audit_trail_get_events(
    file: UploadFile = File(...),
    event_type: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
):
    """Retrieve audit events for a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_audit_trail_service.get_events(
            pdf_bytes, event_type or None, start_date or None, end_date or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Audit get events error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to retrieve audit events.")


@router.post("/audit-trail/report")
async def audit_trail_report(file: UploadFile = File(...)):
    """Generate an audit trail report."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_audit_trail_service.generate_report(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Audit report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate audit report.")


# ── Copyright History ────────────────────────────────────────────────────────


@router.post("/history/add-entry")
async def copyright_history_add_entry(
    file: UploadFile = File(...),
    change_type: str = Form(""),
    previous_info: str = Form(""),
    updated_info: str = Form(""),
    description: str = Form(""),
):
    """Add a history entry for a copyright change."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        prev = None
        upd = None
        if previous_info:
            try:
                prev = json.loads(previous_info)
            except (json.JSONDecodeError, TypeError):
                prev = previous_info
        if updated_info:
            try:
                upd = json.loads(updated_info)
            except (json.JSONDecodeError, TypeError):
                upd = updated_info
        return copyright_history_service.add_entry(pdf_bytes, change_type, prev, upd, description=description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"History add entry error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to add history entry.")


@router.post("/history/get-history")
async def copyright_history_get(
    file: UploadFile = File(...),
    change_type: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
):
    """Retrieve copyright history for a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_history_service.get_history(
            pdf_bytes, change_type or None, start_date or None, end_date or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"History get error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to retrieve history.")


@router.post("/history/report")
async def copyright_history_report(file: UploadFile = File(...)):
    """Generate a copyright history report."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_history_service.generate_report(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"History report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate history report.")


# ── Copyright Transfer Management ────────────────────────────────────────────


@router.post("/transfer/get-current-owner")
async def transfer_get_current_owner(file: UploadFile = File(...)):
    """Get current copyright owner information."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_transfer_management_service.get_current_owner(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Transfer get owner error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to get current owner.")


@router.post("/transfer/execute")
async def transfer_execute(
    file: UploadFile = File(...),
    current_owner_name: str = Form(""),
    current_owner_org: str = Form(""),
    new_owner_name: str = Form(""),
    new_owner_org: str = Form(""),
    new_owner_contact: str = Form(""),
    effective_date: str = Form(""),
    transfer_reason: str = Form(""),
    supporting_reference: str = Form(""),
    notes: str = Form(""),
):
    """Execute a copyright ownership transfer."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_transfer_management_service.execute_transfer(
            pdf_bytes, current_owner_name, current_owner_org,
            new_owner_name, new_owner_org, new_owner_contact,
            effective_date, transfer_reason, supporting_reference, notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Transfer execute error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to execute transfer.")


@router.post("/transfer/history")
async def transfer_history(file: UploadFile = File(...)):
    """Get transfer history for a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_transfer_management_service.get_transfer_history(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Transfer history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to get transfer history.")


@router.post("/transfer/report")
async def transfer_report(file: UploadFile = File(...)):
    """Generate a transfer report."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_transfer_management_service.generate_report(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Transfer report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate transfer report.")


# ── Copyright Expiration Tracking ────────────────────────────────────────────


@router.post("/expiration/track")
async def expiration_track(
    file: UploadFile = File(...),
    effective_date: str = Form(""),
    expiration_date: str = Form(""),
    copyright_holder: str = Form(""),
    expiration_threshold_days: int = Form(90),
):
    """Track copyright expiration for a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_expiration_tracking_service.track(
            pdf_bytes, effective_date, expiration_date, copyright_holder, expiration_threshold_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Expiration track error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to track expiration.")


@router.post("/expiration/report")
async def expiration_report(file: UploadFile = File(...)):
    """Generate an expiration tracking report."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_expiration_tracking_service.track(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Expiration report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate expiration report.")


# ── Copyright Renewal Reminder ───────────────────────────────────────────────


@router.get("/renewal/presets")
async def renewal_presets():
    """Get available renewal reminder presets."""
    return copyright_renewal_reminder_service.get_presets()


@router.post("/renewal/configure")
async def renewal_configure(
    file: UploadFile = File(...),
    enabled: bool = Form(True),
    reminder_days: int = Form(30),
    expiration_date: str = Form(""),
    custom_description: str = Form(""),
):
    """Configure a renewal reminder for a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_renewal_reminder_service.configure_reminder(
            pdf_bytes, enabled, reminder_days, expiration_date, custom_description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Renewal configure error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to configure renewal reminder.")


@router.post("/renewal/status")
async def renewal_status(file: UploadFile = File(...)):
    """Get renewal reminder status for a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_renewal_reminder_service.get_reminder_status(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Renewal status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to get renewal status.")


@router.post("/renewal/report")
async def renewal_report(file: UploadFile = File(...)):
    """Generate a renewal reminder report."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_renewal_reminder_service.generate_report(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Renewal report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate renewal report.")


# ── Copyright Revocation Record ──────────────────────────────────────────────


@router.post("/revocation/get-record")
async def revocation_get_record(file: UploadFile = File(...)):
    """Get current copyright record for review before revocation."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_revocation_record_service.get_copyright_record(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Revocation get record error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to get copyright record.")


@router.post("/revocation/record")
async def revocation_record(
    file: UploadFile = File(...),
    revocation_date: str = Form(""),
    revocation_reason: str = Form(""),
    reference_number: str = Form(""),
    description: str = Form(""),
    notes: str = Form(""),
):
    """Record a copyright revocation."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_revocation_record_service.record_revocation(
            pdf_bytes, revocation_date, revocation_reason, reference_number, description, notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Revocation record error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to record revocation.")


@router.post("/revocation/history")
async def revocation_history(file: UploadFile = File(...)):
    """Get revocation history for a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_revocation_record_service.get_revocation_history(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Revocation history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to get revocation history.")


@router.post("/revocation/report")
async def revocation_report(file: UploadFile = File(...)):
    """Generate a revocation report."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return copyright_revocation_record_service.generate_report(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Revocation report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate revocation report.")


# ── Document Provenance Tracking ─────────────────────────────────────────────


@router.post("/provenance/track")
async def provenance_track(file: UploadFile = File(...)):
    """Track document provenance timeline."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return document_provenance_tracking_service.track(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Provenance track error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to track provenance.")


@router.post("/provenance/report")
async def provenance_report(file: UploadFile = File(...)):
    """Generate a provenance report."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return document_provenance_tracking_service.generate_report(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Provenance report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate provenance report.")


# ── Blockchain Copyright Registration ────────────────────────────────────────


@router.post("/blockchain/prepare")
async def blockchain_prepare(file: UploadFile = File(...)):
    """Prepare a blockchain registration record."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return blockchain_copyright_registration_service.prepare_registration(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Blockchain prepare error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to prepare blockchain registration.")


@router.post("/blockchain/report")
async def blockchain_report(file: UploadFile = File(...)):
    """Generate a blockchain registration preparation report."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return blockchain_copyright_registration_service.generate_report(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Blockchain report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate blockchain report.")


# ── Blockchain Ownership Verification ────────────────────────────────────────


@router.post("/blockchain-ownership-verification/process")
async def blockchain_ownership_verification_process(file: UploadFile = File(...)):
    """Verify blockchain ownership metadata in a PDF."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No PDF file provided.")
    try:
        pdf_bytes = await file.read()
        return blockchain_copyright_registration_service.verify_ownership(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Blockchain ownership verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to verify blockchain ownership.")
