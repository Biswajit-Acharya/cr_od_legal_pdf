import fitz
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class BlackoutAreasService:
    def apply_blackout(self, input_path: str, output_path: str, areas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply permanent redaction to the given areas."""
        try:
            doc = fitz.open(input_path)
            for area in areas:
                page_idx = area.get("page", 1) - 1
                rect_coords = area.get("rect")
                if 0 <= page_idx < len(doc) and rect_coords:
                    page = doc[page_idx]
                    rect = fitz.Rect(rect_coords)
                    # Add redaction annotation (crosses out text and objects beneath)
                    page.add_redact_annot(rect, fill=(0, 0, 0))
            
            # Apply all redactions across all pages permanently
            for page in doc:
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                
            doc.save(output_path, garbage=3, deflate=True)
            doc.close()
            return {"status": "success", "message": "Redaction applied successfully"}
        except Exception as e:
            raise ValueError(f"Failed to apply blackout: {str(e)}")

blackout_areas_service = BlackoutAreasService()
