"""
Blockchain Copyright Registration Service — PDF Copyright Protection Section.

Prepares blockchain registration records since no blockchain provider is configured.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - environment may not have PyMuPDF installed
    fitz = None

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024


class BlockchainCopyrightRegistrationService:
    """Prepare blockchain registration records for PDF documents."""

    def _validate_pdf(self, pdf_bytes: bytes) -> None:
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise ValueError("Uploaded file is empty.")
        if len(pdf_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValueError("File size exceeds the 200 MB limit.")
        if not pdf_bytes[:5].startswith(b"%PDF"):
            raise ValueError("Invalid PDF document (missing %PDF header).")

    def _compute_hash(self, pdf_bytes: bytes) -> str:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            content_hash = hashlib.sha256()
            has_content = False
            for page in doc:
                text = page.get_text()
                if text:
                    content_hash.update(text.encode('utf-8'))
                    has_content = True
                for img in page.get_images(full=True):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    if base_image and "image" in base_image:
                        content_hash.update(base_image["image"])
                        has_content = True
            doc.close()
            if has_content:
                return content_hash.hexdigest()
            return hashlib.sha256(pdf_bytes).hexdigest()
        except Exception:
            return hashlib.sha256(pdf_bytes).hexdigest()

    def _extract_metadata(self, pdf_bytes: bytes) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        try:
            if fitz is None:
                raise ImportError(
                    "PyMuPDF (fitz) is not installed. Install with: pip install PyMuPDF"
                )
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            meta = doc.metadata or {}
            for key in ["author", "creator", "producer", "title", "subject"]:
                result[key] = str(meta.get(key, "")).strip()
            result["creation_date"] = str(meta.get("creationDate", "")).strip()
            custom_keys = ["copyright_holders", "ownership_information", "copyright_registration"]
            for key in custom_keys:
                raw = meta.get(key, "") or ""
                if raw:
                    try:
                        result[key] = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = raw
                else:
                    result[key] = None
            result["total_pages"] = doc.page_count
            result["file_size"] = len(pdf_bytes)
            doc.close()
        except Exception as e:
            logger.warning(f"Metadata extraction error: {e}")
        return result

    def prepare_registration(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Prepare a blockchain registration record."""
        self._validate_pdf(pdf_bytes)
        doc_hash = self._compute_hash(pdf_bytes)
        metadata = self._extract_metadata(pdf_bytes)
        now = datetime.now(timezone.utc)
        copyright_holders = metadata.get("copyright_holders")
        holder_info = None
        if copyright_holders and isinstance(copyright_holders, list) and copyright_holders:
            holder_info = copyright_holders[0]
        elif metadata.get("author"):
            holder_info = {"name": metadata["author"], "organization": ""}
        else:
            holder_info = {"name": "Not specified", "organization": ""}
        registration_payload = {
            "document_hash": doc_hash,
            "hash_algorithm": "SHA-256",
            "copyright_holder": holder_info,
            "document_identifier": metadata.get("title", "") or "Untitled",
            "registration_timestamp": now.isoformat(),
            "copyright_info": {
                "author": metadata.get("author", "") or "Not Available",
                "title": metadata.get("title", "") or "Not Available",
                "creation_date": metadata.get("creation_date", "") or "Not Available",
            },
            "registration_info": metadata.get("copyright_registration"),
            "file_size": metadata.get("file_size", 0),
            "total_pages": metadata.get("total_pages", 0),
        }
        return {
            "success": True,
            "registration": {
                "status": "Prepared for Blockchain Registration",
                "network": "Not configured",
                "transaction_hash": None,
                "block_number": None,
                "confirmation_count": None,
                "registration_payload": registration_payload,
                "document_info": {
                    "title": metadata.get("title", "") or "Untitled",
                    "author": metadata.get("author", "") or "Not Available",
                    "document_hash": doc_hash,
                },
            },
            "timestamp": now.isoformat(),
            "message": "Blockchain registration record prepared successfully.",
            "disclaimer": (
                "Blockchain transaction not submitted — no blockchain network is configured. "
                "This record is prepared for future blockchain registration only. "
                "It does not constitute a blockchain registration or confirmation."
            ),
        }

    def generate_report(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Generate a blockchain registration preparation report."""
        result = self.prepare_registration(pdf_bytes)
        return {
            "success": True,
            "report": result["registration"],
            "timestamp": result["timestamp"],
            "message": "Blockchain registration preparation report generated.",
            "disclaimer": result["disclaimer"],
        }
    def verify_ownership(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Verify if the document has blockchain ownership metadata."""
        self._validate_pdf(pdf_bytes)
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            metadata = doc.metadata or {}
            
            # Check for blockchain specific metadata
            blockchain_tx = metadata.get("BlockchainTxId", "") or metadata.get("blockchain_tx_id", "") or metadata.get("tx_id", "")
            owner = metadata.get("CopyrightOwner", "") or metadata.get("author", "") or metadata.get("creator", "")
            network = metadata.get("BlockchainNetwork", "") or metadata.get("network", "")
            
            # Additional check: look through XMP metadata if available
            xmp = doc.get_xml_metadata()
            if xmp and not blockchain_tx:
                if "BlockchainTxId" in xmp:
                    blockchain_tx = "Found in XMP"
                    
            is_verified = bool(blockchain_tx)
            
            verification_result = {
                "is_verified": is_verified,
                "blockchain_tx_id": blockchain_tx if is_verified else None,
                "owner": owner if owner else "Unknown",
                "network": network if network else ("Ethereum" if is_verified else None),
                "timestamp": metadata.get("creationDate", "") if is_verified else None,
                "hash": self._compute_hash(pdf_bytes)
            }
            
            return {
                "status": "success",
                "message": "Blockchain ownership verification successful." if is_verified else "No blockchain records found.",
                "verification_result": verification_result
            }
            
        except Exception as e:
            logger.error(f"Error in verifying ownership: {e}")
            raise ValueError("Failed to analyze PDF for blockchain ownership.")


blockchain_copyright_registration_service = BlockchainCopyrightRegistrationService()
