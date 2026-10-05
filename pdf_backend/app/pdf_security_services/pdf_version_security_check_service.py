import fitz
import os
import logging
from pathlib import Path
from typing import Dict, Any
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

class PDFVersionSecurityCheckService:
    def __init__(self):
        pass

    async def analyze(self, filepath: Path, original_filename: str) -> Dict[str, Any]:
        """Identifies the PDF version and provides a compatibility/security assessment."""
        if not filepath.exists():
            return {"success": False, "error": "File not found."}

        try:
            doc = fitz.open(filepath)
            
            try:
                reader = PdfReader(filepath)
                version_str = reader.pdf_header or "Unknown"
                if version_str.startswith("%PDF-"):
                    version_str = version_str[1:]
            except:
                version_str = "Unknown"
            
            is_encrypted = doc.is_encrypted
            emb_count = doc.embfile_count()
            
            # Forms & Signatures
            has_forms = False
            is_signed = False
            if doc.is_form_pdf:
                has_forms = True
                for page in doc:
                    for widget in page.widgets():
                        if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                            is_signed = True
                            
            # JS and Actions (Basic check for security compatibility context)
            has_js = False
            has_actions = False
            
            try:
                catalog = doc.xref_object(doc.pdf_catalog())
                if "/OpenAction" in catalog:
                    has_actions = True
                if "/AA" in catalog:
                    has_actions = True
            except:
                pass
                
            # xref scan for JS
            for xref in range(1, doc.xref_length()):
                try:
                    obj_text = doc.xref_object(xref)
                    if not obj_text: continue
                    if "/JS" in obj_text or "/JavaScript" in obj_text:
                        has_js = True
                    if "/Launch" in obj_text:
                        has_actions = True
                except:
                    continue
                    
            doc.close()
            
            if has_js or has_actions or emb_count > 0:
                assessment = "Security review recommended because the document contains active content or features requiring additional inspection."
            else:
                assessment = "PDF version detected successfully. No version-specific security concern was identified from the available static checks."
                
            # Required compliance fallback string
            vulnerability_note = "Version identified. No local vulnerability intelligence database is configured; therefore version-based vulnerability confirmation is not available."

            return {
                "success": True,
                "status": "completed",
                "document_version": version_str,
                "version_detection": "Detected successfully",
                "security_compatibility": {
                    "Encryption": "Enabled" if is_encrypted else "Disabled",
                    "JavaScript": "Present" if has_js else "Not Detected",
                    "Embedded Files": "Detected" if emb_count > 0 else "None Detected",
                    "Digital Signature": "Present" if is_signed else "Not Detected",
                    "Active Actions": "Detected" if has_actions else "None Detected"
                },
                "assessment": assessment,
                "vulnerability_note": vulnerability_note
            }

        except Exception as e:
            logger.error(f"Error in version check: {e}", exc_info=True)
            return {"success": False, "error": f"Unable to analyze this PDF because the document is corrupted or uses an unsupported structure."}

pdf_version_security_check_service = PDFVersionSecurityCheckService()
