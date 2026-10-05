import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone
import hashlib

from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign import signers, validation
from pyhanko.sign.validation import SignatureCoverageLevel
from asn1crypto import x509

logger = logging.getLogger(__name__)

class TrustedCertificatesService:
    def __init__(self):
        pass

    def _extract_name_dict(self, name: x509.Name) -> Dict[str, str]:
        """Extracts human-readable fields from an ASN.1 x509 Name."""
        out = {}
        for rdn in name.chosen:
            for type_val in rdn:
                attr_type = type_val['type'].native
                attr_value = type_val['value'].native
                if isinstance(attr_value, bytes):
                    try:
                        attr_value = attr_value.decode('utf-8', errors='replace')
                    except:
                        pass
                if attr_type == 'common_name':
                    out['CN'] = str(attr_value)
                elif attr_type == 'organization_name':
                    out['O'] = str(attr_value)
                elif attr_type == 'organizational_unit_name':
                    out['OU'] = str(attr_value)
                elif attr_type == 'country_name':
                    out['C'] = str(attr_value)
                elif attr_type == 'email_address':
                    out['Email'] = str(attr_value)
        return out

    def _format_name(self, name_dict: Dict[str, str]) -> str:
        parts = []
        if 'CN' in name_dict: parts.append(name_dict['CN'])
        if 'O' in name_dict: parts.append(name_dict['O'])
        if 'OU' in name_dict: parts.append(name_dict['OU'])
        if 'C' in name_dict: parts.append(name_dict['C'])
        return ", ".join(parts) if parts else "Unknown"

    async def analyze(self, filepath: Path, original_filename: str) -> Dict[str, Any]:
        """
        Analyzes the PDF for digital signatures and validates them using PyHanko.
        """
        if not filepath.exists():
            return {"success": False, "error": "File not found."}

        try:
            with open(filepath, 'rb') as f:
                reader = PdfFileReader(f)
                
                # Check for signatures
                embedded_signatures = reader.embedded_signatures
                
                if not embedded_signatures:
                    return {
                        "success": True,
                        "document": original_filename,
                        "signature_count": 0,
                        "overall_status": "No Digital Signature Found",
                        "validation_summary": "This PDF does not contain a detectable embedded digital signature. Certificate trust validation cannot be performed.",
                        "signatures": []
                    }

                signatures = []
                all_valid = True
                all_trusted = True
                
                # Try to use default OS trust (might be limited without explicitly loading certs)
                # But we can still validate the byte integrity and extract basic cert fields.
                # pyHanko defaults to trusting nothing if no root context is given, which is safe.
                validation_context = validation.ValidationContext(trust_roots=[]) 

                for sig in embedded_signatures:
                    sig_info = {
                        "signature_status": "Unknown",
                        "signer": {},
                        "issuer": {},
                        "validity": {},
                        "certificate": {},
                        "integrity": "Unknown",
                        "trust": "Not Verified",
                        "revocation": "Unknown",
                        "chain": []
                    }

                    try:
                        # 1. Cryptographic Validation
                        status = await validation.async_validate_pdf_signature(sig, validation_context)
                        
                        # 2. Document Integrity Check
                        coverage = status.coverage
                        if coverage == SignatureCoverageLevel.ENTIRE_FILE:
                            sig_info['integrity'] = "Valid: Signature covers entire document"
                        elif coverage == SignatureCoverageLevel.ENTIRE_REVISION:
                            sig_info['integrity'] = "Valid: Signature covers revision (document appended later)"
                        else:
                            sig_info['integrity'] = "Invalid or Modified: Signed content was improperly altered"
                            all_valid = False

                        # 3. Signature Cryptographic Status
                        if status.intact:
                            sig_info['signature_status'] = "Cryptographically Valid"
                        else:
                            sig_info['signature_status'] = "Invalid"
                            all_valid = False
                            
                        # Trust status based on strict chain building (if no root supplied, usually returns untrusted)
                        if status.trusted:
                            sig_info['trust'] = "Trusted"
                        else:
                            sig_info['trust'] = "Untrusted / Validation Failed (Root not in trust store)"
                            all_trusted = False
                            
                        # Extract Certificate Info
                        cert = status.signing_cert
                        if cert:
                            # Parse subject
                            subject_dict = self._extract_name_dict(cert.subject)
                            sig_info['signer'] = {
                                "Name": self._format_name(subject_dict),
                                "CN": subject_dict.get('CN', ''),
                                "O": subject_dict.get('O', '')
                            }
                            
                            # Parse issuer
                            issuer_dict = self._extract_name_dict(cert.issuer)
                            sig_info['issuer'] = {
                                "Name": self._format_name(issuer_dict),
                                "CN": issuer_dict.get('CN', '')
                            }
                            
                            # Validity dates
                            not_before = cert['tbs_certificate']['validity']['not_before'].native
                            not_after = cert['tbs_certificate']['validity']['not_after'].native
                            now = datetime.now(timezone.utc)
                            
                            if not isinstance(not_before, datetime):
                                not_before = not_before.replace(tzinfo=timezone.utc)
                            if not isinstance(not_after, datetime):
                                not_after = not_after.replace(tzinfo=timezone.utc)

                            validity_state = "Valid"
                            if now < not_before:
                                validity_state = "Not Yet Valid"
                                all_valid = False
                            elif now > not_after:
                                validity_state = "Expired"
                                all_valid = False
                                
                            sig_info['validity'] = {
                                "status": validity_state,
                                "not_before": not_before.strftime('%Y-%m-%d %H:%M:%S UTC'),
                                "not_after": not_after.strftime('%Y-%m-%d %H:%M:%S UTC')
                            }
                            
                            # Certificate details
                            pub_key = cert.public_key
                            alg = pub_key.algorithm
                            
                            sig_info['certificate'] = {
                                "serial_number": str(cert.serial_number),
                                "signature_algorithm": cert['signature_algorithm']['algorithm'].native,
                                "public_key_algorithm": alg,
                                "sha256": hashlib.sha256(cert.dump()).hexdigest()
                            }
                            
                            # Revocation status (we didn't supply an OCSP client, so it's unknown locally)
                            sig_info['revocation'] = "Unknown (Revocation information could not be checked locally)"
                            
                    except Exception as e:
                        logger.error(f"Error validating individual signature: {e}")
                        sig_info['signature_status'] = "Validation Errored"
                        sig_info['validation_messages'] = str(e)
                        all_valid = False

                    signatures.append(sig_info)

                if all_valid and all_trusted:
                    overall = "Trusted"
                elif all_valid and not all_trusted:
                    overall = "Valid but Untrusted / Warnings Found"
                else:
                    overall = "Validation Failed / Invalid Signatures"

                return {
                    "success": True,
                    "document": original_filename,
                    "signature_count": len(signatures),
                    "overall_status": overall,
                    "validation_summary": f"Detected {len(signatures)} digital signature(s). Local cryptographic validation performed.",
                    "signatures": signatures
                }

        except Exception as e:
            logger.error(f"Error in trusted certificates: {e}", exc_info=True)
            return {"success": False, "error": f"An error occurred while analyzing certificates: {str(e)}"}

trusted_certificates_service = TrustedCertificatesService()
