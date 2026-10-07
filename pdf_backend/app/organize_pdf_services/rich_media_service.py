from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import struct
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz
import pikepdf
from PIL import Image

from app.core.paths import Paths
from app.utils.filename import output_filename

logger = logging.getLogger(__name__)

SUPPORTED_PDF_EXT = {".pdf"}
SUPPORTED_MEDIA_EXT = {
    ".mp4", ".avi", ".mov", ".webm",
    ".mp3", ".wav", ".gif", ".m4a", ".ogg", ".flac",
}
SUPPORTED_MEDIA_MIME = {
    ".mp4": "video/mp4", ".avi": "video/avi", ".mov": "video/quicktime",
    ".webm": "video/webm", ".mp3": "audio/mpeg", ".wav": "audio/wav",
    ".gif": "image/gif", ".m4a": "audio/mp4", ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
IMAGE_EXTENSIONS = {".gif"}

MAX_PDF_SIZE = 200 * 1024 * 1024
MAX_MEDIA_SIZE = 500 * 1024 * 1024
MAX_PDF_PAGES = 2000
MAX_TOTAL_SESSION_SIZE = 2 * 1024 * 1024 * 1024

PDF_SIGNATURES = [b"%PDF"]

MEDIA_SIGNATURES = {
    b"\x00\x00\x00": "iso_base",
    b"\x1aE\xdf\xa3": "mkv_webm",
    b"ID3": "mp3_id3",
    b"\xff\xfb": "mp3_frame",
    b"\xff\xf3": "mp3_frame",
    b"\xff\xf2": "mp3_frame",
    b"RIFF": "wav_avi",
    b"GIF8": "gif",
    b"ftyp": "mp4_m4a",
    b"\x00\x00\x00\x1c": "mp4_brand",
    b"\x00\x00\x00\x18": "mp4_brand",
}


class RichMediaError(Exception):
    def __init__(self, message: str, code: str = "UNKNOWN", status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class RichMediaService:

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, request_id: str) -> Dict[str, Any]:
        session = {
            "request_id": request_id,
            "pdf_path": None,
            "pdf_filename": None,
            "page_count": 0,
            "page_sizes": [],
            "placements": [],
            "media_files": [],
            "poster_files": {},
            "output_filename": None,
            "created_at": time.time(),
            "processing_stage": None,
            "processing_progress": 0,
        }
        self._sessions[request_id] = session
        Paths.request_temp(request_id).mkdir(parents=True, exist_ok=True)
        Paths.request_upload(request_id).mkdir(parents=True, exist_ok=True)
        Paths.request_output(request_id).mkdir(parents=True, exist_ok=True)
        return {"success": True, "request_id": request_id}

    def _get_session(self, request_id: str) -> Dict[str, Any]:
        if request_id not in self._sessions:
            raise RichMediaError(
                f"Session not found: {request_id}",
                code="SESSION_NOT_FOUND", status_code=404,
            )
        return self._sessions[request_id]

    def cleanup(self, request_id: str) -> None:
        session = self._sessions.pop(request_id, None)
        if session:
            for mf in session.get("media_files", []):
                p = Path(mf.get("stored_path", ""))
                if p.exists():
                    try:
                        p.unlink()
                    except OSError:
                        pass
            for poster_path in session.get("poster_files", {}).values():
                p = Path(poster_path)
                if p.exists():
                    try:
                        p.unlink()
                    except OSError:
                        pass
            pdf_path_str = session.get("pdf_path")
            if pdf_path_str:
                p = Path(pdf_path_str)
                if p.exists():
                    try:
                        p.unlink()
                    except OSError:
                        pass

    def _validate_pdf(self, file_path: Path, filename: str) -> None:
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_PDF_EXT:
            raise RichMediaError(
                f"Invalid file type: {ext}. Only PDF files are accepted.",
                code="INVALID_PDF_TYPE",
            )

        file_size = file_path.stat().st_size
        if file_size == 0:
            raise RichMediaError(
                "PDF file is empty (0 bytes).",
                code="EMPTY_PDF",
            )
        if file_size > MAX_PDF_SIZE:
            raise RichMediaError(
                f"PDF file too large: {file_size / (1024*1024):.1f} MB. Maximum allowed: {MAX_PDF_SIZE / (1024*1024):.0f} MB.",
                code="PDF_TOO_LARGE",
            )

        header = b""
        try:
            with open(file_path, "rb") as f:
                header = f.read(1024)
        except Exception:
            raise RichMediaError(
                "Cannot read PDF file. It may be corrupted.",
                code="PDF_READ_ERROR",
            )

        if not header.startswith(b"%PDF"):
            raise RichMediaError(
                "Invalid PDF file: missing PDF signature (%PDF header).",
                code="INVALID_PDF_SIGNATURE",
            )

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            raise RichMediaError(
                f"Cannot open PDF — it may be corrupted or damaged: {e}",
                code="CORRUPTED_PDF",
            )

        try:
            if doc.is_encrypted:
                doc.close()
                raise RichMediaError(
                    "Password-protected PDFs are not supported. Please provide an unlocked PDF.",
                    code="PASSWORD_PROTECTED",
                )
        except RichMediaError:
            raise
        except Exception:
            doc.close()
            raise RichMediaError(
                "Cannot read PDF metadata. The file may be corrupted or encrypted.",
                code="PDF_READ_ERROR",
            )

        page_count = len(doc)
        if page_count == 0:
            doc.close()
            raise RichMediaError(
                "PDF has no pages.",
                code="EMPTY_PDF",
            )
        if page_count > MAX_PDF_PAGES:
            doc.close()
            raise RichMediaError(
                f"PDF has too many pages ({page_count}). Maximum allowed: {MAX_PDF_PAGES}.",
                code="PDF_TOO_MANY_PAGES",
            )

        page_sizes = []
        for page in doc:
            rect = page.rect
            page_sizes.append({
                "width": round(rect.width, 2),
                "height": round(rect.height, 2),
            })
        doc.close()

    def upload_pdf(
        self, file_path: Path, filename: str, request_id: str
    ) -> Dict[str, Any]:
        session = self._get_session(request_id)
        self._validate_pdf(file_path, filename)

        doc = fitz.open(str(file_path))
        page_count = len(doc)
        page_sizes = []
        for page in doc:
            rect = page.rect
            page_sizes.append({
                "width": round(rect.width, 2),
                "height": round(rect.height, 2),
            })
        doc.close()

        session["pdf_path"] = str(file_path)
        session["pdf_filename"] = filename
        session["page_count"] = page_count
        session["page_sizes"] = page_sizes

        return {
            "success": True,
            "filename": filename,
            "page_count": page_count,
            "page_sizes": page_sizes,
            "file_size": file_path.stat().st_size,
            "file_size_human": self._human_size(file_path.stat().st_size),
        }

    def _validate_media(self, file_path: Path, filename: str) -> None:
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_MEDIA_EXT:
            raise RichMediaError(
                f"Unsupported media format: {ext}. "
                f"Supported: {', '.join(sorted(SUPPORTED_MEDIA_EXT))}",
                code="UNSUPPORTED_MEDIA_FORMAT",
            )

        file_size = file_path.stat().st_size
        if file_size == 0:
            raise RichMediaError(
                "Media file is empty (0 bytes).",
                code="EMPTY_MEDIA",
            )
        if file_size > MAX_MEDIA_SIZE:
            raise RichMediaError(
                f"Media file too large: {file_size / (1024*1024):.1f} MB. Maximum allowed: {MAX_MEDIA_SIZE / (1024*1024):.0f} MB.",
                code="MEDIA_TOO_LARGE",
            )

        try:
            with open(file_path, "rb") as f:
                header = f.read(16)
            if len(header) < 4:
                raise RichMediaError(
                    "Media file is too small or corrupted.",
                    code="CORRUPTED_MEDIA",
                )

            # Safe validation of media signatures based on extension
            valid_signature = False
            if ext in {".mp4", ".m4a"}:
                # MP4/M4A typically starts with size + b"ftyp" in the first 12 bytes
                if b"ftyp" in header[:12]:
                    valid_signature = True
            elif ext == ".mov":
                # Quicktime MOV contains ftypqt or moov or wide
                if b"ftyp" in header[:12] or b"moov" in header[:12] or b"wide" in header[:12]:
                    valid_signature = True
            elif ext == ".webm":
                # WebM EBML header
                if header.startswith(b"\x1aE\xdf\xa3"):
                    valid_signature = True
            elif ext == ".mp3":
                # MP3 ID3 header or syncword frame header
                if header.startswith(b"ID3") or header.startswith(b"\xff\xfb") or header.startswith(b"\xff\xf3") or header.startswith(b"\xff\xf2"):
                    valid_signature = True
            elif ext == ".wav":
                # WAV RIFF header containing b"WAVE" at offset 8
                if header.startswith(b"RIFF") and b"WAVE" in header[8:16]:
                    valid_signature = True
            elif ext == ".ogg":
                # OggS container header
                if header.startswith(b"OggS"):
                    valid_signature = True
            elif ext == ".avi":
                # AVI RIFF header containing b"AVI " at offset 8
                if header.startswith(b"RIFF") and b"AVI " in header[8:16]:
                    valid_signature = True
            elif ext == ".gif":
                # GIF87a or GIF89a header
                if header.startswith(b"GIF8"):
                    valid_signature = True
            else:
                # Fallback for generic formats
                valid_signature = True

            if not valid_signature:
                raise RichMediaError(
                    f"Corrupted or invalid media file signature for format: {ext}.",
                    code="CORRUPTED_MEDIA",
                )
        except RichMediaError:
            raise
        except Exception as e:
            raise RichMediaError(
                f"Cannot validate media file: {e}",
                code="MEDIA_READ_ERROR",
            )

    def _detect_media_duplicate(
        self, file_path: Path, request_id: str
    ) -> Optional[str]:
        session = self._get_session(request_id)
        try:
            new_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
        except Exception:
            return None
        for mf in session.get("media_files", []):
            if mf.get("md5") == new_hash:
                return mf["media_id"]
        return None

    def upload_media(
        self, file_path: Path, filename: str, request_id: str
    ) -> Dict[str, Any]:
        session = self._get_session(request_id)
        self._validate_media(file_path, filename)

        duplicate_id = self._detect_media_duplicate(file_path, request_id)
        if duplicate_id:
            for m in session.get("media_files", []):
                if m["media_id"] == duplicate_id:
                    return {
                        "success": True,
                        "media": m,
                        "total_media": len(session["media_files"]),
                        "duplicate": True,
                        "message": f"Duplicate file detected. Reusing existing media: {m['filename']}",
                    }

        ext = Path(filename).suffix.lower()
        media_id = str(uuid.uuid4())[:8]
        try:
            md5 = hashlib.md5(file_path.read_bytes()).hexdigest()
        except Exception:
            md5 = ""

        media_info = {
            "media_id": media_id,
            "filename": filename,
            "stored_path": str(file_path),
            "extension": ext,
            "mime_type": SUPPORTED_MEDIA_MIME.get(ext, "application/octet-stream"),
            "file_size": file_path.stat().st_size,
            "file_size_human": self._human_size(file_path.stat().st_size),
            "md5": md5,
            "is_video": ext in VIDEO_EXTENSIONS,
            "is_audio": ext in AUDIO_EXTENSIONS,
            "is_gif": ext in IMAGE_EXTENSIONS,
        }

        if "media_files" not in session:
            session["media_files"] = []
        session["media_files"].append(media_info)

        return {
            "success": True,
            "media": media_info,
            "total_media": len(session["media_files"]),
            "duplicate": False,
        }

    def upload_poster(
        self, file_path: Path, filename: str, request_id: str, media_id: str
    ) -> Dict[str, Any]:
        session = self._get_session(request_id)
        ext = Path(filename).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            raise RichMediaError(
                "Poster image must be JPG, PNG, WebP, or BMP.",
                code="INVALID_POSTER_FORMAT",
            )

        try:
            img = Image.open(str(file_path))
            img.verify()
        except Exception:
            raise RichMediaError(
                "Poster image is corrupted or invalid.",
                code="CORRUPTED_POSTER",
            )

        if media_id not in session.get("poster_files", {}):
            session.setdefault("poster_files", {})

        poster_id = str(uuid.uuid4())[:8]
        poster_ext = ext if ext in {".jpg", ".jpeg", ".png"} else ".jpg"
        poster_name = f"poster_{media_id}_{poster_id}{poster_ext}"
        poster_dir = Paths.request_upload(request_id)
        poster_dest = poster_dir / poster_name

        try:
            if ext in {".jpg", ".jpeg", ".png"}:
                import shutil
                shutil.copy2(str(file_path), str(poster_dest))
            else:
                img = Image.open(str(file_path))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(str(poster_dest), "JPEG", quality=85)
        except Exception as e:
            raise RichMediaError(
                f"Failed to save poster image: {e}",
                code="POSTER_SAVE_ERROR",
            )

        session["poster_files"][media_id] = str(poster_dest)

        return {
            "success": True,
            "poster_id": poster_id,
            "media_id": media_id,
            "poster_path": str(poster_dest),
            "message": "Poster uploaded successfully",
        }

    def auto_generate_poster(
        self, request_id: str, media_id: str
    ) -> Dict[str, Any]:
        session = self._get_session(request_id)
        media_file = None
        for m in session.get("media_files", []):
            if m["media_id"] == media_id:
                media_file = m
                break
        if not media_file:
            raise RichMediaError("Media file not found.", code="MEDIA_NOT_FOUND")

        ext = media_file["extension"]
        media_path = Path(media_file["stored_path"])
        if not media_path.exists():
            raise RichMediaError("Media file not found on disk.", code="MEDIA_FILE_MISSING")

        poster_dest = None

        if ext in VIDEO_EXTENSIONS or ext == ".gif":
            try:
                doc = fitz.open(str(media_path))
                page = doc[0]
                zoom = min(800 / page.rect.width, 800 / page.rect.height, 2.0)
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                poster_bytes = pix.tobytes("jpeg")
                doc.close()

                poster_id = str(uuid.uuid4())[:8]
                poster_name = f"poster_{media_id}_{poster_id}.jpg"
                poster_dest = Paths.request_upload(request_id) / poster_name
                poster_dest.write_bytes(poster_bytes)
            except Exception:
                poster_dest = None

        if poster_dest is None:
            try:
                img = Image.new("RGB", (320, 240), color=(240, 240, 240))
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                label = media_file["filename"]
                if len(label) > 20:
                    label = label[:17] + "..."
                try:
                    font = ImageFont.truetype("arial.ttf", 16)
                except Exception:
                    font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), label, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                draw.text(
                    ((320 - tw) // 2, (240 - th) // 2),
                    label, fill=(100, 100, 100), font=font,
                )

                icon = "🎬" if media_file["is_video"] else "🎵" if media_file["is_audio"] else "🎞"
                try:
                    icon_font = ImageFont.truetype("segoeuiemoji.ttf", 36)
                except Exception:
                    icon_font = font
                draw.text(((320 - 36) // 2, 60), icon, fill=(80, 80, 80), font=icon_font)

                poster_id = str(uuid.uuid4())[:8]
                poster_name = f"poster_{media_id}_{poster_id}.jpg"
                poster_dest = Paths.request_upload(request_id) / poster_name
                img.save(str(poster_dest), "JPEG", quality=85)
            except Exception as e:
                raise RichMediaError(
                    f"Failed to generate poster: {e}",
                    code="POSTER_GENERATION_FAILED",
                )

        session.setdefault("poster_files", {})[media_id] = str(poster_dest)

        return {
            "success": True,
            "media_id": media_id,
            "poster_path": str(poster_dest),
            "message": "Poster auto-generated",
        }

    def delete_poster(self, request_id: str, media_id: str) -> Dict[str, Any]:
        session = self._get_session(request_id)
        poster_path = session.get("poster_files", {}).pop(media_id, None)
        if poster_path:
            p = Path(poster_path)
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
        return {"success": True, "message": "Poster deleted"}

    def get_page_preview(
        self, request_id: str, page_index: int, max_size: int = 800
    ) -> Optional[bytes]:
        session = self._get_session(request_id)
        if not session.get("pdf_path"):
            return None
        try:
            doc = fitz.open(session["pdf_path"])
            if page_index < 0 or page_index >= len(doc):
                doc.close()
                return None
            page = doc[page_index]
            zoom = min(max_size / page.rect.width, max_size / page.rect.height, 2.0)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            doc.close()
            return png_bytes
        except Exception as e:
            logger.warning("Page preview failed: %s", e)
            return None

    def add_placement(
        self,
        request_id: str,
        media_id: str,
        page_index: int,
        x: float,
        y: float,
        width: float,
        height: float,
        autoplay: bool = False,
        loop: bool = False,
        muted: bool = False,
        show_controls: bool = True,
        play_on_click: bool = False,
        interaction_mode: str = "embedded",
        start_time: float = 0.0,
        end_time: float = 0.0,
        volume: float = 1.0,
        rotation: float = 0.0,
        poster_media_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        session = self._get_session(request_id)

        media_found = False
        for m in session.get("media_files", []):
            if m["media_id"] == media_id:
                media_found = True
                break
        if not media_found:
            raise RichMediaError("Media file not found.", code="MEDIA_NOT_FOUND")

        if page_index < 0 or page_index >= session.get("page_count", 0):
            raise RichMediaError(
                f"Invalid page index: {page_index}. Valid: 0-{session.get('page_count', 1)-1}",
                code="INVALID_PAGE_INDEX",
            )

        x = max(0.0, min(x, 100.0))
        y = max(0.0, min(y, 100.0))
        width = max(2.0, min(width, 100.0))
        height = max(2.0, min(height, 100.0))
        volume = max(0.0, min(volume, 1.0))
        start_time = max(0.0, start_time)
        end_time = max(0.0, end_time)
        if end_time > 0 and start_time >= end_time:
            end_time = 0.0

        placement_id = str(uuid.uuid4())[:8]
        placement = {
            "placement_id": placement_id,
            "media_id": media_id,
            "page_index": page_index,
            "x": round(x, 2),
            "y": round(y, 2),
            "width": round(width, 2),
            "height": round(height, 2),
            "autoplay": autoplay,
            "loop": loop,
            "muted": muted,
            "show_controls": show_controls,
            "play_on_click": play_on_click,
            "interaction_mode": interaction_mode,
            "start_time": round(start_time, 3),
            "end_time": round(end_time, 3),
            "volume": round(volume, 2),
            "rotation": round(rotation, 1),
            "poster_media_id": poster_media_id,
        }
        session["placements"].append(placement)
        return {
            "success": True,
            "placement": placement,
            "total_placements": len(session["placements"]),
        }

    def update_placement(
        self, request_id: str, placement_id: str, **kwargs
    ) -> Dict[str, Any]:
        session = self._get_session(request_id)
        for p in session["placements"]:
            if p["placement_id"] == placement_id:
                for k, v in kwargs.items():
                    if k in p:
                        if k == "page_index" and isinstance(v, int):
                            if v < 0 or v >= session.get("page_count", 0):
                                raise RichMediaError(
                                    f"Invalid page index: {v}",
                                    code="INVALID_PAGE_INDEX",
                                )
                        if k in ("x", "y"):
                            v = max(0.0, min(float(v), 100.0))
                        elif k in ("width", "height"):
                            v = max(2.0, min(float(v), 100.0))
                        elif k == "volume":
                            v = max(0.0, min(float(v), 1.0))
                        p[k] = v
                return {"success": True, "placement": p}
        raise RichMediaError(
            f"Placement not found: {placement_id}",
            code="PLACEMENT_NOT_FOUND", status_code=404,
        )

    def remove_placement(
        self, request_id: str, placement_id: str
    ) -> Dict[str, Any]:
        session = self._get_session(request_id)
        original = len(session["placements"])
        session["placements"] = [
            p for p in session["placements"] if p["placement_id"] != placement_id
        ]
        if len(session["placements"]) == original:
            raise RichMediaError(
                f"Placement not found: {placement_id}",
                code="PLACEMENT_NOT_FOUND", status_code=404,
            )
        return {
            "success": True,
            "total_placements": len(session["placements"]),
        }

    def duplicate_placement(
        self, request_id: str, placement_id: str
    ) -> Dict[str, Any]:
        session = self._get_session(request_id)
        source = None
        for p in session["placements"]:
            if p["placement_id"] == placement_id:
                source = p
                break
        if not source:
            raise RichMediaError(
                f"Placement not found: {placement_id}",
                code="PLACEMENT_NOT_FOUND", status_code=404,
            )
        new_id = str(uuid.uuid4())[:8]
        dup = dict(source)
        dup["placement_id"] = new_id
        dup["x"] = min(source["x"] + 3, 95.0)
        dup["y"] = min(source["y"] + 3, 95.0)
        session["placements"].append(dup)
        return {
            "success": True,
            "placement": dup,
            "total_placements": len(session["placements"]),
        }

    def remove_media(self, request_id: str, media_id: str) -> Dict[str, Any]:
        session = self._get_session(request_id)
        session["placements"] = [
            p for p in session["placements"] if p["media_id"] != media_id
        ]
        removed = None
        new_media = []
        for m in session.get("media_files", []):
            if m["media_id"] == media_id:
                removed = m
                p = Path(m.get("stored_path", ""))
                if p.exists():
                    try:
                        p.unlink()
                    except OSError:
                        pass
            else:
                new_media.append(m)
        session["media_files"] = new_media
        session.get("poster_files", {}).pop(media_id, None)

        return {
            "success": True,
            "removed": removed is not None,
            "total_media": len(session.get("media_files", [])),
            "total_placements": len(session["placements"]),
        }

    def _build_rich_media_annotation(
        self, pdf: pikepdf.Pdf, placement: Dict[str, Any], media_file: Dict[str, Any],
        session: Dict[str, Any],
    ) -> Optional[pikepdf.Dictionary]:
        media_path = Path(media_file["stored_path"])
        if not media_path.exists():
            return None

        try:
            media_bytes = media_path.read_bytes()
        except Exception:
            return None

        ext = media_file["extension"]
        mime = SUPPORTED_MEDIA_MIME.get(ext, "application/octet-stream")
        filename = media_file["filename"]

        page_idx = placement["page_index"]
        if page_idx >= len(pdf.pages):
            return None
        page = pdf.pages[page_idx]
        page_rect = page.mediabox
        pw = float(page_rect[2]) - float(page_rect[0])
        ph = float(page_rect[3]) - float(page_rect[1])

        x = placement["x"] * pw / 100.0
        y_from_top = placement["y"] * ph / 100.0
        w = placement["width"] * pw / 100.0
        h = placement["height"] * ph / 100.0
        y = ph - y_from_top - h

        # ── 1. Embedded media file (store raw bytes) ──
        media_stream = pdf.make_stream(media_bytes)
        media_stream["/Type"] = pikepdf.Name("/EmbeddedFile")
        media_stream["/Subtype"] = pikepdf.Name("/" + mime)

        # ── 2. Filespec (build dicts item-by-item to avoid bad cast) ──
        ef_dict = pikepdf.Dictionary()
        ef_dict[pikepdf.Name("/F")] = media_stream

        file_spec = pdf.make_indirect(pikepdf.Dictionary({
            "/Type": pikepdf.Name("/Filespec"),
            "/F": pikepdf.String(filename),
            "/UF": pikepdf.String(filename),
            "/EF": ef_dict
        }))

        # ── 3. Assets Name Tree ──
        assets_names = pdf.make_indirect(pikepdf.Dictionary({
            "/Names": pikepdf.Array([pikepdf.String(filename), file_spec])
        }))

        # ── 4. RichMediaParams & Instance ──
        is_audio = ext in AUDIO_EXTENSIONS
        instance_subtype = pikepdf.Name("/Audio") if is_audio else pikepdf.Name("/Video")

        flashvars = []
        if placement.get("autoplay"):
            flashvars.append("autoplay=true")
        else:
            flashvars.append("autoplay=false")
        if placement.get("loop"):
            flashvars.append("loop=true")
        else:
            flashvars.append("loop=false")
        if placement.get("muted"):
            flashvars.append("muted=true")
        vol = placement.get("volume", 1.0)
        flashvars.append(f"volume={vol}")
        if placement.get("show_controls") is False:
            flashvars.append("showControls=false")
        else:
            flashvars.append("showControls=true")
            
        flashvars.append(f"source={filename}")
        flashvars.append("scaleMode=letterbox")
        flashvars_str = "&".join(flashvars)

        rm_params = pdf.make_indirect(pikepdf.Dictionary({
            "/Type": pikepdf.Name("/RichMediaParams"),
            "/FlashVars": pikepdf.String(flashvars_str)
        }))

        rm_instance = pikepdf.Dictionary({
            "/Type": pikepdf.Name("/RichMediaInstance"),
            "/Subtype": instance_subtype,
            "/Asset": pikepdf.String(filename),
            "/Params": rm_params
        })

        # ── 5. RichMediaConfiguration ──
        rm_config = pdf.make_indirect(pikepdf.Dictionary({
            "/Type": pikepdf.Name("/RichMediaConfiguration"),
            "/Subtype": instance_subtype,
            "/Name": pikepdf.String("DefaultConfig"),
            "/Instances": pikepdf.Array([rm_instance])
        }))

        # ── 6. RichMediaContent ──
        rm_content = pdf.make_indirect(pikepdf.Dictionary({
            "/Type": pikepdf.Name("/RichMediaContent"),
            "/Assets": assets_names,
            "/Configurations": pikepdf.Array([rm_config])
        }))

        # ── 7. RichMediaActivation & Settings ──
        if placement.get("autoplay"):
            condition = pikepdf.Name("/PO")
        elif placement.get("play_on_click"):
            condition = pikepdf.Name("/XA")
        else:
            condition = pikepdf.Name("/XA")

        rm_activation = pdf.make_indirect(pikepdf.Dictionary({
            "/Type": pikepdf.Name("/RichMediaActivation"),
            "/Condition": condition,
            "/Presentation": pikepdf.Dictionary({
                "/Type": pikepdf.Name("/RichMediaPresentation"),
                "/Style": pikepdf.Name("/Embedded"),
                "/Toolbar": False,
                "/NavigationPane": False
            })
        }))

        rm_settings = pdf.make_indirect(pikepdf.Dictionary({
            "/Type": pikepdf.Name("/RichMediaSettings"),
            "/Activation": rm_activation
        }))

        # ── 8. Poster / Appearance Stream (wrapped in Form XObject) ──
        poster_path_str = session.get("poster_files", {}).get(media_file["media_id"])
        if not poster_path_str or not Path(poster_path_str).exists():
            poster_path_str = session.get("poster_files", {}).get(
                placement.get("poster_media_id") or media_file["media_id"]
            )

        ap_dict = pikepdf.Dictionary()

        # Helper to generate Form XObject wrapping Image XObject
        def make_form_ap(img_bytes: bytes, img_w: int, img_h: int) -> pikepdf.Object:
            # 1. Create Image XObject
            img_stream = pdf.make_stream(img_bytes)
            img_stream["/Type"] = pikepdf.Name("/XObject")
            img_stream["/Subtype"] = pikepdf.Name("/Image")
            img_stream["/Filter"] = pikepdf.Name("/DCTDecode")
            img_stream["/Width"] = img_w
            img_stream["/Height"] = img_h
            img_stream["/ColorSpace"] = pikepdf.Name("/DeviceRGB")
            img_stream["/BitsPerComponent"] = 8
            img_indirect = pdf.make_indirect(img_stream)

            # 2. Create Form XObject content stream
            form_content = f"q {w:.3f} 0 0 {h:.3f} 0 0 cm /Img0 Do Q".encode("ascii")
            form_stream = pdf.make_stream(form_content)
            form_stream["/Type"] = pikepdf.Name("/XObject")
            form_stream["/Subtype"] = pikepdf.Name("/Form")
            form_stream["/BBox"] = pikepdf.Array([0, 0, w, h])
            form_stream["/Resources"] = pikepdf.Dictionary({
                "/XObject": pikepdf.Dictionary({
                    "/Img0": img_indirect
                })
            })
            return pdf.make_indirect(form_stream)

        if poster_path_str and Path(poster_path_str).exists():
            try:
                poster_bytes = Path(poster_path_str).read_bytes()
                # Read poster dimensions
                poster_img = Image.open(io.BytesIO(poster_bytes))
                pw_poster, ph_poster = poster_img.size
                poster_img.close()

                ap_dict[pikepdf.Name("/N")] = make_form_ap(poster_bytes, pw_poster, ph_poster)
            except Exception as e:
                logger.warning("Failed to create poster appearance: %s", e)

        # Fallback: create blank appearance stream
        if "/N" not in ap_dict:
            try:
                buf = io.BytesIO()
                img = Image.new("RGB", (int(w), int(h)), color=(240, 240, 240))
                img.save(buf, format="JPEG")
                img.close()
                ap_dict[pikepdf.Name("/N")] = make_form_ap(buf.getvalue(), int(w), int(h))
            except Exception as e:
                logger.warning("Failed to create fallback appearance stream: %s", e)

        # ── 9. MK dictionary (appearance characteristics) ──
        mk_dict = pikepdf.Dictionary()
        if "/N" in ap_dict:
            mk_dict[pikepdf.Name("/R")] = 0  # rotation

        # ── 10. Build the RichMedia annotation ──
        annot_dict = pikepdf.Dictionary({
            "/Type": pikepdf.Name("/Annot"),
            "/Subtype": pikepdf.Name("/RichMedia"),
            "/Rect": pikepdf.Array([x, y, x + w, y + h]),
            "/F": 4,  # Print
            "/RichMediaContent": rm_content,
            "/RichMediaSettings": rm_settings,
        })

        if ap_dict:
            annot_dict[pikepdf.Name("/AP")] = ap_dict
        if mk_dict:
            annot_dict[pikepdf.Name("/MK")] = mk_dict

        screen_annot = pdf.make_indirect(annot_dict)

        # ── 11. Add to page annotations ──
        if "/Annots" not in page:
            page["/Annots"] = pikepdf.Array()
        page["/Annots"].append(screen_annot)

        return screen_annot

    def _preserve_pdf_structure(
        self, original_pdf: pikepdf.Pdf, output_path: Path
    ) -> None:
        pass

    def process(
        self, request_id: str, output_name: Optional[str] = None
    ) -> Dict[str, Any]:
        session = self._get_session(request_id)

        if not session.get("pdf_path"):
            raise RichMediaError("No PDF uploaded.", code="NO_PDF")
        if not session.get("placements"):
            raise RichMediaError(
                "No media placements to embed.",
                code="NO_PLACEMENTS",
            )

        pdf_path = Path(session["pdf_path"])
        if not pdf_path.exists():
            raise RichMediaError(
                "Original PDF file no longer exists.",
                code="PDF_MISSING",
            )

        out_name = output_name or output_filename(prefix="rich_media_")
        out_dir = Paths.request_output(request_id)
        out_path = out_dir / out_name

        session["processing_stage"] = "opening_pdf"
        session["processing_progress"] = 10

        try:
            pdf = pikepdf.open(str(pdf_path))
        except Exception as e:
            raise RichMediaError(
                f"Cannot open PDF: {e}",
                code="PDF_OPEN_FAILED",
            )

        original_page_count = len(pdf.pages)
        session["processing_stage"] = "embedding_media"
        session["processing_progress"] = 30

        embedded_count = 0
        failed_count = 0
        for idx, placement in enumerate(session["placements"]):
            media_id = placement["media_id"]
            media_file = None
            for m in session.get("media_files", []):
                if m["media_id"] == media_id:
                    media_file = m
                    break
            if not media_file:
                failed_count += 1
                continue

            media_path = Path(media_file["stored_path"])
            if not media_path.exists():
                failed_count += 1
                continue

            try:
                screen_annot = self._build_rich_media_annotation(
                    pdf, placement, media_file, session
                )
                if screen_annot is None:
                    failed_count += 1
                    continue
                embedded_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to embed media %s on page %d: %s",
                    media_file["filename"], placement["page_index"], e,
                )
                failed_count += 1

            progress = 30 + int(60 * (idx + 1) / len(session["placements"]))
            session["processing_progress"] = min(progress, 90)

        session["processing_stage"] = "saving"
        session["processing_progress"] = 92

        try:
            pdf.save(str(out_path), compress_streams=False)
            pdf.close()
        except Exception as e:
            pdf.close()
            self.cleanup(request_id)
            raise RichMediaError(
                f"Failed to save output PDF: {e}",
                code="SAVE_FAILED",
            )

        session["processing_stage"] = "finalizing"
        session["processing_progress"] = 98

        try:
            verify_doc = fitz.open(str(out_path))
            final_page_count = len(verify_doc)
            verify_doc.close()
        except Exception:
            final_page_count = original_page_count

        file_size = out_path.stat().st_size
        session["output_filename"] = out_name
        session["processing_stage"] = "completed"
        session["processing_progress"] = 100

        res_data = {
            "success": True,
            "message": "Media embedded successfully",
            "request_id": request_id,
            "filename": out_name,
            "download_url": f"/api/pdf/rich-media/download/{request_id}/{out_name}",
            "page_count": final_page_count,
            "placements_count": embedded_count,
            "failed_count": failed_count,
            "file_size": file_size,
            "file_size_human": self._human_size(file_size),
            "processing_time": round(time.time() - session.get("created_at", time.time()), 1),
        }

        # Delete temporary assets on success
        self.cleanup(request_id)

        return res_data

    def get_status(self, request_id: str) -> Dict[str, Any]:
        session = self._get_session(request_id)
        return {
            "request_id": request_id,
            "pdf_uploaded": session.get("pdf_path") is not None,
            "pdf_filename": session.get("pdf_filename"),
            "page_count": session.get("page_count", 0),
            "media_count": len(session.get("media_files", [])),
            "placements_count": len(session.get("placements", [])),
            "output_filename": session.get("output_filename"),
            "processing_stage": session.get("processing_stage"),
            "processing_progress": session.get("processing_progress", 0),
        }

    @staticmethod
    def _human_size(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


rich_media_service = RichMediaService()
