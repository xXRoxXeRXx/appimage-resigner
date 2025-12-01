"""
Signing Service
Handles AppImage signing operations.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.resigner import AppImageResigner
from src.key_manager import GPGKeyManager
from web.core.exceptions import (
    GPGSigningError,
    GPGKeyNotFoundError,
    MissingFileError,
    InvalidPassphraseError
)
from web.core.security import obfuscate_passphrase
from web.api.models import SigningResponse, SigningStatus


class SigningService:
    """Service for handling AppImage signing operations."""

    def __init__(self, gpg_home: Optional[str] = None):
        """Initialize signing service.

        Args:
            gpg_home: Path to GPG home directory (optional)
        """
        self.resigner = AppImageResigner(gpg_home=gpg_home)
        self.key_manager = GPGKeyManager(gpg_home=gpg_home)

    def sign_appimage(
        self,
        appimage_path: Path,
        key_id: Optional[str] = None,
        passphrase: Optional[str] = None,
        embed_signature: bool = True
    ) -> SigningResponse:
        """Sign an AppImage file.

        Args:
            appimage_path: Path to the AppImage file
            key_id: GPG key ID to use (optional, uses default if None)
            passphrase: Passphrase for the key
            embed_signature: Whether to embed signature in AppImage

        Returns:
            SigningResponse with signing result

        Raises:
            MissingFileError: If AppImage file not found
            GPGKeyNotFoundError: If specified key not found
            GPGSigningError: If signing fails
        """
        # Check if file exists
        if not appimage_path.exists():
            raise MissingFileError("appimage", str(appimage_path))

        # Verify key exists if key_id specified
        if key_id:
            keys = self.key_manager.list_keys(secret=True)
            if not any(k['keyid'] == key_id for k in keys):
                raise GPGKeyNotFoundError(key_id)

        try:
            # Perform signing
            signature_path = Path(str(appimage_path) + ".asc")

            success = self.resigner.sign_appimage(
                appimage_path=str(appimage_path),
                key_id=key_id,
                passphrase=passphrase,
                output_path=str(signature_path),
                embed_signature=embed_signature
            )

            # Obfuscate passphrase in memory
            if passphrase:
                obfuscate_passphrase(passphrase)

            if not success:
                raise GPGSigningError("Signing operation failed")

            # Create response
            return SigningResponse(
                status=SigningStatus.SUCCESS,
                session_id=appimage_path.parent.name,
                filename=appimage_path.name,
                signature_file=signature_path.name if not embed_signature else None,
                key_id=key_id,
                embedded=embed_signature,
                signed_at=datetime.now(),
                message="AppImage signed successfully"
            )

        except Exception as e:
            if isinstance(e, (GPGKeyNotFoundError, MissingFileError)):
                raise

            # Check for common GPG errors
            error_str = str(e).lower()
            if "bad passphrase" in error_str or "invalid passphrase" in error_str:
                raise InvalidPassphraseError(key_id or "unknown")

            raise GPGSigningError(str(e))

    def import_key(
        self,
        key_path: Path,
        key_type: str = "private"
    ) -> Dict[str, Any]:
        """Import a GPG key from file.

        Args:
            key_path: Path to the key file
            key_type: Type of key ("public" or "private")

        Returns:
            Dictionary with import result

        Raises:
            MissingFileError: If key file not found
            GPGKeyImportError: If import fails
        """
        from web.core.exceptions import GPGKeyImportError

        if not key_path.exists():
            raise MissingFileError(key_type + "_key", str(key_path))

        try:
            success = self.key_manager.import_key(str(key_path))

            if not success:
                raise GPGKeyImportError("Key import returned failure status")

            return {
                "success": True,
                "key_type": key_type,
                "key_path": str(key_path)
            }

        except Exception as e:
            if isinstance(e, (MissingFileError, GPGKeyImportError)):
                raise
            raise GPGKeyImportError(str(e))

    def list_available_keys(self, secret: bool = False) -> list:
        """List available GPG keys.

        Args:
            secret: If True, list private keys, otherwise public keys

        Returns:
            List of key dictionaries
        """
        return self.key_manager.list_keys(secret=secret)

    def get_key_info(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific key.

        Args:
            key_id: GPG key ID

        Returns:
            Key information dictionary or None if not found
        """
        keys = self.key_manager.list_keys(secret=True)
        for key in keys:
            if key['keyid'] == key_id or key['fingerprint'] == key_id:
                return key

        # Try public keys
        keys = self.key_manager.list_keys(secret=False)
        for key in keys:
            if key['keyid'] == key_id or key['fingerprint'] == key_id:
                return key

        return None

    def remove_signature(self, appimage_path: Path) -> bool:
        """Remove existing signature from AppImage.

        Args:
            appimage_path: Path to the AppImage file

        Returns:
            True if signature was removed or didn't exist

        Raises:
            MissingFileError: If AppImage file not found
        """
        if not appimage_path.exists():
            raise MissingFileError("appimage", str(appimage_path))

        return self.resigner.remove_signature(str(appimage_path))
