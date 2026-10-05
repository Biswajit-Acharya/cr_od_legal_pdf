"""
Email to PDF conversion service.

Supports EML, MSG, and MBOX email formats.
Parses email structure, extracts headers/body/attachments, renders HTML via Playwright,
and generates professional PDF output.

Uses the existing project's Playwright-based HTML-to-PDF rendering.
"""

from __future__ import annotations

import asyncio
import base64
import email
import email.header
import email.policy
import html as html_module
import logging
import mailbox
import re
from email import message_from_bytes
from email.message import Message
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.paths import Paths

logger = logging.getLogger(__name__)

PDF_ATTACHMENT_EXT = ".pdf"
IMAGE_ATTACHMENT_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}


def _decode_header_value(raw: Any) -> str:
    if not raw:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    elif not isinstance(raw, str):
        raw = str(raw)
    try:
        parts = email.header.decode_header(raw)
        decoded: list[str] = []
        for data, charset in parts:
            if isinstance(data, bytes):
                decoded.append(data.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(str(data))
        return " ".join(decoded).strip()
    except Exception:
        return str(raw)


def _extract_text_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    if isinstance(payload, bytes):
        charset = part.get_param("charset") or "utf-8"
        if not isinstance(charset, str):
            charset = str(charset)
        try:
            return payload.decode(charset, errors="replace")
        except (LookupError, UnicodeDecodeError):
            return payload.decode("utf-8", errors="replace")
    elif isinstance(payload, str):
        return payload
    return str(payload)


def _sanitize_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    cleaned = re.sub(r"<script[\s\S]*?</script>", "", raw_html, flags=re.IGNORECASE)
    cleaned = re.sub(r"<iframe[\s\S]*?</iframe>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<object[\s\S]*?</object>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<embed[\s\S]*?/?>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+on\w+\s*=\s*\"[^\"]*\"", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+on\w+\s*=\s*'[^']*'", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+on\w+\s*=\s*\S+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'href\s*=\s*"javascript:[^"]*"', 'href="#"', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'src\s*=\s*"javascript:[^"]*"', 'src=""', cleaned, flags=re.IGNORECASE)
    return cleaned


def _escape_text(text: str) -> str:
    return html_module.escape(text)


def _format_date(raw: Optional[str]) -> str:
    if not raw:
        return ""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(raw)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(raw)


def _safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.strip(". ")
    if not name:
        name = "email"
    return name[:200]


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


class EmailData:
    def __init__(self) -> None:
        self.from_address: str = ""
        self.to_addresses: str = ""
        self.cc_addresses: str = ""
        self.bcc_addresses: str = ""
        self.reply_to: str = ""
        self.subject: str = ""
        self.date: str = ""
        self.date_formatted: str = ""
        self.message_id: str = ""
        self.html_body: str = ""
        self.text_body: str = ""
        self.attachments: List[Dict[str, Any]] = []
        self.inline_images: Dict[str, bytes] = {}
        self.raw_headers: str = ""
        self.source_filename: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_address,
            "to": self.to_addresses,
            "cc": self.cc_addresses,
            "bcc": self.bcc_addresses,
            "reply_to": self.reply_to,
            "subject": self.subject,
            "date": self.date_formatted or self.date,
            "message_id": self.message_id,
            "attachment_count": len(self.attachments),
            "has_html": bool(self.html_body),
            "has_text": bool(self.text_body),
            "source_filename": self.source_filename,
        }


