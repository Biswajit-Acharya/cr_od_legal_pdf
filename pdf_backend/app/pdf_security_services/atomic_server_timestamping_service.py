import fitz
import os
import uuid
import datetime
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any

from app.core.paths import Paths

logger = logging.getLogger(__name__)

class AtomicServerTimestampingService:
    def __init__(self):
        pass
        
    def _calculate_sha256(self, filepath: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    async def apply_timestamp(self, filepath: Path, original_filename: str, request_id: str) -> Dict[str, Any]:
        """
        Applies a trusted server timestamp to the PDF.
        Since no external TSA is configured, this acts as a 'Server Timestamp'.
        It calculates the document's SHA-256 hash and associates it securely.
        """
        if not filepath.exists():
            return {"success": False, "error": "File not found."}

        try:
            # 1. Calculate Document Hash
            doc_hash = self._calculate_sha256(filepath)

            # Generate UTC timestamp
            now = datetime.datetime.now(datetime.timezone.utc)
            timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Format standard PDF date string: D:YYYYMMDDHHmmSSZ
            pdf_date_str = now.strftime("D:%Y%m%d%H%M%SZ")
            
            output_filename = f"timestamped_{uuid.uuid4().hex[:8]}_{original_filename}"
            output_path = Paths.request_output(request_id) / output_filename
            
            # 2. Embed Server Timestamp Metadata
            doc = fitz.open(filepath)
            
            if doc.is_encrypted:
                doc.close()
                return {"success": False, "error": "Cannot timestamp encrypted PDF. Please unlock it first."}

            # Check if digital signatures exist (we cannot modify signed PDFs without breaking them)
            # fitz has doc.get_sigflags() but it's easier to check if form fields have signatures.
            # PyMuPDF doesn't strictly invalidate signatures on append if we use incremental=True, 
            # but standard save() breaks them. Let's do a basic check.
            if doc.is_form_pdf:
                for widget in doc[0].widgets():
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        doc.close()
                        return {
                            "success": False, 
                            "error": "Existing Digital Signature Detected. Applying a server timestamp would invalidate the existing signature."
                        }

            meta = doc.metadata
            meta["modDate"] = pdf_date_str
            meta["producer"] = "Nexora Server Timestamping Engine"
            meta["subject"] = f"Server Timestamp Hash: {doc_hash}"
            
            doc.set_metadata(meta)

            # 3. Add visual timestamp annotation on the first page
            if doc.page_count > 0:
                page = doc[0]
                rect = fitz.Rect(10, 10, 500, 45)
                text = f"SERVER TIMESTAMP\nTime: {timestamp_str}\nHash: {doc_hash[:32]}..."
                
                annot = page.add_text_annot(rect.tl, text)
                annot.set_colors(stroke=(0.2, 0.2, 0.8), fill=(0.9, 0.9, 1))
                annot.info["title"] = "Nexora Server Timestamp"
                annot.info["content"] = f"Time: {timestamp_str}\nHash (SHA-256): {doc_hash}"
                annot.info["creationDate"] = pdf_date_str
                annot.info["modDate"] = pdf_date_str
                annot.set_flags(fitz.PDF_ANNOT_IS_LOCKED | fitz.PDF_ANNOT_IS_PRINT | fitz.PDF_ANNOT_IS_READ_ONLY)
                annot.update()
            
            # Save the document securely
            doc.save(output_path, encryption=fitz.PDF_ENCRYPT_KEEP)
            doc.close()

            # 4. Verification Check
            # We reopen the output and check if our metadata exists
            verify_doc = fitz.open(output_path)
            verify_meta = verify_doc.metadata
            verify_doc.close()
            
            verification_passed = (
                verify_meta.get("modDate") == pdf_date_str and 
                "Nexora" in verify_meta.get("producer", "")
            )

            return {
                "success": True,
                "timestamp_type": "Server Timestamp",
                "timestamp": timestamp_str,
                "hash_sha256": doc_hash,
                "verification_status": "Verified" if verification_passed else "Failed",
                "verification_passed": verification_passed,
                "original_filename": original_filename,
                "download_url": f"/api/pdf/download/{request_id}/{output_filename}"
            }

        except Exception as e:
            logger.error(f"Error applying timestamp: {e}")
            return {"success": False, "error": str(e)}

atomic_server_timestamping_service = AtomicServerTimestampingService()
