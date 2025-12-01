"""
Custom Exceptions for AppImage Re-Signer API.
Provides specific error types for better error handling and HTTP responses.
"""

from typing import Optional, Any, Dict
from fastapi import HTTPException, status


class AppImageResigerException(Exception):
    """Base exception for all application-specific errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail={
                "error": self.message,
                "details": self.details
            }
        )


class SessionNotFoundError(AppImageResigerException):
    """Raised when a session ID is not found."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session not found: {session_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"session_id": session_id}
        )


class SessionExpiredError(AppImageResigerException):
    """Raised when a session has expired."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session expired: {session_id}",
            status_code=status.HTTP_410_GONE,
            details={"session_id": session_id}
        )


class InvalidAppImageError(AppImageResigerException):
    """Raised when an uploaded file is not a valid AppImage."""

    def __init__(self, filename: str, reason: str):
        super().__init__(
            message=f"Invalid AppImage file: {filename}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"filename": filename, "reason": reason}
        )


class FileTooLargeError(AppImageResigerException):
    """Raised when an uploaded file exceeds size limits."""

    def __init__(self, filename: str, size: int, max_size: int):
        super().__init__(
            message=f"File too large: {filename}",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details={
                "filename": filename,
                "size_bytes": size,
                "max_size_bytes": max_size,
                "size_mb": round(size / 1024 / 1024, 2),
                "max_size_mb": round(max_size / 1024 / 1024, 2)
            }
        )


class GPGKeyNotFoundError(AppImageResigerException):
    """Raised when a GPG key is not found."""

    def __init__(self, key_id: str):
        super().__init__(
            message=f"GPG key not found: {key_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"key_id": key_id}
        )


class GPGSigningError(AppImageResigerException):
    """Raised when GPG signing fails."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"GPG signing failed: {reason}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {"reason": reason}
        )


class GPGVerificationError(AppImageResigerException):
    """Raised when GPG verification fails."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"GPG verification failed: {reason}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {"reason": reason}
        )


class GPGKeyImportError(AppImageResigerException):
    """Raised when GPG key import fails."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"GPG key import failed: {reason}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"reason": reason}
        )


class FileOperationError(AppImageResigerException):
    """Raised when a file operation fails."""

    def __init__(self, operation: str, path: str, reason: str):
        super().__init__(
            message=f"File {operation} failed: {path}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "operation": operation,
                "path": path,
                "reason": reason
            }
        )


class MissingFileError(AppImageResigerException):
    """Raised when a required file is missing."""

    def __init__(self, file_type: str, session_id: str):
        super().__init__(
            message=f"Missing {file_type} file for session: {session_id}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "file_type": file_type,
                "session_id": session_id
            }
        )


class InvalidPassphraseError(AppImageResigerException):
    """Raised when GPG passphrase is incorrect."""

    def __init__(self, key_id: str):
        super().__init__(
            message=f"Invalid passphrase for key: {key_id}",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"key_id": key_id}
        )


class ConfigurationError(AppImageResigerException):
    """Raised when there's a configuration error."""

    def __init__(self, parameter: str, reason: str):
        super().__init__(
            message=f"Configuration error: {parameter}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "parameter": parameter,
                "reason": reason
            }
        )


class GPGNotAvailableError(AppImageResigerException):
    """Raised when GPG is not available on the system."""

    def __init__(self):
        super().__init__(
            message="GPG is not available on this system",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={
                "suggestion": "Install GnuPG (gpg) or set GPG_BINARY_PATH environment variable"
            }
        )
