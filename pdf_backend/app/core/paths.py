"""
Centralised path resolution for all storage directories.

Every module should import paths from here instead of constructing
directories ad-hoc.  Directories are created on first access.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings


def _ensure_dir(path: Path) -> Path:
    """Create directory if it doesn't exist and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


class Paths:
    """Resolved application directories."""

    @staticmethod
    def storage() -> Path:
        return _ensure_dir(Path(settings.STORAGE_DIR))

    @staticmethod
    def uploads() -> Path:
        return _ensure_dir(Path(settings.UPLOAD_DIR))

    @staticmethod
    def outputs() -> Path:
        return _ensure_dir(Path(settings.OUTPUT_DIR))

    @staticmethod
    def temp() -> Path:
        return _ensure_dir(Path(settings.TEMP_DIR))

    @staticmethod
    def request_upload(request_id: str) -> Path:
        return _ensure_dir(Path(settings.UPLOAD_DIR) / request_id)

    @staticmethod
    def request_output(request_id: str) -> Path:
        return _ensure_dir(Path(settings.OUTPUT_DIR) / request_id)

    @staticmethod
    def request_temp(request_id: str) -> Path:
        return _ensure_dir(Path(settings.TEMP_DIR) / request_id)

    @staticmethod
    def file_manager_root() -> Path:
        return _ensure_dir(Path(settings.STORAGE_DIR) / "file_manager")

    @staticmethod
    def annotations() -> Path:
        return _ensure_dir(Path(settings.ANNOTATION_DIR))

    @staticmethod
    def secure_shares() -> Path:
        return _ensure_dir(Path(settings.STORAGE_DIR) / "secure_shares")



def get_upload_path(document_id: str) -> Path:
    return Path(settings.UPLOAD_DIR) / f"{document_id}.pdf"


def get_output_path(document_id: str) -> Path:
    return Path(settings.OUTPUT_DIR) / f"{document_id}_annotated.pdf"


def get_annotation_path(document_id: str) -> Path:
    # Ensure annotations directory exists
    Path(settings.ANNOTATION_DIR).mkdir(parents=True, exist_ok=True)
    return Path(settings.ANNOTATION_DIR) / f"{document_id}_annotations.json"


# Compatibility constants for Image Processing services
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = Path(settings.UPLOAD_DIR)
DOWNLOADS_DIR = Path(settings.OUTPUT_DIR)
TEMP_PROCESSING_DIR = Path(settings.TEMP_DIR)

