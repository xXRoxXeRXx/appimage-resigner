#!/usr/bin/env python3
"""
Custom Exceptions for AppImage Re-Signer
Provides specific exception types for different error scenarios.
"""


class AppImageResignerError(Exception):
    """Base exception for all AppImage Re-Signer errors."""
    pass


class GPGError(AppImageResignerError):
    """Exception raised for GPG-related errors."""
    pass


class GPGBinaryNotFoundError(GPGError):
    """Exception raised when GPG binary cannot be found."""

    def __init__(self, message: str = "GPG binary not found on system"):
        self.message = message
        super().__init__(self.message)


class GPGKeyError(GPGError):
    """Exception raised for GPG key-related errors."""
    pass


class GPGKeyNotFoundError(GPGKeyError):
    """Exception raised when a GPG key is not found."""

    def __init__(self, key_id: str):
        self.key_id = key_id
        self.message = f"GPG key not found: {key_id}"
        super().__init__(self.message)


class GPGKeyImportError(GPGKeyError):
    """Exception raised when GPG key import fails."""

    def __init__(self, message: str = "Failed to import GPG key"):
        self.message = message
        super().__init__(self.message)


class GPGSigningError(GPGError):
    """Exception raised when signing operation fails."""

    def __init__(self, message: str, details: str = ""):
        self.message = message
        self.details = details
        super().__init__(f"{message}: {details}" if details else message)


class GPGVerificationError(GPGError):
    """Exception raised when signature verification fails."""

    def __init__(self, message: str, status: str = ""):
        self.message = message
        self.status = status
        super().__init__(f"{message}: {status}" if status else message)


class AppImageError(AppImageResignerError):
    """Exception raised for AppImage file-related errors."""
    pass


class AppImageNotFoundError(AppImageError):
    """Exception raised when AppImage file is not found."""

    def __init__(self, path: str):
        self.path = path
        self.message = f"AppImage file not found: {path}"
        super().__init__(self.message)


class AppImageInvalidError(AppImageError):
    """Exception raised when AppImage file is invalid."""

    def __init__(self, path: str, reason: str = ""):
        self.path = path
        self.reason = reason
        self.message = f"Invalid AppImage file: {path}"
        if reason:
            self.message += f" ({reason})"
        super().__init__(self.message)


class SignatureError(AppImageResignerError):
    """Exception raised for signature-related errors."""
    pass


class SignatureNotFoundError(SignatureError):
    """Exception raised when signature is not found."""

    def __init__(self, appimage_path: str):
        self.appimage_path = appimage_path
        self.message = f"No signature found for: {appimage_path}"
        super().__init__(self.message)


class SignatureInvalidError(SignatureError):
    """Exception raised when signature is invalid."""

    def __init__(self, appimage_path: str, reason: str = ""):
        self.appimage_path = appimage_path
        self.reason = reason
        self.message = f"Invalid signature for: {appimage_path}"
        if reason:
            self.message += f" ({reason})"
        super().__init__(self.message)


class FileOperationError(AppImageResignerError):
    """Exception raised for file operation errors."""

    def __init__(self, operation: str, path: str, original_error: Exception):
        self.operation = operation
        self.path = path
        self.original_error = original_error
        self.message = f"File {operation} failed for '{path}': {original_error}"
        super().__init__(self.message)
