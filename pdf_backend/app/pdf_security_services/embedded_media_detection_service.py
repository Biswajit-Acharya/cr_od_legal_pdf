import fitz
import os
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EmbeddedMediaDetectionService:
    def __init__(self):
        pass

    async def analyze(self, filepath: Path, original_filename: str) -> Dict[str, Any]:
        """Inspects the PDF for media and embedded content."""
        if not filepath.exists():
            return {"success": False, "error": "File not found."}

        try:
            doc = fitz.open(filepath)
            
            if doc.is_encrypted:
                doc.close()
                return {"success": False, "error": "Cannot analyze an encrypted PDF. Please unlock it first."}

            media_findings = []
            
            total_images = 0
            total_audio = 0
            total_video = 0
            total_multimedia_annots = 0
            total_unknown = 0
            
            # Check Embedded Files
            emb_count = doc.embfile_count()
            if emb_count > 0:
                names = doc.embfile_names()
                for i, name in enumerate(names):
                    info = doc.embfile_info(name)
                    media_findings.append({
                        "Type": "Embedded File",
                        "Location_Page": "Document Level",
                        "Filename": name,
                        "MIME_Type": "Unknown/Binary",
                        "Size": f"{info.get('size', 0)} bytes",
                        "Status": "Review Required"
                    })
                    
            # Page level media detection
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Check Images
                image_list = page.get_images(full=True)
                for img_idx, img in enumerate(image_list):
                    total_images += 1
                    # Only report a few images so the UI isn't flooded if a doc has 1000s
                    if total_images <= 25:
                        xref = img[0]
                        media_findings.append({
                            "Type": "Image",
                            "Location_Page": str(page_num + 1),
                            "Object": f"xref {xref}",
                            "Size": "Varies by resolution",
                            "Status": "Detected"
                        })
                
                # Check Multimedia annotations (/Screen, /Movie, /3D)
                for annot in page.annots():
                    if annot.type[0] in [fitz.PDF_ANNOT_SCREEN, fitz.PDF_ANNOT_MOVIE, fitz.PDF_ANNOT_3D]:
                        total_multimedia_annots += 1
                        media_findings.append({
                            "Type": "Multimedia Annotation",
                            "Location_Page": str(page_num + 1),
                            "Object": f"Annot type {annot.type[1]}",
                            "Size": "Embedded Stream",
                            "Status": "Review Required"
                        })

            doc.close()
            
            total_objects = total_images + total_audio + total_video + emb_count + total_multimedia_annots + total_unknown
            
            if emb_count > 0 or total_multimedia_annots > 0:
                security_assessment = "Potentially suspicious embedded content requires review."
            else:
                security_assessment = "No suspicious media indicators detected."

            return {
                "success": True,
                "status": "completed",
                "summary": {
                    "Total media objects": total_objects,
                    "Images": total_images,
                    "Audio": total_audio,
                    "Video": total_video,
                    "Embedded files": emb_count,
                    "Multimedia annotations": total_multimedia_annots,
                    "Unknown/other media": total_unknown
                },
                "findings": media_findings,
                "security_assessment": security_assessment
            }

        except Exception as e:
            logger.error(f"Error in media detection: {e}", exc_info=True)
            return {"success": False, "error": f"Unable to analyze this PDF because the document is corrupted or uses an unsupported structure."}

embedded_media_detection_service = EmbeddedMediaDetectionService()
