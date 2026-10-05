"""
Digital signature verification service.

Performs local PDF signature detection, pyHanko cryptographic validation,
certificate analysis, integrity/modification assessment, and report generation.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz
from cryptography import x509 as crypto_x509
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed25519, ed448, rsa

from app.core.config import settings

logger = logging.getLogger(__name__)


class DigitalSignatureVerificationService:
    """Verify digitally signed PDFs using local open-source tooling."""

    def validate_pdf(self, input_path: str | Path) -> Dict[str, Any]:
        """Validate file type, size and basic PDF readability."""
        path = Path(input_path)
        if not path.exists() or path.stat().st_size == 0:
            raise ValueError("Valid PDF file is required.")
        if path.suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported.")

        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        size = path.stat().st_size
        if size > max_size:
            raise ValueError(f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.")

        try:
            with open(path, "rb") as handle:
                if handle.read(5) != b"%PDF-":
                    raise ValueError("Invalid PDF file.")
            doc = fitz.open(path)
            info = {
                "filename": path.name,
                "file_size": size,
                "page_count": doc.page_count,
                "is_encrypted": doc.is_encrypted,
                "pdf_version": self._pdf_version(path),
            }
            doc.close()
            return info
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Invalid or corrupted PDF file.") from exc

    def _has_visual_signature(self, input_path: str | Path) -> bool:
        """Check if the PDF has a visual signature/stamp (e.g. from iLovePDF) without a cryptographic signature."""
        import fitz
        try:
            doc = fitz.open(input_path)
            # 1. Check xref for PieceInfo, Signature#20 (common in some tools like iLovePDF)
            for i in range(1, doc.xref_length()):
                try:
                    obj_str = doc.xref_object(i)
                    if not obj_str:
                        continue
                    if "PieceInfo" in obj_str or "/Signature#" in obj_str:
                        return True
                    # Check for generic Stamps that might be signatures
                    if "/Type /Annot" in obj_str and "/Subtype /Stamp" in obj_str and "Signature" in obj_str:
                        return True
                except Exception:
                    pass

            # 2. Check annotations directly
            for page in doc:
                for annot in page.annots():
                    if annot.type[0] == fitz.PDF_ANNOT_STAMP:
                        info = annot.info
                        if info and ("signature" in str(info).lower() or "sign" in str(info).lower()):
                            return True
                    elif annot.type[0] == fitz.PDF_ANNOT_WIDGET:
                        info = annot.info
                        if info and "signature" in str(info).lower():
                            return True
            return False
        except Exception:
            return False
        finally:
            if 'doc' in locals():
                doc.close()

    def detect_signatures(self, input_path: str | Path) -> List[Any]:
        """Detect embedded PDF signatures with pyHanko."""
        from pyhanko.pdf_utils.reader import PdfFileReader

        with open(input_path, "rb") as handle:
            reader = PdfFileReader(handle)
            return list(reader.embedded_signatures)

    def extract_signature_information(self, embedded_sig: Any) -> Dict[str, Any]:
        """Extract non-sensitive signature dictionary information."""
        info: Dict[str, Any] = {
            "signature_field_name": self._safe_str(getattr(embedded_sig, "field_name", None) or getattr(embedded_sig, "sig_field_name", None)),
            "signature_timestamp": None,
            "reason": None,
            "location": None,
            "filter": None,
            "sub_filter": None,
        }
        try:
            sig_obj = embedded_sig.sig_object
            if sig_obj:
                info["signature_timestamp"] = self._pdf_obj_text(sig_obj.get("/M"))
                info["reason"] = self._pdf_obj_text(sig_obj.get("/Reason"))
                info["location"] = self._pdf_obj_text(sig_obj.get("/Location"))
                info["filter"] = self._pdf_obj_text(sig_obj.get("/Filter"))
                info["sub_filter"] = self._pdf_obj_text(sig_obj.get("/SubFilter"))
        except Exception:
            pass
        return info

    def verify_cryptographic_signature(self, embedded_sig: Any) -> Any:
        """Run pyHanko's cryptographic PDF signature validation.

        pyHanko's ``validate_pdf_signature`` calls ``asyncio.run()`` internally.
        When invoked from an async context (e.g. FastAPI/uvicorn), that call
        fails with "asyncio.run() cannot be called from a running event loop".
        The fix is to execute the validation in a thread-pool worker which
        starts with a clean (no running) event loop.
        """
        import concurrent.futures
        from pyhanko.sign.validation import validate_pdf_signature
        from pyhanko_certvalidator import ValidationContext

        def _run() -> Any:
            validation_context = ValidationContext(
                trust_roots=[],
                other_certs=[],
                allow_fetching=False,
                revocation_mode="soft-fail",
            )
            return validate_pdf_signature(
                embedded_sig,
                signer_validation_context=validation_context,
                ts_validation_context=validation_context,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run)
            return future.result(timeout=60)


    def extract_certificate(self, status: Any) -> Any:
        """Extract the signing certificate from a pyHanko validation status."""
        return getattr(status, "signing_cert", None) or getattr(status, "signer_cert", None)

    def parse_certificate(self, cert: Any) -> Dict[str, Any]:
        """Parse signer certificate details using cryptography."""
        if cert is None:
            return self._empty_certificate("UNKNOWN")

        try:
            crypto_cert = crypto_x509.load_der_x509_certificate(cert.dump())
            now = datetime.now(timezone.utc)
            valid_from = crypto_cert.not_valid_before_utc
            valid_until = crypto_cert.not_valid_after_utc

            if valid_until < now:
                cert_status = "EXPIRED"
            elif valid_from > now:
                cert_status = "NOT_YET_VALID"
            else:
                cert_status = "VALID"

            public_key = crypto_cert.public_key()
            if isinstance(public_key, rsa.RSAPublicKey):
                public_key_algorithm = "RSA"
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key_algorithm = "EC"
            elif isinstance(public_key, dsa.DSAPublicKey):
                public_key_algorithm = "DSA"
            elif isinstance(public_key, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
                public_key_algorithm = public_key.__class__.__name__.replace("PublicKey", "")
            else:
                public_key_algorithm = public_key.__class__.__name__

            subject = crypto_cert.subject.rfc4514_string()
            issuer = crypto_cert.issuer.rfc4514_string()

            return {
                "certificate_status": cert_status,
                "certificate_subject": subject,
                "certificate_issuer": issuer,
                "certificate_serial_number": str(crypto_cert.serial_number),
                "certificate_valid_from": valid_from.isoformat(),
                "certificate_valid_until": valid_until.isoformat(),
                "signature_algorithm": crypto_cert.signature_algorithm_oid._name or crypto_cert.signature_algorithm_oid.dotted_string,
                "public_key_algorithm": public_key_algorithm,
                "signer_name": self.get_certificate_subject_attr(crypto_cert, crypto_x509.NameOID.COMMON_NAME),
                "organization": self.get_certificate_subject_attr(crypto_cert, crypto_x509.NameOID.ORGANIZATION_NAME),
                "organizational_unit": self.get_certificate_subject_attr(crypto_cert, crypto_x509.NameOID.ORGANIZATIONAL_UNIT_NAME),
                "country": self.get_certificate_subject_attr(crypto_cert, crypto_x509.NameOID.COUNTRY_NAME),
                "email": self.get_certificate_subject_attr(crypto_cert, crypto_x509.NameOID.EMAIL_ADDRESS),
            }
        except Exception as exc:
            logger.warning("Certificate parsing failed: %s", exc)
            return self._empty_certificate("INVALID")

    @staticmethod
    def get_certificate_subject_attr(cert: Any, oid: Any) -> Optional[str]:
        try:
            attrs = cert.subject.get_attributes_for_oid(oid)
            return attrs[0].value if attrs else None
        except Exception:
            return None

    @staticmethod
    def get_certificate_subject(cert_info: Dict[str, Any]) -> Optional[str]:
        return cert_info.get("certificate_subject")

    @staticmethod
    def get_certificate_issuer(cert_info: Dict[str, Any]) -> Optional[str]:
        return cert_info.get("certificate_issuer")

    @staticmethod
    def get_certificate_serial_number(cert_info: Dict[str, Any]) -> Optional[str]:
        return cert_info.get("certificate_serial_number")

    @staticmethod
    def check_certificate_validity(cert_info: Dict[str, Any]) -> str:
        return cert_info.get("certificate_status") or "UNKNOWN"

    def check_document_integrity(self, status: Any) -> str:
        """Map pyHanko integrity/coverage results to explicit states."""
        intact = getattr(status, "intact", None)
        if intact is True:
            return "INTACT"
        if intact is False:
            return "MODIFIED_AFTER_SIGNING"
        return "UNKNOWN"

    def detect_post_signing_modification(self, status: Any) -> Optional[bool]:
        integrity = self.check_document_integrity(status)
        if integrity == "INTACT":
            return False
        if integrity == "MODIFIED_AFTER_SIGNING":
            return True
        return None

    def extract_signature_timestamp(self, status: Any, sig_info: Dict[str, Any]) -> tuple[Optional[str], str]:
        timestamp_status = getattr(status, "timestamp_validity", None)
        if timestamp_status is not None:
            ts_valid = bool(getattr(timestamp_status, "valid", False))
            ts_intact = bool(getattr(timestamp_status, "intact", False))
            return sig_info.get("signature_timestamp"), "VALID" if ts_valid and ts_intact else "INVALID"

        signer_dt = getattr(status, "signer_reported_dt", None)
        if signer_dt:
            try:
                return signer_dt.isoformat(), "UNTRUSTED_SIGNER_REPORTED_TIME"
            except Exception:
                return str(signer_dt), "UNTRUSTED_SIGNER_REPORTED_TIME"
        return sig_info.get("signature_timestamp"), "NOT_AVAILABLE" if not sig_info.get("signature_timestamp") else "UNKNOWN"

    def evaluate_trust_status(self, status: Any, cert_status: Optional[str] = None) -> str:
        """Evaluate trust status from pyHanko validation status.

        TRUSTED: chain validated to a trusted root.
        UNTRUSTED: cert is structurally invalid (expired, not yet valid, or explicitly invalid).
        UNKNOWN: chain not verifiable (self-signed, unknown issuer, etc.) — crypto may still be valid.
        NOT_VERIFIABLE: trust could not be assessed at all.
        """
        trusted = getattr(status, "trusted", None)
        if trusted is True:
            return "TRUSTED"
        # If we have certificate status, use it to distinguish UNTRUSTED from UNKNOWN
        _invalid_cert_statuses = {"EXPIRED", "NOT_YET_VALID", "INVALID"}
        if trusted is False:
            if cert_status and cert_status.upper() in _invalid_cert_statuses:
                return "UNTRUSTED"
            return "UNKNOWN"
        return "NOT_VERIFIABLE"

    @staticmethod
    def _revocation_status(status: Any) -> str:
        revoked = getattr(status, "revoked", None)
        if revoked is True:
            return "REVOKED"
        if revoked is False and getattr(status, "trusted", False):
            return "GOOD"
        return "NOT_CHECKED"

    def build_signature_result(self, index: int, embedded_sig: Any, status: Any | None = None, error: Exception | None = None) -> Dict[str, Any]:
        sig_info = self.extract_signature_information(embedded_sig)
        result: Dict[str, Any] = {
            "signature_index": index,
            "signature_field_name": sig_info.get("signature_field_name") or f"Signature {index}",
            "reason": sig_info.get("reason"),
            "location": sig_info.get("location"),
            "filter": sig_info.get("filter"),
            "sub_filter": sig_info.get("sub_filter"),
            "signer_name": None,
            "organization": None,
            "organizational_unit": None,
            "country": None,
            "email": None,
            "signature_status": "ERROR" if error else "UNKNOWN",
            "cryptographic_signature_validity": "ERROR" if error else "UNKNOWN",
            "certificate_status": "UNKNOWN",
            "certificate_subject": None,
            "certificate_issuer": None,
            "certificate_serial_number": None,
            "certificate_valid_from": None,
            "certificate_valid_until": None,
            "signature_algorithm": None,
            "public_key_algorithm": None,
            "document_integrity_status": "UNKNOWN",
            "document_modified_after_signing": None,
            "signature_timestamp": sig_info.get("signature_timestamp"),
            "timestamp_status": "UNKNOWN",
            "trust_status": "NOT_VERIFIABLE",
            "revocation_status": "NOT_CHECKED",
            "error": str(error)[:500] if error else None,
        }

        if status is None:
            return result

        valid = getattr(status, "valid", None)
        intact = getattr(status, "intact", None)
        if valid is True and intact is True:
            signature_status = "VALID"
        elif valid is False or intact is False:
            signature_status = "INVALID"
        else:
            signature_status = "UNKNOWN"

        cert_info = self.parse_certificate(self.extract_certificate(status))
        timestamp, timestamp_status = self.extract_signature_timestamp(status, sig_info)

        # Determine trust using both pyHanko's trust flag and parsed certificate status
        cert_status_value = cert_info.get("certificate_status", "UNKNOWN")
        trust_status = self.evaluate_trust_status(status, cert_status=cert_status_value)

        result.update(cert_info)
        result.update({
            "signer_name": cert_info.get("signer_name"),
            "organization": cert_info.get("organization"),
            "organizational_unit": cert_info.get("organizational_unit"),
            "country": cert_info.get("country"),
            "email": cert_info.get("email"),
            "signature_status": signature_status,
            "cryptographic_signature_validity": signature_status,
            "document_integrity_status": self.check_document_integrity(status),
            "document_modified_after_signing": self.detect_post_signing_modification(status),
            "signature_timestamp": timestamp,
            "timestamp_status": timestamp_status,
            "trust_status": trust_status,
            "revocation_status": self._revocation_status(status),
            "error": None,
        })
        return result

    # Certificate statuses that indicate the certificate itself is structurally invalid
    _INVALID_CERT_STATUSES = frozenset({"EXPIRED", "NOT_YET_VALID", "INVALID"})

    def build_overall_verification_result(self, signatures: List[Dict[str, Any]]) -> str:
        """Derive overall status without collapsing unknown trust into success.

        Priority order (highest to lowest):
          MODIFIED         - any signature proves post-signing modification.
          INVALID          - any signature is cryptographically invalid, OR any certificate
                             is expired / not-yet-valid / structurally invalid, OR all sigs errored.
          VERIFIED         - all sigs cryptographically valid + intact + certificate VALID + TRUSTED.
          PARTIALLY_VERIFIED - all sigs valid/intact but local trust UNKNOWN (e.g. self-signed).
          UNABLE_TO_VERIFY - signatures exist but none could be cryptographically evaluated.
          NO_SIGNATURE     - no embedded signatures found.
        """
        if not signatures:
            return "NO_SIGNATURE"

        # 1. Document integrity failure (highest priority)
        if any(sig.get("document_integrity_status") == "MODIFIED_AFTER_SIGNING" for sig in signatures):
            return "MODIFIED"

        # 2. Any cryptographic signature invalid
        if any(sig.get("signature_status") == "INVALID" for sig in signatures):
            return "INVALID"

        # 3. Any certificate is expired, not-yet-valid, or structurally invalid
        if any(
            sig.get("certificate_status", "UNKNOWN").upper() in self._INVALID_CERT_STATUSES
            for sig in signatures
        ):
            return "INVALID"

        # 4. All signatures resulted in errors (no status obtained)
        if all(sig.get("signature_status") in ("ERROR", "UNKNOWN") for sig in signatures):
            return "UNABLE_TO_VERIFY"

        # 5. All sigs valid and intact
        if all(sig.get("signature_status") == "VALID" for sig in signatures):
            # Full verification: cryptographically valid + cert valid + trusted root
            if all(
                sig.get("certificate_status") == "VALID"
                and sig.get("trust_status") == "TRUSTED"
                for sig in signatures
            ):
                return "VERIFIED"
            # Cryptographically valid but trust unknown (self-signed / no trusted root)
            return "PARTIALLY_VERIFIED"

        return "UNABLE_TO_VERIFY"

    def verify_pdf(self, input_path: str, original_filename: str | None = None, output_dir: str | Path | None = None) -> Dict[str, Any]:
        """Run full digital signature verification and optionally persist reports."""
        try:
            document_info = self.validate_pdf(input_path)
            filename = original_filename or document_info["filename"]
            verification_id = uuid.uuid4().hex
            signatures: List[Dict[str, Any]] = []

            from pyhanko.pdf_utils.reader import PdfFileReader

            with open(input_path, "rb") as handle:
                reader = PdfFileReader(handle)
                embedded_signatures = list(reader.embedded_signatures)
                if not embedded_signatures:
                    result = self._base_result(verification_id, filename, document_info, [])
                    if self._has_visual_signature(input_path):
                        result["overall_status"] = "NO_CRYPTOGRAPHIC_SIGNATURE"
                        result["signature_type"] = "NONE_OR_VISUAL"
                        result["message"] = "A visual signature or stamp may be present, but no certificate-based digital signature was detected. This document cannot be cryptographically verified."
                    else:
                        result["overall_status"] = "NO_SIGNATURE"
                        result["message"] = "No digital signature detected."
                    self._persist_result(result, output_dir)
                    return result

                for index, embedded_sig in enumerate(embedded_signatures, start=1):
                    try:
                        status = self.verify_cryptographic_signature(embedded_sig)
                        signatures.append(self.build_signature_result(index, embedded_sig, status=status))
                    except Exception as exc:
                        logger.warning("Signature verification failed for signature %s: %s", index, exc)
                        signatures.append(self.build_signature_result(index, embedded_sig, error=exc))

            result = self._base_result(verification_id, filename, document_info, signatures)
            result["overall_status"] = self.build_overall_verification_result(signatures)
            result["signature_type"] = "CRYPTOGRAPHIC"
            result["message"] = "Digital signature verification completed."
            self._persist_result(result, output_dir)
            return result
        except ValueError as exc:
            logger.warning("digital signature verification validation failed: %s", exc)
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("digital signature verification failed: %s", exc, exc_info=True)
            return {"success": False, "error": "Unable to verify digital signatures for this PDF."}

    def generate_verification_report(self, result: Dict[str, Any]) -> bytes:
        """Generate a PDF verification report safe for download."""
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        
        y = 50
        def add_text(text, fontsize=10, bold=False):
            nonlocal y, page
            fontname = "helv"
            if bold: fontname = "hebo"
            page.insert_text((50, y), str(text), fontsize=fontsize, fontname=fontname)
            y += fontsize + 5
            if y > page.rect.height - 50:
                page = doc.new_page()
                y = 50

        add_text("Digital Signature Verification Report", fontsize=16, bold=True)
        y += 10
        add_text("Document Information", fontsize=12, bold=True)
        add_text(f"Filename: {result.get('filename')}")
        add_text(f"Verification ID: {result.get('verification_id')}")
        add_text(f"Verification Date: {result.get('verified_at')}")
        add_text(f"Signature Count: {result.get('signature_count')}")
        add_text(f"Overall Verification Status: {result.get('overall_status')}")
        y += 15

        for sig in result.get("signatures", []):
            add_text(f"Signature {sig.get('signature_index')}", fontsize=12, bold=True)
            add_text(f"Signature Field: {sig.get('signature_field_name')}")
            add_text(f"Signer: {sig.get('signer_name')}")
            add_text(f"Signature Status: {sig.get('signature_status')}")
            add_text(f"Certificate Status: {sig.get('certificate_status')}")
            add_text(f"Subject: {sig.get('certificate_subject')}")
            add_text(f"Issuer: {sig.get('certificate_issuer')}")
            add_text(f"Serial Number: {sig.get('certificate_serial_number')}")
            add_text(f"Valid From: {sig.get('certificate_valid_from')}")
            add_text(f"Valid Until: {sig.get('certificate_valid_until')}")
            add_text(f"Document Integrity: {sig.get('document_integrity_status')}")
            add_text(f"Modified After Signing: {sig.get('document_modified_after_signing')}")
            add_text(f"Timestamp: {sig.get('signature_timestamp')}")
            add_text(f"Timestamp Status: {sig.get('timestamp_status')}")
            add_text(f"Trust Status: {sig.get('trust_status')}")
            add_text(f"Revocation Status: {sig.get('revocation_status')}")
            y += 15

        if not result.get("signatures"):
            add_text("No digital signature detected.")
            y += 10

        add_text("Final Result", fontsize=12, bold=True)
        add_text(f"Overall Status: {result.get('overall_status')}")

        return doc.write()

    def cleanup_temporary_files(self, paths: List[str | Path]) -> None:
        for path in paths:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                logger.warning("Could not clean temporary file: %s", path)

    def load_result(self, output_dir: str | Path, verification_id: str) -> Dict[str, Any]:
        path = Path(output_dir) / f"{verification_id}.json"
        if not path.exists():
            raise ValueError("Verification result not found.")
        return json.loads(path.read_text(encoding="utf-8"))

    def report_path(self, output_dir: str | Path, verification_id: str) -> Path:
        return Path(output_dir) / f"{verification_id}_report.pdf"

    def _base_result(self, verification_id: str, filename: str, document_info: Dict[str, Any], signatures: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "success": True,
            "verification_id": verification_id,
            "filename": filename,
            "has_signature": bool(signatures),
            "signature_count": len(signatures),
            "overall_status": "UNABLE_TO_VERIFY",
            "signature_type": "NONE",
            "signatures": signatures,
            "document_info": {
                "page_count": document_info.get("page_count"),
                "pdf_version": document_info.get("pdf_version"),
                "is_encrypted": document_info.get("is_encrypted"),
                "file_size": document_info.get("file_size"),
            },
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    def _persist_result(self, result: Dict[str, Any], output_dir: str | Path | None) -> None:
        if output_dir is None:
            return
        out_dir = Path(output_dir)
        os.makedirs(out_dir, exist_ok=True)
        verification_id = result["verification_id"]
        result["result_url"] = f"result/{verification_id}"
        result["report_filename"] = f"{verification_id}_report.pdf"
        result["report_url"] = f"/api/pdf/security/digital-signature-verify/report/{verification_id}"
        (out_dir / f"{verification_id}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (out_dir / result["report_filename"]).write_bytes(self.generate_verification_report(result))



    @staticmethod
    def _empty_certificate(status: str) -> Dict[str, Any]:
        return {
            "certificate_status": status,
            "certificate_subject": None,
            "certificate_issuer": None,
            "certificate_serial_number": None,
            "certificate_valid_from": None,
            "certificate_valid_until": None,
            "signature_algorithm": None,
            "public_key_algorithm": None,
            "signer_name": None,
            "organization": None,
            "organizational_unit": None,
            "country": None,
            "email": None,
        }

    @staticmethod
    def _safe_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value)
        return text if text else None

    @staticmethod
    def _pdf_obj_text(value: Any) -> Optional[str]:
        """Safely convert a pyHanko/pypdf PDF object to a plain string."""
        if value is None:
            return None
        try:
            # pyHanko PDF string objects expose raw bytes
            if hasattr(value, "original_bytes"):
                raw = value.original_bytes
                if isinstance(raw, (bytes, bytearray)):
                    return raw.decode("utf-8", errors="replace").strip()
            # pypdf / pyHanko sometimes wrap in a class with native_value
            if hasattr(value, "native_value"):
                native = value.native_value
                if native is not None:
                    return str(native).strip()
            # pyHanko LatexString / ByteStringObject
            if hasattr(value, "get_object"):
                obj = value.get_object()
                if obj is not value:
                    return DigitalSignatureVerificationService._pdf_obj_text(obj)
            text = str(value).strip()
            return text if text else None
        except Exception:
            return None

    @staticmethod
    def _pdf_version(path: Path) -> Optional[str]:
        try:
            with open(path, "rb") as handle:
                header = handle.read(16).decode("latin-1", errors="ignore")
            if "%PDF-" in header:
                return header.split("%PDF-", 1)[1].splitlines()[0].strip()
        except Exception:
            pass
        return None


digital_signature_verification_service = DigitalSignatureVerificationService()
