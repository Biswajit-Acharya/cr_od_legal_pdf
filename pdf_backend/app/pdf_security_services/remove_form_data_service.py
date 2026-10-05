import logging
from pathlib import Path
from typing import Dict, Any
import pikepdf
from app.core.paths import Paths
import traceback

logger = logging.getLogger(__name__)

def process(input_path: str, request_id: str) -> Dict[str, Any]:
    """
    Removes filled values from form fields in a PDF, restoring it to a blank reusable state.
    Preserves form field structure but removes the `/V` (value) and `/AP` (appearance) entries.
    """
    input_file = Path(input_path)
    if not input_file.exists():
        return {"success": False, "error": "Input file not found."}
        
    output_dir = Paths.request_output(request_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"no_forms_{input_file.name}"
    output_path = output_dir / output_filename
    
    try:
        pdf = pikepdf.Pdf.open(input_path, allow_overwriting_input=False)
        
        form_fields_detected = 0
        filled_fields_detected = 0
        cleared_fields_count = 0
        is_xfa = False
        has_acroform = "/AcroForm" in pdf.Root
        
        if has_acroform:
            acroform = pdf.Root.AcroForm
            if "/XFA" in acroform:
                is_xfa = True
        
        # We will iterate through all page annotations looking for form fields (/Widget)
        for page in pdf.pages:
            if "/Annots" in page:
                for annot in page.Annots:
                    if annot.get("/Subtype") == "/Widget":
                        form_fields_detected += 1
                        has_value = False
                        
                        # Check if it has a value or appearance
                        if "/V" in annot:
                            has_value = True
                        
                        # Some checkboxes/radios use /AS for appearance state
                        if "/AS" in annot and annot.get("/AS") != "/Off":
                            has_value = True
                            
                        # If the field is a child of a field dict, the value might be in the parent
                        if "/Parent" in annot:
                            parent = annot.Parent
                            if "/V" in parent:
                                has_value = True
                                
                        if has_value:
                            filled_fields_detected += 1
                            
                        # Now remove data
                        if "/V" in annot:
                            del annot["/V"]
                            
                        # Clear appearance stream so old text doesn't show
                        if "/AP" in annot:
                            del annot["/AP"]
                            
                        # Clear appearance state for checkboxes/radios
                        if "/AS" in annot:
                            annot["/AS"] = pikepdf.Name("/Off")
                            
                        # If value is in parent, clear it there too
                        if "/Parent" in annot:
                            parent = annot.Parent
                            if "/V" in parent:
                                del parent["/V"]
                            
                        if has_value:
                            cleared_fields_count += 1
        
        # If there's an AcroForm dictionary, we can also check the /Fields array
        # to catch fields not properly linked to page annotations
        if has_acroform:
            acroform = pdf.Root.AcroForm
            if "/Fields" in acroform:
                # Helper function to recursively traverse fields
                def process_fields(field_array):
                    nonlocal form_fields_detected, filled_fields_detected, cleared_fields_count
                    for field in field_array:
                        # Some fields don't have a Subtype, but are still fields. 
                        # If it has kids, traverse them
                        if "/Kids" in field:
                            process_fields(field.Kids)
                            
                        is_widget = field.get("/Subtype") == "/Widget"
                        # If it's a field dict but not a widget, we should still clear its /V
                        if "/V" in field:
                            if not is_widget:
                                # We might not have counted this as a widget annotation, but it holds a value
                                filled_fields_detected += 1
                                cleared_fields_count += 1
                            del field["/V"]
                        if "/AP" in field:
                            del field["/AP"]

                process_fields(acroform.Fields)
                
            # If it's XFA, we just clear the XFA array/stream, because XFA forms are XML based.
            if is_xfa:
                del acroform["/XFA"]
                # For XFA forms, it's often best to mark it as processed, though full support is complex
                cleared_fields_count += 1 

        if form_fields_detected == 0 and not is_xfa:
            return {
                "success": False,
                "error": "No fillable form fields were found in this PDF.",
                "feature": "Remove Form Data",
                "form_fields_detected": 0
            }

        if is_xfa and form_fields_detected == 0:
            return {
                "success": False,
                "error": "The PDF uses an unsupported XFA form structure which cannot be safely processed automatically.",
                "feature": "Remove Form Data"
            }

        pdf.save(output_path)
        
        # Verify the removal
        verification_passed = True
        try:
            ver_pdf = pikepdf.Pdf.open(output_path)
            for page in ver_pdf.pages:
                if "/Annots" in page:
                    for annot in page.Annots:
                        if annot.get("/Subtype") == "/Widget":
                            if "/V" in annot:
                                verification_passed = False
                            if "/Parent" in annot and "/V" in annot.Parent:
                                verification_passed = False
        except Exception:
            verification_passed = False

        return {
            "success": True,
            "feature": "Remove Form Data",
            "form_fields_detected": form_fields_detected,
            "filled_fields_detected": filled_fields_detected,
            "blank_fields": form_fields_detected - filled_fields_detected,
            "cleared_fields_count": cleared_fields_count,
            "form_type": "XFA" if is_xfa else "AcroForm",
            "verification_passed": verification_passed,
            "output_file": output_filename
        }
        
    except pikepdf.PdfError as e:
        logger.error(f"Pikepdf error during form data removal: {str(e)}")
        return {"success": False, "error": "The PDF file is corrupted or unsupported."}
    except Exception as e:
        logger.error(f"Unexpected error during form data removal: {str(e)}\n{traceback.format_exc()}")
        return {"success": False, "error": "An unexpected error occurred while processing the form."}
