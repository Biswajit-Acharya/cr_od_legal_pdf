import os
import fitz  # PyMuPDF
import base64
import json
from fastapi import UploadFile, HTTPException
from app.utils.file_handler import save_upload_file_tmp
from app.core.paths import get_output_path
import uuid
import datetime

class PdfSignService:
    @staticmethod
    async def process_pdf_sign(file: UploadFile, signatures_json: str):
        """
        Process the PDF and apply the elements (signatures, initials, date, time).
        signatures_json format:
        [
            {
                "id": "uuid",
                "type": "signature" | "initial" | "date" | "time",
                "page": 1,
                "x": 100,
                "y": 200,
                "width": 150,
                "height": 50,
                "data": "data:image/png;base64,iVBORw..." or text content for date/time
            }
        ]
        """
        await file.seek(0)
        temp_input_path = await save_upload_file_tmp(file)
        
        file_name, ext = os.path.splitext(file.filename)
        output_filename = f"{file_name}_signed_{uuid.uuid4().hex[:6]}{ext}"
        output_path = get_output_path(output_filename)

        try:
            elements = json.loads(signatures_json)
            doc = None
            doc = fitz.open(temp_input_path)

            for el in elements:
                page_num = int(el.get("page", 1)) - 1
                if page_num < 0 or page_num >= len(doc):
                    raise HTTPException(status_code=400, detail=f"Invalid page number {page_num + 1}")

                page = doc[page_num]

                x0 = float(el.get("x", 0))
                y0 = float(el.get("y", 0))
                w = float(el.get("width", 100))
                h = float(el.get("height", 50))
                rect = fitz.Rect(x0, y0, x0 + w, y0 + h)
                
                el_type = el.get("type", "signature")
                el_data = el.get("data", "")

                if el_type in ["signature", "initial"] and el_data.startswith("data:image"):
                    b64_data = el_data.split(",")[1] if "," in el_data else el_data
                    img_bytes = base64.b64decode(b64_data)
                    page.insert_image(rect, stream=img_bytes, keep_proportion=False)
                elif el_type in ["date", "time"] or (el_type in ["signature", "initial"] and not el_data.startswith("data:image")):
                    # It's a text element
                    # Validate date/time timestamp on server if needed, here we just trust the client format or use server time
                    text_content = el_data
                    if el_type == "date" and not text_content:
                        text_content = datetime.datetime.now().strftime("%Y-%m-%d")
                    elif el_type == "time" and not text_content:
                        text_content = datetime.datetime.now().strftime("%H:%M:%S")

                    # Draw text inside rect
                    page.insert_textbox(rect, text_content, fontsize=h*0.8, fontname="helv", align=fitz.TEXT_ALIGN_CENTER)

            doc.save(str(output_path), garbage=4, deflate=True, clean=True)

            return {
                "success": True,
                "message": "PDF signed successfully",
                "filename": output_filename,
                "downloadUrl": f"/api/pdf/signature/download/{output_filename}"
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error signing PDF: {str(e)}")
        finally:
            if 'doc' in locals() and doc is not None and not doc.is_closed:
                doc.close()
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)

