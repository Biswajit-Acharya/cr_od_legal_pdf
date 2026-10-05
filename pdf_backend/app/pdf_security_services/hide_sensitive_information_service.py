import fitz
import logging
import re
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class HideSensitiveInformationService:
    def detect_sensitive_info(self, input_path: str) -> Dict[str, Any]:
        """Detect sensitive information like emails, phones, SSNs."""
        try:
            doc = fitz.open(input_path)
            detected = []
            
            patterns = {
                "Email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
                "Phone": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
                "SSN/ID": r"\b\d{3}-\d{2}-\d{4}\b",
                "Credit Card": r"\b(?:\d[ -]*?){13,16}\b"
            }
            
            item_id = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                for p_type, p_regex in patterns.items():
                    matches = re.finditer(p_regex, text)
                    for match in matches:
                        match_text = match.group()
                        text_instances = page.search_for(match_text)
                        for inst in text_instances:
                            detected.append({
                                "id": str(item_id),
                                "type": p_type,
                                "page": page_num + 1,
                                "text": match_text,
                                "rect": [inst.x0, inst.y0, inst.x1, inst.y1],
                                "confidence": "High"
                            })
                            item_id += 1
            doc.close()
            
            # Group summary
            summary = {}
            for item in detected:
                summary[item["type"]] = summary.get(item["type"], 0) + 1

            return {
                "status": "success", 
                "detected_items": detected,
                "summary": {
                    "total_detected": len(detected),
                    "types": summary
                }
            }
        except Exception as e:
            raise ValueError(f"Failed to detect sensitive info: {str(e)}")

hide_sensitive_information_service = HideSensitiveInformationService()
