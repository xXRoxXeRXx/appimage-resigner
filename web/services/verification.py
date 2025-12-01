"""
Verification Service
Handles AppImage signature verification operations.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.verify import AppImageVerifier
from web.core.exceptions import MissingFileError, GPGVerificationError
from web.api.models import VerificationResponse, SignatureStatus


class VerificationService:
    """Service for handling AppImage signature verification."""
    
    def __init__(self, gpg_home: Optional[str] = None):
        """Initialize verification service."""
        self.verifier = AppImageVerifier(gpg_home=gpg_home)
    
    def verify_signature(
        self,
        appimage_path: Path,
        signature_path: Optional[Path] = None
    ) -> VerificationResponse:
        """Verify AppImage signature.
        
        Args:
            appimage_path: Path to the AppImage file
            signature_path: Optional path to detached signature
            
        Returns:
            VerificationResponse with verification result
        """
        if not appimage_path.exists():
            raise MissingFileError("appimage", str(appimage_path))
        
        try:
            result = self.verifier.verify_signature(
                str(appimage_path),
                str(signature_path) if signature_path else None
            )
            
            status = SignatureStatus.VALID if result.get('valid') else SignatureStatus.INVALID
            
            return VerificationResponse(
                status=status,
                filename=appimage_path.name,
                signed_by=result.get('username'),
                key_id=result.get('key_id'),
                fingerprint=result.get('fingerprint'),
                timestamp=datetime.fromisoformat(result['timestamp']) if result.get('timestamp') else None,
                trust_level=result.get('trust'),
                signature_type='embedded' if not signature_path else 'detached',
                message=result.get('message', 'Verification complete')
            )
            
        except Exception as e:
            if isinstance(e, MissingFileError):
                raise
            raise GPGVerificationError(str(e))
    
    def get_signature_info(self, appimage_path: Path) -> Dict[str, Any]:
        """Get signature information without verification.
        
        Args:
            appimage_path: Path to the AppImage file
            
        Returns:
            Signature information dictionary
        """
        if not appimage_path.exists():
            raise MissingFileError("appimage", str(appimage_path))
        
        return self.verifier.get_signature_info(str(appimage_path))
