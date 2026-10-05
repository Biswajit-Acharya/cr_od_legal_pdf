import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import PyKCS11
from pyhanko.sign import signers, fields
from pyhanko.pdf_utils import text, incremental_writer
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.writer import PdfFileWriter
from pyhanko.keys import load_cert_from_pemder

logger = logging.getLogger(__name__)

class UsbTokenService:
    # A common default for Windows (eMudhra / Safenet / ePass2003 etc)
    # The actual path should be loaded from env, as per requirements.
    DEFAULT_PKCS11_LIB = os.environ.get("PKCS11_LIB_PATH", "C:\\Windows\\System32\\eps2003csp11.dll")

    @classmethod
    def get_token_status(cls) -> Dict[str, Any]:
        """Detect token status using PKCS#11."""
        lib_path = cls.DEFAULT_PKCS11_LIB
        if not os.path.exists(lib_path):
            return {
                "connected": False,
                "status": "TOKEN_NOT_DETECTED",
                "error": f"PKCS#11 library not found at {lib_path}"
            }
        
        try:
            pkcs11 = PyKCS11.PyKCS11Lib()
            pkcs11.load(lib_path)
            slots = pkcs11.getSlotList(tokenPresent=True)
            
            if not slots:
                return {
                    "connected": False,
                    "status": "TOKEN_NOT_DETECTED",
                    "error": "No token inserted"
                }

            slot = slots[0]
            token_info = pkcs11.getTokenInfo(slot)
            
            return {
                "connected": True,
                "token_name": token_info.label.strip(),
                "manufacturer": token_info.manufacturerID.strip(),
                "serial_number": token_info.serialNumber.strip(),
                "slot_id": str(slot),
                "status": "ready"
            }
        except Exception as e:
            logger.error(f"Error getting token status: {e}")
            return {
                "connected": False,
                "status": "ERROR",
                "error": str(e)
            }

    @classmethod
    def get_certificates(cls) -> Dict[str, Any]:
        """Retrieve available certificates from the USB token."""
        lib_path = cls.DEFAULT_PKCS11_LIB
        if not os.path.exists(lib_path):
            raise ValueError("PKCS#11 library not found.")
            
        try:
            pkcs11 = PyKCS11.PyKCS11Lib()
            pkcs11.load(lib_path)
            slots = pkcs11.getSlotList(tokenPresent=True)
            if not slots:
                raise ValueError("No token inserted.")
            
            slot = slots[0]
            session = pkcs11.openSession(slot, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
            
            # Find all certificates
            certs = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE)])
            
            cert_list = []
            for cert in certs:
                # Extract CKA_VALUE which contains the DER encoded certificate
                attributes = session.getAttributeValue(cert, [PyKCS11.CKA_VALUE, PyKCS11.CKA_ID])
                der_cert = bytes(attributes[0])
                key_id = bytes(attributes[1]).hex() if attributes[1] else None
                
                try:
                    from cryptography import x509
                    from cryptography.hazmat.backends import default_backend
                    parsed_cert = x509.load_der_x509_certificate(der_cert, default_backend())
                    
                    cert_info = {
                        "owner": parsed_cert.subject.rfc4514_string(),
                        "issuer": parsed_cert.issuer.rfc4514_string(),
                        "serial_number": str(parsed_cert.serial_number),
                        "validity_start": parsed_cert.not_valid_before.isoformat(),
                        "validity_end": parsed_cert.not_valid_after.isoformat(),
                        "algorithm": parsed_cert.signature_hash_algorithm.name if parsed_cert.signature_hash_algorithm else "Unknown",
                        "status": "valid" if parsed_cert.not_valid_before <= datetime.utcnow() <= parsed_cert.not_valid_after else "invalid",
                        "key_id": key_id
                    }
                    cert_list.append(cert_info)
                except Exception as ex:
                    logger.warning(f"Could not parse a certificate on token: {ex}")
                    
            session.closeSession()
            return {"success": True, "certificates": cert_list}
        except Exception as e:
            logger.error(f"Error discovering certificates: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    def validate_certificate(cls, serial_number: str) -> Dict[str, Any]:
        """Validate if a certificate is suitable for signing."""
        certs_res = cls.get_certificates()
        if not certs_res.get("success"):
            return certs_res
            
        cert = next((c for c in certs_res["certificates"] if c["serial_number"] == str(serial_number)), None)
        if not cert:
            return {"valid": False, "error": "Certificate not found on token."}
            
        if cert["status"] != "valid":
            return {"valid": False, "error": "Certificate is expired or not yet valid."}
            
        return {
            "valid": True,
            "certificate": cert
        }

    @classmethod
    def sign_pdf(cls, file_path: str, output_path: str, pin: str, cert_serial: str, user_id: str) -> Dict[str, Any]:
        """Perform cryptographic signing using the token."""
        lib_path = cls.DEFAULT_PKCS11_LIB
        if not os.path.exists(lib_path):
            raise ValueError("PKCS#11 library not found.")
            
        try:
            # We use pyHanko's PKCS11 signer
            from pyhanko.sign import pkcs11 as pyhanko_pkcs11
            
            pkcs11_session = pyhanko_pkcs11.open_pkcs11_session(lib_path, user_pin=pin)
            
            # Setup the signer
            signer = pyhanko_pkcs11.PKCS11Signer(
                pkcs11_session=pkcs11_session,
                # In a real implementation we would match the key by ID or label
                # For this implementation we'll let pyhanko pick the first available signing key
                # or we could specify cert_label or key_id if extracted
            )
            
            with open(file_path, 'rb') as doc_file:
                w = incremental_writer.IncrementalPdfFileWriter(doc_file)
                # Create a signature field
                fields.append_signature_field(
                    w, sig_field_spec=fields.SigFieldSpec(
                        'Signature1', box=(50, 50, 250, 100)
                    )
                )
                
                with open(output_path, 'wb') as out_file:
                    signers.sign_pdf(
                        w, signers.PdfSignatureMetadata(field_name='Signature1'),
                        signer=signer, out_file=out_file
                    )
                    
            return {
                "success": True,
                "message": "Document signed successfully",
                "signed_at": datetime.utcnow().isoformat(),
                "signer": user_id
            }
        except PyKCS11.PyKCS11Error as e:
            logger.error(f"PKCS11 Error during signing: {e}")
            if "CKR_PIN_INCORRECT" in str(e):
                raise ValueError("Incorrect PIN provided.")
            raise ValueError(f"Hardware token error: {e}")
        except Exception as e:
            logger.error(f"Error signing PDF: {e}")
            raise ValueError(f"Signing failed: {e}")

    @classmethod
    def validate_signature(cls, file_path: str) -> Dict[str, Any]:
        """Validate the generated digital signature."""
        try:
            from pyhanko.sign.validation import validate_pdf_signature, validate_pdf_ltv_signature
            from pyhanko.pdf_utils.reader import PdfFileReader
            
            with open(file_path, 'rb') as f:
                r = PdfFileReader(f)
                sig_fields = r.embedded_signatures
                
                if not sig_fields:
                    return {"signature_valid": False, "error": "No signatures found."}
                
                # Validate the first signature
                sig = sig_fields[0]
                status = validate_pdf_signature(sig)
                
                return {
                    "signature_valid": status.valid and status.intact,
                    "document_integrity": status.intact,
                    "certificate_valid": status.trusted,
                    "signer": status.signer_info.subject.rfc4514_string() if status.signer_info else "Unknown",
                    "signed_at": sig.signer_info.signing_time.isoformat() if hasattr(sig.signer_info, "signing_time") and sig.signer_info.signing_time else None,
                }
        except Exception as e:
            logger.error(f"Error validating signature: {e}")
            return {"signature_valid": False, "error": str(e)}

    @classmethod
    def get_history(cls, user_id: str) -> List[Dict[str, Any]]:
        # Dummy DB fetch
        return []
