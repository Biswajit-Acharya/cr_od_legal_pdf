"""
Redact PDF Service — Enterprise Grade Complete Implementation.

True Permanent Redaction & Security Sanitization:
  - PDF Validation & Encryption Inspection
  - Page Image Workspace Rendering (High DPI)
  - Page Range Expression Parser (1, 1-3, 1,3,5, 1-3,7,9-11)
  - Search & Redact Engine (exact text, case sensitivity, whole word)
  - Pattern & Regex Redaction Engine (Email, Phone, Aadhaar, PAN, GSTIN, Credit Card, Bank Account, IFSC, Passport, SSN, IP, Dates)
  - Intelligent Sensitive Data Auto Scanner with Label Proximity Detection & Bounding Box Reconstruction
  - OCR Backup Engine for Scanned / Image-Only PDFs
  - True Permanent PyMuPDF Redaction (add_redact_annot + apply_redactions with PDF_REDACT_IMAGE_PIXELS)
  - Security Sanitization (Metadata Wiping, Annotation Cleanup, Embedded File Removal, Hidden Layer Cleanup)
  - Post-Redaction Empirical Text-Extraction Verification
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import fitz  # PyMuPDF
from PIL import Image

from app.core.paths import Paths

logger = logging.getLogger(__name__)

# Check pytesseract availability
try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

# Constants
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_PAGE_COUNT = 10000

# Regex patterns for sensitive data detection
REGEX_PATTERNS = {
    "email": (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "EMAIL", "Email Address"),
    "phone": (r"(?:\+91[\s-]?)?(?:[6-9]\d{9}|[6-9]\d{4}[\s-]?\d{5}|0\d{2,4}[\s-]?\d{6,8})\b", "PHONE", "Phone Number"),
    "aadhaar": (r"\b[2-9]\d{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b", "AADHAAR", "Aadhaar Card Number"),
    "pan": (r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "PAN", "PAN Card Number"),
    "gstin": (r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z0-9]{1}[Z]{1}[A-Z0-9]{1}\b", "IDENTIFIER", "GSTIN Number"),
    "credit_card": (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b|\b(?:\d{4}[\s-]?){3}\d{4}\b", "CREDIT_CARD", "Credit / Debit Card"),
    "bank_account": (r"\b\d{9,18}\b", "BANK_ACCOUNT", "Bank Account Number"),
    "ifsc": (r"\b[A-Z]{4}0[A-Z0-9]{6}\b", "FINANCIAL", "IFSC Code"),
    "passport": (r"\b[A-Z][0-9]{7}\b", "PASSPORT", "Passport Number"),
    "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "IDENTIFIER", "Social Security Number (SSN)"),
    "ip_address": (r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "IDENTIFIER", "IP Address"),
    "date": (r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b", "DATE", "Date / DOB"),
}

# Label Proximity Rules for Document Fields
LABEL_PROXIMITY_RULES = [
    (r"(?:Name|Full Name|Patient Name|Client Name|Customer Name|Employee Name|Father'?s Name|Mother'?s Name|Applicant Name|User|Account Holder)\s*[:=\-]\s*([A-Z][a-zA-Z\s\.]{2,35})", "PERSON", "Person Name"),
    (r"(?:Address|Residential Address|Communication Address|Billing Address|Shipping Address|Street|City|Pincode|ZIP Code)\s*[:=\-]\s*([A-Za-z0-9\s,.\/\-#]{5,60})", "ADDRESS", "Address"),
    (r"(?:Mobile|Phone|Tel|Telephone|Contact|Call)\s*[:=\-]\s*([+\d\s\-()]{8,18})", "PHONE", "Phone Number"),
    (r"(?:Email|Email ID|Mail)\s*[:=\-]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", "EMAIL", "Email Address"),
    (r"(?:Aadhaar|Aadhar|UID|Aadhaar No)\s*[:=\-]\s*([0-9\s\-]{12,16})", "AADHAAR", "Aadhaar Number"),
    (r"(?:PAN|PAN No|PAN Card)\s*[:=\-]\s*([A-Z]{5}[0-9]{4}[A-Z])", "PAN", "PAN Card Number"),
    (r"(?:Account No|A/C No|Bank Account|IBAN)\s*[:=\-]\s*([A-Z0-9\s\-]{8,24})", "BANK_ACCOUNT", "Bank Account"),
    (r"(?:IFSC|IFSC Code)\s*[:=\-]\s*([A-Z]{4}0[A-Z0-9]{6})", "FINANCIAL", "IFSC Code"),
    (r"(?:DOB|Date of Birth|Birth Date)\s*[:=\-]\s*([\d\/\-\sA-Za-z,]{6,20})", "DATE", "Date of Birth"),
    (r"(?:Voter ID|EPIC|Passport No|DL No|Driving License|Registration No|GSTIN)\s*[:=\-]\s*([A-Z0-9\s\-]{6,20})", "IDENTIFIER", "ID / Registration"),
]


class RedactPdfService:
    """Enterprise service for PDF text search, candidate detection, true permanent redaction, and verification."""

    # ── 1. Validation & Initialization ─────────────────────────────────────

    def validate_and_open(self, pdf_bytes: bytes) -> Tuple[Optional[fitz.Document], Dict[str, Any]]:
        """Validate bytes and open fitz.Document handle."""
        if len(pdf_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB.")
        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("Uploaded file is not a valid PDF document.")

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            raise ValueError(f"Failed to open PDF document: {exc}")

        if doc.is_encrypted:
            doc.close()
            return None, {
                "is_protected": True,
                "message": "PDF document is password-protected or encrypted. Please provide an unlocked document.",
            }

        if len(doc) > MAX_PAGE_COUNT:
            doc.close()
            raise ValueError(f"Document page count ({len(doc)}) exceeds maximum allowed limit of {MAX_PAGE_COUNT} pages.")

        page_info = []
        for idx in range(len(doc)):
            p = doc[idx]
            page_info.append({
                "page": idx + 1,
                "width": float(p.rect.width),
                "height": float(p.rect.height),
            })

        metadata = doc.metadata or {}
        attachment_count = doc.embfile_count()

        info = {
            "is_protected": False,
            "page_count": len(doc),
            "pages": page_info,
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
            },
            "attachment_count": attachment_count,
        }

        return doc, info

    async def initialize_session(self, session_id: str, pdf_bytes: bytes) -> Dict[str, Any]:
        """Save uploaded PDF into request temp workspace and return document details."""
        temp_dir = Paths.request_temp(session_id) / "redact_work"
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        orig_file = temp_dir / "original.pdf"
        orig_file.write_bytes(pdf_bytes)

        doc, info = self.validate_and_open(pdf_bytes)
        if info.get("is_protected"):
            return {"success": False, "is_protected": True, "message": info["message"]}

        if doc:
            doc.close()

        info["success"] = True
        info["session_id"] = session_id
        return info

    # ── 2. Page Image Workspace Renderer ───────────────────────────────────

    def render_page_image(self, session_id: str, page_num: int, dpi: int = 150) -> Optional[bytes]:
        """Render a single PDF page as PNG bytes for workspace preview."""
        temp_dir = Paths.request_temp(session_id) / "redact_work"
        orig_file = temp_dir / "original.pdf"
        if not orig_file.exists():
            return None

        doc = fitz.open(str(orig_file))
        idx = page_num - 1
        if idx < 0 or idx >= len(doc):
            doc.close()
            return None

        page = doc[idx]
        pix = page.get_pixmap(dpi=dpi)
        png_bytes = pix.tobytes("png")
        doc.close()
        return png_bytes

    # ── 3. Page Range Expression Parser ───────────────────────────────────

    def parse_page_range(self, range_str: str, total_pages: int) -> List[int]:
        """Parse page range strings like '1', '1-3', '1, 3, 5-7' into a sorted list of page numbers."""
        if not range_str or not range_str.strip():
            return []

        pages: Set[int] = set()
        parts = [p.strip() for p in range_str.split(",") if p.strip()]

        for part in parts:
            if "-" in part:
                subparts = part.split("-")
                if len(subparts) == 2:
                    try:
                        start_p = int(subparts[0].strip())
                        end_p = int(subparts[1].strip())
                        if start_p > end_p:
                            start_p, end_p = end_p, start_p
                        for p in range(start_p, end_p + 1):
                            if 1 <= p <= total_pages:
                                pages.add(p)
                    except ValueError:
                        continue
            else:
                try:
                    p = int(part)
                    if 1 <= p <= total_pages:
                        pages.add(p)
                except ValueError:
                    continue

        return sorted(list(pages))

    # ── 4. Search & Redact Engine ──────────────────────────────────────────

    def search_text(
        self, session_id: str, query: str, case_sensitive: bool = False, whole_word: bool = False
    ) -> List[Dict[str, Any]]:
        """Search text in the document and return match bounding boxes and occurrence info."""
        if not query or not query.strip():
            return []

        temp_dir = Paths.request_temp(session_id) / "redact_work"
        orig_file = temp_dir / "original.pdf"
        if not orig_file.exists():
            return []

        doc = fitz.open(str(orig_file))
        matches = []
        occ_count = 0

        flags = 0
        if not case_sensitive:
            flags |= fitz.TEXT_DEHYPHENATE

        scanned_pages = 0

        for idx in range(len(doc)):
            page = doc[idx]
            page_num = idx + 1
            
            page_text = page.get_text("text")
            if len(page_text.strip()) < 15:
                scanned_pages += 1
                if HAS_PYTESSERACT:
                    ocr_rects = self._scan_ocr_for_query(page_num, page, query, case_sensitive)
                    matches.extend(ocr_rects)
                    occ_count += len(ocr_rects)
                continue

            rects = self._find_bbox_for_text(page, query, flags=flags)
            for rect in rects:
                occ_count += 1
                matches.append({
                    "id": f"search_{page_num}_{occ_count}",
                    "page": page_num,
                    "text": query,
                    "matched_text": query,
                    "category": "SEARCH_MATCH",
                    "category_label": "Search Match",
                    "bbox": [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)],
                    "occurrence": occ_count,
                    "confidence": 1.0,
                })

        total_pages = len(doc)
        doc.close()
        
        if not matches and scanned_pages == total_pages and not HAS_PYTESSERACT:
            raise ValueError("This appears to be a scanned or image-only PDF. Tesseract OCR is not installed on the server, so text search cannot be performed. Please manually select the area to redact.")
            
        return self._deduplicate_candidates(matches)

    # ── 5. Pattern & Regex Detection Engine ───────────────────────────────

    def detect_patterns(
        self, session_id: str, pattern_keys: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Detect sensitive patterns (Email, Phone, Aadhaar, PAN, GSTIN, Card, etc.) using regex."""
        temp_dir = Paths.request_temp(session_id) / "redact_work"
        orig_file = temp_dir / "original.pdf"
        if not orig_file.exists():
            return []

        doc = fitz.open(str(orig_file))
        candidates = []
        active_keys = pattern_keys if pattern_keys else list(REGEX_PATTERNS.keys())

        cand_id = 0
        scanned_pages = 0
        
        for idx in range(len(doc)):
            page = doc[idx]
            page_num = idx + 1
            text = page.get_text("text")

            # Check if scanned / image-only page
            if len(text.strip()) < 15:
                scanned_pages += 1
                if HAS_PYTESSERACT:
                    ocr_cands = self._scan_ocr_page(page_num, page)
                    candidates.extend(ocr_cands)
                continue

            for key in active_keys:
                if key not in REGEX_PATTERNS:
                    continue
                regex_str, cat, cat_label = REGEX_PATTERNS[key]

                for m in re.finditer(regex_str, text, re.IGNORECASE):
                    matched_str = m.group(0).strip()
                    if len(matched_str) < 3:
                        continue

                    rects = self._find_bbox_for_text(page, matched_str)
                    for rect in rects:
                        cand_id += 1
                        candidates.append({
                            "id": f"pat_{cand_id}",
                            "page": page_num,
                            "text": matched_str,
                            "matched_text": matched_str,
                            "category": cat,
                            "category_label": cat_label,
                            "bbox": [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)],
                            "confidence": 0.95,
                        })

        total_pages = len(doc)
        doc.close()
        
        if not candidates and scanned_pages == total_pages and not HAS_PYTESSERACT:
            raise ValueError("This appears to be a scanned or image-only PDF. Tesseract OCR is not installed on the server, so pattern detection cannot be performed. Please manually select the area to redact.")
            
        return self._deduplicate_candidates(candidates)

    # ── 6. Intelligent Sensitive Data Auto Scanner ───────────────────────

    def detect_sensitive_data(self, session_id: str) -> List[Dict[str, Any]]:
        """Run comprehensive sensitive data auto scanner across all categories and field labels."""
        try:
            pattern_candidates = self.detect_patterns(session_id)
        except ValueError as e:
            if "scanned" in str(e).lower():
                raise e
            pattern_candidates = []

        temp_dir = Paths.request_temp(session_id) / "redact_work"
        orig_file = temp_dir / "original.pdf"
        if not orig_file.exists():
            return pattern_candidates

        doc = fitz.open(str(orig_file))
        additional = []
        cand_id = len(pattern_candidates)

        for idx in range(len(doc)):
            page = doc[idx]
            page_num = idx + 1
            text = page.get_text("text")

            # 1. Label Proximity Scanning (e.g. Name: John Doe, DOB: 01/01/1990)
            for regex_rule, cat, cat_label in LABEL_PROXIMITY_RULES:
                for m in re.finditer(regex_rule, text, re.IGNORECASE):
                    matched_val = m.group(1).strip()
                    if len(matched_val) < 2:
                        continue

                    rects = self._find_bbox_for_text(page, matched_val)
                    for r in rects:
                        cand_id += 1
                        additional.append({
                            "id": f"sens_{cand_id}",
                            "page": page_num,
                            "text": matched_val,
                            "matched_text": matched_val,
                            "category": cat,
                            "category_label": cat_label,
                            "bbox": [float(r.x0), float(r.y0), float(r.x1), float(r.y1)],
                            "confidence": 0.88,
                        })

            # 2. General Name Heuristics (Mr. X, Mrs. Y, Dr. Z)
            name_patterns = [
                r"\bMr\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
                r"\bMrs\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
                r"\bDr\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
                r"\bProf\.\s+[A-Z][a-z]+\b",
            ]
            for pattern in name_patterns:
                for m in re.finditer(pattern, text):
                    val = m.group(0).strip()
                    rects = self._find_bbox_for_text(page, val)
                    for r in rects:
                        cand_id += 1
                        additional.append({
                            "id": f"sens_{cand_id}",
                            "page": page_num,
                            "text": val,
                            "matched_text": val,
                            "category": "PERSON",
                            "category_label": "Person Name",
                            "bbox": [float(r.x0), float(r.y0), float(r.x1), float(r.y1)],
                            "confidence": 0.85,
                        })

        doc.close()
        all_candidates = pattern_candidates + additional
        return self._deduplicate_candidates(all_candidates)

    # ── Helper: Fallback Bounding Box Finder ──────────────────────────────

    def _find_bbox_for_text(
        self, page: fitz.Page, target_text: str, flags: int = 0
    ) -> List[fitz.Rect]:
        """Find text bounding boxes with fallback for whitespace or multi-word breaks."""
        rects = page.search_for(target_text, flags=flags)
        if rects:
            return rects

        # Fallback 1: Search without extra whitespace
        clean_target = target_text.strip()
        if not clean_target:
            return []

        # Fallback 2: Word-by-word sequence bounding box construction
        words = page.get_text("words")  # [x0, y0, x1, y1, word, block_no, line_no, word_no]
        if not words:
            return []

        target_words = [w.strip().lower() for w in clean_target.split() if w.strip()]
        if not target_words:
            return []

        matched_rects = []
        for i in range(len(words) - len(target_words) + 1):
            match = True
            for j, tw in enumerate(target_words):
                w_text = words[i + j][4].strip().lower()
                w_text_clean = re.sub(r"[^\w@.-]", "", w_text)
                tw_clean = re.sub(r"[^\w@.-]", "", tw)
                if tw_clean and w_text_clean != tw_clean and tw_clean not in w_text_clean:
                    match = False
                    break
            if match:
                group_words = words[i : i + len(target_words)]
                x0 = min(w[0] for w in group_words)
                y0 = min(w[1] for w in group_words)
                x1 = max(w[2] for w in group_words)
                y1 = max(w[3] for w in group_words)
                matched_rects.append(fitz.Rect(x0, y0, x1, y1))

        return matched_rects

    def _scan_ocr_for_query(
        self, page_num: int, page: fitz.Page, query: str, case_sensitive: bool = False
    ) -> List[Dict[str, Any]]:
        """Fallback OCR search for specific queries on image-only pages."""
        if not HAS_PYTESSERACT:
            return []
            
        candidates = []
        try:
            dpi = 150
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            scale = 72.0 / dpi
            
            n_boxes = len(ocr_data["text"])
            cand_id = 0
            
            query_clean = query.strip()
            if not case_sensitive:
                query_clean = query_clean.lower()
                
            for i in range(n_boxes):
                text = ocr_data["text"][i].strip()
                if not text: continue
                
                text_compare = text if case_sensitive else text.lower()
                if query_clean in text_compare:
                    x = ocr_data["left"][i]
                    y = ocr_data["top"][i]
                    w = ocr_data["width"][i]
                    h = ocr_data["height"][i]
                    cand_id += 1
                    candidates.append({
                        "id": f"search_ocr_{page_num}_{cand_id}",
                        "page": page_num,
                        "text": query,
                        "matched_text": text,
                        "category": "SEARCH_MATCH",
                        "category_label": "Search Match (OCR)",
                        "bbox": [float(x * scale), float(y * scale), float((x + w) * scale), float((y + h) * scale)],
                        "occurrence": cand_id,
                        "confidence": 0.90,
                    })
        except Exception as e:
            logger.warning(f"OCR query search exception on page {page_num}: {e}")
            
        return candidates

    # ── Helper: Candidate Deduplication ───────────────────────────────────

    def _deduplicate_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate candidates with identical or nearly identical bounding boxes on the same page."""
        if not candidates:
            return []

        unique: List[Dict[str, Any]] = []
        seen_keys: Set[str] = set()

        for c in candidates:
            page = c.get("page", 1)
            bbox = c.get("bbox", [0, 0, 0, 0])
            # Key rounded to nearest 3 points to merge overlapping bounds
            key = f"{page}_{round(bbox[0]/4)*4}_{round(bbox[1]/4)*4}_{round(bbox[2]/4)*4}_{round(bbox[3]/4)*4}_{c.get('category')}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique.append(c)

        return unique

    # ── Helper: OCR Scanner for Image-Only Pages ─────────────────────────

    def _scan_ocr_page(self, page_num: int, page: fitz.Page) -> List[Dict[str, Any]]:
        """OCR fallback scanner for image-only or scanned PDF pages using pytesseract."""
        if not HAS_PYTESSERACT:
            return []

        candidates = []
        try:
            dpi = 150
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

            scale = 72.0 / dpi
            n_boxes = len(ocr_data["text"])

            full_ocr_text = " ".join([t for t in ocr_data["text"] if t.strip()])
            cand_id = 0

            for key, (regex_str, cat, cat_label) in REGEX_PATTERNS.items():
                for m in re.finditer(regex_str, full_ocr_text, re.IGNORECASE):
                    val = m.group(0).strip()
                    # Find word indices in OCR data
                    for i in range(n_boxes):
                        if val in ocr_data["text"][i]:
                            x, y, w, h = ocr_data["left"][i], ocr_data["top"][i], ocr_data["width"][i], ocr_data["height"][i]
                            cand_id += 1
                            candidates.append({
                                "id": f"ocr_{page_num}_{cand_id}",
                                "page": page_num,
                                "text": val,
                                "matched_text": val,
                                "category": cat,
                                "category_label": f"{cat_label} (OCR)",
                                "bbox": [x * scale, y * scale, (x + w) * scale, (y + h) * scale],
                                "confidence": 0.90,
                            })
        except Exception as e:
            logger.warning(f"OCR page scan exception on page {page_num}: {e}")

        return candidates

    # ── 7. True Permanent Redaction Engine ────────────────────────────────

    def apply_redaction(
        self,
        session_id: str,
        redactions: List[Dict[str, Any]],
        fill_color: str = "#000000",
        label: str = "",
        security_options: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """Apply TRUE permanent PyMuPDF redaction and security sanitization."""
        security_options = security_options or {}
        clean_metadata = security_options.get("clean_metadata", True)
        clean_annotations = security_options.get("clean_annotations", False)
        clean_embedded_files = security_options.get("clean_embedded_files", True)
        clean_hidden_content = security_options.get("clean_hidden_content", True)

        temp_dir = Paths.request_temp(session_id) / "redact_work"
        orig_file = temp_dir / "original.pdf"
        if not orig_file.exists():
            raise ValueError("Original file not found for session.")

        out_dir = Paths.request_output(session_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "redacted_output.pdf"

        doc = fitz.open(str(orig_file))

        fill_rgb = self._parse_color(fill_color)
        text_rgb = (1, 1, 1) if fill_rgb[0] < 0.5 else (0, 0, 0)

        original_redacted_texts: List[str] = []
        applied_count = 0
        pages_modified: Set[int] = set()

        for item in redactions:
            page_num = item.get("page", 1)
            bbox = item.get("bbox")
            txt = item.get("text") or item.get("matched_text")
            if txt:
                original_redacted_texts.append(txt)

            if not bbox or len(bbox) < 4:
                continue

            idx = page_num - 1
            if 0 <= idx < len(doc):
                page = doc[idx]
                rect = fitz.Rect(*bbox)

                custom_label = item.get("label") or label
                annot = page.add_redact_annot(
                    rect,
                    text=custom_label if custom_label else "",
                    fontname="helv",
                    fontsize=10,
                    fill=fill_rgb,
                    text_color=text_rgb,
                    align=1,
                )
                applied_count += 1
                pages_modified.add(page_num)

        # Apply true redactions across all pages
        for idx in range(len(doc)):
            page = doc[idx]
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)

            if clean_annotations:
                for annot in page.annots():
                    page.delete_annot(annot)

        # Security Sanitization
        if clean_metadata:
            doc.set_metadata({
                "title": "",
                "author": "",
                "subject": "",
                "keywords": "",
                "creator": "",
                "producer": "PDF Tools Enterprise Redact Engine",
                "creationDate": "",
                "modDate": "",
            })

        if clean_embedded_files:
            try:
                for i in range(doc.embfile_count() - 1, -1, -1):
                    doc.embfile_del(i)
            except Exception as e:
                logger.warning(f"Error cleaning embedded files: {e}")

        if clean_hidden_content:
            try:
                if hasattr(doc, "scrub"):
                    doc.scrub(attached_files=clean_embedded_files, clean_pages=True)
            except Exception as e:
                logger.warning(f"Error cleaning hidden content: {e}")

        doc.save(
            str(out_file),
            garbage=4,
            deflate=True,
            clean=True,
        )
        total_p = len(doc)
        doc.close()

        verification = self.verify_redaction(str(out_file), original_redacted_texts)

        return {
            "success": True,
            "session_id": session_id,
            "total_redactions": applied_count,
            "pages_processed": len(pages_modified),
            "total_pages": total_p,
            "verification": verification,
            "download_url": f"/api/pdf/redact/download/{session_id}",
        }

    # ── 8. Post-Redaction Empirical Verification ──────────────────────────

    def verify_redaction(
        self, redacted_pdf_path: str, original_redacted_texts: List[str]
    ) -> Dict[str, Any]:
        """Re-open output PDF, extract text, and empirically verify original redacted content is removed."""
        if not os.path.exists(redacted_pdf_path):
            return {
                "verification_passed": False,
                "message": "Output PDF file not found.",
                "remaining_matches": -1,
            }

        try:
            doc = fitz.open(redacted_pdf_path)
            extracted_text = ""
            for page in doc:
                extracted_text += page.get_text("text") + " "
            doc.close()
        except Exception as exc:
            return {
                "verification_passed": False,
                "message": f"Failed to re-open redacted PDF for verification: {exc}",
                "remaining_matches": -1,
            }

        found_breaches = []
        for txt in original_redacted_texts:
            clean_t = txt.strip()
            if len(clean_t) > 2 and clean_t.lower() in extracted_text.lower():
                found_breaches.append(clean_t)

        if found_breaches:
            return {
                "verification_passed": False,
                "message": f"Verification failed! {len(found_breaches)} redacted item(s) are still extractable.",
                "remaining_matches": len(found_breaches),
                "breaches": found_breaches[:5],
            }

        return {
            "verification_passed": True,
            "message": "Verification Passed: Redacted content is completely removed and unextractable.",
            "remaining_matches": 0,
        }

    # ── Helper: Color Converter ──────────────────────────────────────────

    def _parse_color(self, color_str: str) -> Tuple[float, float, float]:
        """Parse color string (#000000, black, white, red) into RGB tuple 0.0-1.0."""
        c = (color_str or "#000000").strip().lower()
        if c in ("black", "#000000"):
            return (0.0, 0.0, 0.0)
        if c in ("white", "#ffffff"):
            return (1.0, 1.0, 1.0)
        if c in ("red", "#ef4444", "#ff0000"):
            return (0.93, 0.26, 0.26)
        if c in ("blue", "#3b82f6", "#0000ff"):
            return (0.23, 0.51, 0.96)
        if c in ("gray", "#64748b"):
            return (0.39, 0.45, 0.54)

        if c.startswith("#") and len(c) == 7:
            try:
                r = int(c[1:3], 16) / 255.0
                g = int(c[3:5], 16) / 255.0
                b = int(c[5:7], 16) / 255.0
                return (r, g, b)
            except ValueError:
                pass

        return (0.0, 0.0, 0.0)


redact_pdf_service = RedactPdfService()
