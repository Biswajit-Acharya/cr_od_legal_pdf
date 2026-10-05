"""Apply predefined PDF security policy templates with real encryption."""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pikepdf

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PolicyPermissionSettings:
    printing: bool = False
    high_quality_printing: bool = False
    copying: bool = False
    editing: bool = False
    form_filling: bool = False
    commenting: bool = False
    accessibility: bool = True
    page_extraction: bool = False
    document_assembly: bool = False


@dataclass(frozen=True)
class SecurityPolicyTemplate:
    id: str
    code: str
    name: str
    description: str
    security_level: str
    permissions: PolicyPermissionSettings
    encryption: str = "AES-256"
    password_required: bool = True
    use_cases: list[str] = field(default_factory=list)


POLICY_TEMPLATES: dict[str, SecurityPolicyTemplate] = {
    "standard_protection": SecurityPolicyTemplate(
        id="standard_protection",
        code="STANDARD_PROTECTION",
        name="Standard Protection",
        description="Balanced protection for everyday business documents.",
        security_level="Medium",
        permissions=PolicyPermissionSettings(
            printing=True,
            form_filling=True,
            commenting=True,
            accessibility=True,
        ),
        use_cases=["Internal documents", "Draft agreements", "Routine review packs"],
    ),
    "confidential": SecurityPolicyTemplate(
        id="confidential",
        code="CONFIDENTIAL",
        name="Confidential",
        description="Strict policy for sensitive documents that can be viewed and printed only.",
        security_level="High",
        permissions=PolicyPermissionSettings(
            printing=True,
            accessibility=True,
        ),
        use_cases=["Client records", "Legal notices", "Financial summaries"],
    ),
    "read_only": SecurityPolicyTemplate(
        id="read_only",
        code="READ_ONLY",
        name="Read Only",
        description="Prevents editing, assembly, extraction, copying, and annotations.",
        security_level="High",
        permissions=PolicyPermissionSettings(
            printing=True,
            high_quality_printing=True,
            accessibility=True,
        ),
        use_cases=["Signed copies", "Published policies", "Reference documents"],
    ),
    "no_printing": SecurityPolicyTemplate(
        id="no_printing",
        code="NO_PRINTING",
        name="No Printing",
        description="Allows screen viewing while blocking both low and high quality printing.",
        security_level="High",
        permissions=PolicyPermissionSettings(accessibility=True),
        use_cases=["Portal-only files", "Preview copies", "Review room documents"],
    ),
    "no_copying": SecurityPolicyTemplate(
        id="no_copying",
        code="NO_COPYING",
        name="No Copying",
        description="Allows viewing and printing while preventing text/image copying and extraction.",
        security_level="High",
        permissions=PolicyPermissionSettings(
            printing=True,
            high_quality_printing=True,
            accessibility=True,
        ),
        use_cases=["Client deliverables", "Court bundles", "Licensed content"],
    ),
    "maximum_protection": SecurityPolicyTemplate(
        id="maximum_protection",
        code="MAXIMUM_PROTECTION",
        name="Maximum Protection",
        description="Locks every discretionary permission except accessibility support.",
        security_level="Maximum",
        permissions=PolicyPermissionSettings(accessibility=True),
        use_cases=["Trade secrets", "Highly confidential matters", "Executive documents"],
    ),
}


