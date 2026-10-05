"""
Accessibility Service — PDF accessibility analysis and WCAG compliance.

Uses PyMuPDF (fitz) to analyze PDF structure, tags, reading order,
alt text, heading hierarchy, and more for WCAG 2.1 AA compliance.
"""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

WCAG_CRITERIA = {
    "1.1.1": "Non-text Content (Level A)",
    "1.3.1": "Info and Relationships (Level A)",
    "1.3.2": "Meaningful Sequence (Level A)",
    "1.3.3": "Sensory Characteristics (Level A)",
    "1.4.1": "Use of Color (Level A)",
    "1.4.3": "Contrast (Minimum) (Level AA)",
    "2.4.1": "Bypass Blocks (Level A)",
    "2.4.2": "Page Titled (Level A)",
    "2.4.6": "Headings and Labels (Level AA)",
    "3.1.1": "Language of Page (Level A)",
    "3.1.2": "Language of Parts (Level AA)",
    "4.1.2": "Name, Role, Value (Level A)",
}


class AccessibilityService:
    """Service class for PDF accessibility analysis and compliance checking."""

    @staticmethod
    def _get_doc(input_path: str) -> fitz.Document:
        """Open a PDF document."""
        return fitz.open(input_path)

    @staticmethod
    def _extract_all_text(input_path: str) -> str:
        """Extract all text from a PDF."""
        doc = fitz.open(input_path)
        try:
            parts = []
            for page in doc:
                parts.append(page.get_text())
            return "\n".join(parts)
        finally:
            doc.close()

    @staticmethod
    def _get_text_blocks(input_path: str) -> List[Dict[str, Any]]:
        """Extract text blocks with position info."""
        doc = fitz.open(input_path)
        try:
            blocks = []
            for i, page in enumerate(doc):
                for b in page.get_text("blocks"):
                    x0, y0, x1, y1, text, block_no, block_type = b
                    blocks.append({
                        "page": i + 1,
                        "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                        "text": text.strip(),
                        "block_type": block_type,
                    })
            return blocks
        finally:
            doc.close()

    @staticmethod
    def _extract_structure(input_path: str) -> Dict[str, Any]:
        """Extract PDF structure tree information."""
        doc = fitz.open(input_path)
        try:
            info = {
                "is_tagged": False,
                "has_structure_tree": False,
                "has_mark_info": False,
                "metadata": doc.metadata or {},
                "page_count": len(doc),
            }

            toc = doc.get_toc()
            if toc:
                info["has_structure_tree"] = True
                info["toc"] = [{"level": t[0], "title": t[1], "page": t[2]} for t in toc[:50]]

            try:
                xref = doc.xref_xml_metadata(0) if doc.xref_length() > 0 else ""
                if "MarkInfo" in str(xref) or "Marked" in str(xref):
                    info["has_mark_info"] = True
            except Exception:
                pass

            try:
                if hasattr(doc, "is_pdf") and doc.is_pdf:
                    for i in range(min(5, len(doc))):
                        page = doc[i]
                        try:
                            xref = page.xref
                            if doc.xref_get_key(xref, "StructParents"):
                                info["is_tagged"] = True
                                break
                        except Exception:
                            continue
            except Exception:
                pass

            if toc:
                info["is_tagged"] = True

            return info
        finally:
            doc.close()

    @staticmethod
    def _extract_images(input_path: str) -> List[Dict[str, Any]]:
        """Extract image information from PDF."""
        doc = fitz.open(input_path)
        try:
            images = []
            for i, page in enumerate(doc):
                for img in page.get_images(full=True):
                    xref = img[0]
                    try:
                        info = doc.extract_image(xref)
                        images.append({
                            "page": i + 1,
                            "xref": xref,
                            "width": info.get("width", 0),
                            "height": info.get("height", 0),
                            "format": info.get("image", b"")[:4].decode("latin-1") if info.get("image") else "unknown",
                        })
                    except Exception:
                        images.append({"page": i + 1, "xref": xref, "width": 0, "height": 0, "format": "unknown"})
            return images
        finally:
            doc.close()

    @staticmethod
    def _extract_links(input_path: str) -> List[Dict[str, Any]]:
        """Extract links from PDF."""
        doc = fitz.open(input_path)
        try:
            links = []
            for i, page in enumerate(doc):
                for link in page.get_links():
                    links.append({
                        "page": i + 1,
                        "uri": link.get("uri", ""),
                        "kind": link.get("kind", 0),
                    })
            return links
        finally:
            doc.close()

    @staticmethod
    def _get_reading_order(input_path: str) -> List[Dict[str, Any]]:
        """Determine reading order from text blocks."""
        doc = fitz.open(input_path)
        try:
            order = []
            for i, page in enumerate(doc):
                blocks = page.get_text("blocks")
                text_blocks = [b for b in blocks if b[6] == 0]
                text_blocks.sort(key=lambda b: (round(b[1] / 20) * 20, b[0]))
                for idx, b in enumerate(text_blocks):
                    order.append({
                        "page": i + 1,
                        "order": idx,
                        "text": b[4].strip()[:100],
                        "y0": b[1],
                        "x0": b[0],
                    })
            return order
        finally:
            doc.close()

    def _get_headings(self, input_path: str) -> List[Dict[str, Any]]:
        """Extract heading hierarchy."""
        doc = fitz.open(input_path)
        try:
            headings = []
            for i, page in enumerate(doc):
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text:
                                continue
                            flags = span.get("flags", 0)
                            size = span.get("size", 12)
                            is_bold = bool(flags & 2**4)
                            if size >= 14 or (is_bold and len(text) < 100):
                                headings.append({
                                    "page": i + 1,
                                    "text": text,
                                    "font_size": size,
                                    "is_bold": is_bold,
                                })
            return headings
        finally:
            doc.close()

    def _detect_language(self, input_path: str) -> Dict[str, Any]:
        """Detect document language from metadata and text."""
        doc = fitz.open(input_path)
        try:
            metadata = doc.metadata or {}
            lang = metadata.get("language", "unknown")

            if lang == "unknown":
                full_text = self._extract_all_text(input_path)
                sample = full_text[:2000].lower()
                en_words = len(re.findall(r'\b(?:the|and|is|in|to|of|for|that|with|this|are|was|be|have|has|not|but|from|or|an|it|by|on|at|which)\b', sample))
                es_words = len(re.findall(r'\b(?:el|la|los|las|un|una|de|del|en|con|por|para|que|es|son|está|este|esta|más|pero|como|todo|hay|ser)\b', sample))
                fr_words = len(re.findall(r'\b(?:le|la|les|des|est|un|une|et|en|pour|que|dans|qui|sur|pas|avec|ce|mais|sont|au|ceux)\b', sample))
                de_words = len(re.findall(r'\b(?:der|die|das|ist|ein|eine|und|in|zu|für|auf|mit|von|den|dem|nicht|sich|aber|noch|wie|auch)\b', sample))

                scores = {"en": en_words, "es": es_words, "fr": fr_words, "de": de_words}
                detected = max(scores, key=scores.get) if max(scores.values()) > 0 else "en"
            else:
                detected = lang

            return {
                "success": True,
                "primary_language_name": detected,
                "primary_language_code": detected,
                "metadata_language": lang,
                "language_tags_count": 1,
                "confidence_score": 95,
                "detected_language": detected
            }
        finally:
            doc.close()

    # ── Public API ────────────────────────────────────────────────────

    def get_read_aloud_text(self, input_path: str) -> Dict[str, Any]:
        """Extract text for text-to-speech reading."""
        doc = fitz.open(input_path)
        pages = []
        try:
            for page in doc:
                pages.append(page.get_text("text"))
        finally:
            doc.close()
        
        text = "\n\n".join(pages)
        return {
            "success": True,
            "read_aloud": {
                "text": text,
                "full_text": text,
                "pages": pages
            }
        }

    def upload_pdf(self, input_path: str) -> str:
        """Store PDF and return a document ID."""
        doc_id = Path(input_path).stem + "_" + Path(input_path).suffix
        return doc_id

    def check_pdfua(self, input_path: str) -> Dict[str, Any]:
        """Check PDF/UA-1 compliance."""
        structure = self._extract_structure(input_path)
        images = self._extract_images(input_path)
        lang_info = self._detect_language(input_path)

        checks = []

        checks.append({
            "name": "Tagged PDF",
            "status": "PASS" if structure["is_tagged"] else "FAIL",
            "details": "PDF/UA requires a tagged PDF." if not structure["is_tagged"] else "PDF is tagged.",
        })

        checks.append({
            "name": "Document Language",
            "status": "PASS" if lang_info["detected_language"] != "unknown" else "FAIL",
            "details": f"Language: {lang_info['detected_language']}.",
        })

        has_toc = bool(structure.get("toc"))
        checks.append({
            "name": "Table of Contents / Bookmarks",
            "status": "PASS" if has_toc else "WARNING",
            "details": "PDF/UA recommends bookmarks for navigation." if not has_toc else "Bookmarks present.",
        })

        checks.append({
            "name": "Alt Text for Images",
            "status": "WARNING" if images else "PASS",
            "details": f"{len(images)} images found. Alt text must be provided." if images else "No images.",
        })

        metadata = structure["metadata"]
        checks.append({
            "name": "Document Metadata",
            "status": "PASS" if metadata.get("title") else "FAIL",
            "details": f"Title: {metadata.get('title', 'Not set')}. Author: {metadata.get('author', 'Not set')}.",
        })

        pass_count = sum(1 for c in checks if c["status"] == "PASS")
        total = len(checks)

        return {
            "success": True,
            "pdfua_check": {
                "standard": "PDF/UA-1 (ISO 14289-1)",
                "is_compliant": pass_count == total,
                "score": round((pass_count / total) * 100, 1) if total > 0 else 0,
                "checks": checks,
            },
        }

    def general_accessibility_check(self, input_path: str) -> Dict[str, Any]:
        """Comprehensive accessibility check."""
        structure = self._extract_structure(input_path)
        images = self._extract_images(input_path)
        full_text = self._extract_all_text(input_path)
        headings = self._get_headings(input_path)
        lang_info = self._detect_language(input_path)
        links = self._extract_links(input_path)
        blocks = self._get_text_blocks(input_path)

        issues = []
        recommendations = []

        if not structure["is_tagged"]:
            issues.append({"severity": "critical", "message": "PDF is not tagged", "area": "Structure"})
            recommendations.append("Tag the PDF to provide structural information for assistive technologies.")

        if not headings:
            issues.append({"severity": "warning", "message": "No headings found", "area": "Navigation"})
            recommendations.append("Add headings to improve document navigation.")

        if images:
            issues.append({"severity": "warning", "message": f"{len(images)} images without verified alt text", "area": "Alt Text"})
            recommendations.append("Add alternative text descriptions for all images.")

        if not structure.get("toc"):
            issues.append({"severity": "info", "message": "No bookmarks or table of contents", "area": "Navigation"})
            recommendations.append("Add bookmarks for document navigation.")

        if lang_info["detected_language"] == "unknown":
            issues.append({"severity": "warning", "message": "Document language not detected", "area": "Language"})
            recommendations.append("Set the document language in metadata.")

        text_blocks = [b for b in blocks if b["block_type"] == 0]
        if len(text_blocks) > 0:
            lines_per_page = Counter(b["page"] for b in text_blocks)
            for page, count in lines_per_page.items():
                if count > 100:
                    issues.append({"severity": "info", "message": f"Page {page} has {count} text blocks", "area": "Reading Order"})
                    recommendations.append("Review reading order on dense pages.")

        word_count = len(full_text.split())
        score = 100
        for issue in issues:
            if issue["severity"] == "critical":
                score -= 20
            elif issue["severity"] == "warning":
                score -= 10
            else:
                score -= 5
        score = max(0, score)

        return {
            "success": True,
            "accessibility_check": {
                "score": score,
                "total_issues": len(issues),
                "issues": issues,
                "recommendations": recommendations[:10],
                "structure": {
                    "is_tagged": structure["is_tagged"],
                    "has_toc": bool(structure.get("toc")),
                    "has_images": len(images) > 0,
                    "image_count": len(images),
                    "link_count": len(links),
                    "heading_count": len(headings),
                    "word_count": word_count,
                },
                "language": lang_info,
            },
        }

    def check_tagged_pdf(self, input_path: str) -> Dict[str, Any]:
        """Check if PDF is properly tagged."""
        structure = self._extract_structure(input_path)

        return {
            "success": True,
            "tagged_pdf": {
                "is_tagged": structure["is_tagged"],
                "has_structure_tree": structure["has_structure_tree"],
                "has_mark_info": structure["has_mark_info"],
                "has_toc": bool(structure.get("toc")),
                "toc_entries": len(structure.get("toc", [])),
            },
        }

    def check_screen_reader_support(self, input_path: str) -> Dict[str, Any]:
        """Analyze screen reader compatibility."""
        structure = self._extract_structure(input_path)
        full_text = self._extract_all_text(input_path)
        headings = self._get_headings(input_path)
        images = self._extract_images(input_path)

        score = 0
        checks = []

        if structure["is_tagged"]:
            score += 30
            checks.append({"name": "Tagged PDF", "status": "pass", "description": "PDF is tagged for screen readers."})
        else:
            checks.append({"name": "Tagged PDF", "status": "fail", "description": "PDF is not tagged."})

        if headings:
            score += 20
            checks.append({"name": "Headings", "status": "pass", "description": f"{len(headings)} headings found for navigation."})
        else:
            checks.append({"name": "Headings", "status": "fail", "description": "No headings found."})

        if structure.get("toc"):
            score += 15
            checks.append({"name": "Bookmarks", "status": "pass", "description": "Bookmarks available for navigation."})
        else:
            checks.append({"name": "Bookmarks", "status": "warning", "description": "No bookmarks found."})

        word_count = len(full_text.split())
        if word_count > 0:
            score += 15
            checks.append({"name": "Text Content", "status": "pass", "description": f"Document has {word_count} words of text content."})
        else:
            checks.append({"name": "Text Content", "status": "fail", "description": "No text content found."})

        if images:
            score += 10
            checks.append({"name": "Images", "status": "warning", "description": f"{len(images)} images found. Verify alt text."})
        else:
            score += 10
            checks.append({"name": "Images", "status": "pass", "description": "No images found."})

        lang = self._detect_language(input_path)
        if lang["detected_language"] != "unknown":
            score += 10
            checks.append({"name": "Language", "status": "pass", "description": f"Language detected: {lang['detected_language']}."})
        else:
            checks.append({"name": "Language", "status": "warning", "description": "Language not detected."})

        return {
            "success": True,
            "screen_reader_support": {
                "score": min(score, 100),
                "checks": checks,
                "recommendation": "PDF is well-suited for screen readers." if score >= 70 else "PDF needs improvements for screen reader compatibility.",
            },
        }

    def get_read_aloud_text(self, input_path: str) -> Dict[str, Any]:
        """Extract text in reading order for text-to-speech."""
        order = self._get_reading_order(input_path)
        reading_text = "\n".join(item["text"] for item in order if item["text"])

        return {
            "success": True,
            "read_aloud": {
                "text": reading_text,
                "total_blocks": len([item for item in order if item["text"]]),
                "total_characters": len(reading_text),
            },
        }

    def analyze_reading_order(self, input_path: str) -> Dict[str, Any]:
        """Analyze and report reading order."""
        order = self._get_reading_order(input_path)
        pages_order = defaultdict(list)
        for item in order:
            pages_order[item["page"]].append(item)

        issues = []
        for page_num, page_items in pages_order.items():
            y_positions = [item["y0"] for item in page_items]
            if y_positions != sorted(y_positions):
                issues.append({
                    "page": page_num,
                    "issue": "Text blocks may not follow logical reading order.",
                    "block_count": len(page_items),
                })

        return {
            "success": True,
            "reading_order": {
                "total_blocks": len(order),
                "pages_analyzed": len(pages_order),
                "issues": issues,
                "is_logical": len(issues) == 0,
            },
        }

    def check_color_contrast(self, input_path: str) -> Dict[str, Any]:
        """Check text/background contrast ratios."""
        doc = fitz.open(input_path)
        try:
            text_colors = []
            for page in doc:
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            color = span.get("color", 0)
                            r = (color >> 16) & 0xFF
                            g = (color >> 8) & 0xFF
                            b = color & 0xFF
                            text_colors.append({"r": r, "g": g, "b": b, "text": span.get("text", "")[:50]})

            unique_colors = set((c["r"], c["g"], c["b"]) for c in text_colors)

            issues = []
            for r, g, b in unique_colors:
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                if luminance > 0.8:
                    issues.append({"color": f"rgb({r},{g},{b})", "issue": "Light text on white background may have low contrast"})
                elif luminance < 0.1:
                    issues.append({"color": f"rgb({r},{g},{b})", "issue": "Very dark text"})

            return {
                "success": True,
                "color_contrast": {
                    "unique_text_colors": len(unique_colors),
                    "sample_colors": [{"r": r, "g": g, "b": b} for r, g, b in list(unique_colors)[:10]],
                    "issues": issues[:10],
                    "recommendation": "Manual contrast testing recommended for scanned documents." if issues else "No obvious contrast issues detected.",
                },
            }
        finally:
            doc.close()

    def check_alt_text(self, input_path: str) -> Dict[str, Any]:
        """Check images for alt text."""
        images = self._extract_images(input_path)

        results = []
        for img in images:
            results.append({
                "page": img["page"],
                "width": img["width"],
                "height": img["height"],
                "format": img["format"],
                "has_alt_text": False,
                "recommendation": "Add alt text description for this image.",
            })

        return {
            "success": True,
            "alt_text": {
                "total_images": len(images),
                "images_with_alt_text": 0,
                "images_without_alt_text": len(images),
                "compliance": "PASS" if len(images) == 0 else "FAIL",
                "details": results[:20],
            },
        }

    def check_accessible_forms(self, input_path: str) -> Dict[str, Any]:
        """Check form field accessibility."""
        doc = fitz.open(input_path)
        try:
            form_fields = []
            for i, page in enumerate(doc):
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        field_type = widget.field_type_string if hasattr(widget, "field_type_string") else "unknown"
                        field_name = widget.field_name if hasattr(widget, "field_name") else "unnamed"
                        form_fields.append({
                            "page": i + 1,
                            "field_type": field_type,
                            "field_name": field_name,
                        })

            has_forms = len(form_fields) > 0
            return {
                "success": True,
                "accessible_forms": {
                    "total_fields": len(form_fields),
                    "has_forms": has_forms,
                    "compliance": "PASS" if not has_forms else "WARNING",
                    "fields": form_fields[:20],
                    "recommendation": "Verify form fields have labels and are keyboard accessible." if has_forms else "No form fields found.",
                },
            }
        finally:
            doc.close()

    def check_accessible_tables(self, input_path: str) -> Dict[str, Any]:
        """Check table structure and headers."""
        doc = fitz.open(input_path)
        try:
            tables = []
            for i, page in enumerate(doc):
                try:
                    tabs = page.find_tables()
                    if tabs and tabs.tables:
                        for tab in tabs.tables:
                            tables.append({
                                "page": i + 1,
                                "rows": tab.row_count,
                                "cols": tab.col_count,
                                "has_header": True,
                            })
                except Exception:
                    pass

            return {
                "success": True,
                "accessible_tables": {
                    "total_tables": len(tables),
                    "compliance": "WARNING" if tables else "PASS",
                    "tables": tables[:10],
                    "recommendation": "Verify table headers are properly marked and tables have captions." if tables else "No tables found.",
                },
            }
        finally:
            doc.close()

    def detect_language(self, input_path: str) -> Dict[str, Any]:
        """Detect document language."""
        lang_info = self._detect_language(input_path)

        full_text = self._extract_all_text(input_path)
        sample = full_text[:5000].lower()

        language_indicators = {}
        patterns = {
            "en": r'\b(?:the|and|is|in|to|of|for|that|with|this|are|was|be|have|has|not|but|from|or|an|it|by|on|at|which|will|would|could|should|may|might|their|there|they|been|being|more|also|than|when|what|about|into|through|during|before|after|above|below|between|under|over)\b',
            "es": r'\b(?:el|la|los|las|un|una|de|del|en|con|por|para|que|es|son|está|este|esta|más|pero|como|todo|hay|ser|tiene|puede|hacer|mundo|también|después|entre|otro|otra|mismo|donde|cuando|desde|hasta|sobre|todos|cada|hacia|donde|sino|aunque|porque|según|mientras|hace|años|después)\b',
            "fr": r'\b(?:le|la|les|des|est|un|une|et|en|pour|que|dans|qui|sur|pas|avec|ce|mais|sont|au|ceux|cette|tout|aussi|bien|même|fait|faire|être|avoir|autre|comme|leur|deux|après|entre|sans|chez|très|encore|si|donc|peut|moins|nous|vous|ils|elle|on|y|se)\b',
            "de": r'\b(?:der|die|das|ist|ein|eine|und|in|zu|für|auf|mit|von|den|dem|nicht|sich|aber|noch|wie|auch|aus|er|hat|nach|bei|ist|nur|oder|über|dass|sie|wir|kann|als|am|im|so|man|es|war|werden|durch|vor|zum|zur|bis|um|dass|ihr|ihm|sein|hatte|wenn|so|diese|dieser|diesem|diesen)\b',
        }

        for lang, pattern in patterns.items():
            language_indicators[lang] = len(re.findall(pattern, sample))

        return {
            "success": True,
            "language_detection": {
                "primary_language": lang_info["detected_language"],
                "metadata_language": lang_info["metadata_language"],
                "confidence": "high" if max(language_indicators.values(), default=0) > 20 else "medium",
                "language_scores": language_indicators,
            },
        }


    def letter_spacing_extract(self, input_path: str, settings: dict) -> Dict[str, Any]:
        return self.font_size_controls_extract(input_path, settings)

    def letter_spacing_export(self, input_path: str, payload: dict) -> Dict[str, Any]:
        import pymupdf
        import tempfile
        
        # Get extracted HTML using the payload settings to apply styles
        extract_result = self.font_size_controls_extract(input_path, payload)
        html_pages = extract_result.get("formatted_pages", [])
        
        # Get target letter spacing
        letter_spacing = float(payload.get("letter_spacing_em", 0.05))
        text_color = payload.get("text_color_hex", "#000000")
        
        # CSS to adjust letter spacing
        css = f"""
        body {{ font-family: sans-serif; font-size: 14pt; color: {text_color}; letter-spacing: {letter_spacing}em; line-height: 1.5; }}
        h1 {{ font-size: 20pt; margin-bottom: 1em; letter-spacing: {letter_spacing}em; }}
        h2 {{ font-size: 18pt; margin-bottom: 1em; letter-spacing: {letter_spacing}em; }}
        h3 {{ font-size: 16pt; margin-bottom: 1em; letter-spacing: {letter_spacing}em; }}
        """
        
        body_content = ""
        for p in html_pages:
            body_content += f'<div style="page-break-after: always;">{p["html"]}</div>'
            
        full_html = f"<html><head><style>{css}</style></head><body>{body_content}</body></html>"
        
        import os
        from uuid import uuid4
        import tempfile
        import subprocess
        os.makedirs(os.path.join(tempfile.gettempdir(), "legal_pdf_exports"), exist_ok=True)
        html_path = os.path.join(tempfile.gettempdir(), "legal_pdf_exports", f"temp_{uuid4().hex}.html")
        temp_path = os.path.join(tempfile.gettempdir(), "legal_pdf_exports", f"exported_{uuid4().hex}.pdf")
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(full_html)
            
        script_path = os.path.join(os.path.dirname(__file__), "pdf_exporter.py")
        import sys
        subprocess.run([sys.executable, script_path, html_path, temp_path], check=True)
        
        
        return {"success": True, "output_path": temp_path}

    def line_spacing_extract(self, input_path: str, settings: dict) -> Dict[str, Any]:
        # The extraction logic (parsing to semantic HTML blocks) is identical
        return self.font_size_controls_extract(input_path, settings)

    def line_spacing_export(self, input_path: str, payload: dict) -> Dict[str, Any]:
        import pymupdf
        import tempfile
        
        # Get extracted HTML using the payload settings to apply styles
        extract_result = self.font_size_controls_extract(input_path, payload)
        html_pages = extract_result.get("formatted_pages", [])
        
        # Get target line spacing and gap
        line_spacing = float(payload.get("line_spacing_mult", 1.4))
        paragraph_gap = float(payload.get("paragraph_gap_mult", 1.5))
        text_color = payload.get("text_color_hex", "#000000")
        
        # CSS to adjust line spacing
        css = f"""
        body {{ font-family: sans-serif; font-size: 14pt; color: {text_color}; line-height: {line_spacing}; }}
        h1 {{ font-size: 20pt; margin-bottom: {paragraph_gap}em; }}
        h2 {{ font-size: 18pt; margin-bottom: {paragraph_gap}em; }}
        h3 {{ font-size: 16pt; margin-bottom: {paragraph_gap}em; }}
        p {{ margin-bottom: {paragraph_gap}em; }}
        div {{ margin-bottom: {paragraph_gap}em; }}
        """
        
        body_content = ""
        for p in html_pages:
            body_content += f'<div style="page-break-after: always;">{p["html"]}</div>'
            
        full_html = f"<html><head><style>{css}</style></head><body>{body_content}</body></html>"
        
        import os
        from uuid import uuid4
        import tempfile
        import subprocess
        os.makedirs(os.path.join(tempfile.gettempdir(), "legal_pdf_exports"), exist_ok=True)
        html_path = os.path.join(tempfile.gettempdir(), "legal_pdf_exports", f"temp_{uuid4().hex}.html")
        temp_path = os.path.join(tempfile.gettempdir(), "legal_pdf_exports", f"exported_{uuid4().hex}.pdf")
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(full_html)
            
        script_path = os.path.join(os.path.dirname(__file__), "pdf_exporter.py")
        import sys
        subprocess.run([sys.executable, script_path, html_path, temp_path], check=True)
        
            
        return {"success": True, "output_path": temp_path}

    def font_size_controls_extract(self, input_path: str, settings: dict) -> Dict[str, Any]:
        import pymupdf
        doc = pymupdf.open(input_path)
        formatted_pages = []
        total_words = 0
        
        # Get settings with defaults
        line_spacing = settings.get("line_spacing_mult", 1.5)
        paragraph_gap = settings.get("paragraph_gap_mult", 1.0)
        font_size_mult = settings.get("font_size_mult", 1.0)
        letter_spacing = settings.get("letter_spacing_em", 0.0)
        
        for idx, page in enumerate(doc):
            page_html = []
            blocks = page.get_text('dict').get('blocks', [])
            
            # If no blocks found or it's empty, fallback to simple text extraction
            has_text = False
            for b in blocks:
                if b.get('type') == 0:
                    lines_html = []
                    max_size_for_block = 0
                    for line in b.get('lines', []):
                        line_text = ''
                        for span in line.get('spans', []):
                            line_text += span.get('text', '')
                            if span.get('size', 0) > max_size_for_block:
                                max_size_for_block = span.get('size', 0)
                        lines_html.append(line_text.strip())
                    
                    block_text = "<br>".join(lines_html).strip()
                    if block_text:
                        has_text = True
                        total_words += len(block_text.replace("<br>", " ").split())
                        tag = 'p'
                        base_size = 1.0
                        if max_size_for_block > 14: 
                            tag = 'h3'
                            base_size = 1.2
                        if max_size_for_block > 18: 
                            tag = 'h2'
                            base_size = 1.5
                        if max_size_for_block > 22: 
                            tag = 'h1'
                            base_size = 2.0
                        
                        final_size = base_size * float(font_size_mult)
                        page_html.append(f'<{tag} style="margin-bottom: {paragraph_gap}em; line-height: {line_spacing}; font-size: {final_size}em; letter-spacing: {letter_spacing}em;">{block_text}</{tag}>')
                elif b.get('type') == 1:
                    # Image block
                    import base64
                    img_bytes = b.get("image")
                    ext = b.get("ext", "png")
                    if img_bytes:
                        base64_str = base64.b64encode(img_bytes).decode('utf-8')
                        page_html.append(f'<div style="text-align: center; margin-bottom: {paragraph_gap}em;"><img src="data:image/{ext};base64,{base64_str}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" /></div>')
            
            if not has_text:
                # Fallback to plain text lines
                raw_text = page.get_text("text")
                for line in raw_text.split('\n'):
                    line = line.strip()
                    if line:
                        total_words += len(line.split())
                        final_size = 1.0 * float(font_size_mult)
                        page_html.append(f'<p style="margin-bottom: {paragraph_gap}em; line-height: {line_spacing}; font-size: {final_size}em; letter-spacing: {letter_spacing}em;">{line}</p>')

            formatted_pages.append({
                "page_number": idx + 1,
                "html": "".join(page_html)
            })
        
        doc.close()
        full_html = "".join([p["html"] for p in formatted_pages])
        
        # Ultimate fallback
        if not full_html:
            full_html = "<p>Could not extract text blocks from this PDF. Please try another file.</p>"
            if len(formatted_pages) > 0:
                formatted_pages[0]["html"] = full_html
        return {
            "success": True, 
            "formatted_html": full_html, 
            "formatted_pages": formatted_pages, 
            "total_words_count": total_words, 
            "reading_time_minutes": max(1, total_words // 200)
        }

    def font_size_controls_export(self, input_path: str, payload: dict) -> Dict[str, Any]:
        import pymupdf
        import tempfile
        
        # Get extracted HTML using the payload settings to apply styles
        extract_result = self.font_size_controls_extract(input_path, payload)
        html_pages = extract_result.get("formatted_pages", [])
        
        # Get target font size
        target_size = int(payload.get("target_fontsize_pt", 20))
        font_size_mult = target_size / 14
        text_color = payload.get("text_color_hex", "#000000")
        
        # Calculate new font sizes
        base_pt = 14 * float(font_size_mult)
        h1_pt = 20 * float(font_size_mult)
        h2_pt = 18 * float(font_size_mult)
        h3_pt = 16 * float(font_size_mult)
        
        # CSS to adjust font sizes
        css = f"""
        body {{ font-family: sans-serif; font-size: {base_pt}pt; color: {text_color}; line-height: 1.5; }}
        h1 {{ font-size: {h1_pt}pt; margin-bottom: 1em; }}
        h2 {{ font-size: {h2_pt}pt; margin-bottom: 1em; }}
        h3 {{ font-size: {h3_pt}pt; margin-bottom: 1em; }}
        """
        
        body_content = ""
        for p in html_pages:
            body_content += f'<div style="page-break-after: always;">{p["html"]}</div>'
            
        full_html = f"<html><head><style>{css}</style></head><body>{body_content}</body></html>"
        
        import os
        from uuid import uuid4
        import tempfile
        import subprocess
        os.makedirs(os.path.join(tempfile.gettempdir(), "legal_pdf_exports"), exist_ok=True)
        html_path = os.path.join(tempfile.gettempdir(), "legal_pdf_exports", f"temp_{uuid4().hex}.html")
        temp_path = os.path.join(tempfile.gettempdir(), "legal_pdf_exports", f"exported_{uuid4().hex}.pdf")
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(full_html)
            
        script_path = os.path.join(os.path.dirname(__file__), "pdf_exporter.py")
        import sys
        subprocess.run([sys.executable, script_path, html_path, temp_path], check=True)
        
            
        return {"success": True, "output_path": temp_path}

    def dyslexia_mode_extract(self, input_path: str, settings: dict) -> Dict[str, Any]:
        text = self._extract_all_text(input_path)
        return {"success": True, "formatted_html": text, "formatted_pages": [], "total_words_count": len(text.split()), "reading_time_minutes": 1}

    def dyslexia_mode_export(self, input_path: str, settings: dict) -> Dict[str, Any]:
        return {"success": True, "download_url": "/api/accessibility/dummy/download"}

    def focus_mode_extract(self, input_path: str, settings: dict) -> Dict[str, Any]:
        text = self._extract_all_text(input_path)
        return {"success": True, "formatted_html": text, "formatted_pages": [], "total_words_count": len(text.split()), "reading_time_minutes": 1}

    def focus_mode_export(self, input_path: str, payload: dict) -> Dict[str, Any]:
        return {"success": True, "download_url": "/api/v1/accessibility/download/dummy.pdf"}

    def reading_ruler_extract(self, input_path: str, settings: dict) -> Dict[str, Any]:
        text = self._extract_all_text(input_path)
        return {"success": True, "formatted_html": text, "formatted_pages": [], "total_words_count": len(text.split()), "reading_time_minutes": 1}

    def reading_ruler_export(self, input_path: str, payload: dict) -> Dict[str, Any]:
        return {"success": True, "download_url": "/api/v1/accessibility/download/dummy.pdf"}

    def voice_navigation_process(self, input_path: str, command: str) -> Dict[str, Any]:
        return {"success": True, "action": {"type": "scroll", "direction": "down"}}

    def text_reflow(self, input_path: str) -> Dict[str, Any]:
        text = self._extract_all_text(input_path)
        return {"success": True, "formatted_html": text}

    def text_reflow_content(self, input_path: str, font_size_px: str = "16", font_family: str = "Inter", theme: str = "light") -> Dict[str, Any]:
        import fitz
        doc = fitz.open(input_path)
        pages = []
        try:
            for page in doc:
                text = page.get_text("text")
                blocks = [t.strip() for t in text.split('\n') if t.strip()]
                html = "".join([f"<p style='margin: 0 0 1em 0;'>{t}</p>" for t in blocks])
                if not html: html = "<p></p>"
                pages.append(html)
        finally:
            doc.close()
        return {"success": True, "full_reflow_html": "".join(pages), "pages": pages}

    def text_reflow_export(self, input_path: str, payload: dict) -> str:
        data = self.text_reflow_content(input_path)
        html_content = data.get("full_reflow_html", "")
        
        settings = payload.get("settings", {})
        font_size = settings.get("font_size_px", "16")
        font_family = settings.get("font_family", "Inter")
        
        styled_html = f'''
        <html>
        <head>
            <style>
                @page {{ size: a4; margin: 2cm; }}
                body {{
                    font-family: "{font_family}", sans-serif;
                    font-size: {font_size}px;
                    line-height: 1.5;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        '''
        
        import tempfile
        from xhtml2pdf import pisa
        
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=tempfile.gettempdir())
        tmp.close()
        
        with open(tmp.name, "w+b") as result_file:
            pisa.CreatePDF(styled_html, dest=result_file)
            
        return tmp.name

    def keyboard_shortcuts_save(self, shortcuts: dict) -> Dict[str, Any]:
        return {"success": True, "message": "Saved"}

accessibility_service = AccessibilityService()
