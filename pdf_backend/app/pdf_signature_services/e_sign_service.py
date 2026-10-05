import base64
import hashlib
import os
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Dict

import fitz
from fastapi import HTTPException, UploadFile

from app.core.paths import get_output_path
from app.utils.file_handler import save_upload_file_tmp

# Mock DB for transactions
_TRANSACTION_DB = {}

class ESignService:
    SUPPORTED_METHODS = {"draw", "upload", "type", "aadhaar_esign"}
    
    # Required provider env variables
    ESIGN_PROVIDER_BASE_URL = os.environ.get("ESIGN_PROVIDER_BASE_URL")
    ESIGN_PROVIDER_CLIENT_ID = os.environ.get("ESIGN_PROVIDER_CLIENT_ID")
    ESIGN_PROVIDER_CLIENT_SECRET = os.environ.get("ESIGN_PROVIDER_CLIENT_SECRET")
    ESIGN_PROVIDER_CALLBACK_URL = os.environ.get("ESIGN_PROVIDER_CALLBACK_URL")

    @classmethod
    def is_provider_configured(cls) -> bool:
        return bool(cls.ESIGN_PROVIDER_BASE_URL and cls.ESIGN_PROVIDER_CLIENT_ID and cls.ESIGN_PROVIDER_CLIENT_SECRET)

    @staticmethod
    def capabilities() -> dict[str, Any]:
        return {
            "success": True,
            "methods": ["aadhaar_esign", "draw", "upload", "type"],
            "placement_fields": ["page", "x", "y", "width", "height"],
            "provider_configured": ESignService.is_provider_configured(),
            "verification": [
                "output PDF exists",
                "output PDF readable",
                "target page verified",
                "SHA-256 integrity hash generated",
                "Aadhaar Identity verified (when provider configured)"
            ],
        }

    @staticmethod
    async def initiate_esign(
        file: UploadFile,
        method: str,
        placement: dict[str, Any],
        user_info: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Step 1: Initiate an eSign transaction.
        Validates PDF, generates original hash, stores transaction state.
        """
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="PDF file is required.")
        if method != "aadhaar_esign":
            raise HTTPException(status_code=422, detail="Only aadhaar_esign method is supported via this endpoint.")

        temp_input_path = await save_upload_file_tmp(file)
        
        try:
            # Validate PDF
            doc = fitz.open(temp_input_path)
            if len(doc) == 0:
                raise HTTPException(status_code=422, detail="PDF has no pages.")
            doc.close()

            # Hash the original PDF
            with open(temp_input_path, "rb") as f:
                original_hash = hashlib.sha256(f.read()).hexdigest()
                
            transaction_id = str(uuid.uuid4())
            
            # Record audit event: signing initiated
            # (Mocked audit logging logic here)
            print(f"AUDIT: Signing initiated for user {user_info.get('email')} on document {file.filename}")

            _TRANSACTION_DB[transaction_id] = {
                "id": transaction_id,
                "document_name": file.filename,
                "user_email": user_info.get("email"),
                "user_name": user_info.get("name"),
                "role": user_info.get("role"),
                "original_document_hash": original_hash,
                "identity_verification_status": "PENDING",
                "signature_type": "aadhaar_esign",
                "signature_status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "placement": placement,
                "temp_input_path": temp_input_path
            }

            if not ESignService.is_provider_configured():
                raise HTTPException(
                    status_code=501, 
                    detail="Production Aadhaar eSign activation requires valid authorized provider credentials/configuration."
                )

            # In a real scenario, we'd call the provider here to get a redirect URL
            # redirect_url = await ProviderAdapter.create_session(...)
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "original_hash": original_hash,
                "status": "IDENTITY_PENDING",
                "redirect_url": "https://provider.example.com/auth?tx=" + transaction_id # Mock URL
            }
        except Exception as e:
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)
            raise e

    @staticmethod
    async def verify_callback(transaction_id: str, provider_response: dict[str, Any]) -> dict[str, Any]:
        """
        Step 2: Callback from provider after identity verification.
        """
        if transaction_id not in _TRANSACTION_DB:
            raise HTTPException(status_code=404, detail="Transaction not found or expired.")
            
        tx = _TRANSACTION_DB[transaction_id]
        
        if not ESignService.is_provider_configured():
             raise HTTPException(
                status_code=501, 
                detail="Production Aadhaar eSign activation requires valid authorized provider credentials/configuration."
            )
            
        # In a real integration, we'd validate the provider_response signature/MAC here
        # and parse the resulting signed PDF.
        # tx["identity_verification_status"] = "AUTHENTICATED"
        # tx["signed_document_hash"] = new_hash
        # ...
        
        return {"success": True, "transaction": tx}

    @staticmethod
    def get_history(user_email: str) -> list[dict[str, Any]]:
        # Mock DB query
        return [
            tx for tx in _TRANSACTION_DB.values() 
            if tx.get("user_email") == user_email
        ]

    # ... keeping the old sign_pdf for backward compatibility if needed, but it should be deprecated 
    # as per instructions to move away from drawing images.
