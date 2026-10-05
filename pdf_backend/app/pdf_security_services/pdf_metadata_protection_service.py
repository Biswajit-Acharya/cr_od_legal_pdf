import fitz
import os
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from PyPDF2 import PdfReader

from app.core.paths import Paths

logger = logging.getLogger(__name__)

class PDFMetadataProtectionService:
    def __init__(self):
        pass

    def _extract_meaningful_metadata(self, filepath: Path) -> Dict[str, str]:
        """Extracts and filters out empty or whitespace-only metadata fields using PyPDF2."""
        extracted = {}
        try:
            reader = PdfReader(str(filepath))
            raw_meta = reader.metadata
            if not raw_meta:
                return extracted

            target_fields_map = {
                '/Title': 'Title',
                '/Author': 'Author',
                '/Subject': 'Subject',
                '/Keywords': 'Keywords',
                '/Creator': 'Creator',
                '/Producer': 'Producer',
                '/CreationDate': 'Creation Date',
                '/ModDate': 'Modification Date'
            }

            for pypdf_key, display_key in target_fields_map.items():
                if pypdf_key in raw_meta:
                    val = raw_meta[pypdf_key]
                    if val and isinstance(val, str) and val.strip():
                        extracted[display_key] = val.strip()

        except Exception as e:
            logger.warning(f"PyPDF2 metadata extraction failed: {e}")
            
        return extracted

    async def analyze_metadata(self, filepath: Path, original_filename: str) -> Dict[str, Any]:
        """
        Analyzes the PDF and returns detected metadata fields and XMP presence.
        """
        if not filepath.exists():
            return {"success": False, "error": "File not found."}

        try:
            doc = fitz.open(filepath)
            
            is_encrypted = doc.is_encrypted
            if is_encrypted:
                doc.close()
                return {"success": False, "error": "Cannot analyze an encrypted PDF. Please unlock it first."}

            # Extract Standard Metadata robustly using PyPDF2
            meaningful_meta = self._extract_meaningful_metadata(filepath)
            
            # Extract XMP Metadata using PyMuPDF (fitz)
            xml_meta = doc.get_xml_metadata()
            xmp_present = bool(xml_meta and xml_meta.strip())

            doc.close()

            # Determine if any metadata is present
            metadata_count = len(meaningful_meta)
            metadata_present = metadata_count > 0 or xmp_present

            return {
                "success": True,
                "metadata_present": metadata_present,
                "metadata_count": metadata_count,
                "metadata": meaningful_meta,
                "xmp_present": xmp_present,
                "original_filename": original_filename
            }

        except Exception as e:
            logger.error(f"Error analyzing metadata: {e}")
            return {"success": False, "error": str(e)}

    async def protect_metadata(self, filepath: Path, original_filename: str, request_id: str, owner_password: Optional[str] = None) -> Dict[str, Any]:
        """
        Removes/sanitizes metadata and XMP data, applies password protection if requested, and verifies the output.
        """
        if not filepath.exists():
            return {"success": False, "error": "File not found."}

        try:
            # 1. Analyze Original
            analysis_result = await self.analyze_metadata(filepath, original_filename)
            if not analysis_result.get("success"):
                return analysis_result

            # If no metadata present, we shouldn't claim we protected anything
            if not analysis_result.get("metadata_present"):
                return {
                    "success": False,
                    "error": "There is no metadata available to protect in this PDF."
                }

            # 2. Perform Protection
            output_filename = f"protected_metadata_{uuid.uuid4().hex[:8]}_{original_filename}"
            output_path = Paths.request_output(request_id) / output_filename
            
            doc = fitz.open(filepath)
            
            # Sanitize Standard Metadata
            meta = doc.metadata
            meta["author"] = ""
            meta["creator"] = "Protected Document"
            meta["producer"] = "Protected Document"
            meta["subject"] = ""
            meta["keywords"] = ""
            meta["title"] = ""
            meta["creationDate"] = ""
            meta["modDate"] = ""
            
            doc.set_metadata(meta)

            # Delete XMP Metadata
            if analysis_result.get("xmp_present"):
                doc.del_xml_metadata()

            # Apply Security Restrictions
            restricted_permissions = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY
            
            if owner_password:
                doc.save(
                    output_path, 
                    encryption=fitz.PDF_ENCRYPT_AES_256,
                    owner_pw=owner_password,
                    user_pw="", 
                    permissions=restricted_permissions
                )
            else:
                doc.save(output_path, encryption=fitz.PDF_ENCRYPT_KEEP)
                
            doc.close()

            # 3. Verify Output
            final_analysis = await self.analyze_metadata(output_path, output_filename)
            
            final_count = final_analysis.get("metadata_count", 0)
            
            xmp_removed = analysis_result.get("xmp_present") and not final_analysis.get("xmp_present")
            xmp_verification = True if not analysis_result.get("xmp_present") else xmp_removed
            
            verification_passed = final_count <= 2 and xmp_verification

            return {
                "success": True,
                "message": "Metadata successfully protected and sanitized.",
                "original_analysis": analysis_result,
                "final_analysis": final_analysis,
                "verification_passed": verification_passed,
                "download_url": f"/api/pdf/download/{request_id}/{output_filename}"
            }

        except Exception as e:
            logger.error(f"Error protecting metadata: {e}")
            return {"success": False, "error": str(e)}

pdf_metadata_protection_service = PDFMetadataProtectionService()