class EmlParser:
    def parse(self, file_path: Path) -> List[EmailData]:
        raw = file_path.read_bytes()
        msg = message_from_bytes(raw, policy=email.policy.default)  # type: ignore[arg-type]
        return [self._parse_message(msg, file_path.name)]

    def _parse_message(self, msg: Message, source_name: str) -> EmailData:
        data = EmailData()
        data.source_filename = source_name
        data.from_address = _decode_header_value(msg.get("From", ""))
        data.to_addresses = _decode_header_value(msg.get("To", ""))
        data.cc_addresses = _decode_header_value(msg.get("Cc", ""))
        data.bcc_addresses = _decode_header_value(msg.get("Bcc", ""))
        data.reply_to = _decode_header_value(msg.get("Reply-To", ""))
        data.subject = _decode_header_value(msg.get("Subject", "(No Subject)"))
        data.date = msg.get("Date", "")
        data.date_formatted = _format_date(data.date)
        data.message_id = msg.get("Message-ID", "")

        header_lines = []
        for key in ["From", "To", "Cc", "Bcc", "Reply-To", "Subject", "Date", "Message-ID"]:
            val = msg.get(key)
            if val:
                header_lines.append(f"{key}: {_decode_header_value(val)}")
        data.raw_headers = "\n".join(header_lines)

        self._walk_parts(msg, data)
        return data

    def _walk_parts(self, msg: Message, data: EmailData) -> None:
        if msg.is_multipart():
            for part in msg.walk():
                self._process_part(part, data)
        else:
            self._process_part(msg, data)

    def _process_part(self, part: Message, data: EmailData) -> None:
        content_type = part.get_content_type()
        disposition = str(part.get("Content-Disposition", ""))
        content_id = part.get("Content-ID", "")
        is_inline = "inline" in disposition
        is_attachment = "attachment" in disposition

        if content_type.startswith("multipart/"):
            return

        filename = part.get_filename()
        if filename:
            filename = _decode_header_value(filename)

        if content_id and content_id.strip("<>"):
            payload = part.get_payload(decode=True)
            if payload and content_type.startswith("image/"):
                cid = content_id.strip("<>")
                if isinstance(payload, bytes):
                    data.inline_images[cid] = payload
                elif isinstance(payload, str):
                    data.inline_images[cid] = payload.encode("utf-8")
                return

        if is_attachment or (filename and not is_inline):
            payload = part.get_payload(decode=True)
            ext = Path(filename).suffix.lower() if filename else ""
            data.attachments.append({
                "filename": filename or f"attachment{ext}",
                "content_type": content_type,
                "size": len(payload) if payload else 0,
                "data": payload or b"",
                "is_pdf": ext == PDF_ATTACHMENT_EXT,
                "is_image": ext in IMAGE_ATTACHMENT_EXTS,
            })
            return

        if content_type == "text/html" and not data.html_body:
            data.html_body = _extract_text_part(part)
        elif content_type == "text/plain" and not data.text_body:
            data.text_body = _extract_text_part(part)


