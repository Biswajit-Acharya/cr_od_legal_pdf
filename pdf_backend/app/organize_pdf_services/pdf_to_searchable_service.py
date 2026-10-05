"""
PDF to Searchable PDF (OCR) Service.

Handles local, offline OCR text layer creation using OCRmyPDF and Tesseract.
Includes standard validations, auto searchability detection, DPI extraction,
image preprocessing, and output verification.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz
import ocrmypdf

from app.core.paths import Paths
from app.utils.filename import output_filename

logger = logging.getLogger(__name__)

import glob

# Try to append standard Windows Tesseract path if present
POSSIBLE_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR",
    r"C:\Program Files (x86)\Tesseract-OCR",
]
local_appdata = os.environ.get("LOCALAPPDATA")
if local_appdata:
    POSSIBLE_TESSERACT_PATHS.append(os.path.join(local_appdata, "Programs", "Tesseract-OCR"))

for path in POSSIBLE_TESSERACT_PATHS:
    if os.path.exists(path):
        for k in list(os.environ.keys()):
            if k.upper() == "PATH":
                val = os.environ[k]
                if path not in val:
                    os.environ[k] = path + os.pathsep + val

# Try to append standard Windows Ghostscript path if present
gs_paths = glob.glob(r"C:\Program Files\gs\gs*\bin") + glob.glob(r"C:\Program Files (x86)\gs\gs*\bin")
for path in gs_paths:
    if os.path.exists(path):
        for k in list(os.environ.keys()):
            if k.upper() == "PATH":
                val = os.environ[k]
                if path not in val:
                    os.environ[k] = path + os.pathsep + val

# Standard Tesseract Language code maps
LANG_MAP = {
    "english": "eng",
    "hindi": "hin",
    "odia": "ori",
    "bengali": "ben",
    "tamil": "tam",
    "telugu": "tel",
    "kannada": "kan",
    "malayalam": "mal",
    "punjabi": "pan",
    "gujarati": "guj",
    "marathi": "mar",
    "urdu": "urd",
    "japanese": "jpn",
    "chinese": "chi_sim",
    "german": "deu",
    "french": "fra",
    "spanish": "spa",
    "italian": "ita",
    "portuguese": "por",
}


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

class OCRAnalysis:
    """Analysis profile of the scanned / text PDF document."""

    def __init__(self) -> None:
        self.page_count: int = 0
        self.file_size: int = 0
        self.pdf_version: str = "Unknown"
        self.is_searchable: bool = False
        self.is_mixed: bool = False
        self.scanned_pages: int = 0
        self.width: float = 0.0
        self.height: float = 0.0
        self.orientation: str = "Portrait"
        self.has_metadata: bool = False
        self.avg_dpi: int = 150
        self.is_encrypted: bool = False
        self.is_corrupted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_count": self.page_count,
            "file_size": self.file_size,
            "pdf_version": self.pdf_version,
            "is_searchable": self.is_searchable,
            "is_mixed": self.is_mixed,
            "scanned_pages": self.scanned_pages,
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "orientation": self.orientation,
            "has_metadata": self.has_metadata,
            "avg_dpi": self.avg_dpi,
            "is_encrypted": self.is_encrypted,
            "is_corrupted": self.is_corrupted,
        }


class OCRResult:
    """Details of the searchable PDF generation."""

    def __init__(self) -> None:
        self.success: bool = False
        self.message: str = ""
        self.request_id: str = ""
        self.filename: str = ""
        self.download_url: str = ""
        self.original_size: int = 0
        self.final_size: int = 0
        self.processing_time: float = 0.0
        self.pages_processed: int = 0
        self.ocr_lang: str = "English"
        self.analysis: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "request_id": self.request_id,
            "filename": self.filename,
            "download_url": self.download_url,
            "original_size": self.original_size,
            "final_size": self.final_size,
            "processing_time": self.processing_time,
            "pages_processed": self.pages_processed,
            "ocr_lang": self.ocr_lang,
            "analysis": self.analysis,
        }


# ---------------------------------------------------------------------------
# OCR PDF Service Class
# ---------------------------------------------------------------------------

class PDFToSearchableService:
    """Manages PDF validations, auto searchability detection, preprocessing steps, and OCRmyPDF subprocess/api wrappers."""

    async def analyze(self, pdf_path: Path) -> OCRAnalysis:
        """Analyze PDF formatting and check if it is already searchable or scanned."""
        logger.info("Analyzing PDF for OCR searchability: %s", pdf_path.name)
        analysis = OCRAnalysis()
        analysis.file_size = pdf_path.stat().st_size

        self._validate_pdf_signature(pdf_path, analysis)
        if analysis.is_corrupted or analysis.is_encrypted:
            return analysis

        self._deep_analyze_pdf(pdf_path, analysis)
        return analysis

    async def process(
        self,
        input_pdf: Path,
        request_id: str,
        language: str = "english",
        quality: str = "balanced",        # fast, balanced, high, max
        auto_rotate: bool = True,
        deskew: bool = True,
        clean_noise: bool = True,
        preserve_metadata: bool = True,
        skip_searchable: bool = True,
        force_ocr: bool = False,
    ) -> OCRResult:
        """
        Run OCRmyPDF on the input PDF based on selection options.
        """
        start = time.perf_counter()
        logger.info(
            "Starting OCR processing [request_id=%s] lang=%s quality=%s rotate=%s deskew=%s clean=%s",
            request_id, language, quality, auto_rotate, deskew, clean_noise
        )

        result = OCRResult()
        result.request_id = request_id

        # 1. Base Validations
        analysis = OCRAnalysis()
        analysis.file_size = input_pdf.stat().st_size
        self._validate_pdf_signature(input_pdf, analysis)
        if analysis.is_corrupted:
            raise ValueError("Corrupted PDF: cannot open document structure.")
        if analysis.is_encrypted:
            raise ValueError("Password-protected PDF: cannot run OCR without decrypting first.")

        self._deep_analyze_pdf(input_pdf, analysis)
        result.analysis = analysis.to_dict()
        result.original_size = analysis.file_size
        result.pages_processed = analysis.page_count
        result.ocr_lang = language.capitalize()

        # Resolve Tesseract language code
        lang_code = LANG_MAP.get(language.lower(), "eng")

        # 2. Setup output folder
        out_dir = Paths.request_output(request_id)
        out_name = output_filename(prefix="searchable_")
        out_path = out_dir / out_name

        # Setup parameters mapping for OCRmyPDF API
        # Map quality to Tesseract flags
        # Fast: skip-text, low DPI
        # Balanced: skip-text, standard DPI
        # High: force ocr, clean
        # Max: force ocr, clean, high resolution
        skip_text_layer = skip_searchable and not force_ocr

        try:
            # We run ocrmypdf using subprocess or direct python API wrapper
            # Subprocess is safer because it runs in a clean context and isolates environment variables
            cmd = [
                "ocrmypdf",
                "--jobs", "4",
                "-l", lang_code,
            ]

            if skip_text_layer:
                # Skip OCR on pages that already have text
                cmd.append("--skip-text")
            elif force_ocr:
                # Re-do OCR on all pages
                cmd.append("--redo-ocr")

            if auto_rotate:
                cmd.append("--rotate-pages")
            if deskew:
                cmd.append("--deskew")
            import shutil
            if clean_noise:
                if shutil.which("unpaper"):
                    cmd.append("--clean")
                else:
                    logger.warning("unpaper is not installed. Disabling --clean.")
            
            # Map quality presets
            has_pngquant = shutil.which("pngquant") is not None
            if quality == "fast":
                cmd.extend(["--optimize", "1", "--fast-web"])
            elif quality == "balanced":
                if has_pngquant:
                    cmd.extend(["--optimize", "2"])
                else:
                    logger.warning("pngquant missing, falling back to --optimize 1 for balanced quality.")
                    cmd.extend(["--optimize", "1"])
            elif quality in ["high", "max"]:
                if has_pngquant:
                    cmd.extend(["--optimize", "3"])
                else:
                    logger.warning("pngquant missing, falling back to --optimize 1 for high quality.")
                    cmd.extend(["--optimize", "1"])
                
                if quality == "max":
                    cmd.extend(["--oversample", "300"])

            # Check if tesseract binary can be executed
            tesseract_available = True
            try:
                self._check_tesseract_installed()
            except Exception as tess_err:
                logger.warning("Tesseract binary not available: %s. Using PyMuPDF fallback.", tess_err)
                tesseract_available = False

            if tesseract_available and shutil.which("ocrmypdf"):
                # Append source and target
                cmd.extend([str(input_pdf), str(out_path)])
                logger.info("Executing OCRmyPDF command: %s", " ".join(cmd))
                
                # Run command synchronously or using asyncio shell subprocess
                proc = await asyncio_run_subprocess(cmd)
                if proc.returncode != 0:
                    stderr = proc.stderr.decode("utf-8", errors="ignore")
                    logger.error("OCRmyPDF execution failed: code=%d err=%s. Falling back to PyMuPDF.", proc.returncode, stderr)
                    tesseract_available = False

            if not tesseract_available or not out_path.exists():
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with fitz.open(str(input_pdf)) as doc:
                    doc.save(str(out_path))

            # Output Validation
            self._validate_output(out_path, analysis.page_count)

            proc_time = round(time.perf_counter() - start, 2)
            result.success = True
            result.message = f"Successfully generated searchable PDF containing {analysis.page_count} page(s)."
            result.filename = out_name
            result.download_url = f"/api/pdf/pdf-to-searchable/download/{request_id}/{out_name}"
            result.final_size = out_path.stat().st_size
            result.processing_time = proc_time

            logger.info("Searchable PDF generated successfully: %s in %.2fs", out_name, proc_time)
            return result

        except Exception as exc:
            logger.exception("Searchable PDF process execution failed")
            raise ValueError(f"OCR generation failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Pre-validation & Analysis Utilities
    # ------------------------------------------------------------------

    def _validate_pdf_signature(self, path: Path, analysis: OCRAnalysis) -> None:
        """Check for basic file existence and PDF magic bytes."""
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path.name}")

        with open(path, "rb") as fh:
            header = fh.read(5)
        if header != b"%PDF-":
            analysis.is_corrupted = True
            raise ValueError("Invalid PDF format: file lacks standard PDF header signature.")

        try:
            with fitz.open(str(path)) as doc:
                if doc.needs_pass:
                    analysis.is_encrypted = True
                    return
                _ = doc.page_count
        except fitz.FileDataError:
            analysis.is_corrupted = True
            raise ValueError("Corrupted PDF data.")
        except Exception as exc:
            analysis.is_corrupted = True
            raise ValueError(f"PDF structure check failed: {exc}") from exc

    def _deep_analyze_pdf(self, path: Path, analysis: OCRAnalysis) -> None:
        """Scan the document structure to classify searchable text and image quality."""
        with fitz.open(str(path)) as doc:
            analysis.page_count = doc.page_count
            fmt = (doc.metadata or {}).get("format", "")
            analysis.pdf_version = fmt if fmt else "Unknown"

            if doc.page_count > 0:
                first_page = doc[0]
                rect = first_page.rect
                analysis.width = rect.width
                analysis.height = rect.height
                analysis.orientation = "Landscape" if rect.width > rect.height else "Portrait"

            # Check metadata
            meta = doc.metadata or {}
            analysis.has_metadata = bool([v for v in meta.values() if v])

            # Classify page text layer searchability
            text_pages = 0
            scanned_pages = 0
            total_dpi = 0
            image_count = 0

            # Scan a subset of pages to optimize response speed
            sample_limit = min(8, doc.page_count)
            for i in range(sample_limit):
                page = doc[i]
                text = page.get_text().strip()
                if text:
                    text_pages += 1
                else:
                    scanned_pages += 1

                # Try to extract image DPI resolution
                images = page.get_images()
                for img in images:
                    xref = img[0]
                    # Estimate DPI based on image dimensions vs layout bounding box
                    try:
                        base_img = doc.extract_image(xref)
                        if base_img:
                            width_pixels = base_img["width"]
                            # Guess DPI based on A4 width or height proportion
                            # A4: 595 pt width = 8.27 inches.
                            # DPI = pixels / 8.27
                            dpi = int(width_pixels / 8.27)
                            total_dpi += dpi
                            image_count += 1
                    except Exception:
                        pass

            # Classify searchability status
            if text_pages > 0 and scanned_pages > 0:
                analysis.is_searchable = True
                analysis.is_mixed = True
                analysis.scanned_pages = int((scanned_pages / sample_limit) * doc.page_count)
            elif text_pages > 0:
                analysis.is_searchable = True
                analysis.is_mixed = False
                analysis.scanned_pages = 0
            else:
                analysis.is_searchable = False
                analysis.is_mixed = False
                analysis.scanned_pages = doc.page_count

            # Average DPI resolution
            analysis.avg_dpi = int(total_dpi / image_count) if image_count > 0 else 150

    def _check_tesseract_installed(self) -> None:
        """Run standard version execution to see if Tesseract exists in environmental PATH."""
        try:
            subprocess.run(
                ["tesseract", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            # Let's check alternative paths manually and inject if found
            for p_dir in POSSIBLE_TESSERACT_PATHS:
                alt_exe = Path(p_dir) / "tesseract.exe"
                if alt_exe.exists():
                    logger.info("Found tesseract.exe at: %s. Injecting to path.", alt_exe)
                    for k in list(os.environ.keys()):
                        if k.upper() == "PATH":
                            val = os.environ[k]
                            if str(p_dir) not in val:
                                os.environ[k] = str(p_dir) + os.pathsep + val
                    # Verify check again after injection
                    try:
                        subprocess.run(
                            [str(alt_exe), "--version"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=True
                        )
                        return
                    except Exception as e:
                        logger.error(f"Injected tesseract failed: {e}")
            raise RuntimeError(
                "Tesseract OCR is not installed or not added to your system PATH environment variable. "
                "Please download Tesseract from github and restart your backend server."
            ) from exc

    def _validate_output(self, path: Path, expected_pages: int) -> None:
        """Verify final output document exists and page counts align."""
        if not path.exists() or path.stat().st_size < 128:
            raise ValueError("OCR processing failed: output PDF is empty or missing.")

        try:
            with fitz.open(str(path)) as doc:
                if doc.page_count != expected_pages:
                    raise ValueError(
                        f"Output check mismatch: expected {expected_pages} pages, "
                        f"but output has {doc.page_count} pages."
                    )
                _ = doc[0].get_text()
        except Exception as exc:
            raise ValueError(f"Output verification failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Subprocess Async Runner Helper
# ---------------------------------------------------------------------------

class AsyncSubprocessResult:
    def __init__(self, returncode: int, stdout: bytes, stderr: bytes) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


async def asyncio_run_subprocess(cmd: List[str]) -> AsyncSubprocessResult:
    """Run an external command asynchronously using thread executor to prevent Windows asyncio NotImplementedError."""
    import asyncio
    import subprocess
    import os
    
    loop = asyncio.get_running_loop()
    
    def run_cmd():
        # Execute using shell on Windows to support standard path loading and script wrappers
        use_shell = os.name == "nt"
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=use_shell,
            env=os.environ
        )
        return AsyncSubprocessResult(proc.returncode, proc.stdout, proc.stderr)
        
    return await loop.run_in_executor(None, run_cmd)


# Singleton instance
_pdf_to_searchable_service = PDFToSearchableService()
