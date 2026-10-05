import fitz
import os
import uuid
import secrets
import string
import logging
from pathlib import Path
from typing import Dict, Any

from app.core.paths import Paths

logger = logging.getLogger(__name__)

class RestrictAccessibilityCopyService:
    def __init__(self):
        pass

    def _generate_secure_password(self, length: int = 32) -> str:
        """Generates a cryptographically secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    async def process_pdf(self, filepath: Path, original_filename: str, request_id: str) -> Dict[str, Any]:
        """
        Applies PDF security to disable Accessibility and Content Extraction.
        Generates a random owner password and restricts the specific permission flags.
        Verifies the output to ensure the restriction was successfully embedded.
        """
        if not filepath.exists():
            return {"success": False, "error": "File not found."}

        try:
            # 1. Open and validate the PDF
            doc = fitz.open(filepath)
            
            if doc.is_encrypted:
                doc.close()
                return {
                    "success": False, 
                    "error": "This PDF could not be processed because its existing security settings prevent modification."
                }
            
            # 2. Setup output path and security constraints
            output_filename = f"protected_{uuid.uuid4().hex[:8]}_{original_filename}"
            output_path = Paths.request_output(request_id) / output_filename
            
            # PDF permissions in PyMuPDF are bitwise flags.
            # fitz.PDF_PERM_ACCESSIBILITY = 512
            # fitz.PDF_PERM_COPY = 16
            
            # Construct permissions by allowing everything EXCEPT COPY and ACCESSIBILITY
            perms = (
                fitz.PDF_PERM_PRINT |
                fitz.PDF_PERM_MODIFY |
                fitz.PDF_PERM_ANNOTATE |
                fitz.PDF_PERM_FORM |
                fitz.PDF_PERM_ASSEMBLE |
                fitz.PDF_PERM_PRINT_HQ
            )
            
            # We need an owner password to enforce permissions.
            owner_pw = self._generate_secure_password()
            
            # 3. Apply restrictions and save
            # We use AES_256 encryption. User password is empty so it opens without prompt.
            doc.save(
                output_path,
                encryption=fitz.PDF_ENCRYPT_AES_256,
                owner_pw=owner_pw,
                user_pw="",
                permissions=perms
            )
            doc.close()
            
            # 4. Independent Verification
            # We must reopen the generated file and verify the permissions were actually written.
            if not output_path.exists():
                return {"success": False, "error": "The PDF could not be securely protected. No protected file was generated."}
                
            verify_doc = fitz.open(output_path)
                
            # Check the permissions flag on the re-opened document
            actual_perms = verify_doc.permissions
            
            # If the accessibility bit (512) is SET, that means it's allowed. 
            # We want it to be 0 (Not allowed).
            accessibility_allowed = bool(actual_perms & fitz.PDF_PERM_ACCESSIBILITY)
            copy_allowed = bool(actual_perms & fitz.PDF_PERM_COPY)
            
            verify_doc.close()
            
            if accessibility_allowed or copy_allowed:
                output_path.unlink(missing_ok=True)
                return {
                    "success": False, 
                    "error": "Verification failed: The PDF library was unable to properly enforce the accessibility restriction on this document."
                }

            # 5. Return success
            return {
                "success": True,
                "message": "Accessibility-based copying and content extraction have been restricted successfully.",
                "original_filename": original_filename,
                "output_filename": output_filename,
                "verification_passed": True,
                "download_url": f"/api/pdf/download/{request_id}/{output_filename}"
            }

        except Exception as e:
            logger.error(f"Error restricting accessibility copy: {e}", exc_info=True)
            return {"success": False, "error": f"An error occurred while processing the document: {str(e)}"}

restrict_accessibility_copy_service = RestrictAccessibilityCopyService()
