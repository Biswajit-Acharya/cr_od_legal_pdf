"""
MOBI to PDF conversion service.
Extracts MOBI to EPUB (KF8) or HTML (MOBI 7) and proxies to the respective services.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Dict, Any
import mobi
from bs4 import BeautifulSoup
import urllib.parse
import os

from app.core.paths import Paths
from app.Convert_to_pdf_services.epub_to_pdf_service import epub_to_pdf_service
from app.Convert_to_pdf_services.html_to_pdf_service import html_to_pdf_service

logger = logging.getLogger(__name__)

class MobiToPdfService:
    
    def validate_and_parse(self, file_path: Path, request_id: str) -> Dict[str, Any]:
        """Validate MOBI and extract metadata for preview."""
        extract_dir = Paths.request_temp(request_id) / "mobi_extract"
        
        try:
            # Clean if exists
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract MOBI
            mobi_tempdir, extracted_path = mobi.extract(str(file_path))
            extracted_path = Path(extracted_path)
            
            if extracted_path.suffix.lower() == ".epub":
                # MOBI 8 (KF8) - Extracted as EPUB
                # Proxy to EpubToPdfService
                # First, copy epub to our temp dir so we don't rely on mobi's hidden tempdir
                our_epub = extract_dir / extracted_path.name
                shutil.copy2(extracted_path, our_epub)
                
                # Call epub service validation
                result = epub_to_pdf_service.validate_and_parse(our_epub, request_id)
                # Ensure we track the type
                result["mobi_internal_type"] = "epub"
                result["internal_file"] = our_epub.name
                
                # Cleanup mobi's original tempdir
                shutil.rmtree(mobi_tempdir, ignore_errors=True)
                return result
                
            elif extracted_path.suffix.lower() == ".html":
                # MOBI 7 - Extracted as HTML
                our_html = extract_dir / extracted_path.name
                shutil.copy2(extracted_path, our_html)
                
                # Basic metadata extraction from HTML
                title = "Unknown Title"
                author = "Unknown Author"
                cover_image = None
                
                try:
                    with open(our_html, "r", encoding="utf-8", errors="ignore") as f:
                        html_content = f.read(20000) # Read start of file
                        soup = BeautifulSoup(html_content, "html.parser")
                        
                        # Try to find a title in headings or bold text
                        title_tag = soup.find("title")
                        if title_tag and title_tag.string:
                            title = title_tag.string.strip()
                        else:
                            for tag in ['h1', 'h2', 'h3', 'h4', 'b']:
                                elements = soup.find_all(tag)
                                if elements:
                                    title = elements[0].text.strip()
                                    if len(elements) > 1 and author == "Unknown Author":
                                        author = elements[1].text.strip()
                                    break
                                    
                        # Try to find the first image to use as cover
                        img_tag = soup.find("img")
                        if img_tag and img_tag.get("src"):
                            src = img_tag.get("src")
                            img_path = (our_html.parent / urllib.parse.unquote(src)).resolve()
                            if img_path.exists():
                                import base64
                                with open(img_path, "rb") as img_file:
                                    encoded = base64.b64encode(img_file.read()).decode("utf-8")
                                    mime_type = "image/jpeg" if img_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                                    cover_image = f"data:{mime_type};base64,{encoded}"
                except Exception as e:
                    logger.warning(f"MOBI 7 parsing warning: {e}")
                    pass
                
                # Cleanup mobi tempdir
                shutil.rmtree(mobi_tempdir, ignore_errors=True)
                
                return {
                    "title": title,
                    "author": author,
                    "chapter_count": 1,
                    "cover_image": cover_image,
                    "mobi_internal_type": "html",
                    "internal_file": our_html.name,
                    "extract_dir": str(extract_dir)
                }
                
            else:
                shutil.rmtree(mobi_tempdir, ignore_errors=True)
                raise ValueError("Unsupported MOBI extraction format.")
                
        except Exception as e:
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise ValueError(f"MOBI validation failed: {str(e)}")

    async def process(
        self,
        request_id: str,
        filename: str,
        config: Dict[str, Any],
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process the extracted MOBI to PDF."""
        file_path = Paths.request_upload(request_id) / filename
        if not file_path.exists():
            raise ValueError("MOBI file not found.")
            
        mobi_internal_type = parsed_data.get("mobi_internal_type")
        internal_file = parsed_data.get("internal_file")
        extract_dir = Paths.request_temp(request_id) / "mobi_extract"
        
        if not extract_dir.exists() or not internal_file:
            # Need to re-extract (e.g., worker restart or clean)
            parsed_data = self.validate_and_parse(file_path, request_id)
            mobi_internal_type = parsed_data.get("mobi_internal_type")
            internal_file = parsed_data.get("internal_file")
            extract_dir = Path(parsed_data["extract_dir"]) if "extract_dir" in parsed_data else Paths.request_temp(request_id) / "mobi_extract"

        try:
            if mobi_internal_type == "epub":
                # Route to EPUB service
                # The epub_to_pdf_service.process normally expects the original filename inside the request upload folder.
                # Since we extracted an EPUB, we need to trick the EPUB service.
                epub_path = extract_dir / internal_file
                # Copy this temporary EPUB to the upload dir as a fake uploaded file so the service can find it
                fake_epub_filename = f"internal_{request_id}.epub"
                fake_epub_path = Paths.request_upload(request_id) / fake_epub_filename
                shutil.copy2(epub_path, fake_epub_path)
                
                # Execute epub processing
                result = await epub_to_pdf_service.process(
                    request_id=request_id,
                    filename=fake_epub_filename,
                    config=config
                )
                
                # Rename the output PDF to match the original MOBI name
                final_pdf_name = filename.rsplit(".", 1)[0] + ".pdf"
                result_pdf_path = Paths.request_output(request_id) / result["filename"]
                final_pdf_path = Paths.request_output(request_id) / final_pdf_name
                
                if result_pdf_path.exists() and result_pdf_path != final_pdf_path:
                    shutil.move(result_pdf_path, final_pdf_path)
                    
                result["filename"] = final_pdf_name
                result["download_url"] = f"/api/convert-to-pdf/mobi-to-pdf/download/{request_id}/{final_pdf_name}"
                result["view_url"] = f"/api/convert-to-pdf/mobi-to-pdf/view/{request_id}"
                
                return result
                
            elif mobi_internal_type == "html":
                # Route to HTML service
                html_path = extract_dir / internal_file
                with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                    html_content = f.read()
                    
                # Fix image URLs if the HTML references them relatively
                # MOBI 7 html might have inline images or relative images in the same folder.
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Inject Unicode fonts
                style_tag = soup.new_tag("style")
                style_tag.string = "body, p, div, span, h1, h2, h3, h4, h5, h6 { font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Helvetica, Arial, 'Nirmala UI', 'Microsoft YaHei', 'Meiryo', 'Malgun Gothic', 'Arial Unicode MS', sans-serif; }"
                if soup.head:
                    soup.head.append(style_tag)
                else:
                    head = soup.new_tag("head")
                    head.append(style_tag)
                    soup.insert(0, head)
                
                for img in soup.find_all('img'):
                    src = img.get('src')
                    if src and not src.startswith(('http://', 'https://', 'data:')):
                        img_path = (html_path.parent / urllib.parse.unquote(src)).resolve()
                        if img_path.exists():
                            img['src'] = f"file:///{img_path.as_posix()}"
                            
                html_content = str(soup)
                
                final_pdf_name = filename.rsplit(".", 1)[0] + ".pdf"
                
                result = await html_to_pdf_service.process(
                    request_id=request_id,
                    input_type="html",
                    content=html_content,
                    page_size=config.get("page_size", "A4"),
                    orientation=config.get("orientation", "portrait"),
                    margin_preset=config.get("margin_preset", "normal"),
                    custom_margin_top=config.get("custom_margin_top", "0"),
                    custom_margin_right=config.get("custom_margin_right", "0"),
                    custom_margin_bottom=config.get("custom_margin_bottom", "0"),
                    custom_margin_left=config.get("custom_margin_left", "0"),
                    custom_page_width="",
                    custom_page_height="",
                    custom_page_unit="mm",
                    print_background=True,
                    header_text=config.get("header_text", ""),
                    footer_text=config.get("footer_text", ""),
                    page_numbers=config.get("page_numbers", False),
                    title=config.get("pdf_title") or parsed_data.get("title", ""),
                    author=config.get("pdf_author") or parsed_data.get("author", ""),
                    subject="",
                    keywords="",
                    password=config.get("password", ""),
                    output_filename=final_pdf_name
                )
                
                # Replace download url route
                result["download_url"] = f"/api/convert-to-pdf/mobi-to-pdf/download/{request_id}/{final_pdf_name}"
                result["view_url"] = f"/api/convert-to-pdf/mobi-to-pdf/view/{request_id}"
                
                return result
            else:
                raise ValueError("Unsupported extraction state.")
                
        except Exception as e:
            logger.error(f"MOBI process error: {str(e)}")
            raise ValueError(f"Failed to convert MOBI: {str(e)}")
            
        finally:
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)

mobi_to_pdf_service = MobiToPdfService()
