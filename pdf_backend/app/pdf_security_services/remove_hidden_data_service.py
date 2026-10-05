import os
import tempfile
import uuid
from pathlib import Path
import pikepdf
from datetime import datetime

def check_digital_signature(pdf: pikepdf.Pdf) -> bool:
    """Detects if the PDF has a digital signature."""
    try:
        if "/AcroForm" in pdf.Root and "/Fields" in pdf.Root.AcroForm:
            fields = pdf.Root.AcroForm.Fields
            for field in fields:
                if field.get("/FT") == "/Sig":
                    return True
    except Exception:
        pass
    return False

def scan_pdf(pdf: pikepdf.Pdf) -> dict:
    """Scans the PDF for hidden data and returns counts/flags."""
    detected = {
        "metadata": False,
        "annotations": 0,
        "embedded_files": 0,
        "javascript": False,
        "automatic_actions": False,
        "optional_content": False
    }

    # 1. Metadata
    if len(pdf.docinfo) > 0 or "/Metadata" in pdf.Root:
        detected["metadata"] = True

    # 2. Annotations
    for page in pdf.pages:
        if "/Annots" in page:
            detected["annotations"] += len(page.Annots)

    # 3. Embedded Files
    if "/Names" in pdf.Root and "/EmbeddedFiles" in pdf.Root.Names:
        detected["embedded_files"] += 1

    # 4. JavaScript
    if "/Names" in pdf.Root and "/JavaScript" in pdf.Root.Names:
        detected["javascript"] = True
    
    # 5. Automatic Actions
    if "/OpenAction" in pdf.Root or "/AA" in pdf.Root:
        detected["automatic_actions"] = True
    for page in pdf.pages:
        if "/AA" in page:
            detected["automatic_actions"] = True

    # 6. Optional Content (Layers)
    if "/OCProperties" in pdf.Root:
        detected["optional_content"] = True

    return detected

def remove_hidden_data(pdf: pikepdf.Pdf) -> dict:
    """Removes detected hidden data from the PDF."""
    removed = {
        "metadata": False,
        "annotations": 0,
        "embedded_files": 0,
        "javascript": False,
        "automatic_actions": False,
        "optional_content": False
    }

    # 1. Metadata
    if len(pdf.docinfo) > 0:
        for key in list(pdf.docinfo.keys()):
            del pdf.docinfo[key]
        removed["metadata"] = True
    if "/Metadata" in pdf.Root:
        del pdf.Root.Metadata
        removed["metadata"] = True

    # 2. Annotations
    for page in pdf.pages:
        if "/Annots" in page:
            removed["annotations"] += len(page.Annots)
            del page.Annots

    # 3. Embedded Files
    if "/Names" in pdf.Root and "/EmbeddedFiles" in pdf.Root.Names:
        del pdf.Root.Names.EmbeddedFiles
        removed["embedded_files"] += 1

    # 4. JavaScript
    if "/Names" in pdf.Root and "/JavaScript" in pdf.Root.Names:
        del pdf.Root.Names.JavaScript
        removed["javascript"] = True

    # 5. Automatic Actions
    if "/OpenAction" in pdf.Root:
        del pdf.Root.OpenAction
        removed["automatic_actions"] = True
    if "/AA" in pdf.Root:
        del pdf.Root.AA
        removed["automatic_actions"] = True
    for page in pdf.pages:
        if "/AA" in page:
            del page.AA
            removed["automatic_actions"] = True

    # 6. Optional Content (Layers)
    if "/OCProperties" in pdf.Root:
        del pdf.Root.OCProperties
        removed["optional_content"] = True

    return removed

def process(input_path: str, request_id: str) -> dict:
    try:
        with pikepdf.open(input_path) as pdf:
            has_signature = check_digital_signature(pdf)
            detected_items = scan_pdf(pdf)
            
            removed_items = remove_hidden_data(pdf)
            
            # Save the PDF
            tmp_out = Path(tempfile.mktemp(suffix=".pdf"))
            pdf.save(str(tmp_out))

        # Re-open and verify
        verification_passed = True
        with pikepdf.open(tmp_out) as v_pdf:
            v_detected = scan_pdf(v_pdf)
            
            # If any item was detected initially but is still detected after removal, verification fails.
            if detected_items["metadata"] and v_detected["metadata"]:
                verification_passed = False
            if detected_items["annotations"] > 0 and v_detected["annotations"] > 0:
                verification_passed = False
            if detected_items["embedded_files"] > 0 and v_detected["embedded_files"] > 0:
                verification_passed = False
            if detected_items["javascript"] and v_detected["javascript"]:
                verification_passed = False
            if detected_items["automatic_actions"] and v_detected["automatic_actions"]:
                verification_passed = False
            if detected_items["optional_content"] and v_detected["optional_content"]:
                verification_passed = False

        # Prepare output
        out_filename = f"cleaned_{uuid.uuid4().hex[:8]}.pdf"
        out_dir = Path("app/static/downloads")
        out_dir.mkdir(parents=True, exist_ok=True)
        final_out = out_dir / out_filename
        
        # Move temp to final
        import shutil
        shutil.move(str(tmp_out), str(final_out))
        
        return {
            "success": True,
            "feature": "Remove Hidden Data",
            "items_detected": detected_items,
            "items_removed": removed_items,
            "verification_passed": verification_passed,
            "signature_warning": has_signature,
            "output_file": final_out.name,
            "download_url": f"/api/pdf/security/download/{request_id}/{final_out.name}"
        }

    except pikepdf.PasswordError:
        raise ValueError("PDF is encrypted and requires the correct password before sanitization can be performed.")
    except pikepdf.PdfError as e:
        raise ValueError(f"Invalid or corrupted PDF file: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to process PDF: {str(e)}")
