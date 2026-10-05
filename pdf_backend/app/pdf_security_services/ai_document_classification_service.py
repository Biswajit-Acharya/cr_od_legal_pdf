import logging
import re
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class AIDocumentClassificationService:
    def __init__(self):
        # Define categories and their strong keyword indicators
        self.categories = {
            "Invoice": [
                r"\binvoice\b", r"\binvoice no\b", r"\bbill to\b", r"\bamount due\b", 
                r"\btotal due\b", r"\bpayment terms\b", r"\bsubtotal\b", r"\btax\b", r"\bshipping\b"
            ],
            "Resume / CV": [
                r"\bresume\b", r"\bcurriculum vitae\b", r"\bexperience\b", r"\beducation\b", 
                r"\bskills\b", r"\breferences\b", r"\bemployment history\b", r"\bwork history\b"
            ],
            "Legal Document": [
                r"\bagreement\b", r"\bcontract\b", r"\bwitnesseth\b", r"\bhereinafter\b", 
                r"\bterms and conditions\b", r"\bparties\b", r"\bindemnification\b", r"\bjurisdiction\b"
            ],
            "Financial Document": [
                r"\bstatement\b", r"\bbank statement\b", r"\bbalance\b", r"\bdeposit\b", 
                r"\bwithdrawal\b", r"\baccount summary\b", r"\btransactions\b", r"\bfunds\b"
            ],
            "Identity Document": [
                r"\bpassport\b", r"\baadhaar\b", r"\bdriving licence\b", r"\bpan card\b", 
                r"\bidentity card\b", r"\bdate of birth\b", r"\bnationality\b", r"\bgender\b"
            ],
            "Medical Document": [
                r"\bpatient\b", r"\bdiagnosis\b", r"\btreatment\b", r"\bprescription\b", 
                r"\bmedical history\b", r"\bdoctor\b", r"\bsymptoms\b", r"\bclinic\b"
            ],
            "Educational Document": [
                r"\btranscript\b", r"\bdiploma\b", r"\bcertificate\b", r"\bdegree\b", 
                r"\buniversity\b", r"\bcollege\b", r"\bgrades\b", r"\bsemester\b"
            ],
            "Technical Document": [
                r"\bspecification\b", r"\barchitecture\b", r"\bdiagram\b", r"\bdocumentation\b", 
                r"\bsystem requirements\b", r"\bimplementation\b", r"\bdeployment\b"
            ],
            "Tax Document": [
                r"\btax return\b", r"\bincome tax\b", r"\btaxable\b", r"\bdeductions\b", 
                r"\bform 16\b", r"\bw-2\b", r"\bassessment\b"
            ]
        }

        # Pre-compile regexes for performance
        self.compiled_patterns = {
            cat: [re.compile(kw, re.IGNORECASE) for kw in keywords]
            for cat, keywords in self.categories.items()
        }

    def _classify_text(self, text: str) -> Dict[str, Any]:
        """Classify the text and return a category, confidence, and reasoning."""
        if not text.strip():
            return {
                "category": "Unknown",
                "confidence": 0.0,
                "secondary_categories": [],
                "reason": "Insufficient text content for classification."
            }

        scores = defaultdict(float)
        matched_keywords = defaultdict(list)

        # Cap text length to avoid performance issues on massive documents
        analyze_text = text[:50000] 

        # Score categories based on keyword frequency
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(analyze_text)
                if matches:
                    weight = 1.0
                    # Title heuristic: if a keyword is in the very first few lines, boost it
                    if pattern.search(analyze_text[:500]):
                        weight += 2.0
                        
                    scores[category] += (len(matches) * weight)
                    if pattern.pattern not in matched_keywords[category]:
                        matched_keywords[category].append(pattern.pattern.replace(r'\b', ''))

        if not scores:
            return {
                "category": "Other / Unknown",
                "confidence": 0.3,
                "secondary_categories": [],
                "reason": "No clear document patterns matched known categories."
            }

        # Normalize scores to find confidence
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_category, top_score = sorted_scores[0]
        
        total_score = sum(scores.values())
        
        # Calculate a pseudo-confidence score (capped at 0.98)
        base_confidence = min(0.98, top_score / (top_score + 10))
        ratio = top_score / total_score if total_score > 0 else 0
        final_confidence = min(0.98, (base_confidence + ratio) / 2)

        # Determine secondary categories
        secondary = []
        if len(sorted_scores) > 1:
            for cat, score in sorted_scores[1:3]:
                if score >= top_score * 0.3:
                    secondary.append(cat)

        # Build reasoning
        kws = ", ".join(matched_keywords[top_category][:5])
        reason = f"Document structure matches '{top_category}' indicators. Found key terminology such as: {kws}."

        return {
            "category": top_category,
            "confidence": round(final_confidence, 2),
            "secondary_categories": secondary,
            "reason": reason
        }

    async def classify_pdf(self, filepath: Path, original_filename: str, request_id: str) -> Dict[str, Any]:
        """Main entry point to perform document classification on a PDF."""
        logger.info(f"Starting AI Document Classification for {original_filename} ({request_id})")
        
        if not filepath.exists():
            return {"success": False, "error": "File does not exist."}

        total_pages = 0
        extracted_text = []
        text_extraction_status = "full"

        try:
            doc = fitz.open(filepath)
            total_pages = len(doc)
            
            if doc.is_encrypted:
                return {"success": False, "error": "Cannot analyze encrypted or password-protected PDF."}

            for page_num in range(min(total_pages, 20)): # Only analyze first 20 pages for classification
                page = doc[page_num]
                text = page.get_text("text").strip()
                if text:
                    extracted_text.append(text)
            
            doc.close()
            
            full_text = "\n".join(extracted_text)
            
            # Check for scanned / image-only PDFs
            if total_pages > 0 and len(full_text) < total_pages * 50:
                text_extraction_status = "partial"
                if len(full_text) < 50:
                     return {
                        "success": True,
                        "category": "Unknown (Requires OCR)",
                        "confidence": 0.0,
                        "secondary_categories": [],
                        "reason": "The document contains insufficient extractable text (likely a scanned image). OCR processing is required before classification.",
                        "filename": original_filename,
                        "total_pages": total_pages,
                        "processing_status": "insufficient_text"
                    }

        except Exception as e:
            logger.error(f"Error during PDF classification extraction: {e}", exc_info=True)
            return {"success": False, "error": "Failed to parse document structure."}

        # Perform Classification
        classification_result = self._classify_text(full_text)
        
        return {
            "success": True,
            "filename": original_filename,
            "total_pages": total_pages,
            "category": classification_result["category"],
            "confidence": classification_result["confidence"],
            "secondary_categories": classification_result["secondary_categories"],
            "reason": classification_result["reason"],
            "processing_status": "completed",
            "text_extraction_status": text_extraction_status
        }

ai_document_classification_service = AIDocumentClassificationService()
