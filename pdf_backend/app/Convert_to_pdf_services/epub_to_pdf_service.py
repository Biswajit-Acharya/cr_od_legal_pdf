import os
import zipfile
import shutil
import logging
import base64
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from app.core.paths import Paths
from app.Convert_to_pdf_services.html_to_pdf_service import html_to_pdf_service

logger = logging.getLogger(__name__)

class EpubToPdfService:
    def __init__(self):
        self.ns = {
            'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'ncx': 'http://www.daisy.org/z3986/2005/ncx/'
        }

    def _extract_epub(self, epub_path: Path, extract_dir: Path):
        """Safely extract EPUB to a temporary directory."""
        if not zipfile.is_zipfile(epub_path):
            raise ValueError("File is not a valid EPUB (ZIP) archive.")
            
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            # Prevent path traversal
            for member in zip_ref.namelist():
                if member.startswith('/') or '..' in member:
                    continue
                zip_ref.extract(member, extract_dir)

    def _find_opf_path(self, extract_dir: Path) -> Path:
        """Find the .opf file from container.xml."""
        container_path = extract_dir / "META-INF" / "container.xml"
        if not container_path.exists():
            raise ValueError("Invalid EPUB: META-INF/container.xml not found.")
            
        tree = ET.parse(container_path)
        root = tree.getroot()
        rootfiles = root.find('.//container:rootfile', self.ns)
        if rootfiles is None:
            raise ValueError("Invalid EPUB: No rootfile found in container.xml.")
            
        opf_path = rootfiles.get('full-path')
        if not opf_path:
            raise ValueError("Invalid EPUB: full-path attribute missing in container.xml.")
            
        full_opf_path = extract_dir / opf_path
        if not full_opf_path.exists():
            raise ValueError(f"Invalid EPUB: OPF file {opf_path} not found.")
            
        return full_opf_path

    def _parse_opf(self, opf_path: Path) -> Dict[str, Any]:
        """Parse metadata, manifest, and spine from OPF."""
        tree = ET.parse(opf_path)
        root = tree.getroot()
        
        # Metadata
        metadata = {
            "title": "Unknown Title",
            "author": "Unknown Author",
            "language": "en"
        }
        meta_node = root.find('opf:metadata', self.ns)
        if meta_node is not None:
            title_node = meta_node.find('dc:title', self.ns)
            if title_node is not None and title_node.text:
                metadata['title'] = title_node.text
                
            creator_node = meta_node.find('dc:creator', self.ns)
            if creator_node is not None and creator_node.text:
                metadata['author'] = creator_node.text
                
            lang_node = meta_node.find('dc:language', self.ns)
            if lang_node is not None and lang_node.text:
                metadata['language'] = lang_node.text

        # Manifest
        manifest = {}
        manifest_node = root.find('opf:manifest', self.ns)
        if manifest_node is not None:
            for item in manifest_node.findall('opf:item', self.ns):
                item_id = item.get('id')
                href = item.get('href')
                media_type = item.get('media-type')
                if item_id and href:
                    # Resolve href relative to OPF path
                    manifest[item_id] = {
                        "href": urllib.parse.unquote(href),
                        "media_type": media_type
                    }

        # Spine
        spine = []
        spine_node = root.find('opf:spine', self.ns)
        toc_id = None
        if spine_node is not None:
            toc_id = spine_node.get('toc')
            for itemref in spine_node.findall('opf:itemref', self.ns):
                idref = itemref.get('idref')
                if idref:
                    spine.append(idref)
                    
        return {
            "metadata": metadata,
            "manifest": manifest,
            "spine": spine,
            "toc_id": toc_id
        }

    def _get_cover_base64(self, opf_path: Path, opf_data: Dict[str, Any]) -> Optional[str]:
        """Try to find and return the cover image as base64."""
        tree = ET.parse(opf_path)
        root = tree.getroot()
        meta_node = root.find('opf:metadata', self.ns)
        
        cover_id = None
        if meta_node is not None:
            for meta in meta_node.findall('opf:meta', self.ns):
                if meta.get('name') == 'cover':
                    cover_id = meta.get('content')
                    break
                    
        if cover_id and cover_id in opf_data['manifest']:
            cover_href = opf_data['manifest'][cover_id]['href']
            cover_path = opf_path.parent / cover_href
            if cover_path.exists():
                try:
                    with open(cover_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                    ext = cover_path.suffix.lower()
                    mime = "image/jpeg"
                    if ext == ".png": mime = "image/png"
                    elif ext == ".gif": mime = "image/gif"
                    return f"data:{mime};base64,{b64}"
                except Exception as e:
                    logger.warning(f"Failed to read cover image: {str(e)}")
        return None

    def validate_and_parse(self, file_path: Path, request_id: str) -> Dict[str, Any]:
        """Validate EPUB and return metadata for preview."""
        extract_dir = Paths.request_temp(request_id) / "epub_extract"
        
        try:
            # Clean if exists
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            self._extract_epub(file_path, extract_dir)
            opf_path = self._find_opf_path(extract_dir)
            opf_data = self._parse_opf(opf_path)
            
            cover_b64 = self._get_cover_base64(opf_path, opf_data)
            
            # Count chapters
            chapter_count = len([s for s in opf_data['spine'] if s in opf_data['manifest']])
            
            return {
                "title": opf_data['metadata']['title'],
                "author": opf_data['metadata']['author'],
                "chapter_count": chapter_count,
                "cover_image": cover_b64,
                "extract_dir": str(extract_dir), # Internal use for process
                "opf_path": str(opf_path) # Internal use for process
            }
            
        except Exception as e:
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise ValueError(f"EPUB validation failed: {str(e)}")

    def _build_unified_html(
        self, 
        opf_path: Path, 
        opf_data: Dict[str, Any], 
        config: Dict[str, Any]
    ) -> str:
        """Merge all spine HTML into a single document and rewrite local paths."""
        base_dir = opf_path.parent
        
        merged_html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='utf-8'>",
            "<style>",
            "body, p, div, span, h1, h2, h3, h4, h5, h6 { font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Helvetica, Arial, 'Nirmala UI', 'Microsoft YaHei', 'Meiryo', 'Malgun Gothic', 'Arial Unicode MS', sans-serif; }",
            "body { max-width: 100%; overflow-x: hidden; }",
            "img { max-width: 100%; height: auto; page-break-inside: avoid; }",
            ".chapter-break { page-break-before: always; }",
            "</style>"
        ]
        
        # Add CSS links explicitly by resolving relative paths to absolute file:// paths
        for item_id, item in opf_data['manifest'].items():
            if item.get('media_type') == 'text/css':
                css_path = (base_dir / item['href']).resolve()
                if css_path.exists():
                    merged_html.append(f"<link rel='stylesheet' type='text/css' href='file:///{css_path.as_posix()}'>")
                    
        merged_html.append("</head><body>")
        
        new_chapter_page = config.get("new_chapter_page", True)
        preserve_cover = config.get("preserve_cover", True)
        
        # Add cover
        if preserve_cover:
            cover_b64 = self._get_cover_base64(opf_path, opf_data)
            if cover_b64:
                merged_html.append(f"<div class='cover-page' style='text-align: center;'><img src='{cover_b64}' style='max-height: 100vh;'></div>")
                if new_chapter_page:
                    merged_html.append("<div class='chapter-break'></div>")

        # Process chapters
        for i, item_id in enumerate(opf_data['spine']):
            if item_id not in opf_data['manifest']:
                continue
                
            item_href = opf_data['manifest'][item_id]['href']
            # handle anchors in spine hrefs
            file_part = item_href.split('#')[0]
            chapter_path = base_dir / file_part
            
            if not chapter_path.exists():
                continue
                
            try:
                with open(chapter_path, 'r', encoding='utf-8') as f:
                    chapter_html = f.read()
            except Exception:
                continue
                
            soup = BeautifulSoup(chapter_html, 'html.parser')
            body = soup.find('body')
            if not body:
                body = soup
                
            # Rewrite img src
            for img in body.find_all('img'):
                src = img.get('src')
                if src and not src.startswith(('http://', 'https://', 'data:')):
                    img_path = (chapter_path.parent / urllib.parse.unquote(src)).resolve()
                    if img_path.exists():
                        img['src'] = f"file:///{img_path.as_posix()}"
                        
            # Rewrite SVG image href
            for image in body.find_all('image'):
                href = image.get('href') or image.get('xlink:href')
                if href and not href.startswith(('http://', 'https://', 'data:')):
                    img_path = (chapter_path.parent / urllib.parse.unquote(href)).resolve()
                    if img_path.exists():
                        if image.has_attr('href'): image['href'] = f"file:///{img_path.as_posix()}"
                        if image.has_attr('xlink:href'): image['xlink:href'] = f"file:///{img_path.as_posix()}"
                        
            # We don't necessarily rewrite internal anchor links (href) here since they might break across the merged doc
            # But Playwright doesn't typically follow them in PDF anyway unless they are anchor IDs on the same page.
            
            chapter_content = str(body)
            # Remove <body> tags if they were preserved
            chapter_content = chapter_content.replace('<body>', '').replace('</body>', '')
            
            # Add chapter separator
            if i > 0 and new_chapter_page:
                merged_html.append("<div class='chapter-break'></div>")
                
            merged_html.append(f"<div class='epub-chapter' id='chapter_{i}'>")
            merged_html.append(chapter_content)
            merged_html.append("</div>")
            
        merged_html.append("</body></html>")
        return "\n".join(merged_html)

    async def process(
        self,
        request_id: str,
        filename: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert EPUB to PDF using unified HTML and HtmlToPdfService."""
        file_path = Paths.request_upload(request_id) / filename
        if not file_path.exists():
            raise ValueError("EPUB file not found.")
            
        extract_dir = Paths.request_temp(request_id) / "epub_extract"
        
        try:
            # We must extract it again in case this is a separate request or worker
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            self._extract_epub(file_path, extract_dir)
            opf_path = self._find_opf_path(extract_dir)
            opf_data = self._parse_opf(opf_path)
            
            # Build unified HTML
            unified_html = self._build_unified_html(opf_path, opf_data, config)
            
            # Setup PDF Config
            pdf_filename = filename
            if pdf_filename.lower().endswith(".epub"):
                pdf_filename = pdf_filename[:-5] + ".pdf"
            elif not pdf_filename.lower().endswith(".pdf"):
                pdf_filename += ".pdf"
                
            # Note: We rely on HtmlToPdfService to handle the Chromium instance.
            # Local file:// access requires --allow-file-access-from-files in playwright args,
            # which HtmlToPdfService should support, or it works by default for navigation.
            # Wait! If Playwright gets the HTML via `page.set_content(html)`, it doesn't have a base URL, 
            # so `file:///` absolute paths are required. We already rewrote them to `file:///...`
            
            # Pass HTML directly to HtmlToPdfService
            # We already resolved img src and link href to absolute local paths
            
            # Metadata mapping
            pdf_title = config.get("pdf_title") or opf_data['metadata']['title']
            pdf_author = config.get("pdf_author") or opf_data['metadata']['author']
            
            result = await html_to_pdf_service.process(
                request_id=request_id,
                input_type="html",
                content=unified_html,
                page_size=config.get("page_size", "A4"),
                orientation=config.get("orientation", "portrait"),
                margin_preset=config.get("margin_preset", "normal"),
                custom_margin_top="", custom_margin_right="", custom_margin_bottom="", custom_margin_left="",
                custom_page_width="", custom_page_height="", custom_page_unit="px",
                print_background=True,
                header_text=config.get("header_text", ""),
                footer_text=config.get("footer_text", ""),
                page_numbers=config.get("page_numbers", False),
                title=pdf_title,
                author=pdf_author,
                subject="",
                keywords="",
                password="",
                output_filename=pdf_filename
            )

            # Override download URL for epub-to-pdf routes
            result["download_url"] = f"/api/convert-to-pdf/epub-to-pdf/download/{request_id}/{result['filename']}"
            result["view_url"] = f"/api/convert-to-pdf/epub-to-pdf/view/{request_id}/{result['filename']}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in EPUB to PDF conversion: {str(e)}")
            raise ValueError(f"Failed to convert EPUB: {str(e)}")
        finally:
            # Clean up temporary extracted files
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)

epub_to_pdf_service = EpubToPdfService()
