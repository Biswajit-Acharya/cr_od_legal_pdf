import fitz
import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

class PDFForensicAnalysisService:
    def __init__(self):
        pass

    def _calculate_sha256(self, filepath: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    async def analyze(self, filepath: Path, original_filename: str) -> Dict[str, Any]:
        """Performs a detailed static forensic examination of the uploaded PDF."""
        if not filepath.exists():
            return {"success": False, "error": "File not found."}

        try:
            doc_hash = self._calculate_sha256(filepath)
            
            doc = fitz.open(filepath)
            
            try:
                reader = PdfReader(filepath)
                pdf_version = reader.pdf_header or "Unknown"
            except:
                pdf_version = "Unknown"
                
            file_size = os.path.getsize(filepath)
            page_count = doc.page_count
            is_encrypted = doc.is_encrypted
            
            findings = []
            
            if is_encrypted:
                findings.append({
                    "severity": "INFO",
                    "finding": "Document is encrypted",
                    "description": "The PDF relies on encryption or password protection.",
                    "evidence": "Encryption detected",
                    "recommendation": "Ensure encryption complies with policy."
                })

            # Check forms and signatures
            forms_count = 0
            is_signed = False
            if doc.is_form_pdf:
                for page in doc:
                    for widget in page.widgets():
                        forms_count += 1
                        if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                            is_signed = True
            
            if is_signed:
                findings.append({
                    "severity": "INFO",
                    "finding": "Digital Signature detected",
                    "description": "The document contains cryptographic signatures.",
                    "evidence": "PDF_WIDGET_TYPE_SIGNATURE",
                    "recommendation": "Verify signature validity independently."
                })
            
            # Check Metadata
            meta = doc.metadata
            creation_date = meta.get("creationDate", "")
            mod_date = meta.get("modDate", "")
            producer = meta.get("producer", "")
            creator = meta.get("creator", "")
            
            if creation_date and mod_date and creation_date != mod_date:
                findings.append({
                    "severity": "INFO",
                    "finding": "Document metadata contains modification information",
                    "description": "The document has been modified since its original creation.",
                    "evidence": f"Creation: {creation_date} | Mod: {mod_date}",
                    "recommendation": "Review modification history if authenticity is critical."
                })

            # Check XMP
            xml_meta = doc.get_xml_metadata()
            if xml_meta and xml_meta.strip():
                findings.append({
                    "severity": "INFO",
                    "finding": "XMP Metadata present",
                    "description": "Extended XML metadata is embedded in the document.",
                    "evidence": "doc.get_xml_metadata() returned data",
                    "recommendation": "No action required unless sanitization is needed."
                })

            # Structural & Active Content Scans
            has_js = False
            has_open_action = False
            suspicious_actions = 0
            
            try:
                catalog_xref = doc.pdf_catalog()
                catalog = doc.xref_object(catalog_xref)
                
                if "/OpenAction" in catalog:
                    has_open_action = True
                    findings.append({
                        "severity": "WARNING",
                        "finding": "OpenAction detected",
                        "description": "The document specifies an action to be performed automatically when opened.",
                        "evidence": "/OpenAction in catalog",
                        "recommendation": "Review the action; it could be used maliciously."
                    })
            except Exception:
                pass
                
            # Scan all xrefs for suspicious keywords
            xref_count = doc.xref_length()
            for xref in range(1, xref_count):
                try:
                    obj_text = doc.xref_object(xref)
                    if not obj_text: continue
                    
                    if "/JS" in obj_text or "/JavaScript" in obj_text:
                        has_js = True
                    if "/Launch" in obj_text or "/SubmitForm" in obj_text or "/ImportData" in obj_text:
                        suspicious_actions += 1
                except:
                    continue
                    
            if has_js:
                findings.append({
                    "severity": "WARNING",
                    "finding": "JavaScript detected — requires review",
                    "description": "The document contains embedded JavaScript.",
                    "evidence": "/JS or /JavaScript found in object streams",
                    "recommendation": "Review embedded scripts. Do not execute untrusted JavaScript."
                })
                
            if suspicious_actions > 0:
                findings.append({
                    "severity": "HIGH RISK",
                    "finding": f"Suspicious action objects detected ({suspicious_actions})",
                    "description": "Actions such as /Launch or /SubmitForm were found.",
                    "evidence": "Suspicious dictionary keys found",
                    "recommendation": "Disable automatic action execution in PDF viewers."
                })

            # Check embedded files
            emb_count = doc.embfile_count()
            if emb_count > 0:
                findings.append({
                    "severity": "WARNING",
                    "finding": "Embedded file detected — requires inspection",
                    "description": f"The document contains {emb_count} embedded attachments.",
                    "evidence": f"{emb_count} embedded files found",
                    "recommendation": "Do not open unknown attachments without scanning."
                })
                
            doc.close()
            
            # Determine overall status
            overall_status = "Pass"
            for f in findings:
                if f["severity"] == "CRITICAL" or f["severity"] == "HIGH RISK":
                    overall_status = "Review Required (High Risk)"
                    break
                elif f["severity"] == "WARNING":
                    if overall_status == "Pass":
                        overall_status = "Review Required"

            # Always output a baseline authenticity warning per rules
            findings.append({
                "severity": "INFO",
                "finding": "Authenticity Assessment",
                "description": "Authenticity cannot be conclusively established through static PDF analysis alone.",
                "evidence": "Static limitation",
                "recommendation": "Use digital signatures for non-repudiation."
            })

            return {
                "success": True,
                "status": "completed",
                "overall_status": overall_status,
                "document_info": {
                    "File Name": original_filename,
                    "File Size": f"{(file_size / 1024):.2f} KB",
                    "Page Count": page_count,
                    "PDF Version": pdf_version,
                    "Creation Date": creation_date or "Not Available",
                    "Modification Date": mod_date or "Not Available",
                    "Producer": producer or "Not Available",
                    "Creator": creator or "Not Available",
                    "Encryption Status": "Encrypted" if is_encrypted else "Unencrypted",
                    "SHA-256 Hash": doc_hash,
                    "Indirect Objects": xref_count
                },
                "forensic_checks": [
                    {"check": "Metadata analyzed", "status": "Checked"},
                    {"check": "Document structure analyzed", "status": "Checked"},
                    {"check": "Objects analyzed", "status": "Checked"},
                    {"check": "Suspicious objects detected" if suspicious_actions > 0 else "No suspicious objects", "status": "Flagged" if suspicious_actions > 0 else "Clean"},
                    {"check": "JavaScript checked", "status": "Flagged" if has_js else "Clean"},
                    {"check": "Embedded files checked", "status": "Flagged" if emb_count > 0 else "Clean"},
                    {"check": "Annotations/Forms checked", "status": "Flagged" if forms_count > 0 else "Clean"}
                ],
                "findings": findings
            }

        except Exception as e:
            logger.error(f"Error in forensic analysis: {e}", exc_info=True)
            return {"success": False, "error": f"Unable to analyze this PDF because the document is corrupted or uses an unsupported structure. Details: {str(e)}"}

pdf_forensic_analysis_service = PDFForensicAnalysisService()
