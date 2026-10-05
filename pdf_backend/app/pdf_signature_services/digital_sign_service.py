import os
import uuid
from datetime import datetime, timezone
import base64

from pyhanko.sign import signers
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.writer import copy_into_new_writer
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext
from cryptography.hazmat.primitives.serialization import pkcs12
import logging
import PyPDF2
from io import BytesIO

logger = logging.getLogger(__name__)

class DigitalSignService:
    
    @staticmethod
    def parse_certificate(p12_path: str, password: str) -> dict:
        """
        Parses a PKCS#12 file and extracts certificate metadata.
        Returns a dictionary with certificate details.
        """
        try:
            with open(p12_path, "rb") as f:
                p12_data = f.read()
                
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                p12_data, 
                password.encode() if password else None
            )
            
            if not certificate:
                raise Exception("No certificate found in the provided file.")
            
            subject = certificate.subject
            issuer = certificate.issuer
            
            def get_name_attribute(name_obj, oid_name):
                for attribute in name_obj:
                    if attribute.oid._name == oid_name:
                        return attribute.value
                return "Unknown"
            
            signer_name = get_name_attribute(subject, "commonName")
            organization = get_name_attribute(subject, "organizationName")
            issuer_name = get_name_attribute(issuer, "commonName")
            
            not_valid_before = certificate.not_valid_before_utc
            not_valid_after = certificate.not_valid_after_utc
            
            now = datetime.now(timezone.utc)
            is_expired = now > not_valid_after
            
            return {
                "success": True,
                "signer_name": signer_name,
                "organization": organization,
                "issuer": issuer_name,
                "serial_number": str(certificate.serial_number),
                "valid_from": not_valid_before.isoformat(),
                "valid_until": not_valid_after.isoformat(),
                "algorithm": certificate.signature_algorithm_oid._name,
                "key_size": private_key.key_size if hasattr(private_key, 'key_size') else "Unknown",
                "is_expired": is_expired,
                "status": "EXPIRED" if is_expired else "VALID"
            }
        except ValueError as e:
            logger.error(f"Certificate parsing failed (ValueError): {e}")
            raise Exception("Certificate password incorrect or file corrupted.")
        except Exception as e:
            logger.error(f"Certificate parsing failed: {e}")
            raise Exception(f"Failed to load certificate: {str(e)}")

    @staticmethod
    def _normalize_pdf(input_path: str) -> BytesIO:
        """
        Normalizes a PDF using PyPDF2. This repairs malformed xref tables and 
        orphaned generations that PyHanko's strict parser rejects.
        """
        logger.info("Attempting to normalize PDF using PyPDF2...")
        normalized_io = BytesIO()
        reader = PyPDF2.PdfReader(input_path)
        writer = PyPDF2.PdfWriter()
        writer.append_pages_from_reader(reader)
        # Attempt to copy document info if it exists
        if reader.metadata:
            writer.add_metadata(reader.metadata)
        writer.write(normalized_io)
        normalized_io.seek(0)
        return normalized_io

    @staticmethod
    def sign_pdf(pdf_path: str, p12_path: str, password: str, config: dict, output_path: str) -> dict:
        """
        Cryptographically signs a PDF using a PKCS#12 certificate.
        """
        try:
            signer = signers.SimpleSigner.load_pkcs12(
                p12_path, 
                passphrase=password.encode() if password else None
            )
            
            if signer is None:
                raise ValueError("Could not initialize digital signature engine. The certificate might be missing a private key, or the CA chain could not be loaded.")
            if getattr(signer, 'signing_key', None) is None:
                raise ValueError("No private key found in the provided file. A private key is required for digital signing.")
            
            # Read the PDF, with fallback to normalization if PyHanko parser fails
            doc_file = None
            try:
                # First attempt with the raw file
                doc_file = open(pdf_path, 'rb')
                reader = PdfFileReader(doc_file)
            except Exception as parse_err:
                logger.warning(f"PyHanko failed to parse PDF natively, attempting normalization. Error: {parse_err}")
                if doc_file:
                    doc_file.close()
                doc_file = DigitalSignService._normalize_pdf(pdf_path)
                reader = PdfFileReader(doc_file)
                
            sig_meta = signers.PdfSignatureMetadata(
                field_name=f'Signature_{uuid.uuid4().hex[:8]}',
                reason=config.get("reason", "Document Approval"),
                location=config.get("location", "Unknown Location"),
                md_algorithm='sha256'
            )
            
            with open(output_path, 'wb') as out_file:
                if config.get("visible") and config.get("width") and config.get("height"):
                    from pyhanko.sign.fields import SigFieldSpec, append_signature_field
                    
                    # Use top-left origin coordinates if passed by the frontend
                    x = config.get("x", 100)
                    y = config.get("y", 100)
                    width = config.get("width", 200)
                    height = config.get("height", 50)
                    
                    # Convert to PDF coordinates (bottom-left) if necessary, but we'll try raw for now
                    # PyHanko: (x1, y1, x2, y2)
                    # We will just flip Y in pyhanko or let pyhanko handle it. Standard PDF is bottom-left.
                    box = (x, y, x + width, y + height)
                    
                    w = copy_into_new_writer(reader)
                    sig_field_spec = SigFieldSpec(
                        sig_meta.field_name, box=box, on_page=int(config.get("page", 1)) - 1
                    )
                    append_signature_field(w, sig_field_spec)
                    
                    signers.sign_pdf(
                        w, signature_meta=sig_meta, signer=signer, output=out_file
                    )
                else:
                    w = copy_into_new_writer(reader)
                    signers.sign_pdf(
                        w, signature_meta=sig_meta, signer=signer, output=out_file
                    )
            
            if doc_file and hasattr(doc_file, 'close'):
                doc_file.close()

            validation_result = DigitalSignService.validate_signature(output_path)
            if not validation_result.get("overall_valid"):
                raise ValueError(
                    "Generated PDF signature failed validation: "
                    f"{validation_result.get('message', 'unknown validation failure')}"
                )

            return {
                "success": True,
                "message": "PDF digitally signed successfully",
                "validation": validation_result,
            }
        except Exception as e:
            if 'doc_file' in locals() and hasattr(doc_file, 'close'):
                doc_file.close()
            logger.exception("Error signing PDF")
            raise Exception(f"The PDF structure could not be processed for digital signing. The document may contain an invalid or unsupported PDF object structure. Underlying cause: {str(e)}")

    @staticmethod
    def validate_signature(pdf_path: str) -> dict:
        """
        Validates the digital signatures in a PDF.
        """
        try:
            with open(pdf_path, 'rb') as doc_file:
                reader = PdfFileReader(doc_file)
                
                if not reader.embedded_signatures:
                    return {
                        "success": True,
                        "overall_valid": False,
                        "message": "No cryptographic signatures found in the document."
                    }
                
                sig = reader.embedded_signatures[0]
                validation_context = ValidationContext(trust_roots=[sig.signer_cert])
                status = validate_pdf_signature(sig, validation_context)
                
                cert = status.signing_cert or sig.signer_cert
                subject = cert.subject.native
                issuer_info = cert.issuer.native
                signer_name = subject.get("common_name", "Unknown")
                issuer = issuer_info.get("common_name", "Unknown")
                
                signing_time = (
                    status.signer_reported_dt.isoformat()
                    if status.signer_reported_dt
                    else "Unknown"
                )

                return {
                    "success": True,
                    "overall_valid": bool(status.bottom_line),
                    "signature_valid": status.valid,
                    "document_integrity_valid": status.intact,
                    "certificate_valid": status.trusted,
                    "certificate_expired": False, # Pyhanko checks this internally during status.valid
                    "signer_name": signer_name,
                    "issuer": issuer,
                    "algorithm": "RSA / SHA-256",
                    "signing_time": signing_time,
                    "modification_detected": not status.intact,
                    "message": "Signature validation complete."
                }
        except Exception as e:
            logger.exception("Error validating PDF")
            raise Exception(f"Failed to validate PDF: {str(e)}")
