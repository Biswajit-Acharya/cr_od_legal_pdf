import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class AISensitiveDataDetectionService:
    def __init__(self):
        # 1. Personal Information
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'\b(?:\+?91[\-\s]?)?[789]\d{9}\b')  # Indian phone formats as primary focus
        
        # 2. Identification Information
        self.pan_pattern = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')
        self.aadhaar_pattern = re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b')
        self.passport_pattern = re.compile(r'\b[A-PR-WYa-pr-wy][1-9]\d\s?\d{4}[1-9]\b') # Standard Indian passport
        
        # 3. Financial Information
        # Naive Card Pattern: 13-19 digits, possibly with spaces or dashes
        self.card_pattern = re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|[25][1-7][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\d{3})\d{11})\b')
        self.ifsc_pattern = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b')
        self.upi_pattern = re.compile(r'\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b')
        self.bank_acc_pattern = re.compile(r'\b(?:account\s*no|a/c|acct)[\s.:\-#]*(\d{9,18})\b', re.IGNORECASE)

        # 4. Confidential Business Information
        self.confidential_keywords = [
            r'\bconfidential\b',
            r'\binternal use only\b',
            r'\bprivate & confidential\b',
            r'\brestricted\b',
            r'\bproprietary\b',
            r'\btrade secret\b'
        ]
        
        # 5. Credentials / Secret Information
        self.api_key_pattern = re.compile(r'(?:api_key|apikey|secret|token|password|passwd|pwd)[\s:=]*([a-zA-Z0-9\-_]{16,64})', re.IGNORECASE)
        self.aws_key_pattern = re.compile(r'\b(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\b')
        
    def _is_luhn_valid(self, num_str: str) -> bool:
        """Validate card-like strings using Luhn algorithm."""
        digits = [int(d) for d in num_str if d.isdigit()]
        if len(digits) < 13:
            return False
        checksum = 0
        reverse_digits = digits[::-1]
        for i, d in enumerate(reverse_digits):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10 == 0

    def _mask_value(self, value: str, category: str, type_str: str) -> str:
        """Mask sensitive values for response."""
        clean_val = value.strip()
        if not clean_val:
            return clean_val

        # Fully mask passwords/API keys
        if category == "Credentials & Secrets":
            return "*" * min(len(clean_val), 16)
            
        # Email: a***@domain.com
        if type_str == "Email Address":
            parts = clean_val.split('@')
            if len(parts) == 2:
                name = parts[0]
                if len(name) > 2:
                    return f"{name[0]}{'*' * (len(name)-2)}{name[-1]}@{parts[1]}"
                return f"**@{parts[1]}"
                
        # Card, Phone, Bank Acc, Aadhaar: Mask all except last 4
        if len(clean_val) > 4:
            return "*" * (len(clean_val) - 4) + clean_val[-4:]
            
        return "*" * len(clean_val)

    def _determine_severity(self, category: str, type_str: str) -> str:
        """Deterministic severity mapping."""
        if category == "Credentials & Secrets":
            return "CRITICAL"
        if category == "Financial Information" or category == "Identification Information":
            return "HIGH"
        if type_str == "Email Address" or type_str == "Phone Number":
            return "MEDIUM"
        return "LOW"

    def _detect_in_text(self, text: str, page_num: int, rect: Optional[List[float]] = None) -> List[Dict]:
        """Detect patterns in text and return preliminary findings."""
        findings = []
        
        # Helper to add finding
        def add_finding(category: str, t_type: str, match_val: str, conf: float):
            findings.append({
                "id": f"SDD-{uuid.uuid4().hex[:8].upper()}",
                "page": page_num,
                "category": category,
                "type": t_type,
                "original_value": match_val,
                "masked_value": self._mask_value(match_val, category, t_type),
                "confidence": conf,
                "severity": self._determine_severity(category, t_type),
                "bbox": {"x0": rect[0], "y0": rect[1], "x1": rect[2], "y1": rect[3]} if rect else None
            })

        # 1. Personal
        for m in self.email_pattern.finditer(text):
            add_finding("Personal Information", "Email Address", m.group(), 0.95)
        for m in self.phone_pattern.finditer(text):
            add_finding("Personal Information", "Phone Number", m.group(), 0.85)
            
        # 2. Identity
        for m in self.pan_pattern.finditer(text):
            add_finding("Identification Information", "PAN Number", m.group(), 0.95)
        for m in self.aadhaar_pattern.finditer(text):
            add_finding("Identification Information", "Aadhaar Number", m.group(), 0.95)
        for m in self.passport_pattern.finditer(text):
            add_finding("Identification Information", "Passport Number", m.group(), 0.80)
            
        # 3. Financial
        for m in self.card_pattern.finditer(text):
            val = m.group()
            if self._is_luhn_valid(val):
                add_finding("Financial Information", "Credit/Debit Card", val, 0.98)
        for m in self.ifsc_pattern.finditer(text):
            add_finding("Financial Information", "IFSC Code", m.group(), 0.90)
        for m in self.upi_pattern.finditer(text):
            val = m.group()
            if val.lower() not in text.lower(): # Basic check to distinguish from email
                 add_finding("Financial Information", "UPI ID", val, 0.85)
        for m in self.bank_acc_pattern.finditer(text):
            add_finding("Financial Information", "Bank Account Number", m.group(1), 0.90)

        # 4. Confidential Business (Case Insensitive)
        lower_text = text.lower()
        for kw in self.confidential_keywords:
            if re.search(kw, lower_text):
                add_finding("Business Confidential", "Confidential Indicator", kw.replace(r'\b', '').title(), 0.70)

        # 5. Credentials
        for m in self.aws_key_pattern.finditer(text):
            add_finding("Credentials & Secrets", "AWS Key", m.group(), 0.99)
        for m in self.api_key_pattern.finditer(text):
            add_finding("Credentials & Secrets", "API/Secret Key", m.group(1), 0.90)

        return findings

    def _merge_duplicates(self, detections: List[Dict]) -> List[Dict]:
        """Merge identical detections on the same page."""
        merged = {}
        for d in detections:
            key = (d['page'], d['category'], d['type'], d['original_value'])
            if key not in merged:
                merged[key] = d
            else:
                # Merge logic: if one has bbox and other doesn't, keep bbox. Keep highest confidence.
                existing = merged[key]
                if d['bbox'] and not existing['bbox']:
                    existing['bbox'] = d['bbox']
                existing['confidence'] = max(existing['confidence'], d['confidence'])
        
        # Convert back and remove original_value
        result = []
        for d in merged.values():
            d.pop('original_value', None)
            result.append(d)
        return result

    async def analyze_pdf(self, filepath: Path, original_filename: str, request_id: str) -> Dict[str, Any]:
        """Main entry point to perform sensitive data detection on a PDF."""
        logger.info(f"Starting AI Sensitive Data Detection for {original_filename} ({request_id})")
        
        all_detections = []
        total_pages = 0
        text_extraction_status = "full"
        
        if not filepath.exists():
            return {"success": False, "error": "File does not exist."}

        try:
            doc = fitz.open(filepath)
            total_pages = len(doc)
            
            if doc.is_encrypted:
                return {"success": False, "error": "Cannot analyze encrypted or password-protected PDF."}

            extracted_text_length = 0
            
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Extract text blocks with bbox
                blocks = page.get_text("blocks")
                
                for block in blocks:
                    # block: (x0, y0, x1, y1, text, block_no, block_type)
                    if len(block) >= 5 and block[6] == 0:  # block_type 0 is text
                        text = block[4].strip()
                        if not text:
                            continue
                            
                        extracted_text_length += len(text)
                        
                        rect = [block[0], block[1], block[2], block[3]]
                        page_findings = self._detect_in_text(text, page_num + 1, rect)
                        all_detections.extend(page_findings)
            
            doc.close()
            
            # Scanned / Image PDF Check (heuristic)
            if total_pages > 0 and extracted_text_length < total_pages * 50:
                text_extraction_status = "partial"

        except Exception as e:
            logger.error(f"Error during PDF sensitive data detection: {e}", exc_info=True)
            return {"success": False, "error": "Failed to parse document for sensitive data."}

        # Post-process detections
        final_detections = self._merge_duplicates(all_detections)
        
        # Summaries
        summary = {
            "personal_information": 0,
            "identification_information": 0,
            "financial_information": 0,
            "confidential_business_information": 0,
            "credentials_and_secrets": 0
        }
        
        risk_summary = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0
        }
        
        category_map = {
            "Personal Information": "personal_information",
            "Identification Information": "identification_information",
            "Financial Information": "financial_information",
            "Business Confidential": "confidential_business_information",
            "Credentials & Secrets": "credentials_and_secrets"
        }
        
        for d in final_detections:
            cat = category_map.get(d['category'])
            if cat:
                summary[cat] += 1
            risk_summary[d['severity'].lower()] += 1

        return {
            "success": True,
            "feature": "AI Sensitive Data Detection",
            "filename": original_filename,
            "total_pages": total_pages,
            "total_detections": len(final_detections),
            "text_extraction_status": text_extraction_status,
            "summary": summary,
            "risk_summary": risk_summary,
            "detections": final_detections
        }

ai_sensitive_data_detection_service = AISensitiveDataDetectionService()
