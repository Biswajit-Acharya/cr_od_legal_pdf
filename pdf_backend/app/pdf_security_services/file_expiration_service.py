"""
File Expiration service.

Provides logic to create and verify file expiration policies.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)

class FileExpirationService:
    """Manages expiration policies for PDF files."""
    
    @staticmethod
    def _get_policy_path(output_dir: Path) -> Path:
        """Get the path to the expiration policy file for a specific request."""
        return output_dir / "expiration_policy.json"
        
    def apply_expiration_policy(
        self,
        output_dir: Path,
        expiration_type: str,
        expires_at: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Creates and stores an expiration policy.
        """
        expiration_type = expiration_type.strip().lower()
        now = datetime.now(timezone.utc)
        
        final_expires_at = None
        
        if expiration_type == "date":
            if not expires_at:
                raise ValueError("expires_at is required for 'date' expiration type")
            try:
                # Expecting ISO format string like "2026-10-01T23:59:59Z"
                dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                final_expires_at = dt
            except ValueError:
                raise ValueError("Invalid expires_at date format. Must be ISO 8601.")
        
        elif expiration_type == "duration":
            if duration_seconds is None or int(duration_seconds) <= 0:
                raise ValueError("duration_seconds must be a positive integer for 'duration' expiration type")
            final_expires_at = now + timedelta(seconds=int(duration_seconds))
            
        else:
            raise ValueError("Invalid expiration_type. Must be 'date' or 'duration'.")
            
        if final_expires_at <= now:
            raise ValueError("Expiration time must be in the future.")
            
        policy = {
            "expiration_type": expiration_type,
            "created_at": now.isoformat(),
            "expires_at": final_expires_at.isoformat(),
            "duration_seconds": duration_seconds,
            "status": "ACTIVE",
            "expired": False
        }
        
        output_dir.mkdir(parents=True, exist_ok=True)
        policy_path = self._get_policy_path(output_dir)
        
        with open(policy_path, "w") as f:
            json.dump(policy, f, indent=4)
            
        return policy

    def check_file_expiration(self, output_dir: Path) -> None:
        """
        Checks if a file in the given output_dir has expired.
        Raises HTTPException 403 if it has expired.
        """
        policy_path = self._get_policy_path(output_dir)
        if not policy_path.exists():
            # No expiration policy means it's valid forever
            return
            
        try:
            with open(policy_path, "r") as f:
                policy = json.load(f)
        except json.JSONDecodeError:
            # Corrupt policy? Deny access to be safe.
            raise HTTPException(status_code=403, detail="Corrupted expiration policy.")
            
        expires_at_str = policy.get("expires_at")
        if not expires_at_str:
            return
            
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
        except ValueError:
            return
            
        now = datetime.now(timezone.utc)
        
        if now >= expires_at:
            # Mark as expired in the JSON if not already (optional but good practice)
            if not policy.get("expired", False):
                policy["expired"] = True
                policy["status"] = "EXPIRED"
                try:
                    with open(policy_path, "w") as f:
                        json.dump(policy, f, indent=4)
                except Exception as e:
                    logger.error(f"Failed to update expiration policy status: {e}")
                    
            raise HTTPException(
                status_code=403, 
                detail="This PDF has expired and is no longer accessible."
            )
            
    def get_expiration_status(self, output_dir: Path) -> Dict[str, Any]:
        """Gets the current expiration status for frontend display."""
        policy_path = self._get_policy_path(output_dir)
        if not policy_path.exists():
            return {"expiration_enabled": False, "status": "NO_EXPIRATION"}
            
        try:
            with open(policy_path, "r") as f:
                policy = json.load(f)
        except json.JSONDecodeError:
            return {"expiration_enabled": False, "status": "ERROR"}
            
        expires_at_str = policy.get("expires_at")
        if not expires_at_str:
             return {"expiration_enabled": False, "status": "NO_EXPIRATION"}
             
        expires_at = datetime.fromisoformat(expires_at_str)
        now = datetime.now(timezone.utc)
        
        expired = now >= expires_at
        
        return {
            "expiration_enabled": True,
            "expires_at": expires_at_str,
            "status": "EXPIRED" if expired else "ACTIVE",
            "expired": expired
        }

file_expiration_service = FileExpirationService()