class MsgParser:
    def parse(self, file_path: Path) -> List[EmailData]:
        try:
            import extract_msg  # type: ignore
        except ImportError:
            raise ValueError(
                "MSG support requires the 'extract-msg' library. "
                "Install it with: pip install extract-msg"
            )

        msg = extract_msg.Message(str(file_path))
        data = EmailData()
        data.source_filename = file_path.name

        data.from_address = str(msg.sender) if msg.sender else ""
        data.to_addresses = ", ".join(str(r) for r in (msg.to or []))
        data.cc_addresses = ", ".join(str(r) for r in (msg.cc or []))
        data.bcc_addresses = ", ".join(str(r) for r in (getattr(msg, "bcc", None) or []))
        data.reply_to = str(getattr(msg, "reply_to", "") or "")
        data.subject = msg.subject or "(No Subject)"
        data.date = str(msg.date) if msg.date else ""
        data.date_formatted = _format_date(data.date)
        data.message_id = ""

        header_lines = []
        if data.from_address:
            header_lines.append(f"From: {data.from_address}")
        if data.to_addresses:
            header_lines.append(f"To: {data.to_addresses}")
        if data.cc_addresses:
            header_lines.append(f"Cc: {data.cc_addresses}")
        if data.bcc_addresses:
            header_lines.append(f"Bcc: {data.bcc_addresses}")
        if data.reply_to:
            header_lines.append(f"Reply-To: {data.reply_to}")
        header_lines.append(f"Subject: {data.subject}")
        if data.date:
            header_lines.append(f"Date: {data.date}")
        data.raw_headers = "\n".join(header_lines)

        if msg.htmlBody:
            if isinstance(msg.htmlBody, bytes):
                data.html_body = msg.htmlBody.decode("utf-8", errors="replace")
            else:
                data.html_body = str(msg.htmlBody)
        if msg.body:
            if isinstance(msg.body, bytes):
                data.text_body = msg.body.decode("utf-8", errors="replace")
            else:
                data.text_body = str(msg.body)

        for att in (msg.attachments or []):
            att_filename = att.name or "attachment"
            att_data = att.data if hasattr(att, "data") else b""
            att_size = len(att_data) if isinstance(att_data, (bytes, str, list, dict, set, tuple)) else 0
            ext = Path(att_filename).suffix.lower()
            data.attachments.append({
                "filename": att_filename,
                "content_type": getattr(att, "mimeType", ""),
                "size": att_size,
                "data": att_data or b"",
                "is_pdf": ext == PDF_ATTACHMENT_EXT,
                "is_image": ext in IMAGE_ATTACHMENT_EXTS,
            })

        try:
            msg.close()
        except Exception:
            pass
        return [data]


class MboxParser:
    def parse(self, file_path: Path) -> List[EmailData]:
        mbox = mailbox.mbox(str(file_path))
        results: List[EmailData] = []
        eml_parser = EmlParser()
        for i, msg in enumerate(mbox):
            try:
                data = eml_parser._parse_message(msg, f"email_{i+1}")
                data.source_filename = file_path.name
                results.append(data)
            except Exception as e:
                logger.warning(f"Skipping malformed email #{i+1} in MBOX: {e}")
                placeholder = EmailData()
                placeholder.subject = f"(Malformed email #{i+1})"
                placeholder.source_filename = file_path.name
                placeholder.text_body = f"This email could not be parsed.\nError: {e}"
                results.append(placeholder)
        try:
            mbox.close()
        except Exception:
            pass
        return results