class PDFSecurityPolicyTemplateService:
    """Service for listing templates and applying verified PDF protection."""

    @staticmethod
    def _normalize_template_id(template_id: str | None) -> str:
        value = (template_id or "").strip().lower().replace("-", "_")
        aliases = {template.code.lower(): template.id for template in POLICY_TEMPLATES.values()}
        aliases.update({template.id: template.id for template in POLICY_TEMPLATES.values()})
        if value not in aliases:
            raise ValueError("Unknown security policy template.")
        return aliases[value]

    @staticmethod
    def _template_payload(template: SecurityPolicyTemplate) -> dict[str, Any]:
        return asdict(template)

    def list_templates(self) -> dict[str, Any]:
        templates = [self._template_payload(template) for template in POLICY_TEMPLATES.values()]
        return {
            "success": True,
            "templates": templates,
            "count": len(templates),
            "message": "Security policy templates loaded.",
        }

    def get_template(self, template_id: str) -> dict[str, Any]:
        normalized = self._normalize_template_id(template_id)
        return {
            "success": True,
            "template": self._template_payload(POLICY_TEMPLATES[normalized]),
        }

    @staticmethod
    def _validate_password(password: str | None, confirm_password: str | None) -> str:
        clean_password = (password or "").strip()
        clean_confirmation = "" if confirm_password is None else confirm_password.strip()
        if not clean_password:
            raise ValueError("Password is required to apply a security policy.")
        if len(clean_password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if confirm_password is not None and clean_password != clean_confirmation:
            raise ValueError("Password confirmation does not match.")
        return clean_password

    @staticmethod
    def _validate_input_pdf(input_path: Path) -> None:
        if not input_path.exists() or input_path.stat().st_size == 0:
            raise ValueError("Valid PDF file is required.")
        if input_path.suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported.")
        if input_path.stat().st_size > settings.MAX_UPLOAD_SIZE:
            raise ValueError(f"PDF exceeds the maximum upload size of {settings.MAX_UPLOAD_SIZE_MB} MB.")

        with open(input_path, "rb") as file_obj:
            header = file_obj.read(5)
        if header != b"%PDF-":
            raise ValueError("Invalid PDF file signature.")

        try:
            with pikepdf.open(input_path) as pdf:
                if len(pdf.pages) < 1:
                    raise ValueError("PDF must contain at least one page.")
        except pikepdf.PasswordError as exc:
            raise ValueError("Encrypted input PDFs must be unlocked before applying a policy.") from exc
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Invalid or corrupt PDF file.") from exc

    @staticmethod
    def _build_permissions(permissions: PolicyPermissionSettings) -> pikepdf.Permissions:
        return pikepdf.Permissions(
            accessibility=permissions.accessibility,
            extract=permissions.copying or permissions.page_extraction,
            modify_annotation=permissions.commenting,
            modify_assembly=permissions.document_assembly,
            modify_form=permissions.form_filling,
            modify_other=permissions.editing,
            print_lowres=permissions.printing or permissions.high_quality_printing,
            print_highres=permissions.high_quality_printing,
        )

    @staticmethod
    def _expected_permission_map(permissions: PolicyPermissionSettings) -> dict[str, bool]:
        return {
            "printing": permissions.printing,
            "high_quality_printing": permissions.high_quality_printing,
            "copying": permissions.copying,
            "editing": permissions.editing,
            "form_filling": permissions.form_filling,
            "commenting": permissions.commenting,
            "accessibility": permissions.accessibility,
            "page_extraction": permissions.page_extraction,
            "document_assembly": permissions.document_assembly,
        }

    @staticmethod
    def _actual_permission_map(allow: pikepdf.Permissions) -> dict[str, bool]:
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

    def _verify_output_pdf(
        self,
        output_path: Path,
        password: str,
        expected_permissions: PolicyPermissionSettings,
    ) -> dict[str, Any]:
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ValueError("Secured PDF output was not created.")

        password_required = False
        try:
            with pikepdf.open(output_path):
                pass
        except pikepdf.PasswordError:
            password_required = True

        expected = self._expected_permission_map(expected_permissions)
        try:
            with pikepdf.open(output_path, password=password) as pdf:
                actual = self._actual_permission_map(pdf.allow)
                encrypted = bool(pdf.is_encrypted)
                pdf_valid = len(pdf.pages) > 0
        except Exception as exc:
            raise ValueError("Secured PDF output could not be opened with the provided password.") from exc

        details = {
            key: {
                "expected": expected_value,
                "actual": actual.get(key),
                "verified": actual.get(key) == expected_value,
            }
            for key, expected_value in expected.items()
        }
        permissions_verified = all(item["verified"] for item in details.values())

        return {
            "pdf_valid": pdf_valid,
            "encrypted": encrypted,
            "password_required": password_required,
            "password_authenticated": True,
            "permissions_verified": permissions_verified,
            "permissions": actual,
            "permission_details": details,
        }

    def apply_template(
        self,
        input_path: str | Path,
        output_path: str | Path,
        *,
        template_id: str,
        password: str | None,
        confirm_password: str | None = None,
        original_filename: str | None = None,
    ) -> dict[str, Any]:
        src = Path(input_path)
        dest = Path(output_path)

        try:
            normalized = self._normalize_template_id(template_id)
            template = POLICY_TEMPLATES[normalized]
            clean_password = self._validate_password(password, confirm_password)
            self._validate_input_pdf(src)

            os.makedirs(dest.parent, exist_ok=True)
            permissions = self._build_permissions(template.permissions)
            owner_password = secrets.token_urlsafe(32)

            with pikepdf.open(src) as pdf:
                pdf.save(
                    dest,
                    encryption=pikepdf.Encryption(
                        owner=owner_password,
                        user=clean_password,
                        R=6,
                        allow=permissions,
                        aes=True,
                        metadata=True,
                    ),
                )

            verification = self._verify_output_pdf(dest, clean_password, template.permissions)
            if not verification["encrypted"] or not verification["password_required"]:
                raise ValueError("Security policy verification failed: output is not password protected.")
            if not verification["permissions_verified"]:
                raise ValueError("Security policy verification failed: permissions did not match the selected template.")

            permission_summary = self._expected_permission_map(template.permissions)
            return {
                "success": True,
                "message": "Security policy applied successfully.",
                "template": template.code,
                "template_id": template.id,
                "template_name": template.name,
                "original_filename": original_filename,
                "security_applied": True,
                "encryption": template.encryption,
                "permissions": permission_summary,
                "verification": verification,
                "policy": self._template_payload(template),
                "output_file": dest.name,
            }
        except Exception as exc:
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    logger.warning("Could not remove failed policy output: %s", dest)
            if isinstance(exc, ValueError):
                logger.warning("security policy template validation failed: %s", exc)
            else:
                logger.error("security policy template failed: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    @staticmethod
    def cleanup_temporary_files(paths: list[str | Path | None]) -> None:
        for item in paths:
            if not item:
                continue
            try:
                Path(item).unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not clean temporary file: %s", item)


pdf_security_policy_template_service = PDFSecurityPolicyTemplateService()
