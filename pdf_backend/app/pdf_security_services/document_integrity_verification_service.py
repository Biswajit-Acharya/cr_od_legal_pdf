"""
Document integrity verification service.

Performs PDF validation, structural checks, hashing, signature detection,
incremental update analysis, metadata extraction, optional trusted reference
comparison, and report generation.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz
from pypdf import PdfReader

from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentIntegrityVerificationService:
    """Verify PDF integrity without overstating authenticity."""

    VALID_MIME_TYPES = {
        None,
        "",
        "application/pdf",
        "application/x-pdf",
        "application/octet-stream",
    }

    STATUSES = {
        "VERIFIED",
        "MODIFIED",
        "SIGNATURE_PRESENT",
        "SIGNATURE_INVALID",
        "SIGNATURE_UNVALIDATED",
        "STRUCTURAL_WARNING",
        "CORRUPTED",
        "REFERENCE_MISMATCH",
        "UNABLE_TO_VERIFY",
    }

    def verify_document(
        self,
        input_path: str | Path,
        *,
        original_filename: str | None = None,
        mime_type: str | None = None,
        reference_path: str | Path | None = None,
        reference_filename: str | None = None,
        reference_mime_type: str | None = None,
        output_dir: str | Path | None = None,
    ) -> Dict[str, Any]:
        """Run the full document integrity verification workflow."""
        verification_id = self.generate_verification_id()
        filename = Path(original_filename or Path(input_path).name).name
        logger.info("Document integrity verification started: %s", verification_id)

        try:
            validation = self.validate_pdf(input_path, mime_type=mime_type)
            hashes = self.calculate_hashes(input_path)
            pdf_integrity = self.analyze_pdf_structure(input_path)
            digital_signature = self.analyze_signatures(input_path)
            incremental_updates = self.analyze_incremental_updates(input_path)
            metadata = self.extract_metadata(input_path)
            reference_comparison = self.compare_reference(
                input_path,
                reference_path,
                reference_mime_type=reference_mime_type,
            )

            warnings = []
            errors = []
            warnings.extend(pdf_integrity.get("warnings", []))
            warnings.extend(digital_signature.get("warnings", []))
            warnings.extend(incremental_updates.get("warnings", []))
            errors.extend(pdf_integrity.get("errors", []))

            status = self.determine_status(
                pdf_integrity=pdf_integrity,
                digital_signature=digital_signature,
                incremental_updates=incremental_updates,
                reference_comparison=reference_comparison,
                errors=errors,
                warnings=warnings,
            )

            result = {
                "success": True,
                "verification_id": verification_id,
                "filename": filename,
                "file_size": validation["file_size"],
                "mime_type": mime_type or "application/pdf",
                "status": status,
                "file_integrity": hashes,
                "hash_fingerprints": [
                    {
                        "algorithm": "SHA-256",
                        "hash": hashes["sha256"],
                        "verified_against_reference": bool(
                            reference_comparison.get("performed")
                            and reference_comparison.get("exact_match") is True
                        ),
                    },
                    {
                        "algorithm": "SHA-512",
                        "hash": hashes["sha512"],
                        "verified_against_reference": False,
                    },
                ],
                "pdf_integrity": pdf_integrity,
                "digital_signature": digital_signature,
                "incremental_updates": incremental_updates,
                "metadata": metadata,
                "reference_comparison": reference_comparison,
                "warnings": warnings,
                "errors": errors,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "message": self._status_message(status, reference_comparison, digital_signature),
            }
            self._persist_result(result, output_dir)
            logger.info("Document integrity verification completed: %s status=%s", verification_id, status)
            return result
        except ValueError as exc:
            logger.warning("Document integrity validation failed: %s", exc)
            return {
                "success": False,
                "verification_id": verification_id,
                "filename": filename,
                "status": "UNABLE_TO_VERIFY",
                "error": str(exc),
                "errors": [str(exc)],
                "warnings": [],
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.error("Document integrity verification failed: %s", exc, exc_info=True)
            return {
                "success": False,
                "verification_id": verification_id,
                "filename": filename,
                "status": "UNABLE_TO_VERIFY",
                "error": "Unable to verify document integrity.",
                "errors": ["An internal verification error occurred."],
                "warnings": [],
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

    def validate_pdf(self, input_path: str | Path, *, mime_type: str | None = None) -> Dict[str, Any]:
        """Validate file existence, size, type, magic bytes and parser readability."""
        path = Path(input_path)
        if not path.exists() or not path.is_file():
            raise ValueError("PDF file is required.")
        if path.suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported.")
        if mime_type not in self.VALID_MIME_TYPES:
            raise ValueError("Uploaded file must be a PDF.")

        size = path.stat().st_size
        if size <= 0:
            raise ValueError("Uploaded PDF is empty.")
        if size > settings.MAX_UPLOAD_SIZE:
            raise ValueError(f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.")

        with open(path, "rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise ValueError("Invalid PDF file.")

        try:
            doc = fitz.open(path)
            page_count = doc.page_count
            encrypted = doc.is_encrypted
            doc.close()
        except Exception as exc:
            raise ValueError("Invalid or corrupted PDF file.") from exc

        return {"file_size": size, "page_count": page_count, "encrypted": encrypted}

    def calculate_hashes(self, input_path: str | Path) -> Dict[str, str]:
        """Calculate SHA-256 and SHA-512 using streaming reads."""
        sha256 = __import__("hashlib").sha256()
        sha512 = __import__("hashlib").sha512()
        with open(input_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sha256.update(chunk)
                sha512.update(chunk)
        return {"sha256": sha256.hexdigest(), "sha512": sha512.hexdigest()}

    def analyze_pdf_structure(self, input_path: str | Path) -> Dict[str, Any]:
        """Analyze parser and structural integrity indicators."""
        warnings: List[str] = []
        errors: List[str] = []
        path = Path(input_path)

        try:
            with open(path, "rb") as handle:
                header = handle.read(16).decode("latin-1", errors="ignore")
        except Exception:
            header = ""
            errors.append("Unable to read PDF header.")

        try:
            with open(path, "rb") as handle:
                handle.seek(max(0, path.stat().st_size - 2048))
                tail = handle.read()
            eof_marker_present = b"%%EOF" in tail
        except Exception:
            eof_marker_present = False
            errors.append("Unable to inspect EOF marker.")

        doc = None
        page_count: Optional[int] = None
        encrypted = False
        xref_count: Optional[int] = None
        document_catalog_present = False
        trailer_present = False
        parser_status = "valid"

        try:
            doc = fitz.open(path)
            page_count = doc.page_count
            encrypted = bool(doc.is_encrypted)
            xref_count = doc.xref_length()
            document_catalog_present = bool(doc.pdf_catalog())
            try:
                trailer_present = bool(doc.pdf_trailer())
            except Exception:
                warnings.append("PDF trailer could not be fully read.")
            for xref in range(1, min(xref_count or 1, 250)):
                try:
                    doc.xref_object(xref)
                except Exception:
                    warnings.append(f"Malformed object detected near xref {xref}.")
                    break
        except Exception as exc:
            parser_status = "invalid"
            errors.append("PDF parser failed to read the document.")
            logger.warning("PDF structural parser failure: %s", exc)
        finally:
            if doc is not None:
                doc.close()

        try:
            reader = PdfReader(str(path), strict=False)
            if not getattr(reader, "trailer", None):
                warnings.append("PDF trailer is missing or unreadable.")
            if "/Root" in reader.trailer:
                document_catalog_present = True
            encrypted = encrypted or bool(reader.is_encrypted)
        except Exception as exc:
            warnings.append("Secondary PDF parser reported structural warnings.")
            logger.debug("pypdf structural analysis warning: %s", exc)

        if not header.startswith("%PDF-"):
            errors.append("PDF header is missing or invalid.")
        if not eof_marker_present:
            warnings.append("EOF marker was not found near the end of the file.")
        if not document_catalog_present:
            warnings.append("Document catalog was not confirmed.")
        if page_count is None:
            errors.append("Page tree could not be read.")

        return {
            "is_valid_pdf": parser_status == "valid" and not errors,
            "parser_status": parser_status,
            "pdf_header": header.strip() or None,
            "pdf_version": self._pdf_version_from_header(header),
            "eof_marker_present": eof_marker_present,
            "cross_reference_objects": xref_count,
            "trailer_present": trailer_present,
            "document_catalog_present": document_catalog_present,
            "page_tree_present": page_count is not None,
            "page_count": page_count,
            "encrypted": encrypted,
            "warnings": warnings,
            "errors": errors,
        }

    def analyze_signatures(self, input_path: str | Path) -> Dict[str, Any]:
        """Detect digital signatures and validate only when library support succeeds."""
        signatures: List[Dict[str, Any]] = []
        warnings: List[str] = []

        try:
            from app.pdf_security_services.digital_signature_verification_service import (
                digital_signature_verification_service,
            )
            from pyhanko.pdf_utils.reader import PdfFileReader

            with open(input_path, "rb") as handle:
                reader = PdfFileReader(handle)
                embedded_signatures = list(reader.embedded_signatures)

                for index, embedded_sig in enumerate(embedded_signatures, start=1):
                    try:
                        status = digital_signature_verification_service.verify_cryptographic_signature(embedded_sig)
                        signatures.append(
                            digital_signature_verification_service.build_signature_result(
                                index,
                                embedded_sig,
                                status=status,
                            )
                        )
                    except Exception as exc:
                        warnings.append("A signature was detected but could not be fully validated.")
                        signatures.append(
                            digital_signature_verification_service.build_signature_result(
                                index,
                                embedded_sig,
                                error=exc,
                            )
                        )
        except Exception as exc:
            logger.warning("Signature detection failed: %s", exc)
            warnings.append("Signature detection was unavailable for this PDF.")
            return {
                "signature_present": False,
                "signature_count": 0,
                "signature_details": [],
                "validation_status": "validation_unavailable",
                "warnings": warnings,
            }

        validation_status = "not_applicable"
        if signatures:
            if any(sig.get("signature_status") == "INVALID" for sig in signatures):
                validation_status = "invalid"
            elif all(sig.get("signature_status") == "VALID" for sig in signatures):
                validation_status = "validated"
            elif any(sig.get("signature_status") in {"ERROR", "UNKNOWN"} for sig in signatures):
                validation_status = "not_validated"
            else:
                validation_status = "unsupported"

        return {
            "signature_present": bool(signatures),
            "signature_count": len(signatures),
            "signature_details": signatures,
            "validation_status": validation_status,
            "warnings": warnings,
        }

    def analyze_incremental_updates(self, input_path: str | Path) -> Dict[str, Any]:
        """Inspect raw PDF markers for incremental revisions."""
        warnings: List[str] = []
        try:
            data = Path(input_path).read_bytes()
            startxref_count = data.count(b"startxref")
            eof_count = data.count(b"%%EOF")
            trailer_count = len(re.findall(rb"\btrailer\b", data))
            prev_count = data.count(b"/Prev")
            revision_count = max(startxref_count, eof_count, 1)
            detected = revision_count > 1 or prev_count > 0
            return {
                "detected": detected,
                "status": "detected" if detected else "not_detected",
                "incremental_updates_detected": detected,
                "revision_count": revision_count,
                "startxref_count": startxref_count,
                "eof_marker_count": eof_count,
                "trailer_count": trailer_count,
                "previous_xref_markers": prev_count,
                "warnings": warnings,
            }
        except Exception as exc:
            logger.warning("Incremental update analysis failed: %s", exc)
            return {
                "detected": None,
                "status": "unknown",
                "incremental_updates_detected": None,
                "revision_count": None,
                "warnings": ["Incremental update analysis failed."],
            }

    def extract_metadata(self, input_path: str | Path) -> Dict[str, Any]:
        """Extract non-content PDF metadata."""
        try:
            doc = fitz.open(input_path)
            meta = doc.metadata or {}
            doc.close()
            return {
                "title": meta.get("title") or None,
                "author": meta.get("author") or None,
                "subject": meta.get("subject") or None,
                "creator": meta.get("creator") or None,
                "producer": meta.get("producer") or None,
                "creation_date": meta.get("creationDate") or None,
                "modification_date": meta.get("modDate") or None,
                "format": meta.get("format") or None,
                "pdf_version": self._pdf_version(Path(input_path)),
            }
        except Exception as exc:
            logger.warning("Metadata extraction failed: %s", exc)
            return {
                "title": None,
                "author": None,
                "subject": None,
                "creator": None,
                "producer": None,
                "creation_date": None,
                "modification_date": None,
                "format": None,
                "pdf_version": None,
                "extraction_status": "failed",
            }

    def compare_reference(
        self,
        uploaded_path: str | Path,
        reference_path: str | Path | None,
        *,
        reference_mime_type: str | None = None,
    ) -> Dict[str, Any]:
        """Compare uploaded PDF bytes against a trusted reference PDF."""
        if reference_path is None:
            return {"performed": False, "exact_match": None}

        self.validate_pdf(reference_path, mime_type=reference_mime_type)
        uploaded_sha256 = self.calculate_hashes(uploaded_path)["sha256"]
        reference_sha256 = self.calculate_hashes(reference_path)["sha256"]
        exact_match = secrets.compare_digest(uploaded_sha256, reference_sha256)
        logger.info("Reference comparison performed exact_match=%s", exact_match)
        return {
            "performed": True,
            "reference_sha256": reference_sha256,
            "uploaded_sha256": uploaded_sha256,
            "exact_match": exact_match,
            "message": (
                "Uploaded file exactly matches the trusted reference at byte level."
                if exact_match
                else "Uploaded file differs from the trusted reference at byte level."
            ),
        }

    def determine_status(
        self,
        *,
        pdf_integrity: Dict[str, Any],
        digital_signature: Dict[str, Any],
        incremental_updates: Dict[str, Any],
        reference_comparison: Dict[str, Any],
        errors: List[str],
        warnings: List[str],
    ) -> str:
        """Derive the final status from evidence without implying authenticity."""
        if errors or not pdf_integrity.get("is_valid_pdf"):
            return "CORRUPTED"
        if reference_comparison.get("performed"):
            return "VERIFIED" if reference_comparison.get("exact_match") else "REFERENCE_MISMATCH"

        sig_status = digital_signature.get("validation_status")
        if sig_status == "invalid":
            return "SIGNATURE_INVALID"
        if any(sig.get("document_modified_after_signing") is True for sig in digital_signature.get("signature_details", [])):
            return "MODIFIED"
        if digital_signature.get("signature_present"):
            if sig_status == "validated":
                return "SIGNATURE_PRESENT"
            return "SIGNATURE_UNVALIDATED"
        if warnings or incremental_updates.get("detected"):
            return "STRUCTURAL_WARNING"
        return "UNABLE_TO_VERIFY"

    def generate_verification_report(self, result: Dict[str, Any]) -> bytes:
        """Generate a compact PDF report for download."""
        doc = fitz.open()
        page = doc.new_page()
        y = 50

        def add_text(label: str, value: Any = "", *, size: int = 10, bold: bool = False) -> None:
            nonlocal page, y
            font = "hebo" if bold else "helv"
            text = f"{label}: {value}" if value != "" else str(label)
            page.insert_text((50, y), text[:180], fontsize=size, fontname=font)
            y += size + 6
            if y > page.rect.height - 50:
                page = doc.new_page()
                y = 50

        add_text("Document Integrity Verification Report", size=16, bold=True)
        add_text("Verification ID", result.get("verification_id"))
        add_text("Filename", result.get("filename"))
        add_text("Verification timestamp", result.get("verified_at"))
        add_text("Final verification status", result.get("status"))
        add_text("File size", result.get("file_size"))
        add_text("SHA-256", result.get("file_integrity", {}).get("sha256"))
        add_text("SHA-512", result.get("file_integrity", {}).get("sha512"))
        add_text("PDF validity", result.get("pdf_integrity", {}).get("is_valid_pdf"))
        add_text("Page count", result.get("pdf_integrity", {}).get("page_count"))
        add_text("Encryption status", result.get("pdf_integrity", {}).get("encrypted"))
        add_text("Digital signature status", result.get("digital_signature", {}).get("validation_status"))
        add_text("Signature count", result.get("digital_signature", {}).get("signature_count"))
        for signature in result.get("digital_signature", {}).get("signature_details", []):
            add_text("Signature field", signature.get("signature_field_name"))
            add_text("Signer", signature.get("signer_name"))
            add_text("Signature validity", signature.get("signature_status"))
            add_text("Certificate status", signature.get("certificate_status"))
            add_text("Modified after signing", signature.get("document_modified_after_signing"))
        add_text("Incremental updates", result.get("incremental_updates", {}).get("status"))
        add_text("Revision count", result.get("incremental_updates", {}).get("revision_count"))
        metadata = result.get("metadata", {})
        add_text("Title", metadata.get("title"))
        add_text("Author", metadata.get("author"))
        add_text("Subject", metadata.get("subject"))
        add_text("Creator", metadata.get("creator"))
        add_text("Producer", metadata.get("producer"))
        add_text("Creation date", metadata.get("creation_date"))
        add_text("Modification date", metadata.get("modification_date"))
        add_text("Reference comparison", result.get("reference_comparison", {}).get("exact_match"))
        add_text("Warnings", ", ".join(result.get("warnings", [])) or "None")
        add_text("Errors", ", ".join(result.get("errors", [])) or "None")
        return doc.write()

    def load_result(self, output_dir: str | Path, verification_id: str) -> Dict[str, Any]:
        path = Path(output_dir) / f"{verification_id}.json"
        if not path.exists():
            raise ValueError("Verification result not found.")
        return json.loads(path.read_text(encoding="utf-8"))

    def report_path(self, output_dir: str | Path, verification_id: str) -> Path:
        return Path(output_dir) / f"{verification_id}_report.pdf"

    def cleanup_temporary_files(self, paths: List[str | Path]) -> None:
        for path in paths:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                logger.warning("Could not clean temporary file: %s", path)

    def _persist_result(self, result: Dict[str, Any], output_dir: str | Path | None) -> None:
        if output_dir is None or not result.get("success"):
            return
        out_dir = Path(output_dir)
        os.makedirs(out_dir, exist_ok=True)
        verification_id = result["verification_id"]
        result["result_url"] = f"/api/pdf/document-integrity/result/{verification_id}"
        result["report_filename"] = f"{verification_id}_report.pdf"
        result["report_url"] = f"/api/pdf/document-integrity/report/{verification_id}"
        (out_dir / f"{verification_id}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (out_dir / result["report_filename"]).write_bytes(self.generate_verification_report(result))

    @staticmethod
    def generate_verification_id() -> str:
        return f"DIV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:12].upper()}"

    @staticmethod
    def _status_message(status: str, reference: Dict[str, Any], signature: Dict[str, Any]) -> str:
        if status == "VERIFIED":
            return "Uploaded file exactly matches the trusted reference at byte level."
        if status == "REFERENCE_MISMATCH":
            return "Uploaded file differs from the trusted reference; this does not by itself prove unauthorized modification."
        if status == "UNABLE_TO_VERIFY":
            return "PDF is structurally readable, but no trusted reference or validated signature was available to prove authenticity."
        if status == "SIGNATURE_UNVALIDATED":
            return "A digital signature was detected, but full validation was unavailable or incomplete."
        if status == "SIGNATURE_PRESENT":
            return "A digital signature was detected. Review signature details and trust status before treating the document as authentic."
        if status == "CORRUPTED":
            return "The PDF has structural errors or could not be safely parsed."
        if signature.get("signature_present"):
            return "Digital signature information is present; review validation details."
        return reference.get("message") or "Document integrity verification completed."

    @staticmethod
    def _pdf_version(path: Path) -> Optional[str]:
        try:
            with open(path, "rb") as handle:
                header = handle.read(16).decode("latin-1", errors="ignore")
            return DocumentIntegrityVerificationService._pdf_version_from_header(header)
        except Exception:
            return None

    @staticmethod
    def _pdf_version_from_header(header: str) -> Optional[str]:
        match = re.search(r"%PDF-(\d+\.\d+)", header or "")
        return match.group(1) if match else None


document_integrity_verification_service = DocumentIntegrityVerificationService()