class EmailHtmlBuilder:
    PAGE_SIZES = {
        "a4": {"width": "210mm", "height": "297mm"},
        "letter": {"width": "215.9mm", "height": "279.4mm"},
        "legal": {"width": "215.9mm", "height": "355.6mm"},
        "a3": {"width": "297mm", "height": "420mm"},
        "a5": {"width": "148mm", "height": "210mm"},
    }
    MARGINS = {"normal": "20mm", "small": "10mm", "large": "30mm"}

    def _build_body(self, email_data: EmailData, config: Dict[str, Any],
                    index: int = 0, is_part_of_batch: bool = False) -> str:
        show_headers = config.get("show_headers", True)
        show_full_headers = config.get("show_full_headers", False)
        attachment_mode = config.get("attachment_mode", "summary")
        show_separator = config.get("show_separator", False)

        parts: list[str] = []
        if show_separator and is_part_of_batch and index > 0:
            parts.append(self._separator(index, email_data))

        parts.append('<div class="email-container">')
        if show_headers:
            parts.append(self._header_section(email_data, show_full_headers))

        parts.append(self._body_section(email_data))

        if email_data.attachments and attachment_mode != "exclude":
            parts.append(self._attachments_section(email_data.attachments, attachment_mode))
        parts.append('</div>')

        return "\n".join(parts)

    def build_single(self, email_data: EmailData, config: Dict[str, Any],
                     index: int = 0, is_part_of_batch: bool = False) -> str:
        page_size = config.get("page_size", "a4")
        orientation = config.get("orientation", "portrait")
        show_page_numbers = config.get("show_page_numbers", False)

        ps = self.PAGE_SIZES.get(page_size, self.PAGE_SIZES["a4"])
        if orientation == "landscape":
            ps = {"width": ps["height"], "height": ps["width"]}

        margin_val = self.MARGINS.get(config.get("margins", "normal"), "20mm")

        parts: list[str] = []
        parts.append(self._html_head(ps, margin_val, show_page_numbers))
        parts.append(self._build_body(email_data, config, index, is_part_of_batch))
        parts.append("</body></html>")
        return "\n".join(parts)

    def build_combined(self, emails: List[EmailData], config: Dict[str, Any]) -> str:
        page_size = config.get("page_size", "a4")
        orientation = config.get("orientation", "portrait")
        show_page_numbers = config.get("show_page_numbers", False)

        ps = self.PAGE_SIZES.get(page_size, self.PAGE_SIZES["a4"])
        if orientation == "landscape":
            ps = {"width": ps["height"], "height": ps["width"]}

        margin_val = self.MARGINS.get(config.get("margins", "normal"), "20mm")

        parts: list[str] = []
        parts.append(self._html_head(ps, margin_val, show_page_numbers))

        for i, ed in enumerate(emails):
            cfg = dict(config)
            cfg["show_separator"] = True
            parts.append(self._build_body(ed, cfg, index=i, is_part_of_batch=True))

        parts.append("</body></html>")
        return "\n".join(parts)

    def _html_head(self, ps: Dict[str, str], margin_val: str, show_page_numbers: bool) -> str:
        page_num_css = ""
        if show_page_numbers:
            page_num_css = """
    @top-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 10px;
        color: #888;
        font-family: Arial, sans-serif;
    }"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
@page {{
    size: {ps['width']} {ps['height']};
    margin: {margin_val};{page_num_css}
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 13px;
    line-height: 1.5;
    color: #1a1a1a;
    background: #fff;
    padding: 10px;
}}
.email-container {{ max-width: 100%; margin-bottom: 30px; }}
.email-header {{
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 16px;
    margin-bottom: 20px;
}}
.email-header h2 {{
    font-size: 16px;
    color: #333;
    margin-bottom: 10px;
    border-bottom: 1px solid #dee2e6;
    padding-bottom: 8px;
}}
.header-row {{
    display: flex;
    margin-bottom: 4px;
    font-size: 12px;
}}
.header-label {{
    font-weight: 700;
    color: #555;
    min-width: 80px;
    flex-shrink: 0;
}}
.header-value {{
    color: #333;
    word-break: break-word;
}}
.email-body {{ margin-bottom: 20px; }}
.email-body h1 {{ font-size: 20px; margin: 12px 0 8px; color: #111; }}
.email-body h2 {{ font-size: 17px; margin: 10px 0 6px; color: #222; }}
.email-body h3 {{ font-size: 15px; margin: 8px 0 4px; color: #333; }}
.email-body p {{ margin: 8px 0; }}
.email-body a {{ color: #0066cc; }}
.email-body img {{ max-width: 100%; height: auto; display: block; margin: 8px 0; }}
.email-body table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
.email-body table td, .email-body table th {{
    border: 1px solid #ccc; padding: 6px 8px; text-align: left; font-size: 12px;
}}
.email-body table th {{ background: #f0f0f0; font-weight: 700; }}
.email-body pre, .email-body code {{
    font-family: 'Courier New', monospace; font-size: 12px;
    background: #f5f5f5; border: 1px solid #ddd; border-radius: 3px;
    padding: 8px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word;
    word-break: break-all;
}}
.email-body blockquote {{
    border-left: 3px solid #ccc; padding-left: 12px; margin: 8px 0; color: #666;
}}
.text-body {{
    font-family: 'Courier New', monospace; font-size: 12px;
    white-space: pre-wrap; word-wrap: break-word; line-height: 1.6;
    word-break: break-all;
}}
.attachments-section {{
    background: #f8f9fa; border: 1px solid #dee2e6;
    border-radius: 6px; padding: 12px 16px; margin-top: 20px;
}}
.attachments-section h3 {{ font-size: 13px; color: #555; margin-bottom: 8px; }}
.attachment-item {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 0; border-bottom: 1px solid #eee; font-size: 12px;
}}
.attachment-item:last-child {{ border-bottom: none; }}
.attachment-name {{ font-weight: 600; color: #333; }}
.attachment-meta {{ color: #888; font-size: 11px; }}
.separator {{ page-break-before: always; padding-top: 10px; }}
.separator-bar {{ border-top: 2px solid #333; padding-top: 12px; margin-bottom: 16px; }}
.separator-title {{ font-size: 14px; font-weight: 700; color: #333; }}
.separator-meta {{ font-size: 11px; color: #777; margin-top: 4px; }}
.raw-headers {{
    font-family: 'Courier New', monospace; font-size: 11px;
    background: #f5f5f5; border: 1px solid #ddd; border-radius: 3px;
    padding: 10px; white-space: pre-wrap; word-wrap: break-word; margin-top: 8px;
}}
.empty-body {{ color: #999; font-style: italic; padding: 20px; text-align: center; }}
</style>
</head>
<body>
"""

    def _separator(self, index: int, ed: EmailData) -> str:
        return f"""
<div class="separator">
    <div class="separator-bar">
        <div class="separator-title">EMAIL {index + 1}</div>
        <div class="separator-meta">
            {_escape_text(ed.from_address)} &mdash; {_escape_text(ed.subject)}
            {(' &mdash; ' + _escape_text(ed.date_formatted)) if ed.date_formatted else ''}
        </div>
    </div>
</div>
"""

    def _header_row(self, label: str, value: str) -> str:
        return f'<div class="header-row"><span class="header-label">{label}:</span><span class="header-value">{_escape_text(value)}</span></div>'

    def _header_section(self, ed: EmailData, show_full: bool) -> str:
        rows = []
        if ed.from_address:
            rows.append(self._header_row("From", ed.from_address))
        if ed.to_addresses:
            rows.append(self._header_row("To", ed.to_addresses))
        if ed.cc_addresses:
            rows.append(self._header_row("Cc", ed.cc_addresses))
        if ed.bcc_addresses:
            rows.append(self._header_row("Bcc", ed.bcc_addresses))
        if ed.reply_to:
            rows.append(self._header_row("Reply-To", ed.reply_to))
        rows.append(self._header_row("Subject", ed.subject))
        if ed.date_formatted:
            rows.append(self._header_row("Date", ed.date_formatted))
        if ed.message_id:
            rows.append(self._header_row("Message-ID", ed.message_id))

        header_html = "\n".join(rows)
        full_headers_html = ""
        if show_full and ed.raw_headers:
            full_headers_html = f'<div class="raw-headers">{_escape_text(ed.raw_headers)}</div>'

        return f"""
<div class="email-header">
    <h2>Email Information</h2>
    {header_html}
    {full_headers_html}
</div>
"""

    def _body_section(self, ed: EmailData) -> str:
        body_parts = []
        if ed.html_body:
            html_content = ed.html_body
            if ed.inline_images:
                for cid, img_data in ed.inline_images.items():
                    mime_type = "image/png"
                    if img_data.startswith(b"\xff\xd8"):
                        mime_type = "image/jpeg"
                    elif img_data.startswith(b"GIF89a") or img_data.startswith(b"GIF87a"):
                        mime_type = "image/gif"
                    elif img_data.startswith(b"\x89PNG\r\n\x1a\n"):
                        mime_type = "image/png"
                    elif img_data.startswith(b"RIFF") and b"WEBP" in img_data[:12]:
                        mime_type = "image/webp"

                    base64_str = base64.b64encode(img_data).decode("utf-8")
                    data_uri = f"data:{mime_type};base64,{base64_str}"

                    pattern_with_brackets = re.escape(f"cid:<{cid}>")
                    pattern_without_brackets = re.escape(f"cid:{cid}")

                    html_content = re.sub(pattern_with_brackets, data_uri, html_content, flags=re.IGNORECASE)
                    html_content = re.sub(pattern_without_brackets, data_uri, html_content, flags=re.IGNORECASE)

            sanitized = _sanitize_html(html_content)
            body_parts.append(f'<div class="email-body">{sanitized}</div>')
        elif ed.text_body:
            escaped = _escape_text(ed.text_body)
            body_parts.append(f'<div class="text-body">{escaped}</div>')
        else:
            body_parts.append('<div class="empty-body">[No email body content]</div>')
        return "\n".join(body_parts)

    def _attachments_section(self, attachments: List[Dict[str, Any]], mode: str) -> str:
        items = []
        for att in attachments:
            size_str = _format_size(att.get("size", 0))
            items.append(
                f'<div class="attachment-item">'
                f'<span class="attachment-name">{_escape_text(att["filename"])}</span>'
                f'<span class="attachment-meta">{_escape_text(att.get("content_type", "unknown"))} &middot; {size_str}</span>'
                f'</div>'
            )

        title = "Attachments"
        if mode == "summary":
            title = "Attachments (summary only)"

        return f"""
<div class="attachments-section">
    <h3>{title} ({len(attachments)})</h3>
    {"".join(items)}
</div>
"""




