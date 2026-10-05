from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse
from app.pdf_signature_services.pdf_sign_service import PdfSignService
from app.pdf_signature_services.digital_sign_service import DigitalSignService
from app.pdf_signature_services.e_sign_service import ESignService
from app.pdf_security_services.secure_sharing_service import SecureSharingService
from app.utils.file_handler import save_upload_file_tmp
from app.core.paths import get_output_path
import asyncio
import os
import json
import uuid
import logging

logger = logging.getLogger(__name__)

# ============================================================
# SUB SECTION 1 — PDF SIGN
# ============================================================

router = APIRouter()

@router.post("/signature/sign")
async def sign_pdf(
    request: Request,
    file: UploadFile = File(...),
    signatures: str = Form(...)
):
    """
    Sign a PDF with multiple image/drawn signatures.
    signatures is a JSON string of a list of signature objects.
    """
    try:
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="PDF file is required.")
        if not signatures:
            raise HTTPException(status_code=400, detail="Signature data is required.")

        result = await PdfSignService.process_pdf_sign(file, signatures)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in sign_pdf endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signature/download/{filename}")
async def download_signed_pdf(filename: str):
    """Download the signed PDF."""
    file_path = get_output_path(filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/pdf", filename=filename)

# ============================================================
# SUB SECTION 3 â€” E-SIGN
# ============================================================

@router.get("/signature/e-sign/capabilities")
async def e_sign_capabilities():
    return ESignService.capabilities()

@router.post("/signature/e-sign/initiate")
async def initiate_aadhaar_esign(
    file: UploadFile = File(...),
    placement: str = Form("{}"),
    user_email: str = Form("mock@example.com"),
    user_name: str = Form("Mock User"),
    user_role: str = Form("Signer")
):
    try:
        try:
            placement_data = json.loads(placement)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="Placement must be valid JSON.") from exc

        user_info = {
            "email": user_email,
            "name": user_name,
            "role": user_role
        }

        return await ESignService.initiate_esign(
            file=file,
            method="aadhaar_esign",
            placement=placement_data,
            user_info=user_info
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("initiate_aadhaar_esign endpoint failed")
        raise HTTPException(status_code=500, detail="Electronic signing initiation failed.") from exc

@router.post("/signature/e-sign/verify-callback")
async def verify_esign_callback(
    request: Request
):
    try:
        data = await request.json()
        transaction_id = data.get("transaction_id")
        provider_response = data.get("provider_response", {})
        if not transaction_id:
            raise HTTPException(status_code=400, detail="transaction_id required.")

        return await ESignService.verify_callback(transaction_id, provider_response)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("verify_esign_callback endpoint failed")
        raise HTTPException(status_code=500, detail="Callback verification failed.") from exc

@router.get("/signature/e-sign/history")
async def esign_history(user_email: str):
    return {"history": ESignService.get_history(user_email)}

@router.post("/signature/e-sign")
async def e_sign_pdf(
    file: UploadFile = File(...),
    method: str = Form(...),
    placement: str = Form(...),
    signature_data: str = Form(""),
    signer_name: str = Form(""),
):
    try:
        raise HTTPException(status_code=400, detail="Legacy e-sign method is deprecated for Aadhaar eSign")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("eSign endpoint failed")
        raise HTTPException(status_code=500, detail="Electronic signing failed due to an unexpected server error.") from exc

@router.post("/signature/e-sign/share")
async def share_e_signed_pdf(
    filename: str = Form(...),
    password: str = Form(""),
    expires_at: str = Form(""),
    allow_download: bool = Form(True),
    allow_print: bool = Form(False),
):
    try:
        file_path = get_output_path(filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Signed PDF file not found.")

        result = SecureSharingService.create_share(
            source_file_path=file_path,
            original_filename=filename,
            password=password or None,
            expires_at=expires_at or None,
            allow_download=allow_download,
            allow_print=allow_print,
        )
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("eSign share endpoint failed")
        raise HTTPException(status_code=500, detail="Could not create a secure share link.") from exc

# ============================================================
# DIGITAL SIGNATURE
# ============================================================

@router.post("/signature/digital/parse-cert")
async def parse_certificate(
    file: UploadFile = File(...),
    password: str = Form("")
):
    try:
        temp_p12 = await save_upload_file_tmp(file)
        result = DigitalSignService.parse_certificate(temp_p12, password)
        os.remove(temp_p12)
        return result
    except Exception as e:
        if 'temp_p12' in locals() and os.path.exists(temp_p12):
            os.remove(temp_p12)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/signature/digital/sign")
async def sign_digital_pdf(
    file: UploadFile = File(...),
    cert_file: UploadFile = File(...),
    password: str = Form(""),
    config: str = Form("{}")
):
    try:
        temp_pdf = await save_upload_file_tmp(file)
        temp_p12 = await save_upload_file_tmp(cert_file)
        
        cfg = json.loads(config)
        
        file_name, ext = os.path.splitext(file.filename)
        output_filename = f"{file_name}_digital_{uuid.uuid4().hex[:6]}{ext}"
        output_path = get_output_path(output_filename)
        
        result = await asyncio.to_thread(
            DigitalSignService.sign_pdf,
            temp_pdf,
            temp_p12,
            password,
            cfg,
            str(output_path),
        )
        
        os.remove(temp_pdf)
        os.remove(temp_p12)
        
        return {
            **result,
            "filename": output_filename,
            "downloadUrl": f"/api/pdf/signature/download/{output_filename}"
        }
    except Exception as e:
        if 'temp_pdf' in locals() and os.path.exists(temp_pdf):
            os.remove(temp_pdf)
        if 'temp_p12' in locals() and os.path.exists(temp_p12):
            os.remove(temp_p12)
        logger.exception("Digital signature endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/signature/digital/validate")
async def validate_digital_signature(
    file: UploadFile = File(...)
):
    try:
        temp_pdf = await save_upload_file_tmp(file)
        result = await asyncio.to_thread(DigitalSignService.validate_signature, temp_pdf)
        os.remove(temp_pdf)
        return result
    except Exception as e:
        if 'temp_pdf' in locals() and os.path.exists(temp_pdf):
            os.remove(temp_pdf)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# USB TOKEN SIGNATURE
# ============================================================
from app.pdf_signature_services.usb_token_service import UsbTokenService

@router.get("/usb-token/status")
async def usb_token_status():
    return UsbTokenService.get_token_status()

@router.get("/usb-token/certificates")
async def usb_token_certificates():
    try:
        return UsbTokenService.get_certificates()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/usb-token/validate-certificate")
async def validate_token_certificate(serial_number: str = Form(...)):
    try:
        return UsbTokenService.validate_certificate(serial_number)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/usb-token/sign")
async def usb_token_sign(
    file: UploadFile = File(...),
    pin: str = Form(...),
    cert_serial: str = Form(...),
    user_id: str = Form("mock_user_id")
):
    try:
        temp_pdf = await save_upload_file_tmp(file)
        
        file_name, ext = os.path.splitext(file.filename)
        output_filename = f"{file_name}_usb_signed_{uuid.uuid4().hex[:6]}{ext}"
        output_path = get_output_path(output_filename)
        
        result = await asyncio.to_thread(
            UsbTokenService.sign_pdf,
            temp_pdf,
            str(output_path),
            pin,
            cert_serial,
            user_id
        )
        
        os.remove(temp_pdf)
        
        return {
            **result,
            "filename": output_filename,
            "downloadUrl": f"/api/pdf/signature/download/{output_filename}"
        }
    except Exception as e:
        if 'temp_pdf' in locals() and os.path.exists(temp_pdf):
            os.remove(temp_pdf)
        logger.exception("USB Token signing failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/usb-token/validate")
async def validate_usb_signature(file: UploadFile = File(...)):
    try:
        temp_pdf = await save_upload_file_tmp(file)
        result = await asyncio.to_thread(UsbTokenService.validate_signature, temp_pdf)
        os.remove(temp_pdf)
        return result
    except Exception as e:
        if 'temp_pdf' in locals() and os.path.exists(temp_pdf):
            os.remove(temp_pdf)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/usb-token/history")
async def usb_token_history(user_id: str):
    return {"history": UsbTokenService.get_history(user_id)}
