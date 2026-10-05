"""
Protect PDF service.

Contains the framework-independent business logic for password protecting
PDFs with AES encryption and viewer-enforced permission flags.
"""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path
from typing import Any, Dict

import pikepdf

logger = logging.getLogger(__name__)


class ProtectPDFService:
    """Apply password protection, encryption, and PDF permission flags."""

    _ENCRYPTION_REVISIONS = {
        "aes-128": 4,
        "aes_128": 4,
        "128": 4,
        "aes128": 4,
        "aes-256": 6,
        "aes_256": 6,
        "256": 6,
        "aes256": 6,
    }

    @staticmethod
    def _normalize_encryption(encryption: str | None) -> tuple[str, int]:
        value = (encryption or "aes-256").strip().lower()
        revision = ProtectPDFService._ENCRYPTION_REVISIONS.get(value)
        if revision is None:
            raise ValueError("Unsupported encryption selection. Choose AES-128 or AES-256.")
        return ("AES-128" if revision == 4 else "AES-256"), revision

    @staticmethod
    def _validate_passwords(user_password: str | None, confirm_password: str | None) -> None:
        password = (user_password or "").strip()
        confirmation = "" if confirm_password is None else confirm_password.strip()

        if not password:
            raise ValueError("Password is required.")
        if confirm_password is not None and password != confirmation:
            raise ValueError("Password confirmation does not match.")

    @staticmethod
    def _build_permissions(
        *,
        allow_print: bool,
        allow_high_quality_print: bool,
        allow_copy: bool,
        allow_edit: bool,
        allow_form_fill: bool,
        allow_comment: bool,
        allow_accessibility: bool,
        allow_page_extraction: bool,
        allow_document_assembly: bool,
    ) -> pikepdf.Permissions:
        return pikepdf.Permissions(
            accessibility=allow_accessibility,
            extract=allow_copy or allow_page_extraction,
            modify_annotation=allow_comment,
            modify_assembly=allow_document_assembly,
            modify_form=allow_form_fill,
            modify_other=allow_edit,
            print_lowres=allow_print or allow_high_quality_print,
            print_highres=allow_high_quality_print,
        )

    @staticmethod
    def _summary_permissions(
        *,
        allow_print: bool,
        allow_high_quality_print: bool,
        allow_copy: bool,
        allow_edit: bool,
        allow_form_fill: bool,
        allow_comment: bool,
        allow_accessibility: bool,
        allow_page_extraction: bool,
        allow_document_assembly: bool,
    ) -> Dict[str, bool]:
        return {
            "printing": allow_print,
            "high_quality_printing": allow_high_quality_print,
            "copying": allow_copy,
            "editing": allow_edit,
            "form_filling": allow_form_fill,
            "commenting": allow_comment,
            "accessibility": allow_accessibility,
            "page_extraction": allow_page_extraction,
            "document_assembly": allow_document_assembly,
        }

    @staticmethod
    def _validate_input_pdf(input_path: Path) -> None:
        if not input_path.exists() or input_path.stat().st_size == 0:
            raise ValueError("Valid PDF file is required.")
        if input_path.suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported.")

        try:
            with pikepdf.open(input_path):
                pass
        except pikepdf.PasswordError as exc:
            raise ValueError("Encrypted input PDFs must be unlocked before protection.") from exc
        except Exception as exc:
            raise ValueError("Invalid or corrupt PDF file.") from exc

    @staticmethod
    def _validate_output_pdf(output_path: Path, user_password: str) -> None:
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ValueError("Protected PDF output was not created.")

        try:
            with pikepdf.open(output_path):
                raise ValueError("Protected PDF output is not encrypted.")
        except pikepdf.PasswordError:
            pass

        try:
            with pikepdf.open(output_path, password=user_password) as pdf:
                if not pdf.is_encrypted:
                    raise ValueError("Protected PDF output is not encrypted.")
                if len(pdf.pages) < 1:
                    raise ValueError("Protected PDF output has no pages.")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Protected PDF output could not be validated.") from exc

    def protect_pdf(
        self,
        input_path: str,
        output_path: str,
        user_password: str,
        *,
        confirm_password: str | None = None,
        owner_password: str | None = None,
        encryption: str | None = "aes-256",
        allow_print: bool = False,
        allow_high_quality_print: bool = False,
        allow_copy: bool = False,
        allow_edit: bool = False,
        allow_form_fill: bool = False,
        allow_comment: bool = False,
        allow_accessibility: bool = True,
        allow_page_extraction: bool = False,
        allow_document_assembly: bool = False,
    ) -> Dict[str, Any]:
        """Protect a PDF with a user password, owner password, AES, and permissions."""
        src = Path(input_path)
        dest = Path(output_path)

        try:
            self._validate_passwords(user_password, confirm_password)
            encryption_label, revision = self._normalize_encryption(encryption)
            self._validate_input_pdf(src)

            permissions = self._build_permissions(
                allow_print=allow_print,
                allow_high_quality_print=allow_high_quality_print,
                allow_copy=allow_copy,
                allow_edit=allow_edit,
                allow_form_fill=allow_form_fill,
                allow_comment=allow_comment,
                allow_accessibility=allow_accessibility,
                allow_page_extraction=allow_page_extraction,
                allow_document_assembly=allow_document_assembly,
            )
            permission_summary = self._summary_permissions(
                allow_print=allow_print,
                allow_high_quality_print=allow_high_quality_print,
                allow_copy=allow_copy,
                allow_edit=allow_edit,
                allow_form_fill=allow_form_fill,
                allow_comment=allow_comment,
                allow_accessibility=allow_accessibility,
                allow_page_extraction=allow_page_extraction,
                allow_document_assembly=allow_document_assembly,
            )

            os.makedirs(dest.parent, exist_ok=True)
            owner = owner_password.strip() if owner_password else secrets.token_urlsafe(32)

            with pikepdf.open(src) as pdf:
                pdf.save(
                    dest,
                    encryption=pikepdf.Encryption(
                        owner=owner,
                        user=user_password,
                        R=revision,
                        allow=permissions,
                        aes=True,
                        metadata=True,
                    ),
                )

            self._validate_output_pdf(dest, user_password)

            return {
                "success": True,
                "message": "PDF protected successfully.",
                "encryption": encryption_label,
                "permissions": permission_summary,
                "security_summary": {
                    "password_protected": True,
                    "owner_password_set": bool(owner_password),
                    "encryption": encryption_label,
                    "permissions_are_viewer_enforced": True,
                    "note": "PDF permission restrictions are enforced by compliant PDF viewers.",
                },
                "output_file": dest.name,
            }
        except Exception as exc:
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    logger.warning("Could not remove invalid protected PDF output: %s", dest)
            if isinstance(exc, ValueError):
                logger.warning("protect_pdf validation failed: %s", exc)
            else:
                logger.error("protect_pdf failed: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}


    @staticmethod
    def _validate_restriction_output(output_path: Path) -> None:
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ValueError("Protected PDF output was not created.")

        try:
            with pikepdf.open(output_path, password="") as pdf:
                if pdf.allow.extract:
                    raise ValueError("Page extraction is still allowed in the output PDF.")
        except pikepdf.PasswordError:
             raise ValueError("Unexpected password required to open the output PDF.")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Protected PDF output could not be validated.") from exc

    def restrict_page_extraction(
        self,
        input_path: str,
        output_path: str,
        encryption: str | None = "aes-256",
    ) -> Dict[str, Any]:
        """Restrict page extraction by applying an owner password and disabling extraction permissions."""
        src = Path(input_path)
        dest = Path(output_path)

        try:
            encryption_label, revision = self._normalize_encryption(encryption)
            self._validate_input_pdf(src)

            permissions = pikepdf.Permissions(
                accessibility=True,
                extract=False,
                modify_annotation=True,
                modify_assembly=True,
                modify_form=True,
                modify_other=True,
                print_lowres=True,
                print_highres=True,
            )

            os.makedirs(dest.parent, exist_ok=True)
            owner = secrets.token_urlsafe(32)
            user_password = "" 

            with pikepdf.open(src) as pdf:
                pdf.save(
                    dest,
                    encryption=pikepdf.Encryption(
                        owner=owner,
                        user=user_password,
                        R=revision,
                        allow=permissions,
                        aes=True,
                        metadata=True,
                    ),
                )

            self._validate_restriction_output(dest)

            return {
                "success": True,
                "feature": "Restrict Page Extraction",
                "message": "Page extraction restriction applied successfully.",
                "extraction_restricted": True,
                "output_file": dest.name,
            }
        except Exception as exc:
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    logger.warning("Could not remove invalid protected PDF output: %s", dest)
            if isinstance(exc, ValueError):
                logger.warning("restrict_page_extraction validation failed: %s", exc)
            else:
                logger.error("restrict_page_extraction failed: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    @staticmethod
    def check_extraction_permission(input_path: Path | str) -> None:
        """
        Verify if the given PDF allows page extraction.
        Raises PermissionError if extraction is restricted.
        """
        try:
            with pikepdf.open(str(input_path), password="") as pdf:
                if not pdf.allow.extract:
                    raise PermissionError("Page extraction is restricted for this PDF. The document owner has disabled page extraction.")
        except pikepdf.PasswordError:
            # If the PDF requires a user password, we can't process it blindly anyway,
            # but if it's strictly an extraction restriction, we raise ValueError.
            raise ValueError("PDF is password protected and cannot be processed.")
        except PermissionError:
            raise
        except Exception as exc:
            # Any other exception (like invalid PDF), just let the next tool handle it, or raise ValueError
            pass

protect_pdf_service = ProtectPDFService()
