"""
Deterministic PDF security score service.

Scores only detectable PDF security controls and returns a transparent
breakdown. This is not a malware verdict or guarantee of safety.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz
from pypdf import PdfReader

from app.core.config import settings

logger = logging.getLogger(__name__)


DISCLAIMER = (
    "Security Score evaluates detectable PDF security controls. It is not a "
    "malware verdict or guarantee that the document is completely safe."
)


class SecurityScoreService:
    """Analyze a PDF and calculate a reproducible security score."""

    def analyze_pdf(
        self,
        input_path: str | Path,
        *,
        original_filename: str | None = None,
        mime_type: str | None = None,
        password: str | None = None,
        output_dir: str | Path | None = None,
    ) -> Dict[str, Any]:
        started = datetime.now(timezone.utc)
        analysis_id = f"PSS-{started.strftime('%Y%m%d')}-{uuid.uuid4().hex[:12].upper()}"
        filename = Path(original_filename or Path(input_path).name).name
        logger.info("PDF security score analysis started: %s", analysis_id)

        try:
            self.validate_upload(input_path, mime_type=mime_type)
            analysis = self._analyze(input_path, password=password)
            breakdown, findings, recommendations = self._score(analysis)
            score = sum(item["points"] for item in breakdown)
            max_score = sum(item["max_points"] for item in breakdown)
            rating = self.rating_for_score(score)

            result = {
                "success": True,
                "analysis_id": analysis_id,
                "filename": filename,
                "file_size": Path(input_path).stat().st_size,
                "score": score,
                "max_score": max_score,
                "rating": rating,
                "analysis": analysis,
                "breakdown": breakdown,
                "findings": findings,
                "warnings": analysis.get("warnings", []),
                "unknown": analysis.get("unknown", []),
                "recommendations": recommendations,
                "disclaimer": DISCLAIMER,
                "analyzed_at": started.isoformat(),
                "processing_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
            }
            self._persist_result(result, output_dir)
            logger.info("PDF security score analysis completed: %s score=%s", analysis_id, score)
            return result
        except ValueError as exc:
            logger.warning("PDF security score validation failed: %s", exc)
            return {
                "success": False,
                "analysis_id": analysis_id,
                "filename": filename,
                "error": str(exc),
                "disclaimer": DISCLAIMER,
            }
        except Exception as exc:
            logger.error("PDF security score analysis failed: %s", exc, exc_info=True)
            return {
                "success": False,
                "analysis_id": analysis_id,
                "filename": filename,
                "error": "Security analysis could not be completed. Please try again.",
                "disclaimer": DISCLAIMER,
            }

    def validate_upload(self, input_path: str | Path, *, mime_type: str | None = None) -> None:
        path = Path(input_path)
        if not path.exists() or not path.is_file():
            raise ValueError("PDF file is required.")
        if path.suffix.lower() != ".pdf":
            raise ValueError("Please upload a valid PDF document.")
        if mime_type and mime_type not in {"application/pdf", "application/x-pdf", "application/octet-stream"}:
            raise ValueError("Please upload a valid PDF document.")
        size = path.stat().st_size
        if size <= 0:
            raise ValueError("Please upload a valid PDF document.")
        if size > settings.MAX_UPLOAD_SIZE:
            raise ValueError(f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.")
        with open(path, "rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise ValueError("Please upload a valid PDF document.")

    def _analyze(self, input_path: str | Path, *, password: str | None = None) -> Dict[str, Any]:
        path = Path(input_path)
        warnings: List[str] = []
        unknown: List[str] = []

        doc = fitz.open(path)
        password_required = bool(doc.needs_pass)
        password_supplied = bool(password)
        authenticated = True
        if password_required:
            authenticated = bool(password and doc.authenticate(password))
            if not authenticated:
                warnings.append("Password-protected PDF detected. Provide the password to inspect all security properties.")

        raw = self._read_limited(path)
        encryption = self._analyze_encryption(path, doc, password_required, authenticated, password=password)
        permissions = self._analyze_permissions(doc, encrypted=encryption["encrypted"], authenticated=authenticated)
        signatures = self._analyze_signatures(path)
        active_content = self._analyze_active_content(doc, raw, authenticated=authenticated)
        document_security = self._analyze_document_security(doc, raw, authenticated=authenticated)
        metadata = self._extract_metadata(doc, authenticated=authenticated)

        doc.close()

        if not authenticated:
            unknown.extend([
                "permissions",
                "page_count",
                "metadata",
                "active_content_details",
            ])

        return {
            "encryption": encryption,
            "permissions": permissions,
            "digital_signature": signatures,
            "active_content": active_content,
            "document_security": document_security,
            "metadata": metadata,
            "password_required": password_required,
            "password_supplied": password_supplied,
            "password_authenticated": authenticated,
            "warnings": warnings,
            "unknown": unknown,
        }

    def _analyze_encryption(
        self,
        path: Path,
        doc: fitz.Document,
        password_required: bool,
        authenticated: bool,
        *,
        password: str | None,
    ) -> Dict[str, Any]:
        encrypted = bool(doc.is_encrypted or password_required)
        algorithm = "unknown"
        revision: str | int = "unknown"
        key_length: str | int = "unknown"
        handler = "unknown"

        try:
            reader = PdfReader(str(path), strict=False)
            if reader.is_encrypted:
                encrypted = True
                if password:
                    reader.decrypt(password)
                enc = getattr(reader, "_encryption", None)
                if enc is not None:
                    revision = getattr(enc, "R", "unknown")
                    key_length = getattr(enc, "Length", getattr(enc, "length", "unknown"))
                    handler = str(getattr(enc, "V", "unknown"))
                    algorithm = self._algorithm_from_revision(revision, key_length)
        except Exception as exc:
            logger.debug("Encryption detail detection unavailable: %s", exc)

        return {
            "encrypted": encrypted,
            "algorithm": algorithm if encrypted else "none",
            "revision": revision if encrypted else None,
            "key_length": key_length if encrypted else None,
            "security_handler": handler if encrypted else None,
            "password_required": password_required,
            "authenticated": authenticated,
        }

    @staticmethod
    def _algorithm_from_revision(revision: Any, key_length: Any) -> str:
        text = f"{revision} {key_length}".lower()
        if "256" in text or str(revision) in {"5", "6"}:
            return "AES-256"
        if "128" in text or str(revision) == "4":
            return "AES-128"
        if str(revision) in {"2", "3"}:
            return "RC4"
        return "unknown"

    @staticmethod
    def _analyze_permissions(doc: fitz.Document, *, encrypted: bool, authenticated: bool) -> Dict[str, Any]:
        keys = {
            "printing": fitz.PDF_PERM_PRINT,
            "high_quality_printing": fitz.PDF_PERM_PRINT_HQ,
            "copying": fitz.PDF_PERM_COPY,
            "content_extraction": fitz.PDF_PERM_COPY,
            "accessibility_extraction": fitz.PDF_PERM_ACCESSIBILITY,
            "modification": fitz.PDF_PERM_MODIFY,
            "annotations": fitz.PDF_PERM_ANNOTATE,
            "form_filling": fitz.PDF_PERM_FORM,
            "document_assembly": fitz.PDF_PERM_ASSEMBLE,
        }
        if not authenticated:
            return {key: "unknown" for key in keys}
        if not encrypted:
            return {key: True for key in keys}
        permissions = doc.permissions
        return {key: bool(permissions & bit) for key, bit in keys.items()}

    def _analyze_signatures(self, path: Path) -> Dict[str, Any]:
        details: List[Dict[str, Any]] = []
        try:
            from app.pdf_security_services.digital_signature_verification_service import (
                digital_signature_verification_service,
            )
            from pyhanko.pdf_utils.reader import PdfFileReader

            with open(path, "rb") as handle:
                reader = PdfFileReader(handle)
                embedded = list(reader.embedded_signatures)
                for index, signature in enumerate(embedded, start=1):
                    try:
                        status = digital_signature_verification_service.verify_cryptographic_signature(signature)
                        details.append(digital_signature_verification_service.build_signature_result(index, signature, status=status))
                    except Exception as exc:
                        details.append(digital_signature_verification_service.build_signature_result(index, signature, error=exc))
        except Exception as exc:
            logger.debug("Signature detection unavailable: %s", exc)
            return {"present": False, "count": 0, "valid": "unknown", "validation_status": "VALIDATION_UNAVAILABLE", "details": []}

        if not details:
            return {"present": False, "count": 0, "valid": False, "validation_status": "NOT_PRESENT", "details": []}
        if any(item.get("signature_status") == "INVALID" for item in details):
            status = "INVALID"
            valid: bool | str = False
        elif all(item.get("signature_status") == "VALID" for item in details):
            status = "VALID"
            valid = True
        else:
            status = "UNKNOWN"
            valid = "unknown"
        return {"present": True, "count": len(details), "valid": valid, "validation_status": status, "details": details}

    def _analyze_active_content(self, doc: fitz.Document, raw: bytes, *, authenticated: bool) -> Dict[str, Any]:
        if not authenticated:
            return {
                "javascript": "unknown",
                "embedded_files": "unknown",
                "open_action": "unknown",
                "launch_actions": "unknown",
                "embedded_multimedia": "unknown",
                "uri_actions": "unknown",
                "automatic_actions": "unknown",
            }

        text = raw.decode("latin-1", errors="ignore")
        uri_count = 0
        try:
            for page in doc:
                uri_count += sum(1 for link in page.get_links() if link.get("kind") == fitz.LINK_URI)
        except Exception:
            uri_count = "unknown"

        try:
            embedded_count = doc.embfile_count()
        except Exception:
            embedded_count = "unknown"

        return {
            "javascript": bool(re.search(r"/(JavaScript|JS)\b", text)),
            "embedded_files": embedded_count != "unknown" and embedded_count > 0,
            "embedded_file_count": embedded_count,
            "open_action": "/OpenAction" in text,
            "launch_actions": "/Launch" in text,
            "embedded_multimedia": any(token in text for token in ["/RichMedia", "/Movie", "/Sound"]),
            "uri_actions": uri_count != "unknown" and uri_count > 0,
            "uri_count": uri_count,
            "automatic_actions": "/AA" in text,
        }

    def _analyze_document_security(self, doc: fitz.Document, raw: bytes, *, authenticated: bool) -> Dict[str, Any]:
        header = raw[:16].decode("latin-1", errors="ignore")
        eof_present = b"%%EOF" in raw[-2048:]
        if not authenticated:
            page_count: int | str = "unknown"
            xref_count: int | str = "unknown"
        else:
            page_count = doc.page_count
            xref_count = doc.xref_length()
        return {
            "parser_status": "valid",
            "pdf_version": self._version_from_header(header),
            "page_count": page_count,
            "xref_count": xref_count,
            "eof_marker_present": eof_present,
            "incremental_revisions": max(raw.count(b"startxref"), raw.count(b"%%EOF"), 1),
        }

    @staticmethod
    def _extract_metadata(doc: fitz.Document, *, authenticated: bool) -> Dict[str, Any]:
        if not authenticated:
            return {"status": "unknown"}
        try:
            meta = doc.metadata or {}
            return {
                "title": meta.get("title") or None,
                "author": meta.get("author") or None,
                "creator": meta.get("creator") or None,
                "producer": meta.get("producer") or None,
                "creation_date": meta.get("creationDate") or None,
                "modification_date": meta.get("modDate") or None,
            }
        except Exception:
            return {"status": "unknown"}

    def _score(self, analysis: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        findings: List[Dict[str, Any]] = []
        recommendations: List[str] = []
        breakdown = [
            self._score_encryption(analysis["encryption"], findings, recommendations),
            self._score_permissions(analysis["permissions"], analysis["encryption"], findings, recommendations),
            self._score_signature(analysis["digital_signature"], findings, recommendations),
            self._score_active_content(analysis["active_content"], findings, recommendations),
            self._score_structure(analysis["document_security"], analysis["metadata"], findings, recommendations),
        ]
        return breakdown, findings, list(dict.fromkeys(recommendations))

    def _score_encryption(self, encryption: Dict[str, Any], findings: List[Dict[str, Any]], recommendations: List[str]) -> Dict[str, Any]:
        max_points = 30
        if not encryption["encrypted"]:
            findings.append(self._finding("LOW", "No encryption detected", "The PDF does not appear to use PDF encryption.", "encryption=false", "Apply strong password protection if confidentiality is required."))
            recommendations.append("Enable strong PDF encryption for confidential documents.")
            return self._breakdown("Encryption", 0, max_points, "missing", "No PDF encryption detected.")
        algorithm = encryption.get("algorithm", "unknown")
        if algorithm == "AES-256":
            return self._breakdown("Encryption", 30, max_points, "strong", "AES-256 encryption detected.")
        if algorithm == "AES-128":
            return self._breakdown("Encryption", 25, max_points, "acceptable", "AES-128 encryption detected.")
        if algorithm == "RC4":
            findings.append(self._finding("HIGH", "Legacy encryption detected", "The PDF appears to use legacy RC4 encryption.", f"algorithm={algorithm}", "Re-encrypt using AES-256."))
            recommendations.append("Replace legacy encryption with AES-256.")
            return self._breakdown("Encryption", 10, max_points, "weak", "Legacy RC4 encryption detected.")
        return self._breakdown("Encryption", 18, max_points, "unknown", "PDF is encrypted, but the algorithm could not be determined.")

    def _score_permissions(self, permissions: Dict[str, Any], encryption: Dict[str, Any], findings: List[Dict[str, Any]], recommendations: List[str]) -> Dict[str, Any]:
        max_points = 20
        if any(value == "unknown" for value in permissions.values()):
            findings.append(self._finding("LOW", "Permissions unavailable", "PDF permissions could not be determined.", "permissions=unknown", "Provide the document password if required and re-run analysis."))
            return self._breakdown("Permissions", 0, max_points, "unknown", "Permission flags could not be determined.")
        if not encryption.get("encrypted"):
            recommendations.append("Restrict unnecessary copy, modification, and extraction permissions when protecting the PDF.")
            return self._breakdown("Permissions", 0, max_points, "unrestricted", "Permissions are not enforceable without PDF encryption.")

        weights = {
            "copying": 4,
            "content_extraction": 3,
            "modification": 4,
            "printing": 3,
            "annotations": 2,
            "form_filling": 1,
            "document_assembly": 2,
            "high_quality_printing": 1,
        }
        points = 0
        unrestricted = []
        for key, weight in weights.items():
            if permissions.get(key) is False:
                points += weight
            else:
                unrestricted.append(key)
        if unrestricted:
            findings.append(self._finding("MEDIUM", "Some permissions are unrestricted", "The PDF allows one or more actions that may not be necessary.", ", ".join(unrestricted), "Restrict permissions that are not required for the workflow."))
            recommendations.append("Review and restrict unnecessary PDF permissions.")
        status = "restricted" if points == max_points else "partial" if points > 0 else "unrestricted"
        return self._breakdown("Permissions", points, max_points, status, "Permission score is based on restricted PDF operations.")

    def _score_signature(self, signature: Dict[str, Any], findings: List[Dict[str, Any]], recommendations: List[str]) -> Dict[str, Any]:
        max_points = 20
        status = signature.get("validation_status")
        if status == "VALID":
            return self._breakdown("Digital Signature", 20, max_points, "valid", "Cryptographically valid signature detected.")
        if status == "INVALID":
            findings.append(self._finding("CRITICAL", "Invalid digital signature", "A detected digital signature failed validation.", "validation_status=INVALID", "Obtain a clean signed copy or re-sign after reviewing document changes."))
            recommendations.append("Review the invalid digital signature before trusting the document.")
            return self._breakdown("Digital Signature", 0, max_points, "invalid", "Digital signature validation failed.")
        if signature.get("present"):
            findings.append(self._finding("INFO", "Signature validation incomplete", "A signature is present, but full validation was unavailable or inconclusive.", f"validation_status={status}", "Validate with trusted certificates where required."))
            recommendations.append("Validate signatures against trusted certificate roots when authenticity matters.")
            return self._breakdown("Digital Signature", 8, max_points, "unknown", "Signature present, but validity could not be fully confirmed.")
        findings.append(self._finding("LOW", "No digital signature detected", "The PDF has no cryptographic signature.", "signature=not_present", "Use digital signatures when authenticity and change detection are required."))
        recommendations.append("Add a digital signature for high-trust workflows.")
        return self._breakdown("Digital Signature", 0, max_points, "not_present", "No digital signature detected.")

    def _score_active_content(self, active: Dict[str, Any], findings: List[Dict[str, Any]], recommendations: List[str]) -> Dict[str, Any]:
        max_points = 15
        points = max_points
        checks = [
            ("javascript", 5, "JavaScript detected", "The PDF contains JavaScript. It can be legitimate but increases attack surface.", "Review or remove JavaScript before sharing."),
            ("launch_actions", 4, "Launch action detected", "The PDF contains a launch action that may invoke external behavior.", "Remove launch actions unless explicitly required."),
            ("open_action", 2, "Open action detected", "The PDF contains an automatic open action.", "Review automatic actions before distribution."),
            ("embedded_files", 3, "Embedded files detected", "The PDF contains embedded files. This is not automatically malicious, but should be reviewed.", "Review embedded files and remove unnecessary attachments."),
            ("embedded_multimedia", 1, "Embedded multimedia detected", "The PDF contains rich media or multimedia objects.", "Review rich media requirements."),
        ]
        triggered = []
        for key, penalty, title, description, recommendation in checks:
            if active.get(key) is True:
                points -= penalty
                triggered.append(title)
                severity = "HIGH" if key == "launch_actions" else "MEDIUM"
                findings.append(self._finding(severity, title, description, f"{key}=true", recommendation))
                recommendations.append(recommendation)
        if active.get("uri_actions") is True:
            findings.append(self._finding("INFO", "External links detected", "The PDF contains URI links. Links are not inherently unsafe.", f"uri_count={active.get('uri_count')}", "Use Unsafe Link Detection for detailed URL risk analysis."))
        status = "clean" if not triggered else "warning"
        reason = "No risky active content indicators detected." if not triggered else "; ".join(triggered)
        return self._breakdown("Active Content", max(points, 0), max_points, status, reason)

    def _score_structure(self, structure: Dict[str, Any], metadata: Dict[str, Any], findings: List[Dict[str, Any]], recommendations: List[str]) -> Dict[str, Any]:
        max_points = 15
        points = 0
        if structure.get("parser_status") == "valid":
            points += 8
        else:
            findings.append(self._finding("CRITICAL", "PDF structure could not be safely parsed", "The PDF parser could not safely inspect the document.", "parser_status=invalid", "Repair or regenerate the PDF from a trusted source."))
        if structure.get("eof_marker_present"):
            points += 3
        else:
            findings.append(self._finding("MEDIUM", "EOF marker missing", "The PDF EOF marker was not found near the end of the file.", "eof_marker_present=false", "Review the PDF for corruption or incomplete transfer."))
        if metadata.get("author") or metadata.get("creator") or metadata.get("producer"):
            findings.append(self._finding("LOW", "Document metadata present", "Metadata can disclose authoring tool or origin information.", "metadata fields present", "Strip metadata before external sharing if confidentiality is required."))
            recommendations.append("Strip unnecessary metadata before sharing externally.")
            points += 2
        else:
            points += 4
        return self._breakdown("Document Security", points, max_points, "valid" if points >= 12 else "partial", "Parser, EOF marker, and metadata exposure checks.")

    @staticmethod
    def rating_for_score(score: int) -> str:
        if score >= 90:
            return "Excellent"
        if score >= 75:
            return "Good"
        if score >= 60:
            return "Moderate"
        if score >= 40:
            return "Weak"
        return "Poor"

    @staticmethod
    def _breakdown(category: str, points: int, max_points: int, status: str, reason: str) -> Dict[str, Any]:
        return {"category": category, "points": points, "max_points": max_points, "status": status, "reason": reason}

    @staticmethod
    def _finding(severity: str, title: str, description: str, evidence: str, recommendation: str) -> Dict[str, str]:
        return {
            "severity": severity,
            "title": title,
            "description": description,
            "evidence": evidence,
            "recommendation": recommendation,
        }

    @staticmethod
    def _read_limited(path: Path) -> bytes:
        with open(path, "rb") as handle:
            return handle.read(settings.MAX_UPLOAD_SIZE)

    @staticmethod
    def _version_from_header(header: str) -> Optional[str]:
        match = re.search(r"%PDF-(\d+\.\d+)", header or "")
        return match.group(1) if match else None

    def generate_report(self, result: Dict[str, Any]) -> bytes:
        doc = fitz.open()
        page = doc.new_page()
        y = 50

        def add(text: str, size: int = 10, bold: bool = False) -> None:
            nonlocal y, page
            page.insert_text((50, y), str(text)[:180], fontsize=size, fontname="hebo" if bold else "helv")
            y += size + 6
            if y > page.rect.height - 50:
                page = doc.new_page()
                y = 50

        add("PDF Security Score Report", 16, True)
        add(f"Filename: {result.get('filename')}")
        add(f"Analyzed At: {result.get('analyzed_at')}")
        add(f"Score: {result.get('score')} / {result.get('max_score')}")
        add(f"Rating: {result.get('rating')}")
        add("")
        add("Score Breakdown", 12, True)
        for item in result.get("breakdown", []):
            add(f"{item['category']}: {item['points']}/{item['max_points']} - {item['status']} - {item['reason']}")
        add("")
        add("Findings", 12, True)
        for finding in result.get("findings", []):
            add(f"{finding['severity']}: {finding['title']} - {finding['description']}")
            add(f"Recommendation: {finding['recommendation']}")
        add("")
        add("Recommendations", 12, True)
        for recommendation in result.get("recommendations", []):
            add(f"- {recommendation}")
        add("")
        add(result.get("disclaimer", DISCLAIMER))
        return doc.write()

    def _persist_result(self, result: Dict[str, Any], output_dir: str | Path | None) -> None:
        if output_dir is None:
            return
        out_dir = Path(output_dir)
        os.makedirs(out_dir, exist_ok=True)
        analysis_id = result["analysis_id"]
        result["result_url"] = f"/api/pdf/security/security-score/result/{analysis_id}"
        result["report_url"] = f"/api/pdf/security/security-score/report/{analysis_id}"
        (out_dir / f"{analysis_id}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (out_dir / f"{analysis_id}_report.pdf").write_bytes(self.generate_report(result))

    def load_result(self, output_dir: str | Path, analysis_id: str) -> Dict[str, Any]:
        path = Path(output_dir) / f"{analysis_id}.json"
        if not path.exists():
            raise ValueError("Security score result not found.")
        return json.loads(path.read_text(encoding="utf-8"))

    def report_path(self, output_dir: str | Path, analysis_id: str) -> Path:
        return Path(output_dir) / f"{analysis_id}_report.pdf"


security_score_service = SecurityScoreService()