class EmailToPdfService:
    def __init__(self) -> None:
        self.eml_parser = EmlParser()
        self.msg_parser = MsgParser()
        self.mbox_parser = MboxParser()
        self.html_builder = EmailHtmlBuilder()

    def validate(self, file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            raise ValueError("File not found.")
        if file_path.stat().st_size == 0:
            raise ValueError("The uploaded email file is empty.")
        ext = file_path.suffix.lower()
        if ext not in (".eml", ".msg", ".mbox"):
            raise ValueError(f"Unsupported format. Only .eml, .msg, and .mbox are allowed. Got: {ext}")
        size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)
        return {
            "filename": file_path.name,
            "size_bytes": file_path.stat().st_size,
            "size_mb": size_mb,
            "format": "Email Message" if ext in (".eml", ".msg") else "Mailbox",
            "extension": ext,
        }

    def parse_email(self, file_path: Path) -> List[EmailData]:
        ext = file_path.suffix.lower()
        if ext == ".eml":
            return self.eml_parser.parse(file_path)
        elif ext == ".msg":
            return self.msg_parser.parse(file_path)
        elif ext == ".mbox":
            return self.mbox_parser.parse(file_path)
        else:
            raise ValueError(f"Unsupported email format: {ext}")

    async def _render_html_to_pdf(
        self, html_content: str, output_path: Path,
        page_size: str = "a4", orientation: str = "portrait",
        margin_top: str = "20mm", margin_bottom: str = "20mm",
        margin_left: str = "20mm", margin_right: str = "20mm",
    ) -> None:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ValueError("Playwright is required for email rendering. Install with: pip install playwright")

        ps_map: Dict[str, Dict[str, float]] = {
            "a4": {"width": 210, "height": 297},
            "letter": {"width": 215.9, "height": 279.4},
            "legal": {"width": 215.9, "height": 355.6},
            "a3": {"width": 297, "height": 420},
            "a5": {"width": 148, "height": 210},
        }
        ps = ps_map.get(page_size, ps_map["a4"])
        if orientation == "landscape":
            ps = {"width": ps["height"], "height": ps["width"]}

        pdf_options: Dict[str, Any] = {
            "path": str(output_path),
            "format": None,
            "width": f"{ps['width']}mm",
            "height": f"{ps['height']}mm",
            "margin": {
                "top": margin_top,
                "bottom": margin_bottom,
                "left": margin_left,
                "right": margin_right,
            },
            "print_background": True,
        }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(html_content, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(0.3)
            await page.pdf(**pdf_options)  # type: ignore[arg-type]
            await browser.close()

    def _safe_pdf_title(self, subject: str) -> str:
        if not subject or subject == "(No Subject)":
            return "Email"
        return _safe_filename(subject)[:100]

    async def process(
        self,
        request_id: str,
        filenames: List[str],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        config = config or {}
        upload_dir = Paths.request_upload(request_id)
        output_dir = Paths.request_output(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_mode = config.get("output_mode", "separate")
        page_size = config.get("page_size", "a4")
        orientation = config.get("orientation", "portrait")
        margins = config.get("margins", "normal")
        margin_map = {"normal": "20mm", "small": "10mm", "large": "30mm"}
        margin_val = margin_map.get(margins, "20mm")

        margin_top = config.get("margin_top", margin_val)
        margin_bottom = config.get("margin_bottom", margin_val)
        margin_left = config.get("margin_left", margin_val)
        margin_right = config.get("margin_right", margin_val)

        if output_mode == "combined":
            return await self._process_combined(
                request_id, filenames, upload_dir, output_dir, config,
                page_size, orientation, margin_top, margin_bottom, margin_left, margin_right,
            )
        else:
            return await self._process_separate(
                request_id, filenames, upload_dir, output_dir, config,
                page_size, orientation, margin_top, margin_bottom, margin_left, margin_right,
            )

    async def _process_separate(
        self, request_id: str, filenames: List[str],
        upload_dir: Path, output_dir: Path, config: Dict[str, Any],
        page_size: str, orientation: str,
        margin_top: str, margin_bottom: str, margin_left: str, margin_right: str,
    ) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []

        for filename in filenames:
            input_path = upload_dir / filename
            if not input_path.exists():
                results.append({
                    "original_filename": filename,
                    "status": "error",
                    "message": "File not found on server.",
                })
                continue

            try:
                emails = self.parse_email(input_path)
                if not emails:
                    results.append({
                        "original_filename": filename,
                        "status": "error",
                        "message": "No emails found in the file.",
                    })
                    continue

                if len(emails) == 1:
                    ed = emails[0]
                    subject = ed.subject if ed.subject and ed.subject != "(No Subject)" else "email"
                    pdf_name = _safe_filename(subject) + ".pdf"
                    pdf_path = output_dir / pdf_name
                    html_content = self.html_builder.build_single(ed, config)
                    await self._render_html_to_pdf(
                        html_content, pdf_path, page_size, orientation,
                        margin_top, margin_bottom, margin_left, margin_right,
                    )
                    results.append({
                        "original_filename": filename,
                        "pdf_filename": pdf_name,
                        "status": "success",
                        "email_count": 1,
                        "subject": ed.subject,
                        "from": ed.from_address,
                        "date": ed.date_formatted or ed.date,
                        "attachment_count": len(ed.attachments),
                        "download_url": f"/api/convert-to-pdf/email-to-pdf/download/{request_id}/{pdf_name}",
                        "view_url": f"/api/convert-to-pdf/email-to-pdf/view/{request_id}/{pdf_name}",
                    })
                else:
                    pdf_names = []
                    for idx, ed in enumerate(emails):
                        subject = ed.subject if ed.subject and ed.subject != "(No Subject)" else f"email_{idx+1}"
                        pdf_name = _safe_filename(subject) + ".pdf"
                        pdf_path = output_dir / pdf_name
                        html_content = self.html_builder.build_single(ed, config, index=idx, is_part_of_batch=False)
                        await self._render_html_to_pdf(
                            html_content, pdf_path, page_size, orientation,
                            margin_top, margin_bottom, margin_left, margin_right,
                        )
                        pdf_names.append(pdf_name)

                    results.append({
                        "original_filename": filename,
                        "status": "success",
                        "email_count": len(emails),
                        "pdf_filenames": pdf_names,
                        "message": f"Converted {len(emails)} emails into {len(pdf_names)} separate PDFs.",
                        "download_url": f"/api/convert-to-pdf/email-to-pdf/download-zip/{request_id}",
                    })

            except ValueError as e:
                logger.error(f"Validation error converting {filename}: {e}")
                results.append({
                    "original_filename": filename,
                    "status": "error",
                    "message": str(e),
                })
            except Exception as e:
                logger.error(f"Error converting {filename}: {e}", exc_info=True)
                results.append({
                    "original_filename": filename,
                    "status": "error",
                    "message": f"Conversion failed: {str(e)}",
                })

        successful = [r for r in results if r.get("status") == "success"]
        return {
            "success": len(successful) > 0,
            "request_id": request_id,
            "results": results,
            "total_files": len(filenames),
            "successful_files": len(successful),
            "failed_files": len(filenames) - len(successful),
        }

    async def _process_combined(
        self, request_id: str, filenames: List[str],
        upload_dir: Path, output_dir: Path, config: Dict[str, Any],
        page_size: str, orientation: str,
        margin_top: str, margin_bottom: str, margin_left: str, margin_right: str,
    ) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []

        for filename in filenames:
            input_path = upload_dir / filename
            if not input_path.exists():
                results.append({
                    "original_filename": filename,
                    "status": "error",
                    "message": "File not found on server.",
                })
                continue

            try:
                emails = self.parse_email(input_path)
                if not emails:
                    results.append({
                        "original_filename": filename,
                        "status": "error",
                        "message": "No emails found in the file.",
                    })
                    continue

                base_name = _safe_filename(Path(filename).stem)
                pdf_name = f"{base_name}_combined.pdf"
                pdf_path = output_dir / pdf_name

                html_content = self.html_builder.build_combined(emails, config)
                await self._render_html_to_pdf(
                    html_content, pdf_path, page_size, orientation,
                    margin_top, margin_bottom, margin_left, margin_right,
                )

                results.append({
                    "original_filename": filename,
                    "pdf_filename": pdf_name,
                    "status": "success",
                    "email_count": len(emails),
                    "message": f"Combined {len(emails)} emails into one PDF.",
                    "download_url": f"/api/convert-to-pdf/email-to-pdf/download/{request_id}/{pdf_name}",
                    "view_url": f"/api/convert-to-pdf/email-to-pdf/view/{request_id}/{pdf_name}",
                })

            except ValueError as e:
                logger.error(f"Validation error converting {filename}: {e}")
                results.append({
                    "original_filename": filename,
                    "status": "error",
                    "message": str(e),
                })
            except Exception as e:
                logger.error(f"Error converting {filename}: {e}", exc_info=True)
                results.append({
                    "original_filename": filename,
                    "status": "error",
                    "message": f"Conversion failed: {str(e)}",
                })

        successful = [r for r in results if r.get("status") == "success"]
        return {
            "success": len(successful) > 0,
            "request_id": request_id,
            "results": results,
            "total_files": len(filenames),
            "successful_files": len(successful),
            "failed_files": len(filenames) - len(successful),
        }

    async def preview(self, file_path: Path, index: int = 0) -> Dict[str, Any]:
        try:
            emails = self.parse_email(file_path)
            if not emails:
                return {"error": "No emails found in the file."}
            ed = emails[index] if index < len(emails) else emails[0]
            result = ed.to_dict()
            if ed.attachments:
                result["attachments"] = [
                    {"filename": a["filename"], "content_type": a["content_type"], "size": a["size"]}
                    for a in ed.attachments
                ]
            if len(emails) > 1:
                result["total_emails"] = len(emails)
                result["email_list"] = [
                    {"index": i, "subject": e.subject, "from": e.from_address, "date": e.date_formatted}
                    for i, e in enumerate(emails)
                ]
            return result
        except Exception as e:
            return {"error": str(e)}


email_to_pdf_service = EmailToPdfService()
