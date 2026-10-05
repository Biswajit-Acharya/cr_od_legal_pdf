"""
Unlock PDF service.

Framework-independent business logic for authorized removal of PDF open
passwords and viewer-enforced security restrictions.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pikepdf

logger = logging.getLogger(__name__)


class UnlockPDFService:
    """Remove PDF encryption/security restrictions after valid authorization."""

    @staticmethod
    def validate_pdf(input_path: str | Path) -> Dict[str, Any]:
        """Validate basic PDF file properties without exposing filesystem details."""
        path = Path(input_path)
        if not path.exists() or path.stat().st_size == 0:
            raise ValueError("Valid PDF file is required.")
        if path.suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported.")

        try:
            with pikepdf.open(path) as pdf:
                return {
                    "encrypted": bool(pdf.is_encrypted),
                    "page_count": len(pdf.pages),
                    "restrictions": UnlockPDFService._permission_summary(pdf),
                }
        except pikepdf.PasswordError:
            return {
                "encrypted": True,
                "page_count": None,
                "restrictions": None,
            }
        except Exception as exc:
            raise ValueError("Invalid or corrupt PDF file.") from exc

    @staticmethod
    def is_pdf_encrypted(input_path: str | Path) -> bool:
        """Return whether the PDF is encrypted or password protected."""
        return bool(UnlockPDFService.validate_pdf(input_path)["encrypted"])

    @staticmethod
    def _permission_summary(pdf: pikepdf.Pdf) -> Dict[str, bool]:
        allow = pdf.allow
        return {
            "printing": bool(allow.print_lowres),
            "high_quality_printing": bool(allow.print_highres),
            "copying": bool(allow.extract),
            "editing": bool(allow.modify_other),
            "form_filling": bool(allow.modify_form),
            "commenting": bool(allow.modify_annotation),
            "accessibility": bool(allow.accessibility),
            "page_extraction": bool(allow.extract),
            "document_assembly": bool(allow.modify_assembly),
        }

    @staticmethod
    def validate_password(input_path: str | Path, password: str | None) -> pikepdf.Pdf:
        """Open the PDF with the supplied password, returning an authorized PDF handle."""
        path = Path(input_path)
        try:
            return pikepdf.open(path)
        except pikepdf.PasswordError:
            if not password:
                raise ValueError("Password is required for this encrypted PDF.")
            try:
                return pikepdf.open(path, password=password)
            except pikepdf.PasswordError as exc:
                raise ValueError("Incorrect password.") from exc
            except Exception as exc:
                raise ValueError("Unable to open the protected PDF.") from exc

    @staticmethod
    def remove_open_password(pdf: pikepdf.Pdf, output_path: str | Path) -> None:
        """Save the authorized PDF without encryption."""
        pdf.save(output_path)

    @staticmethod
    def remove_security_restrictions(pdf: pikepdf.Pdf, output_path: str | Path) -> None:
        """Remove viewer-enforced permission restrictions by saving without encryption."""
        UnlockPDFService.remove_open_password(pdf, output_path)

    @staticmethod
    def remove_editing_restriction(pdf: pikepdf.Pdf, output_path: str | Path) -> None:
        """Remove editing restriction where represented by PDF encryption permissions."""
        UnlockPDFService.remove_security_restrictions(pdf, output_path)

    @staticmethod
    def remove_printing_restriction(pdf: pikepdf.Pdf, output_path: str | Path) -> None:
        """Remove printing restriction where represented by PDF encryption permissions."""
        UnlockPDFService.remove_security_restrictions(pdf, output_path)

    @staticmethod
    def remove_copying_restriction(pdf: pikepdf.Pdf, output_path: str | Path) -> None:
        """Remove copying restriction where represented by PDF encryption permissions."""
        UnlockPDFService.remove_security_restrictions(pdf, output_path)

    @staticmethod
    def validate_unlocked_pdf(
        output_path: str | Path,
        *,
        expected_page_count: int | None = None,
    ) -> Dict[str, Any]:
        """Validate that generated output is readable and no longer encrypted."""
        path = Path(output_path)
        if not path.exists() or path.stat().st_size == 0:
            raise ValueError("Unlocked PDF output was not created.")

        try:
            with pikepdf.open(path) as pdf:
                page_count = len(pdf.pages)
                if pdf.is_encrypted:
                    raise ValueError("Unlocked PDF output is still encrypted.")
                if expected_page_count is not None and page_count != expected_page_count:
                    raise ValueError("Unlocked PDF page count does not match the input.")
                if page_count < 1:
                    raise ValueError("Unlocked PDF output has no pages.")
                return {
                    "page_count": page_count,
                    "encrypted": False,
                    "restrictions": UnlockPDFService._permission_summary(pdf),
                }
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Unlocked PDF output could not be validated.") from exc

    @staticmethod
    def _atomic_output_path(dest: Path) -> Path:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{dest.stem}_",
            suffix=".pdf.tmp",
            dir=str(dest.parent),
        )
        os.close(fd)
        return Path(tmp_name)

    def unlock_pdf(
        self,
        input_path: str,
        output_path: str,
        password: str | None = None,
    ) -> Dict[str, Any]:
        """Unlock a single PDF after validating authorization."""
        src = Path(input_path)
        dest = Path(output_path)
        tmp_path: Path | None = None

        try:
            input_info = self.validate_pdf(src)
            os.makedirs(dest.parent, exist_ok=True)
            tmp_path = self._atomic_output_path(dest)

            with self.validate_password(src, password) as pdf:
                page_count = len(pdf.pages)
                before_restrictions = self._permission_summary(pdf)
                was_encrypted = bool(pdf.is_encrypted)
                self.remove_security_restrictions(pdf, tmp_path)

            output_info = self.validate_unlocked_pdf(
                tmp_path,
                expected_page_count=page_count,
            )
            os.replace(tmp_path, dest)
            tmp_path = None

            return {
                "success": True,
                "message": "PDF unlocked successfully.",
                "was_encrypted": bool(input_info["encrypted"] or was_encrypted),
                "page_count": output_info["page_count"],
                "restrictions_removed": before_restrictions,
                "security_summary": {
                    "password_removed": bool(input_info["encrypted"] or was_encrypted),
                    "permissions_removed": True,
                    "encrypted": False,
                    "note": "Only authorized unlocking is supported; no password bypass or recovery is performed.",
                },
                "output_file": dest.name,
            }
        except Exception as exc:
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    logger.warning("Could not remove invalid unlocked PDF output: %s", dest)
            if isinstance(exc, ValueError):
                logger.warning("unlock_pdf validation failed: %s", exc)
            else:
                logger.error("unlock_pdf failed: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    logger.warning("Could not remove temporary unlock output: %s", tmp_path)

    def unlock_multiple_pdfs(
        self,
        jobs: Iterable[Tuple[str, str, str | None]],
    ) -> Dict[str, Any]:
        """Unlock multiple PDFs by reusing the same single-file implementation."""
        results: List[Dict[str, Any]] = []
        success_count = 0

        for input_path, output_path, password in jobs:
            result = self.unlock_pdf(input_path, output_path, password)
            results.append(result)
            if result.get("success"):
                success_count += 1

        return {
            "success": success_count == len(results),
            "total": len(results),
            "unlocked": success_count,
            "failed": len(results) - success_count,
            "results": results,
        }


unlock_pdf_service = UnlockPDFService()
