import logging
import fitz
import uuid
from pathlib import Path
from typing import Dict, Any, List

from app.pdf_security_services.malware_scan_service import malware_scan_service
from app.pdf_security_services.unsafe_link_detection_service import unsafe_link_detection_service
from app.pdf_security_services.digital_signature_verification_service import digital_signature_verification_service
from app.core.paths import Paths

logger = logging.getLogger(__name__)

class AISecurityRiskDetectionService:
    def __init__(self):
        pass

    async def analyze_pdf(self, filepath: Path, original_filename: str, request_id: str) -> Dict[str, Any]:
        """
        Analyze a PDF for security risks using deterministic checks combined with
        existing malware and link scanning services.
        """
        if not filepath.exists():
            return {"success": False, "error": "File not found."}
            
        findings: List[Dict[str, Any]] = []
        score = 0
        
        # Initialize Security Checks tracking
        checks = {
            "javascript": {"status": "not_checked"},
            "external_links": {"status": "not_checked"},
            "embedded_files": {"status": "not_checked"},
            "launch_actions": {"status": "not_checked"},
            "forms": {"status": "not_checked"},
            "encryption": {"status": "not_checked"},
            "digital_signature": {"status": "not_checked"},
            "metadata": {"status": "not_checked"}
        }

        # 1. Deterministic Structural Checks via PyMuPDF
        try:
            doc = fitz.open(filepath)
            
            # --- Encryption ---
            if doc.is_encrypted:
                checks["encryption"] = {"status": "enabled", "details": "PDF is encrypted"}
                score += 0 # Encryption itself isn't a risk, but limits analysis
                findings.append({
                    "category": "Encryption",
                    "severity": "INFORMATIONAL",
                    "title": "Encryption Enabled",
                    "description": "The PDF is protected with encryption.",
                    "evidence": "PDF encryption dictionary present.",
                    "recommendation": "Ensure you have the necessary permissions or passwords."
                })
            else:
                checks["encryption"] = {"status": "not_enabled", "details": "PDF is not encrypted"}
                
            # If not encrypted, we can do deeper structural checks
            if not doc.is_encrypted:
                # --- Metadata ---
                meta = doc.metadata
                has_meta = False
                found_meta = []
                for key in ["author", "creator", "producer", "title", "subject"]:
                    if meta.get(key) and meta.get(key) != "Unknown":
                        has_meta = True
                        found_meta.append(key)
                if has_meta:
                    checks["metadata"] = {"status": "present", "fields_detected": len(found_meta), "details": f"Fields found: {', '.join(found_meta)}"}
                    findings.append({
                        "category": "Metadata",
                        "severity": "INFORMATIONAL",
                        "title": "Metadata Found",
                        "description": "The PDF contains document metadata.",
                        "evidence": f"Found {len(found_meta)} populated metadata fields.",
                        "recommendation": "Remove unnecessary metadata before publicly sharing the document."
                    })
                else:
                    checks["metadata"] = {"status": "not_present", "details": "No significant metadata found"}

                # --- Forms ---
                if doc.is_form_pdf:
                    checks["forms"] = {"status": "detected", "details": "Interactive forms detected"}
                    score += 10
                    findings.append({
                        "category": "Forms",
                        "severity": "LOW",
                        "title": "Interactive Forms Detected",
                        "description": "The PDF contains interactive form fields.",
                        "evidence": "Form fields detected in document structure.",
                        "recommendation": "Interactive elements should be reviewed."
                    })
                else:
                    checks["forms"] = {"status": "not_detected", "details": "No interactive forms detected"}

                # --- Deep Object Inspection (JS, Embedded, Launch) ---
                js_detected = False
                embedded_detected = False
                launch_detected = False
                
                try:
                    # Check Catalog Names dictionary for JS and EmbeddedFiles
                    catalog = doc.xref_get_key(doc.pdf_catalog(), "Names")
                    if catalog[0] != "null":
                        names_obj = catalog[1]
                        if "JavaScript" in doc.xref_object(int(names_obj.split()[0])):
                            js_detected = True
                        if "EmbeddedFiles" in doc.xref_object(int(names_obj.split()[0])):
                            embedded_detected = True
                except:
                    pass

                # Check pages for annotations and actions
                for page in doc:
                    links = page.get_links()
                    for link in links:
                        kind = link.get("kind")
                        if kind == fitz.LINK_LAUNCH:
                            launch_detected = True
                        elif kind == fitz.LINK_JAVASCRIPT:
                            js_detected = True
                            
                # Check document level OpenAction
                try:
                    open_action = doc.xref_get_key(doc.pdf_catalog(), "OpenAction")
                    if open_action[0] != "null":
                        # Simplistic check, if OpenAction exists, we consider it a potential action. 
                        # To be precise, we'd have to parse the action dict, but presence is enough to flag for review.
                        launch_detected = True 
                except:
                    pass

                # Update JS Check
                if js_detected:
                    checks["javascript"] = {"status": "detected", "details": "JavaScript detected in document structure"}
                    score += 40
                    findings.append({
                        "category": "JavaScript",
                        "severity": "HIGH",
                        "title": "JavaScript Detected",
                        "description": "The PDF contains embedded JavaScript.",
                        "evidence": "Found /JS or JavaScript link actions.",
                        "recommendation": "Disable JavaScript in your PDF reader before opening."
                    })
                else:
                    checks["javascript"] = {"status": "not_detected", "details": "No JavaScript detected"}

                # Update Embedded Check
                if embedded_detected:
                    checks["embedded_files"] = {"status": "detected", "details": "Embedded files detected in document"}
                    score += 20
                    findings.append({
                        "category": "Embedded Content",
                        "severity": "MEDIUM",
                        "title": "Embedded Files Detected",
                        "description": "The PDF contains embedded attachments.",
                        "evidence": "Found /EmbeddedFiles structural entry.",
                        "recommendation": "Do not open or execute attachments found inside this PDF."
                    })
                else:
                    checks["embedded_files"] = {"status": "not_detected", "details": "No embedded files detected"}

                # Update Launch Check
                if launch_detected:
                    checks["launch_actions"] = {"status": "detected", "details": "Automatic or launch actions detected"}
                    score += 80
                    findings.append({
                        "category": "Action",
                        "severity": "CRITICAL",
                        "title": "Launch Action Detected",
                        "description": "The PDF attempts to launch an external application or contains automatic actions.",
                        "evidence": "Found /Launch or /OpenAction entries.",
                        "recommendation": "Do not open this file. It exhibits highly suspicious behavior."
                    })
                else:
                    checks["launch_actions"] = {"status": "not_detected", "details": "No launch actions detected"}

            else:
                # If encrypted, we can't reliably check JS, Embedded, Launch, Forms, Meta
                checks["metadata"] = {"status": "unable_to_check", "details": "PDF is encrypted"}
                checks["forms"] = {"status": "unable_to_check", "details": "PDF is encrypted"}
                checks["javascript"] = {"status": "unable_to_check", "details": "PDF is encrypted"}
                checks["embedded_files"] = {"status": "unable_to_check", "details": "PDF is encrypted"}
                checks["launch_actions"] = {"status": "unable_to_check", "details": "PDF is encrypted"}
                
            doc.close()
        except Exception as e:
            logger.error(f"Error extracting document info: {e}")
            checks["metadata"] = {"status": "unable_to_check"}
            checks["forms"] = {"status": "unable_to_check"}
            checks["encryption"] = {"status": "unable_to_check"}
            checks["javascript"] = {"status": "unable_to_check"}
            checks["embedded_files"] = {"status": "unable_to_check"}
            checks["launch_actions"] = {"status": "unable_to_check"}
            score += 20
            findings.append({
                "category": "Structure",
                "severity": "MEDIUM",
                "title": "PDF Structure Anomalies",
                "description": "The PDF structure is malformed or could not be fully parsed.",
                "evidence": str(e),
                "recommendation": "PDF structure requires review as it may be corrupted."
            })

        # 2. Run Malware Scan (Existing Service) - Supplemental
        malware_result = await malware_scan_service.scan_pdf(filepath, request_id, original_filename)
        malware_status = malware_result.get("final_security_status", "UNKNOWN")
        clamav_data = malware_result.get("clamav", {})
        
        if malware_status == "MALICIOUS":
            score += 100
            findings.append({
                "category": "Malware",
                "severity": "CRITICAL",
                "title": "Malware Detected",
                "description": f"The antivirus engine detected a threat: {clamav_data.get('detection', 'Unknown')}",
                "evidence": "ClamAV engine detection",
                "recommendation": "Do NOT open this file on your system. Delete it immediately."
            })

        # 3. External Links Check
        try:
            link_result = unsafe_link_detection_service.scan_pdf_links(filepath)
            stats = link_result.get("stats", {})
            total_links = stats.get("total", 0)
            
            if total_links > 0:
                checks["external_links"] = {"status": "detected", "count": total_links, "details": f"{total_links} external links detected"}
                if stats.get("high_risk", 0) > 0 or stats.get("dangerous_scheme", 0) > 0:
                    score += 60
                    findings.append({
                        "category": "Hyperlinks",
                        "severity": "HIGH",
                        "title": "Dangerous Links Detected",
                        "description": "The PDF contains links with dangerous schemes or high-risk domains.",
                        "evidence": f"High risk links found.",
                        "recommendation": "Do not click on any links inside this document."
                    })
                elif stats.get("suspicious", 0) > 0:
                    score += 20
                    findings.append({
                        "category": "Hyperlinks",
                        "severity": "MEDIUM",
                        "title": "Suspicious Links Detected",
                        "description": "The PDF contains suspicious or uncommon links.",
                        "evidence": "Suspicious links found.",
                        "recommendation": "Exercise caution and verify destinations before clicking links."
                    })
            else:
                checks["external_links"] = {"status": "not_detected", "count": 0, "details": "No external links detected"}
        except Exception as e:
            logger.error(f"Error analyzing links: {e}")
            checks["external_links"] = {"status": "unable_to_check", "details": "Failed to analyze links"}
            
        # 4. Digital Signature Check
        try:
            signatures = digital_signature_verification_service.detect_signatures(filepath)
            if signatures:
                checks["digital_signature"] = {"status": "present", "count": len(signatures), "details": f"{len(signatures)} digital signature(s) detected"}
                findings.append({
                    "category": "Digital Signature",
                    "severity": "INFORMATIONAL",
                    "title": "Digital Signature Detected",
                    "description": f"The PDF contains {len(signatures)} digital signature(s).",
                    "evidence": "Signature entries found.",
                    "recommendation": "Verify signature validity using the Digital Signature Verification tool."
                })
            else:
                checks["digital_signature"] = {"status": "not_present", "details": "No digital signatures found"}
        except Exception as e:
            logger.error(f"Error detecting signatures: {e}")
            checks["digital_signature"] = {"status": "unable_to_check", "details": "Failed to parse signatures"}

        # 6. Determine Overall Risk
        score = min(score, 100)
        overall_risk = "Low Risk"
        if score >= 80:
            overall_risk = "Critical Risk"
        elif score >= 50:
            overall_risk = "High Risk"
        elif score >= 20:
            overall_risk = "Moderate Risk"
            
        if len(findings) == 0:
             findings.append({
                "category": "General",
                "severity": "LOW",
                "title": "No Obvious Threats",
                "description": "No significant security risks were detected.",
                "evidence": "Static analysis completed cleanly.",
                "recommendation": "Document appears generally safe."
            })

        # Return structured format
        return {
            "success": True,
            "filename": original_filename,
            "analysis_mode": "deterministic_security_analysis",
            "overall_risk": overall_risk,
            "risk_score": score,
            "summary": "Security analysis completed successfully.",
            "findings": findings,
            "security_checks": checks,
            "recommendations": [
                {
                    "title": f["title"],
                    "priority": f["severity"].lower(),
                    "description": f["description"],
                    "impact": f["category"] + " Security",
                    "implementation": f["recommendation"]
                } for f in findings if f.get("recommendation")
            ]
        }

ai_security_risk_detection_service = AISecurityRiskDetectionService()
