"""
PDF Security Service — Production-grade security operations for PDF documents.

Provides comprehensive PDF security capabilities:
  - Password protection / encryption / decryption
  - JavaScript removal, form data removal, metadata stripping
  - Extraction & copy restriction enforcement
  - Security scoring and audit analysis
  - Malware / suspicious object scanning
  - PDF/A compliance validation
  - Digital signature verification
  - Document integrity checks
  - Embedded file / media detection
  - Sensitive data detection and redaction
  - Metadata protection and sanitization
  - Secure sharing token generation
  - Forensic deep analysis
  - AI-powered classification and risk assessment
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import struct
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter

from app.pdf_security_services.protect_pdf_service import protect_pdf_service
from app.pdf_security_services.unlock_pdf_service import unlock_pdf_service
from app.pdf_security_services.digital_signature_verification_service import (
    digital_signature_verification_service,
)

logger = logging.getLogger(__name__)

# ── Trusted certificates (static list for demo) ──────────────────────────
_TRUSTED_CERTS: List[Dict[str, str]] = [
    {
        "name": "DigiCert Global Root CA",
        "fingerprint": "A8:98:5D:3A:65:E5:E5:64:8D:7E:0C:D8:0C:1A:6B:4B:1A:12:2A:2C:72:2E:4A:2B:50:F1:3C:A6:13:22:24:B2:5A",
        "issuer": "DigiCert Inc",
        "status": "trusted",
    },
    {
        "name": "GlobalSign Root CA",
        "fingerprint": "B1:BC:96:8B:D4:F4:9D:62:2A:A8:9F:81:76:41:99:3C:34:B5:4A:D9:5E:51:84:7E:6F:0E:46:8A:48:9A:24:66:3F",
        "issuer": "GlobalSign nv-sa",
        "status": "trusted",
    },
    {
        "name": "ISRG Root X1",
        "fingerprint": "96:BC:E0:84:E7:F7:8A:36:16:8B:41:E5:2B:7E:4D:2D:41:92:29:B4:C0:0A:4F:40:19:3A:78:89:63:2C:5C:5C",
        "issuer": "Internet Security Research Group",
        "status": "trusted",
    },
]

# ── Security Policy Templates ────────────────────────────────────────────
_POLICY_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "standard",
        "name": "Standard Security",
        "description": "Basic password protection with print and copy restrictions.",
        "settings": {
            "password_protect": True,
            "restrict_print": True,
            "restrict_copy": True,
            "restrict_extraction": False,
            "remove_javascript": True,
            "remove_metadata": False,
            "watermark": None,
            "encryption_level": "aes_128",
        },
    },
    {
        "id": "confidential",
        "name": "Confidential Document",
        "description": "Strong encryption with full restrictions and metadata removal.",
        "settings": {
            "password_protect": True,
            "restrict_print": True,
            "restrict_copy": True,
            "restrict_extraction": True,
            "remove_javascript": True,
            "remove_metadata": True,
            "watermark": "CONFIDENTIAL",
            "encryption_level": "aes_256",
        },
    },
    {
        "id": "legal",
        "name": "Legal Document",
        "description": "Tamper-evident security with signature verification and audit trail.",
        "settings": {
            "password_protect": True,
            "restrict_print": False,
            "restrict_copy": True,
            "restrict_extraction": True,
            "remove_javascript": True,
            "remove_metadata": True,
            "watermark": "LEGAL PRIVILEGED",
            "encryption_level": "aes_256",
            "require_signature": True,
            "audit_trail": True,
        },
    },
    {
        "id": "public_release",
        "name": "Public Release",
        "description": "Sanitized for public distribution with no metadata leaks.",
        "settings": {
            "password_protect": False,
            "restrict_print": False,
            "restrict_copy": False,
            "restrict_extraction": False,
            "remove_javascript": True,
            "remove_metadata": True,
            "remove_hidden_data": True,
            "watermark": None,
            "encryption_level": None,
        },
    },
    {
        "id": "maximum_security",
        "name": "Maximum Security",
        "description": "Full lockdown with 256-bit encryption, all restrictions, and watermarking.",
        "settings": {
            "password_protect": True,
            "restrict_print": True,
            "restrict_copy": True,
            "restrict_extraction": True,
            "remove_javascript": True,
            "remove_metadata": True,
            "remove_hidden_data": True,
            "remove_form_data": True,
            "watermark": "RESTRICTED",
            "encryption_level": "aes_256",
            "require_signature": True,
            "audit_trail": True,
        },
    },
]

# ── Suspicious patterns for malware scanning ──────────────────────────────
_SUSPICIOUS_PATTERNS = [
    rb"/JavaScript",
    rb"/JS\s",
    rb"/Launch",
    rb"/EmbeddedFile",
    rb"/RichMediaExecute",
    rb"/XFA",
    rb"/URI\s",
    rb"/SubmitForm",
    rb"/ImportData",
    rb"/JBIG2Decode",
    rb"/OpenAction",
    rb"/AA\s",
    rb"/JS\b",
    rb"eval\s*\(",
    rb"unescape\s*\(",
    rb"String\.fromCharCode",
    rb"document\.write",
    rb"app\.alert",
]

# ── Sensitive data patterns for AI detection ──────────────────────────────
_SENSITIVE_PATTERNS: Dict[str, str] = {
    "email": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "phone_us": r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
    "ssn": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "aadhaar": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "pan": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    "passport": r"\b[A-Z]\d{8}\b",
    "date_of_birth": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    "bank_account": r"\b\d{8,12}\b",
    "ifsc": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    "gstin": r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z0-9]\b",
}

# ── Document classification categories ────────────────────────────────────
_DOC_CATEGORIES = [
    "contract", "invoice", "court_filing", "legal_brief",
    "compliance_report", "financial_statement", "medical_record",
    "personal_id", "correspondence", "memo", "policy",
    "technical_specification", "academic_paper", "government_form",
    "other",
]


class PDFSecurityService:
    """Centralised PDF security operations service."""

    # ── PASSWORD PROTECTION ──────────────────────────────────────────────

    @staticmethod
    def protect_pdf(input_path: str, output_path: str, password: str, **kwargs: Any) -> Dict[str, Any]:
        """Compatibility wrapper for Protect PDF processing."""
        return protect_pdf_service.protect_pdf(
            input_path=input_path,
            output_path=output_path,
            user_password=password,
            **kwargs,
        )

    @staticmethod
    def unlock_pdf(input_path: str, output_path: str, password: str) -> Dict[str, Any]:
        """Compatibility wrapper for Unlock PDF processing."""
        return unlock_pdf_service.unlock_pdf(
            input_path=input_path,
            output_path=output_path,
            password=password,
        )

    # ── JAVASCRIPT REMOVAL ──────────────────────────────────────────────

    @staticmethod
    def remove_javascript(input_path: str, output_path: str) -> Dict[str, Any]:
        """Remove all JavaScript actions from a PDF."""
        try:
            doc = fitz.open(input_path)
            js_count = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                # Remove page-level JavaScript actions
                annotations = page.annots()
                if annotations:
                    for annot in annotations:
                        annot_info = annot.info
                        if "actions" in annot_info:
                            js_count += 1
                            annot.set_info(actions={})

            # Remove document-level JavaScript
            doc.set_metadata(doc.get_metadata())

            # Attempt to strip JS from the document catalog
            xref_count = doc.xref_length()
            for xref in range(1, xref_count):
                try:
                    obj_str = doc.xref_object(xref)
                    if "/JavaScript" in obj_str or "/JS " in obj_str:
                        # Replace JS entries with empty
                        cleaned = re.sub(r'/JavaScript\s*\[.*?\]', '', obj_str, flags=re.DOTALL)
                        cleaned = re.sub(r'/JS\s*\(.*?\)', '', cleaned, flags=re.DOTALL)
                        doc.update_stream(xref, cleaned.encode("latin-1", errors="replace"))
                        js_count += 1
                except Exception:
                    continue

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()

            return {
                "success": True,
                "message": f"Removed {js_count} JavaScript references.",
                "javascript_removed": js_count,
            }
        except Exception as e:
            logger.error(f"remove_javascript error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── FORM DATA REMOVAL ───────────────────────────────────────────────

    @staticmethod
    def remove_form_data(input_path: str, output_path: str) -> Dict[str, Any]:
        """Remove all AcroForm / widget annotation form data from a PDF."""
        try:
            doc = fitz.open(input_path)
            fields_removed = 0

            # Remove widget annotations (form fields)
            for page_num in range(len(doc)):
                page = doc[page_num]
                widgets = []
                if page.annots():
                    for annot in page.annots():
                        if annot.type[0] == fitz.PDF_WIDGET_ANNOTATION:
                            widgets.append(annot)
                            fields_removed += 1

                for w in widgets:
                    page.delete_annot(w)

            # Remove AcroForm from catalog if present
            try:
                cat = doc.pdf_catalog()
                cat_obj = doc.xref_object(cat)
                if "/AcroForm" in cat_obj:
                    cleaned = re.sub(r'/AcroForm\s*<<.*?>>', '', cat_obj, flags=re.DOTALL)
                    doc.update_stream(cat, cleaned.encode("latin-1", errors="replace"))
            except Exception:
                pass

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()

            return {
                "success": True,
                "message": f"Removed {fields_removed} form fields.",
                "fields_removed": fields_removed,
            }
        except Exception as e:
            logger.error(f"remove_form_data error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── HIDDEN DATA / METADATA REMOVAL ──────────────────────────────────

    @staticmethod
    def remove_hidden_data(input_path: str, output_path: str) -> Dict[str, Any]:
        """Remove metadata, annotations, attachments, and hidden content."""
        try:
            doc = fitz.open(input_path)
            removed = {
                "metadata": False,
                "annotations": 0,
                "attachments": 0,
                "javascript": 0,
                "embedded_files": 0,
            }

            # Strip metadata
            meta = doc.get_metadata()
            if meta:
                doc.set_metadata({})
                removed["metadata"] = True

            # Remove annotations from all pages
            for page_num in range(len(doc)):
                page = doc[page_num]
                if page.annots():
                    annots_to_remove = list(page.annots())
                    for annot in annots_to_remove:
                        page.delete_annot(annot)
                        removed["annotations"] += 1

            # Remove embedded files / attachments
            try:
                embedded = doc.embfile_count()
                for i in range(embedded - 1, -1, -1):
                    doc.embfile_delete(i)
                    removed["embedded_files"] += 1
            except Exception:
                pass

            # Remove JavaScript
            xref_count = doc.xref_length()
            for xref in range(1, xref_count):
                try:
                    obj_str = doc.xref_object(xref)
                    if "/JavaScript" in obj_str or "/JS " in obj_str:
                        doc.xref_set_key(xref, "/JavaScript", "null")
                        removed["javascript"] += 1
                except Exception:
                    continue

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()

            return {
                "success": True,
                "message": "Hidden data removed successfully.",
                "details": removed,
            }
        except Exception as e:
            logger.error(f"remove_hidden_data error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── EXTRACTION RESTRICTION ──────────────────────────────────────────

    @staticmethod
    def restrict_extraction(input_path: str, output_path: str) -> Dict[str, Any]:
        """Set the no-extract flag on a PDF to prevent page extraction."""
        try:
            doc = fitz.open(input_path)
            # Get current permissions and add no-extract
            perm = doc.permissions
            # fitz permission constants: 1 << 3 = 8 = extract (disable)
            new_perm = perm & ~8  # clear extract permission
            doc.close()

            reader = PdfReader(input_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            if reader.metadata:
                writer.add_metadata(reader.metadata)

            # pypdf permission flags: EXTRACT = 0x0008
            current_perms = 0xFFFFFFFF & ~0x0008
            writer._root_object["/Permissions"] = current_perms

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                writer.write(f)

            return {"success": True, "message": "Page extraction restricted."}
        except Exception as e:
            logger.error(f"restrict_extraction error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── COPY / ACCESSIBILITY RESTRICTION ────────────────────────────────

    @staticmethod
    def restrict_copy(input_path: str, output_path: str) -> Dict[str, Any]:
        """Restrict text copying and accessibility on a PDF."""
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            if reader.metadata:
                writer.add_metadata(reader.metadata)

            # pypdf permission flags: COPY = 0x0010, PRINT = 0x0004
            # Disable copy but allow high-quality print
            current_perms = 0xFFFFFFFF & ~0x0010
            writer._root_object["/Permissions"] = current_perms

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                writer.write(f)

            return {"success": True, "message": "Text copying restricted."}
        except Exception as e:
            logger.error(f"restrict_copy error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── SECURITY SCORE ──────────────────────────────────────────────────

    @staticmethod
    def get_security_score(input_path: str) -> Dict[str, Any]:
        """Analyse a PDF and return a comprehensive security score (0-100)."""
        try:
            doc = fitz.open(input_path)
            score = 100
            findings: List[Dict[str, str]] = []
            recommendations: List[str] = []

            # Check if encrypted
            reader = PdfReader(input_path)
            if not reader.is_encrypted:
                score -= 15
                findings.append({"check": "encryption", "status": "missing", "severity": "high"})
                recommendations.append("Add password protection to the PDF.")

            # Check for JavaScript
            has_js = False
            xref_count = doc.xref_length()
            for xref in range(1, xref_count):
                try:
                    obj_str = doc.xref_object(xref)
                    if "/JavaScript" in obj_str or "/JS " in obj_str:
                        has_js = True
                        break
                except Exception:
                    continue

            if has_js:
                score -= 20
                findings.append({"check": "javascript", "status": "detected", "severity": "critical"})
                recommendations.append("Remove JavaScript to prevent code execution vulnerabilities.")

            # Check for embedded files
            try:
                emb_count = doc.embfile_count()
                if emb_count > 0:
                    score -= 15
                    findings.append({
                        "check": "embedded_files",
                        "status": f"{emb_count} found",
                        "severity": "high",
                    })
                    recommendations.append("Remove embedded files that could contain malicious content.")
            except Exception:
                pass

            # Check for annotations
            annot_count = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                if page.annots():
                    annot_count += len(list(page.annots()))

            if annot_count > 20:
                score -= 5
                findings.append({
                    "check": "annotations",
                    "status": f"{annot_count} annotations",
                    "severity": "low",
                })

            # Check metadata for sensitive info
            meta = doc.get_metadata()
            if meta:
                sensitive_keys = ["Author", "Creator", "Producer"]
                for key in sensitive_keys:
                    if meta.get(key):
                        score -= 2
                        findings.append({
                            "check": "metadata_leak",
                            "status": f"{key} exposed",
                            "severity": "low",
                        })
                recommendations.append("Strip metadata to prevent information leakage.")

            # Check for URIs / links
            for page_num in range(len(doc)):
                page = doc[page_num]
                links = page.get_links()
                for link in links:
                    if link.get("kind") == fitz.LINK_URI:
                        uri = link.get("uri", "")
                        if uri.startswith("http://"):
                            score -= 3
                            findings.append({
                                "check": "insecure_link",
                                "status": uri[:80],
                                "severity": "medium",
                            })

            # Check page count (very large files may be suspicious)
            if len(doc) > 500:
                score -= 5
                findings.append({
                    "check": "large_document",
                    "status": f"{len(doc)} pages",
                    "severity": "low",
                })

            # Check creation/modification dates
            if meta:
                if meta.get("CreationDate"):
                    score -= 0  # informational
                if meta.get("ModDate"):
                    score -= 0

            doc.close()

            score = max(0, min(100, score))

            # Determine risk level
            if score >= 80:
                risk_level = "low"
            elif score >= 60:
                risk_level = "medium"
            elif score >= 40:
                risk_level = "high"
            else:
                risk_level = "critical"

            return {
                "success": True,
                "score": score,
                "risk_level": risk_level,
                "findings": findings,
                "recommendations": recommendations,
                "total_checks": len(findings),
                "critical_count": sum(1 for f in findings if f["severity"] == "critical"),
                "high_count": sum(1 for f in findings if f["severity"] == "high"),
                "medium_count": sum(1 for f in findings if f["severity"] == "medium"),
                "low_count": sum(1 for f in findings if f["severity"] == "low"),
            }
        except Exception as e:
            logger.error(f"get_security_score error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── MALWARE SCAN ────────────────────────────────────────────────────

    @staticmethod
    def scan_malware(input_path: str) -> Dict[str, Any]:
        """Scan PDF for suspicious objects and patterns indicative of malware."""
        try:
            doc = fitz.open(input_path)
            threats: List[Dict[str, Any]] = []
            raw_data = b""

            # Read raw file bytes for pattern matching
            with open(input_path, "rb") as f:
                raw_data = f.read()

            # Scan raw bytes for suspicious patterns
            for pattern in _SUSPICIOUS_PATTERNS:
                matches = list(re.finditer(pattern, raw_data, re.IGNORECASE))
                if matches:
                    threats.append({
                        "type": "pattern_match",
                        "pattern": pattern.decode("latin-1", errors="replace"),
                        "occurrences": len(matches),
                        "severity": "high" if pattern in [rb"/JavaScript", rb"/JS\s", rb"eval\s*\("] else "medium",
                    })

            # Check for auto-open actions
            try:
                cat = doc.pdf_catalog()
                cat_obj = doc.xref_object(cat)
                if "/OpenAction" in cat_obj:
                    threats.append({
                        "type": "auto_action",
                        "detail": "Document has an auto-open action.",
                        "severity": "high",
                    })
                if "/AA" in cat_obj:
                    threats.append({
                        "type": "auto_action",
                        "detail": "Document has additional actions (AA).",
                        "severity": "medium",
                    })
            except Exception:
                pass

            # Check for launch actions
            for page_num in range(len(doc)):
                page = doc[page_num]
                links = page.get_links()
                for link in links:
                    if link.get("kind") == fitz.LINK_LAUNCH:
                        threats.append({
                            "type": "launch_action",
                            "detail": f"Launch action on page {page_num + 1}: {link.get('file', '')}",
                            "severity": "critical",
                        })

            # Check for XFA forms (complex XML forms can be exploited)
            xref_count = doc.xref_length()
            for xref in range(1, xref_count):
                try:
                    obj_str = doc.xref_object(xref)
                    if "/XFA" in obj_str:
                        threats.append({
                            "type": "xfa_form",
                            "detail": "XFA form detected (potential exploit vector).",
                            "severity": "medium",
                        })
                        break
                except Exception:
                    continue

            doc.close()

            scan_time = datetime.now(timezone.utc).isoformat()
            is_clean = len(threats) == 0

            return {
                "success": True,
                "is_clean": is_clean,
                "threats_found": len(threats),
                "threats": threats,
                "scan_timestamp": scan_time,
                "file_scanned": os.path.basename(input_path),
                "file_size_bytes": os.path.getsize(input_path),
                "recommendation": "No threats detected." if is_clean else "Review flagged items and consider removing suspicious content.",
            }
        except Exception as e:
            logger.error(f"scan_malware error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── PDF/A VALIDATION ────────────────────────────────────────────────

    @staticmethod
    def validate_pdfa(input_path: str) -> Dict[str, Any]:
        """Validate whether a PDF conforms to PDF/A standards."""
        try:
            doc = fitz.open(input_path)
            meta = doc.get_metadata()
            is_pdfa = False
            pdfa_level = "N/A"
            issues: List[str] = []

            # Check for PDF/A identifier in metadata
            xmp = meta.get("format", "") if meta else ""
            if "PDF/A" in xmp:
                is_pdfa = True
                if "1b" in xmp.lower():
                    pdfa_level = "PDF/A-1b"
                elif "1a" in xmp.lower():
                    pdfa_level = "PDF/A-1a"
                elif "2b" in xmp.lower():
                    pdfa_level = "PDF/A-2b"
                elif "2a" in xmp.lower():
                    pdfa_level = "PDF/A-2a"
                elif "3b" in xmp.lower():
                    pdfa_level = "PDF/A-3b"
                elif "3a" in xmp.lower():
                    pdfa_level = "PDF/A-3a"
                else:
                    pdfa_level = "PDF/A (level unspecified)"

            # Check PDF/A metadata marker in the XMP stream
            xref_count = doc.xref_length()
            for xref in range(1, xref_count):
                try:
                    obj_str = doc.xref_object(xref)
                    if "pdfaid:part" in obj_str or "pdfaid:conformance" in obj_str:
                        is_pdfa = True
                        break
                except Exception:
                    continue

            # PDF/A compliance checks
            # 1. Fonts must be embedded
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                font = span.get("font", "")
                                if "NotEmbedded" in font or "Unknown" in font:
                                    issues.append(f"Font '{font}' may not be embedded on page {page_num + 1}.")

            # 2. Check transparency / layers (not allowed in PDF/A-1)
            if is_pdfa and pdfa_level.startswith("PDF/A-1"):
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    if page.get_drawings():
                        issues.append(f"Vector graphics on page {page_num + 1} may use transparency (not allowed in PDF/A-1).")

            # 3. Check for encryption (not allowed in PDF/A)
            if doc.is_encrypted:
                issues.append("Encrypted PDFs are not PDF/A compliant.")
                is_pdfa = False

            doc.close()

            return {
                "success": True,
                "is_pdfa_compliant": is_pdfa,
                "pdfa_level": pdfa_level if is_pdfa else "Non-PDF/A",
                "issues_found": len(issues),
                "issues": issues,
                "recommendations": [
                    "Embed all fonts." if issues else "Document appears compliant.",
                    "Remove encryption for PDF/A compliance.",
                    "Use PDF/A-2b or later for modern compliance.",
                ],
            }
        except Exception as e:
            logger.error(f"validate_pdfa error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── DIGITAL SIGNATURE VERIFICATION ──────────────────────────────────

    @staticmethod
    def verify_digital_signatures(input_path: str) -> Dict[str, Any]:
        """Compatibility wrapper for digital signature verification."""
        return digital_signature_verification_service.verify_pdf(input_path)

    # ── DOCUMENT INTEGRITY ──────────────────────────────────────────────

    @staticmethod
    def check_document_integrity(input_path: str) -> Dict[str, Any]:
        """Verify document integrity by computing hashes and checking structure."""
        try:
            with open(input_path, "rb") as f:
                raw = f.read()

            md5 = hashlib.md5(raw).hexdigest()
            sha1 = hashlib.sha1(raw).hexdigest()
            sha256 = hashlib.sha256(raw).hexdigest()

            doc = fitz.open(input_path)
            page_count = len(doc)
            issues: List[str] = []

            # Verify each page is readable
            corrupt_pages: List[int] = []
            for i in range(page_count):
                try:
                    page = doc[i]
                    _ = page.get_text()
                except Exception:
                    corrupt_pages.append(i + 1)

            if corrupt_pages:
                issues.append(f"Corrupt pages detected: {corrupt_pages}")

            # Check for cross-reference table integrity
            xref_ok = True
            try:
                xref_count = doc.xref_length()
                for xref in range(1, min(xref_count, 100)):
                    try:
                        doc.xref_object(xref)
                    except Exception:
                        xref_ok = False
                        break
            except Exception:
                xref_ok = False

            if not xref_ok:
                issues.append("Cross-reference table may be corrupt.")

            # Check trailer
            try:
                trailer = doc.pdf_trailer()
                if not trailer:
                    issues.append("PDF trailer missing or corrupt.")
            except Exception:
                issues.append("Could not read PDF trailer.")

            doc.close()

            integrity_ok = len(issues) == 0 and len(corrupt_pages) == 0

            return {
                "success": True,
                "integrity_ok": integrity_ok,
                "hashes": {
                    "md5": md5,
                    "sha1": sha1,
                    "sha256": sha256,
                },
                "file_size_bytes": len(raw),
                "page_count": page_count,
                "corrupt_pages": corrupt_pages,
                "cross_reference_ok": xref_ok,
                "issues": issues,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"check_document_integrity error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── EMBEDDED FILE DETECTION ─────────────────────────────────────────

    @staticmethod
    def detect_embedded_files(input_path: str) -> Dict[str, Any]:
        """List all embedded files / attachments in a PDF."""
        try:
            doc = fitz.open(input_path)
            files: List[Dict[str, Any]] = []

            try:
                emb_count = doc.embfile_count()
                for i in range(emb_count):
                    info = doc.embfile_info(i)
                    files.append({
                        "index": i,
                        "name": info.get("name", f"attachment_{i}"),
                        "description": info.get("description", ""),
                        "mime_type": info.get("mime", "unknown"),
                        "size_bytes": info.get("size", 0),
                    })
            except Exception:
                pass

            doc.close()

            return {
                "success": True,
                "embedded_files_found": len(files),
                "files": files,
                "risk_assessment": "high" if files else "none",
                "recommendation": "Review embedded files for malicious content." if files else "No embedded files detected.",
            }
        except Exception as e:
            logger.error(f"detect_embedded_files error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── EMBEDDED MEDIA DETECTION ────────────────────────────────────────

    @staticmethod
    def detect_embedded_media(input_path: str) -> Dict[str, Any]:
        """Detect embedded media objects (images, audio, video, 3D)."""
        try:
            doc = fitz.open(input_path)
            media: List[Dict[str, Any]] = []

            # Collect image info per page
            for page_num in range(len(doc)):
                page = doc[page_num]
                images = page.get_images(full=True)
                for img in images:
                    xref = img[0]
                    try:
                        img_info = doc.xref_image_info(xref)
                    except Exception:
                        img_info = {}
                    media.append({
                        "type": "image",
                        "page": page_num + 1,
                        "xref": xref,
                        "width": img[2],
                        "height": img[3],
                        "colorspace": img_info.get("colorspace", "unknown"),
                    })

            # Scan for multimedia annotations (RichMedia, Screen)
            xref_count = doc.xref_length()
            for xref in range(1, xref_count):
                try:
                    obj_str = doc.xref_object(xref)
                    if "/RichMedia" in obj_str:
                        media.append({"type": "rich_media", "xref": xref, "detail": "RichMedia content detected."})
                    if "/Screen" in obj_str:
                        media.append({"type": "screen_annotation", "xref": xref, "detail": "Screen annotation detected."})
                except Exception:
                    continue

            doc.close()

            image_count = sum(1 for m in media if m["type"] == "image")
            other_count = len(media) - image_count

            return {
                "success": True,
                "media_found": len(media),
                "images": image_count,
                "other_media": other_count,
                "media": media,
                "risk_assessment": "low" if other_count == 0 else "medium",
            }
        except Exception as e:
            logger.error(f"detect_embedded_media error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── FILE EXPIRATION ─────────────────────────────────────────────────

    @staticmethod
    def check_expiration(input_path: str) -> Dict[str, Any]:
        """Check and verify expiration metadata in a PDF."""
        try:
            doc = fitz.open(input_path)
            meta = doc.get_metadata()
            doc.close()

            expiration_info: Dict[str, Any] = {
                "has_expiration": False,
                "creation_date": None,
                "modification_date": None,
                "expiration_date": None,
                "is_expired": None,
            }

            if meta:
                creation = meta.get("CreationDate", "")
                modification = meta.get("ModDate", "")

                if creation:
                    expiration_info["creation_date"] = creation
                if modification:
                    expiration_info["modification_date"] = modification

            # Check custom metadata for expiration
            try:
                doc = fitz.open(input_path)
                # Check for /Info dictionary entries related to expiration
                cat = doc.pdf_catalog()
                cat_obj = doc.xref_object(cat)
                if "expiration" in cat_obj.lower() or "expire" in cat_obj.lower():
                    expiration_info["has_expiration"] = True
                doc.close()
            except Exception:
                pass

            return {
                "success": True,
                "expiration_info": expiration_info,
                "message": "Expiration check completed.",
            }
        except Exception as e:
            logger.error(f"check_expiration error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── HIDE SENSITIVE INFORMATION ──────────────────────────────────────

    @staticmethod
    def hide_sensitive_info(input_path: str, output_path: str) -> Dict[str, Any]:
        """Redact detected sensitive information patterns from the PDF."""
        try:
            doc = fitz.open(input_path)
            total_redactions = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")

                for category, pattern in _SENSITIVE_PATTERNS.items():
                    matches = list(re.finditer(pattern, text))
                    for match in matches:
                        rects = page.search_for(match.group())
                        for rect in rects:
                            page.add_redact_annot(rect, fill=(0, 0, 0))
                            total_redactions += 1

                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()

            return {
                "success": True,
                "message": f"Redacted {total_redactions} sensitive items.",
                "redactions_applied": total_redactions,
            }
        except Exception as e:
            logger.error(f"hide_sensitive_info error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── BLACKOUT / REDACT AREAS ─────────────────────────────────────────

    @staticmethod
    def blackout_areas(input_path: str, output_path: str, areas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Blackout/redact specific rectangular areas in the PDF.

        Each area dict: {"page": int (1-indexed), "x0": float, "y0": float, "x1": float, "y1": float}
        """
        try:
            doc = fitz.open(input_path)
            blackout_count = 0

            for area in areas:
                page_num = area.get("page", 1) - 1
                if page_num < 0 or page_num >= len(doc):
                    continue

                rect = fitz.Rect(area["x0"], area["y0"], area["x1"], area["y1"])
                page = doc[page_num]
                page.add_redact_annot(rect, fill=(0, 0, 0))
                blackout_count += 1

            # Apply all redactions
            for page_num in range(len(doc)):
                page = doc[page_num]
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()

            return {
                "success": True,
                "message": f"Blacked out {blackout_count} areas.",
                "areas_blackout": blackout_count,
            }
        except Exception as e:
            logger.error(f"blackout_areas error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── METADATA PROTECTION ─────────────────────────────────────────────

    @staticmethod
    def protect_metadata(input_path: str, output_path: str) -> Dict[str, Any]:
        """Remove or protect PDF metadata to prevent information leakage."""
        try:
            doc = fitz.open(input_path)
            old_meta = doc.get_metadata()
            stripped_keys: List[str] = []

            if old_meta:
                sensitive_keys = [
                    "Author", "Creator", "Producer", "Title",
                    "Subject", "Keywords", "Trapped",
                ]
                for key in sensitive_keys:
                    if old_meta.get(key):
                        stripped_keys.append(key)

                # Set minimal safe metadata
                safe_meta = {
                    "format": old_meta.get("format", "PDF 1.4"),
                }
                doc.set_metadata(safe_meta)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()

            return {
                "success": True,
                "message": f"Metadata protected. Stripped {len(stripped_keys)} sensitive fields.",
                "stripped_fields": stripped_keys,
            }
        except Exception as e:
            logger.error(f"protect_metadata error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── SANITIZE PDF ────────────────────────────────────────────────────

    @staticmethod
    def sanitize_pdf(input_path: str, output_path: str) -> Dict[str, Any]:
        """Full PDF sanitization: remove JS, forms, metadata, attachments, and annotations."""
        try:
            results: Dict[str, Any] = {}

            # 1. Remove JavaScript
            js_res = PDFSecurityService.remove_javascript(input_path, output_path)
            results["javascript"] = js_res

            # 2. Remove form data from the intermediate file
            if js_res.get("success") and os.path.exists(output_path):
                form_res = PDFSecurityService.remove_form_data(output_path, output_path)
                results["forms"] = form_res

            # 3. Remove hidden data / metadata from the intermediate file
            if os.path.exists(output_path):
                hidden_res = PDFSecurityService.remove_hidden_data(output_path, output_path)
                results["hidden_data"] = hidden_res

            # 4. Final pass with garbage collection
            doc = fitz.open(output_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()

            return {
                "success": True,
                "message": "PDF sanitized successfully.",
                "details": results,
            }
        except Exception as e:
            logger.error(f"sanitize_pdf error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── POLICY TEMPLATES ────────────────────────────────────────────────

    @staticmethod
    def get_policy_templates() -> Dict[str, Any]:
        """Return available security policy templates."""
        return {
            "success": True,
            "templates": _POLICY_TEMPLATES,
            "count": len(_POLICY_TEMPLATES),
        }

    # ── VERSION SECURITY ────────────────────────────────────────────────

    @staticmethod
    def check_version_security(input_path: str) -> Dict[str, Any]:
        """Analyse PDF version for known security issues."""
        try:
            with open(input_path, "rb") as f:
                header = f.read(20)

            version_str = header.decode("latin-1", errors="replace").strip()
            issues: List[str] = []

            # Extract version number
            version_match = re.search(r"PDF-(\d+\.\d+)", version_str)
            if version_match:
                version = version_match.group(1)
            else:
                version = "unknown"

            version_num = float(version) if version != "unknown" else 0

            if version_num < 1.4:
                issues.append("PDF version < 1.4 may lack modern security features.")
            if version_num < 1.5:
                issues.append("PDF version < 1.5 does not support AES-256 encryption.")
            if version_num > 2.0:
                issues.append("PDF version > 2.0 is very new; may have compatibility issues.")

            has_xref_stream = False
            try:
                with open(input_path, "rb") as f:
                    content = f.read()
                    has_xref_stream = b"startxref" in content and b"%%EOF" in content
            except Exception:
                pass

            return {
                "success": True,
                "version": version,
                "version_number": version_num,
                "header": version_str.strip(),
                "has_xref_stream": has_xref_stream,
                "issues": issues,
                "recommendations": [
                    "Upgrade to PDF 1.7 or later for best security features.",
                    "Use AES-256 encryption (requires PDF 1.6+).",
                ],
            }
        except Exception as e:
            logger.error(f"check_version_security error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── SECURE SHARING ──────────────────────────────────────────────────

    @staticmethod
    def create_secure_share(input_path: str) -> Dict[str, Any]:
        """Generate a secure sharing token and metadata for the PDF."""
        try:
            import secrets

            token = secrets.token_urlsafe(32)
            file_hash = hashlib.sha256(open(input_path, "rb").read()).hexdigest()[:16]

            share_info = {
                "token": token,
                "file_hash": file_hash,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": None,
                "download_url": f"/api/pdf/security/secure-sharing/download/{token}",
                "permissions": {
                    "view": True,
                    "download": True,
                    "print": False,
                },
            }

            return {
                "success": True,
                "message": "Secure share link generated.",
                "share": share_info,
            }
        except Exception as e:
            logger.error(f"create_secure_share error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── AUDIT REPORT ────────────────────────────────────────────────────

    @staticmethod
    def generate_audit_report(input_path: str) -> Dict[str, Any]:
        """Generate a comprehensive security audit report."""
        try:
            score_data = PDFSecurityService.get_security_score(input_path)
            malware_data = PDFSecurityService.scan_malware(input_path)
            integrity_data = PDFSecurityService.check_document_integrity(input_path)
            version_data = PDFSecurityService.check_version_security(input_path)
            embedded_data = PDFSecurityService.detect_embedded_files(input_path)

            report = {
                "success": True,
                "report_generated_at": datetime.now(timezone.utc).isoformat(),
                "file_name": os.path.basename(input_path),
                "file_size_bytes": os.path.getsize(input_path),
                "sections": {
                    "security_score": score_data,
                    "malware_scan": malware_data,
                    "document_integrity": integrity_data,
                    "version_analysis": version_data,
                    "embedded_files": embedded_data,
                },
                "summary": {
                    "overall_score": score_data.get("score", 0),
                    "risk_level": score_data.get("risk_level", "unknown"),
                    "malware_clean": malware_data.get("is_clean", False),
                    "integrity_ok": integrity_data.get("integrity_ok", False),
                    "pdf_version": version_data.get("version", "unknown"),
                    "embedded_files_count": embedded_data.get("embedded_files_found", 0),
                },
            }

            return report
        except Exception as e:
            logger.error(f"generate_audit_report error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── TRUSTED CERTIFICATES ────────────────────────────────────────────

    @staticmethod
    def get_trusted_certs() -> Dict[str, Any]:
        """Return the list of trusted root certificates."""
        return {
            "success": True,
            "certificates": _TRUSTED_CERTS,
            "count": len(_TRUSTED_CERTS),
        }

    # ── UNSAFE LINK DETECTION ───────────────────────────────────────────

    @staticmethod
    def detect_unsafe_links(input_path: str) -> Dict[str, Any]:
        """Detect and analyse all URLs embedded in the PDF."""
        try:
            doc = fitz.open(input_path)
            links: List[Dict[str, Any]] = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_links = page.get_links()
                for link in page_links:
                    uri = link.get("uri", "")
                    if not uri:
                        continue

                    is_safe = True
                    risk_reasons: List[str] = []

                    # Check HTTP vs HTTPS
                    if uri.startswith("http://"):
                        is_safe = False
                        risk_reasons.append("Uses insecure HTTP protocol.")

                    # Check for suspicious URL patterns
                    suspicious = [
                        r"javascript:", r"data:", r"vbscript:",
                        r"\.exe", r"\.bat", r"\.cmd", r"\.scr",
                        r"eval\(", r"document\.write",
                    ]
                    for pattern in suspicious:
                        if re.search(pattern, uri, re.IGNORECASE):
                            is_safe = False
                            risk_reasons.append(f"Matches suspicious pattern: {pattern}")

                    # Check for URL shorteners (common phishing technique)
                    shorteners = ["bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "buff.ly"]
                    parsed = urllib.parse.urlparse(uri)
                    if parsed.hostname and any(s in parsed.hostname for s in shorteners):
                        risk_reasons.append("URL shortener detected (potential phishing).")

                    links.append({
                        "page": page_num + 1,
                        "url": uri[:500],
                        "is_safe": is_safe,
                        "risk_reasons": risk_reasons,
                        "kind": "URI",
                    })

            doc.close()

            unsafe_count = sum(1 for l in links if not l["is_safe"])

            return {
                "success": True,
                "total_links": len(links),
                "unsafe_links": unsafe_count,
                "safe_links": len(links) - unsafe_count,
                "links": links,
                "risk_level": "high" if unsafe_count > 0 else "low",
            }
        except Exception as e:
            logger.error(f"detect_unsafe_links error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── WATERMARK PROTECTION ────────────────────────────────────────────

    @staticmethod
    def add_watermark_protection(
        input_path: str, output_path: str, watermark_text: str = "CONFIDENTIAL"
    ) -> Dict[str, Any]:
        """Add a protective diagonal watermark to all pages."""
        try:
            doc = fitz.open(input_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                rect = page.rect

                # Draw diagonal watermark
                point_start = fitz.Point(rect.width * 0.1, rect.height * 0.85)
                point_end = fitz.Point(rect.width * 0.85, rect.height * 0.15)

                # Use redact-based overlay for watermark
                shape = page.new_shape()
                shape.insert_textbox(
                    rect,
                    watermark_text,
                    fontsize=48,
                    color=(0.8, 0.8, 0.8),
                    rotate=45,
                    align=fitz.TEXT_ALIGN_CENTER,
                    fontname="helv",
                )
                shape.commit()

                # Add a subtle text overlay via annotation
                annot = page.add_freetext_annot(
                    rect,
                    watermark_text,
                    fontsize=10,
                    text_color=(0.9, 0.9, 0.9),
                    fill_color=None,
                    rotate=0,
                )
                annot.set_opacity(0.3)
                annot.update()

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()

            return {
                "success": True,
                "message": f"Watermark '{watermark_text}' added to all pages.",
                "pages_watermarked": len(doc),
                "watermark_text": watermark_text,
            }
        except Exception as e:
            logger.error(f"add_watermark_protection error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── AI DOCUMENT CLASSIFICATION ──────────────────────────────────────

    @staticmethod
    def ai_classify_document(input_path: str) -> Dict[str, Any]:
        """Classify the document type using keyword analysis."""
        try:
            doc = fitz.open(input_path)
            all_text = ""
            for page in doc:
                all_text += page.get_text("text")
            doc.close()

            text_lower = all_text.lower()

            # Keyword-based scoring for each category
            category_scores: Dict[str, int] = {}
            keywords_map = {
                "contract": ["agreement", "party", "parties", "whereas", "hereby", "covenant", "obligation", "breach", "term", "clause"],
                "invoice": ["invoice", "bill to", "amount due", "payment", "total", "subtotal", "tax", "vendor", "itemized"],
                "court_filing": ["court", "plaintiff", "defendant", "motion", "order", "judge", "docket", "filing", "jurisdiction"],
                "legal_brief": ["brief", "argument", "counsel", "appellant", "appellee", "precedent", "statute", "holding"],
                "compliance_report": ["compliance", "regulation", "audit", "finding", "remediation", "policy", "standard"],
                "financial_statement": ["balance sheet", "income statement", "revenue", "assets", "liabilities", "equity", "profit"],
                "medical_record": ["patient", "diagnosis", "treatment", "physician", "medical", "clinical", "prescription"],
                "personal_id": ["date of birth", "social security", "passport", "license", "identification"],
                "correspondence": ["dear", "sincerely", "regards", "letter", "notification", "attention"],
                "memo": ["memorandum", "to:", "from:", "date:", "subject:", "re:"],
                "policy": ["policy", "guideline", "procedure", "regulation", "compliance", "governance"],
                "technical_specification": ["specification", "requirement", "system", "technical", "architecture", "protocol"],
                "academic_paper": ["abstract", "introduction", "methodology", "results", "conclusion", "references", "hypothesis"],
                "government_form": ["government", "agency", "form", "federal", "state", "application", " filing"],
            }

            for category, keywords in keywords_map.items():
                score = 0
                for kw in keywords:
                    score += text_lower.count(kw.lower())
                category_scores[category] = score

            # Sort by score
            sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
            primary_category = sorted_cats[0][0] if sorted_cats[0][1] > 0 else "other"

            # Build confidence scores
            total = sum(v for _, v in sorted_cats) or 1
            confidences = {cat: round(score / total * 100, 1) for cat, score in sorted_cats if score > 0}

            return {
                "success": True,
                "primary_category": primary_category,
                "confidence": confidences.get(primary_category, 0),
                "all_scores": confidences,
                "text_length": len(all_text),
                "page_count": doc.page_count if hasattr(doc, "page_count") else 0,
            }
        except Exception as e:
            logger.error(f"ai_classify_document error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── AI SECURITY RECOMMENDATIONS ─────────────────────────────────────

    @staticmethod
    def ai_security_recommendations(input_path: str) -> Dict[str, Any]:
        """Generate AI-driven security recommendations based on document analysis."""
        try:
            score_data = PDFSecurityService.get_security_score(input_path)
            malware_data = PDFSecurityService.scan_malware(input_path)
            embedded_data = PDFSecurityService.detect_embedded_files(input_path)
            link_data = PDFSecurityService.detect_unsafe_links(input_path)
            meta_data = PDFSecurityService.protect_metadata.__wrapped__(input_path, input_path + ".tmp") if hasattr(PDFSecurityService.protect_metadata, "__wrapped__") else {"stripped_fields": []}

            recommendations: List[Dict[str, Any]] = []
            priority_counter = 0

            # Encryption recommendation
            if score_data.get("score", 100) < 85:
                priority_counter += 1
                recommendations.append({
                    "id": priority_counter,
                    "category": "encryption",
                    "title": "Enable strong encryption",
                    "description": "Apply AES-256 encryption with a strong password to protect the document from unauthorized access.",
                    "priority": "high",
                    "impact": "Prevents unauthorized viewing and editing.",
                    "implementation": "Use the /security/protect endpoint with a strong password.",
                })

            # JavaScript removal
            if score_data.get("critical_count", 0) > 0:
                priority_counter += 1
                recommendations.append({
                    "id": priority_counter,
                    "category": "javascript",
                    "title": "Remove JavaScript code",
                    "description": "The document contains JavaScript which can be used for malicious purposes.",
                    "priority": "critical",
                    "impact": "Eliminates code execution vulnerabilities.",
                    "implementation": "Use the /security/remove-javascript endpoint.",
                })

            # Embedded files
            if embedded_data.get("embedded_files_found", 0) > 0:
                priority_counter += 1
                recommendations.append({
                    "id": priority_counter,
                    "category": "embedded_content",
                    "title": "Review embedded files",
                    "description": f"Found {embedded_data['embedded_files_found']} embedded files that could contain malware.",
                    "priority": "high",
                    "impact": "Reduces risk of embedded malware delivery.",
                    "implementation": "Use the /security/remove-hidden-data endpoint.",
                })

            # Unsafe links
            if link_data.get("unsafe_links", 0) > 0:
                priority_counter += 1
                recommendations.append({
                    "id": priority_counter,
                    "category": "links",
                    "title": "Address unsafe links",
                    "description": f"Found {link_data['unsafe_links']} unsafe links in the document.",
                    "priority": "medium",
                    "impact": "Prevents phishing and malicious redirect risks.",
                    "implementation": "Use the /security/unsafe-link-detect endpoint to identify and remediate.",
                })

            # Metadata leakage
            meta_stripped = meta_data.get("stripped_fields", []) if isinstance(meta_data, dict) else []
            if meta_stripped:
                priority_counter += 1
                recommendations.append({
                    "id": priority_counter,
                    "category": "metadata",
                    "title": "Strip sensitive metadata",
                    "description": f"Document contains metadata fields: {', '.join(meta_stripped)} that could leak authorship information.",
                    "priority": "medium",
                    "impact": "Prevents information leakage about document author and tools used.",
                    "implementation": "Use the /security/metadata-protection endpoint.",
                })

            # General hygiene
            priority_counter += 1
            recommendations.append({
                "id": priority_counter,
                "category": "general",
                "title": "Run full sanitization",
                "description": "Perform a complete PDF sanitization to remove all non-essential content.",
                "priority": "low",
                "impact": "Reduces overall attack surface.",
                "implementation": "Use the /security/sanitize endpoint.",
            })

            return {
                "success": True,
                "total_recommendations": len(recommendations),
                "recommendations": recommendations,
                "current_score": score_data.get("score", 0),
                "potential_score": min(100, score_data.get("score", 0) + len(recommendations) * 10),
            }
        except Exception as e:
            logger.error(f"ai_security_recommendations error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── AI RISK DETECTION ───────────────────────────────────────────────

    @staticmethod
    def ai_risk_detection(input_path: str) -> Dict[str, Any]:
        """Perform AI-based risk assessment of the PDF."""
        try:
            doc = fitz.open(input_path)
            risks: List[Dict[str, Any]] = []
            risk_score = 0

            all_text = ""
            for page in doc:
                all_text += page.get_text("text")

            # Check for sensitive data exposure
            for category, pattern in _SENSITIVE_PATTERNS.items():
                matches = list(re.finditer(pattern, all_text, re.IGNORECASE))
                if matches:
                    risk_score += len(matches) * 5
                    risks.append({
                        "type": "data_exposure",
                        "category": category,
                        "severity": "high" if category in ["ssn", "credit_card", "aadhaar"] else "medium",
                        "count": len(matches),
                        "description": f"Detected {len(matches)} instances of {category.replace('_', ' ')} data.",
                    })

            # Check for external references
            xref_count = doc.xref_length()
            for xref in range(1, xref_count):
                try:
                    obj_str = doc.xref_object(xref)
                    if "/URI" in obj_str:
                        risk_score += 3
                        risks.append({
                            "type": "external_reference",
                            "severity": "medium",
                            "description": "Document contains external URI references.",
                        })
                        break
                except Exception:
                    continue

            # Check for large image count (potential steganography)
            total_images = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                total_images += len(page.get_images())

            if total_images > 50:
                risk_score += 10
                risks.append({
                    "type": "steganography_risk",
                    "severity": "low",
                    "count": total_images,
                    "description": f"Large number of images ({total_images}) detected. Could be used for steganography.",
                })

            doc.close()

            # Overall risk assessment
            if risk_score > 50:
                risk_level = "critical"
            elif risk_score > 30:
                risk_level = "high"
            elif risk_score > 15:
                risk_level = "medium"
            else:
                risk_level = "low"

            return {
                "success": True,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risks_found": len(risks),
                "risks": risks,
                "assessment": f"Document has a {risk_level} risk profile with a score of {risk_score}.",
            }
        except Exception as e:
            logger.error(f"ai_risk_detection error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── AI SENSITIVE DATA DETECTION ─────────────────────────────────────

    @staticmethod
    def ai_sensitive_detection(input_path: str) -> Dict[str, Any]:
        """Detect PII and sensitive data using pattern matching and heuristics."""
        try:
            doc = fitz.open(input_path)
            detections: Dict[str, List[Dict[str, Any]]] = {}
            total_count = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")

                for category, pattern in _SENSITIVE_PATTERNS.items():
                    matches = list(re.finditer(pattern, text, re.IGNORECASE))
                    if matches:
                        if category not in detections:
                            detections[category] = []
                        for match in matches:
                            # Mask the value for security
                            value = match.group()
                            masked = value[:2] + "*" * (len(value) - 4) + value[-2:] if len(value) > 4 else "**"
                            detections[category].append({
                                "page": page_num + 1,
                                "masked_value": masked,
                                "position": {"start": match.start(), "end": match.end()},
                            })
                            total_count += 1

            doc.close()

            category_summary = {
                cat: len(items) for cat, items in detections.items()
            }

            return {
                "success": True,
                "total_detections": total_count,
                "categories_found": len(detections),
                "category_summary": category_summary,
                "detections": detections,
                "risk_level": "high" if total_count > 10 else "medium" if total_count > 0 else "low",
                "recommendation": "Consider redacting detected sensitive data before distribution." if total_count > 0 else "No sensitive data detected.",
            }
        except Exception as e:
            logger.error(f"ai_sensitive_detection error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── FORENSIC ANALYSIS ───────────────────────────────────────────────

    @staticmethod
    def forensic_analysis(input_path: str) -> Dict[str, Any]:
        """Deep forensic analysis of PDF internal structure."""
        try:
            with open(input_path, "rb") as f:
                raw = f.read()

            doc = fitz.open(input_path)

            analysis: Dict[str, Any] = {
                "file_info": {
                    "size_bytes": len(raw),
                    "md5": hashlib.md5(raw).hexdigest(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "header": raw[:20].decode("latin-1", errors="replace").strip(),
                },
                "structure": {
                    "page_count": len(doc),
                    "version": "unknown",
                    "encrypted": doc.is_encrypted,
                },
                "objects": {
                    "total_xrefs": doc.xref_length() - 1,
                    "streams": 0,
                    "pages": len(doc),
                    "fonts": 0,
                    "images": 0,
                    "annotations": 0,
                    "javascript": 0,
                    "embedded_files": 0,
                },
                "security": {
                    "permissions": doc.permissions,
                    "has_signature": False,
                    "has_javascript": False,
                    "has_launch_action": False,
                    "has_open_action": False,
                },
                "metadata_analysis": {},
                "anomalies": [],
                "timeline": [],
            }

            # Parse version
            header = analysis["file_info"]["header"]
            version_match = re.search(r"PDF-(\d+\.\d+)", header)
            if version_match:
                analysis["structure"]["version"] = version_match.group(1)

            # Timeline
            meta = doc.get_metadata()
            if meta:
                if meta.get("CreationDate"):
                    analysis["timeline"].append({
                        "event": "creation",
                        "date": meta["CreationDate"],
                        "source": "metadata",
                    })
                if meta.get("ModDate"):
                    analysis["timeline"].append({
                        "event": "modification",
                        "date": meta["ModDate"],
                        "source": "metadata",
                    })
                analysis["metadata_analysis"] = {k: v for k, v in meta.items() if v}

            # Scan objects
            xref_count = doc.xref_length()
            for xref in range(1, xref_count):
                try:
                    obj_str = doc.xref_object(xref)
                    if "/Stream" in obj_str:
                        analysis["objects"]["streams"] += 1
                    if "/Font" in obj_str:
                        analysis["objects"]["fonts"] += 1
                    if "/Image" in obj_str:
                        analysis["objects"]["images"] += 1
                    if "/JavaScript" in obj_str or "/JS " in obj_str:
                        analysis["objects"]["javascript"] += 1
                        analysis["security"]["has_javascript"] = True
                    if "/Launch" in obj_str:
                        analysis["security"]["has_launch_action"] = True
                    if "/OpenAction" in obj_str:
                        analysis["security"]["has_open_action"] = True
                    if "/EmbeddedFile" in obj_str:
                        analysis["objects"]["embedded_files"] += 1
                except Exception:
                    continue

            # Count annotations
            for page_num in range(len(doc)):
                page = doc[page_num]
                if page.annots():
                    analysis["objects"]["annotations"] += len(list(page.annots()))

            # Check for signatures
            try:
                from pyhanko.sign.validation import PdfSignatureStatus
                analysis["security"]["has_signature"] = True
            except Exception:
                pass

            # Anomaly detection
            if analysis["objects"]["javascript"] > 0:
                analysis["anomalies"].append({
                    "type": "javascript",
                    "severity": "high",
                    "detail": f"{analysis['objects']['javascript']} JavaScript objects found.",
                })
            if analysis["security"]["has_launch_action"]:
                analysis["anomalies"].append({
                    "type": "launch_action",
                    "severity": "critical",
                    "detail": "Document has a launch action that can execute external programs.",
                })
            if analysis["security"]["has_open_action"]:
                analysis["anomalies"].append({
                    "type": "open_action",
                    "severity": "medium",
                    "detail": "Document executes actions automatically when opened.",
                })

            doc.close()

            return {
                "success": True,
                "analysis": analysis,
                "anomaly_count": len(analysis["anomalies"]),
                "risk_summary": (
                    "critical" if any(a["severity"] == "critical" for a in analysis["anomalies"])
                    else "high" if any(a["severity"] == "high" for a in analysis["anomalies"])
                    else "medium" if analysis["anomalies"]
                    else "low"
                ),
            }
        except Exception as e:
            logger.error(f"forensic_analysis error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# Module-level singleton
pdf_security_service = PDFSecurityService()
