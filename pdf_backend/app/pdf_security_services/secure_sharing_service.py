import json
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from fastapi import HTTPException
from passlib.context import CryptContext

from app.core.paths import Paths

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecureSharingService:
    """Service for managing secure PDF sharing."""

    @staticmethod
    def _get_shares_dir() -> Path:
        return Paths.secure_shares()

    @staticmethod
    def _get_share_path(token: str) -> Path:
        return SecureSharingService._get_shares_dir() / f"{token}.json"

    @staticmethod
    def create_share(
        source_file_path: Path,
        original_filename: str,
        password: Optional[str] = None,
        expires_at: Optional[str] = None,
        allow_download: bool = False,
        allow_print: bool = False
    ) -> Dict[str, Any]:
        """Creates a secure share and returns tokens."""
        share_token = secrets.token_urlsafe(32)
        management_token = secrets.token_urlsafe(32)

        # Store a copy of the shared file inside the secure shares directory
        shared_file_path = SecureSharingService._get_shares_dir() / f"{share_token}.pdf"
        shutil.copy2(source_file_path, shared_file_path)

        password_hash = pwd_context.hash(password) if password else None

        share_data = {
            "token": share_token,
            "management_token": management_token,
            "filename": original_filename,
            "password_hash": password_hash,
            "expires_at": expires_at,
            "allow_download": allow_download,
            "allow_print": allow_print,
            "is_revoked": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "access_count": 0,
            "last_accessed_at": None,
        }

        # Save metadata
        metadata_path = SecureSharingService._get_share_path(share_token)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(share_data, f, indent=2)

        return {
            "share_token": share_token,
            "management_token": management_token,
            "share_url": f"/shared/{share_token}",
            "expires_at": expires_at,
            "allow_download": allow_download,
            "allow_print": allow_print
        }

    @staticmethod
    def _load_share(token: str) -> Dict[str, Any]:
        """Load share metadata, raise exception if invalid."""
        metadata_path = SecureSharingService._get_share_path(token)
        if not metadata_path.exists():
            raise HTTPException(status_code=404, detail="Share not found or invalid token.")

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Corrupted share metadata.")

    @staticmethod
    def _save_share(token: str, data: Dict[str, Any]) -> None:
        """Save share metadata."""
        metadata_path = SecureSharingService._get_share_path(token)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def validate_share_access(token: str, password: Optional[str] = None) -> Dict[str, Any]:
        """Validate if a share can be accessed, checks expiry and revocation."""
        share_data = SecureSharingService._load_share(token)

        if share_data.get("is_revoked"):
            raise HTTPException(status_code=403, detail="Access to this document has been revoked.")

        expires_at = share_data.get("expires_at")
        if expires_at:
            try:
                # Handle ISO format parsing safely
                if expires_at.endswith('Z'):
                    expires_at = expires_at[:-1] + '+00:00'
                expiry_dt = datetime.fromisoformat(expires_at)
                if datetime.now(timezone.utc) > expiry_dt:
                    raise HTTPException(status_code=403, detail="This secure share link has expired.")
            except ValueError:
                pass  # If we can't parse it, we skip the check (or handle differently)

        return share_data

    @staticmethod
    def verify_password(token: str, password: str) -> bool:
        """Verifies the password for a share."""
        share_data = SecureSharingService._load_share(token)
        
        # Validate revocation and expiration first
        SecureSharingService.validate_share_access(token)

        password_hash = share_data.get("password_hash")
        if not password_hash:
            return True  # No password required
            
        if not password:
            raise HTTPException(status_code=401, detail="Password is required.")

        if not pwd_context.verify(password, password_hash):
            raise HTTPException(status_code=401, detail="Incorrect password.")

        return True

    @staticmethod
    def record_access(token: str) -> None:
        """Record that a share was accessed."""
        share_data = SecureSharingService._load_share(token)
        share_data["access_count"] = share_data.get("access_count", 0) + 1
        share_data["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
        SecureSharingService._save_share(token, share_data)

    @staticmethod
    def get_shared_file_path(token: str) -> Path:
        """Returns the path to the physical PDF file."""
        return SecureSharingService._get_shares_dir() / f"{token}.pdf"

    @staticmethod
    def revoke_share(token: str, management_token: str) -> Dict[str, Any]:
        """Revokes a share if the management token is valid."""
        share_data = SecureSharingService._load_share(token)
        
        if share_data.get("management_token") != management_token:
            raise HTTPException(status_code=403, detail="Not authorized to revoke this share.")
            
        share_data["is_revoked"] = True
        SecureSharingService._save_share(token, share_data)
        
        return {"status": "success", "message": "Share revoked successfully."}

    @staticmethod
    def update_share(
        token: str, 
        management_token: str,
        password: Optional[str] = None,
        expires_at: Optional[str] = None,
        allow_download: Optional[bool] = None,
        allow_print: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Updates share settings if the management token is valid."""
        share_data = SecureSharingService._load_share(token)
        
        if share_data.get("management_token") != management_token:
            raise HTTPException(status_code=403, detail="Not authorized to update this share.")
            
        if password is not None:
            share_data["password_hash"] = pwd_context.hash(password) if password else None
            
        if expires_at is not None:
            share_data["expires_at"] = expires_at
            
        if allow_download is not None:
            share_data["allow_download"] = allow_download
            
        if allow_print is not None:
            share_data["allow_print"] = allow_print
            
        SecureSharingService._save_share(token, share_data)
        
        return {"status": "success", "message": "Share updated successfully.", "share": {k: v for k, v in share_data.items() if k not in ["management_token", "password_hash"]}}

    @staticmethod
    def get_shares_by_management_tokens(management_tokens: List[str]) -> List[Dict[str, Any]]:
        """Finds all shares matching the provided management tokens."""
        shares_dir = SecureSharingService._get_shares_dir()
        result = []
        
        if not shares_dir.exists():
            return result
            
        for filepath in shares_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    share_data = json.load(f)
                    if share_data.get("management_token") in management_tokens:
                        # Exclude sensitive data
                        safe_data = {k: v for k, v in share_data.items() if k not in ["password_hash"]}
                        safe_data["has_password"] = bool(share_data.get("password_hash"))
                        
                        # Add dynamic status
                        status = "Active"
                        if safe_data.get("is_revoked"):
                            status = "Revoked"
                        elif safe_data.get("expires_at"):
                            expires_at = safe_data["expires_at"]
                            if expires_at.endswith('Z'):
                                expires_at = expires_at[:-1] + '+00:00'
                            try:
                                if datetime.now(timezone.utc) > datetime.fromisoformat(expires_at):
                                    status = "Expired"
                            except ValueError:
                                pass
                        safe_data["status"] = status
                        
                        result.append(safe_data)
            except (json.JSONDecodeError, OSError):
                continue
                
        # Sort by creation date descending
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return result
