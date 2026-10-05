"""
Service to remove JavaScript from PDF files.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

import pikepdf
from pikepdf import Pdf, Dictionary, Array, Name

from app.core.paths import Paths
from app.utils.filename import output_filename

logger = logging.getLogger(__name__)


class RemoveJavascriptService:
    """Service to detect and remove embedded PDF JavaScript."""

    def _is_javascript_action(self, obj: Any) -> bool:
        """Helper to determine if a PDF object is a JavaScript Action."""
        if isinstance(obj, Dictionary):
            s = obj.get(Name.S)
            if s == Name.JavaScript:
                return True
        return False

    def _clean_action_dict(self, dictionary: Dictionary, key: Name, js_count: list[int]) -> None:
        """Check a specific key in a dictionary, if it's JS, remove it."""
        if key in dictionary:
            obj = dictionary[key]
            if self._is_javascript_action(obj):
                del dictionary[key]
                js_count[0] += 1

    def _clean_additional_actions(self, dictionary: Dictionary, js_count: list[int]) -> None:
        """Clean an /AA dictionary of JavaScript actions."""
        if Name.AA in dictionary:
            aa = dictionary.AA
            if not isinstance(aa, Dictionary):
                return
            to_delete = []
            for k, v in aa.items():
                if self._is_javascript_action(v):
                    to_delete.append(k)
            for k in to_delete:
                del aa[k]
                js_count[0] += 1
            if len(aa) == 0:
                del dictionary.AA

    def _sanitize_pdf(self, pdf: Pdf) -> Dict[str, Any]:
        """Perform the actual sanitization on the pikepdf object tree."""
        metrics = {
            "document_level_javascript": 0,
            "javascript_actions": 0,
            "open_action_javascript": 0,
            "additional_action_javascript": 0,
            "annotation_javascript": 0,
            "form_javascript": 0
        }

        # 1. Document Level /Names /JavaScript
        if Name.Names in pdf.Root and Name.JavaScript in pdf.Root.Names:
            del pdf.Root.Names.JavaScript
            metrics["document_level_javascript"] += 1

        # 2. Document OpenAction
        if Name.OpenAction in pdf.Root:
            action = pdf.Root.OpenAction
            if self._is_javascript_action(action):
                del pdf.Root.OpenAction
                metrics["open_action_javascript"] += 1

        # 3. Document Additional Actions (AA)
        if Name.AA in pdf.Root:
            count_holder = [0]
            self._clean_additional_actions(pdf.Root, count_holder)
            metrics["additional_action_javascript"] += count_holder[0]

        # 4. Pages and Annotations
        for page in pdf.pages:
            # Page AA
            count_holder = [0]
            self._clean_additional_actions(page, count_holder)
            metrics["additional_action_javascript"] += count_holder[0]

            # Annotations
            if Name.Annots in page:
                annots = page.Annots
                if isinstance(annots, Array):
                    for annot in annots:
                        if isinstance(annot, Dictionary):
                            # /A (Action)
                            c1 = [0]
                            self._clean_action_dict(annot, Name.A, c1)
                            metrics["annotation_javascript"] += c1[0]
                            # /AA (Additional Actions)
                            c2 = [0]
                            self._clean_additional_actions(annot, c2)
                            metrics["annotation_javascript"] += c2[0]

        # 5. AcroForm
        if Name.AcroForm in pdf.Root and Name.Fields in pdf.Root.AcroForm:
            def clean_fields(fields_array):
                if not isinstance(fields_array, Array):
                    return
                for field in fields_array:
                    if isinstance(field, Dictionary):
                        c1 = [0]
                        self._clean_action_dict(field, Name.A, c1)
                        metrics["form_javascript"] += c1[0]

                        c2 = [0]
                        self._clean_additional_actions(field, c2)
                        metrics["form_javascript"] += c2[0]

                        if Name.Kids in field:
                            clean_fields(field.Kids)
            clean_fields(pdf.Root.AcroForm.Fields)

        total_removed = sum(metrics.values())
        return {
            "removed_count": total_removed,
            "metrics": metrics
        }

    def _detect_signature(self, pdf: Pdf) -> bool:
        """Check if PDF has digital signatures in AcroForm SigFlags."""
        if Name.AcroForm in pdf.Root:
            acro = pdf.Root.AcroForm
            if Name.SigFlags in acro:
                flags = int(acro.SigFlags)
                return (flags & 1) != 0 # Bit 1 is SignaturesExist
        return False

    def remove_javascript(self, input_path: str, request_id: str) -> Dict[str, Any]:
        """
        Main entrypoint.
        Detects, removes, re-verifies, and generates security report.
        """
        src = Path(input_path)
        if not src.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        out_dir = Paths.request_output(request_id)
        out_name = output_filename(operation="no_javascript")
        out_path = out_dir / out_name

        try:
            # First pass: Detection and sanitization
            with pikepdf.open(src) as pdf:
                # Detect encrypted
                if pdf.is_encrypted:
                    raise ValueError("PDF is encrypted and requires the correct password before JavaScript sanitization can be performed.")

                is_signed = self._detect_signature(pdf)
                original_pages = len(pdf.pages)

                # Dry run scan to see if JS exists? We can just sanitize and see if anything was removed.
                sanitization_results = self._sanitize_pdf(pdf)
                total_removed = sanitization_results["removed_count"]

                # If no JS found, don't modify the file unnecessarily
                if total_removed == 0:
                    return {
                        "success": True,
                        "feature": "Remove JavaScript",
                        "original_filename": src.name,
                        "javascript_detected": False,
                        "javascript_locations": [],
                        "javascript_count": 0,
                        "removed_count": 0,
                        "verification_passed": True,
                        "pages_preserved": True,
                        "digital_signature_detected": is_signed,
                        "message": "No embedded PDF JavaScript was detected.",
                        "output_file": src.name, 
                        "download_url": f"/api/pdf/security/download/{request_id}/{src.name}"
                    }

                # Save sanitized version to temp file
                tmp_out = Path(tempfile.mktemp(suffix=".pdf"))
                pdf.save(str(tmp_out))

            # Verification pass
            with pikepdf.open(tmp_out) as verified_pdf:
                ver_results = self._sanitize_pdf(verified_pdf)
                if ver_results["removed_count"] > 0:
                    # Very rare: some nested JS evaded removal
                    raise ValueError("Failed to completely remove JavaScript due to complex embedded structures.")
                
                final_pages = len(verified_pdf.pages)

            # Move verified file to final destination
            shutil.move(str(tmp_out), str(out_path))

            # Build detailed locations array
            locations = []
            metrics = sanitization_results["metrics"]
            if metrics["document_level_javascript"] > 0: locations.append("Document-level JavaScript")
            if metrics["open_action_javascript"] > 0: locations.append("OpenAction")
            if metrics["additional_action_javascript"] > 0: locations.append("Additional Actions")
            if metrics["annotation_javascript"] > 0: locations.append("Annotations")
            if metrics["form_javascript"] > 0: locations.append("Form Fields")

            report = {
                "success": True,
                "feature": "Remove JavaScript",
                "original_filename": src.name,
                "javascript_detected": True,
                "javascript_locations": locations,
                "javascript_count": total_removed,
                "removed_count": total_removed,
                "verification_passed": True,
                "pages_preserved": original_pages == final_pages,
                "digital_signature_detected": is_signed,
                "message": "PDF JavaScript was removed and the sanitized PDF was successfully verified.",
                "output_file": out_name,
                "download_url": f"/api/pdf/security/download/{request_id}/{out_name}"
            }

            if is_signed:
                report["signature_validity_after_modification"] = "requires_reverification"

            return report

        except pikepdf.PasswordError:
            logger.warning("Password protected PDF detected in remove_javascript.")
            raise ValueError("PDF is encrypted and requires the correct password before JavaScript sanitization can be performed.")
        except pikepdf.PdfError as e:
            logger.error(f"Corrupted or invalid PDF detected: {e}")
            raise ValueError(f"Invalid or corrupted PDF file: {str(e)}")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"remove_javascript error: {e}", exc_info=True)
            raise ValueError(f"Failed to process PDF: {str(e)}")
        finally:
            if 'tmp_out' in locals() and tmp_out.exists():
                try:
                    tmp_out.unlink()
                except Exception:
                    pass

remove_javascript_service = RemoveJavascriptService()
