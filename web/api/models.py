"""
Pydantic Models for API Request/Response Validation
Provides type-safe data models for the AppImage Re-Signer API.
"""

from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict
)


# Enums
class SignatureStatus(str, Enum):
    """Signature verification status."""
    VALID = "valid"
    INVALID = "invalid"
    NO_SIGNATURE = "no_signature"
    ERROR = "error"


class SigningStatus(str, Enum):
    """Signing operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


# Request Models
class SignRequest(BaseModel):
    """Request model for signing an AppImage."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    session_id: str = Field(
        ...,
        description="Unique session identifier",
        min_length=32,
        max_length=128,
        pattern=r'^[a-f0-9\-]+$'
    )

    key_id: Optional[str] = Field(
        None,
        description="GPG key ID to use for signing (optional if importing key)",
        min_length=8,
        max_length=40,
        pattern=r'^[A-F0-9]+$'
    )

    passphrase: str = Field(
        "",
        description="Passphrase for the GPG key (can be empty for keys without passphrase)",
        max_length=1024
    )

    embed_signature: bool = Field(
        True,
        description="Whether to embed signature in AppImage or create detached .asc file"
    )

    @field_validator('key_id')
    @classmethod
    def normalize_key_id(cls, v: Optional[str]) -> Optional[str]:
        """Normalize key ID to uppercase."""
        if v:
            return v.upper().strip()
        return v

    @model_validator(mode='after')
    def validate_sign_request(self) -> 'SignRequest':
        """Validate that we have either a key_id or will import a key."""
        # This will be extended when we add key import to the request
        return self


class VerifyRequest(BaseModel):
    """Request model for verifying an AppImage signature."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    session_id: str = Field(
        ...,
        description="Unique session identifier",
        min_length=32,
        max_length=128,
        pattern=r'^[a-f0-9\-]+$'
    )

    import_key: bool = Field(
        False,
        description="Whether to import the public key from uploaded key file"
    )


class KeyImportRequest(BaseModel):
    """Request model for importing a GPG key."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    session_id: str = Field(
        ...,
        description="Unique session identifier",
        min_length=32,
        max_length=128,
        pattern=r'^[a-f0-9\-]+$'
    )

    key_type: str = Field(
        "public",
        description="Type of key to import",
        pattern=r'^(public|private|secret)$'
    )


# Response Models
class UploadResponse(BaseModel):
    """Response model for file upload."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "filename": "MyApp-1.0.0-x86_64.AppImage",
                "size": 52428800,
                "uploaded_at": "2025-12-01T10:30:00Z"
            }
        }
    )

    session_id: str = Field(..., description="Unique session identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes", ge=0)
    uploaded_at: datetime = Field(
        default_factory=datetime.now,
        description="Upload timestamp"
    )


class SigningResponse(BaseModel):
    """Response model for signing operation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "filename": "MyApp-1.0.0-x86_64.AppImage",
                "signature_file": "MyApp-1.0.0-x86_64.AppImage.asc",
                "key_id": "1234567890ABCDEF",
                "embedded": True,
                "signed_at": "2025-12-01T10:35:00Z"
            }
        }
    )

    status: SigningStatus = Field(..., description="Signing operation status")
    session_id: str = Field(..., description="Session identifier")
    filename: str = Field(..., description="Signed AppImage filename")
    signature_file: Optional[str] = Field(
        None,
        description="Detached signature filename (if embedded=False)"
    )
    key_id: Optional[str] = Field(None, description="Key ID used for signing")
    embedded: bool = Field(..., description="Whether signature is embedded")
    signed_at: datetime = Field(
        default_factory=datetime.now,
        description="Signing timestamp"
    )
    message: Optional[str] = Field(None, description="Additional information")
    error: Optional[str] = Field(None, description="Error message if status=failed")


class VerificationResponse(BaseModel):
    """Response model for signature verification."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "valid",
                "filename": "MyApp-1.0.0-x86_64.AppImage",
                "signed_by": "John Doe <john@example.com>",
                "key_id": "1234567890ABCDEF",
                "fingerprint": "ABCD 1234 EFGH 5678 IJKL 9012 MNOP 3456 QRST 7890",
                "timestamp": "2025-12-01T10:35:00Z",
                "trust_level": "ultimate",
                "signature_type": "embedded"
            }
        }
    )

    status: SignatureStatus = Field(..., description="Verification status")
    filename: str = Field(..., description="Verified filename")
    signed_by: Optional[str] = Field(None, description="Signer identity")
    key_id: Optional[str] = Field(None, description="Signing key ID")
    fingerprint: Optional[str] = Field(None, description="Key fingerprint")
    timestamp: Optional[datetime] = Field(None, description="Signature timestamp")
    trust_level: Optional[str] = Field(None, description="Key trust level")
    signature_type: Optional[str] = Field(
        None,
        description="Type of signature (embedded or detached)"
    )
    message: Optional[str] = Field(None, description="Verification details")
    error: Optional[str] = Field(None, description="Error message if verification failed")


class KeyInfo(BaseModel):
    """Information about a GPG key."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key_id": "1234567890ABCDEF",
                "fingerprint": "ABCD 1234 EFGH 5678 IJKL 9012 MNOP 3456 QRST 7890",
                "uids": ["John Doe <john@example.com>"],
                "type": "RSA",
                "length": 4096,
                "creation_date": "2024-01-01T00:00:00Z",
                "expiration_date": "2026-01-01T00:00:00Z",
                "trust": "ultimate"
            }
        }
    )

    key_id: str = Field(..., description="Key ID")
    fingerprint: str = Field(..., description="Key fingerprint")
    uids: List[str] = Field(default_factory=list, description="User IDs")
    type: str = Field(..., description="Key type (RSA, DSA, etc.)")
    length: int = Field(..., description="Key length in bits", gt=0)
    creation_date: Optional[datetime] = Field(None, description="Creation date")
    expiration_date: Optional[datetime] = Field(None, description="Expiration date")
    trust: Optional[str] = Field(None, description="Trust level")
    has_secret: bool = Field(False, description="Whether secret key is available")

    @field_validator('fingerprint')
    @classmethod
    def normalize_fingerprint(cls, v: str) -> str:
        """Normalize fingerprint format."""
        # Remove spaces and convert to uppercase
        normalized = v.replace(' ', '').upper()
        # Add spaces every 4 characters for readability
        return ' '.join(normalized[i:i+4] for i in range(0, len(normalized), 4))


class KeyListResponse(BaseModel):
    """Response model for listing GPG keys."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "keys": [
                    {
                        "key_id": "1234567890ABCDEF",
                        "fingerprint": "ABCD 1234 EFGH 5678",
                        "uids": ["John Doe <john@example.com>"]
                    }
                ],
                "count": 1
            }
        }
    )

    keys: List[KeyInfo] = Field(default_factory=list, description="List of keys")
    count: int = Field(..., description="Number of keys", ge=0)


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "2.0.0",
                "gpg_available": True,
                "timestamp": "2025-12-01T10:00:00Z",
                "uptime_seconds": 3600,
                "active_sessions": 5,
                "disk_usage": {"uploads": 1024000, "signed": 2048000}
            }
        }
    )

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")
    gpg_available: bool = Field(..., description="Whether GPG is available")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Health check timestamp"
    )
    uptime_seconds: Optional[int] = Field(None, description="Application uptime", ge=0)
    active_sessions: Optional[int] = Field(None, description="Number of active sessions", ge=0)
    disk_usage: Optional[Dict[str, int]] = Field(
        None,
        description="Disk usage statistics"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Invalid AppImage file",
                "detail": "File does not have ELF magic bytes",
                "status_code": 400,
                "timestamp": "2025-12-01T10:00:00Z"
            }
        }
    )

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code", ge=100, lt=600)
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Error timestamp"
    )
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")


class SessionInfoResponse(BaseModel):
    """Response model for session information."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "created_at": "2025-12-01T10:00:00Z",
                "expires_at": "2025-12-02T10:00:00Z",
                "appimage_file": "MyApp-1.0.0-x86_64.AppImage",
                "has_key": True,
                "is_signed": False
            }
        }
    )

    session_id: str = Field(..., description="Session identifier")
    created_at: datetime = Field(..., description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiration time")
    appimage_file: Optional[str] = Field(None, description="Uploaded AppImage filename")
    key_file: Optional[str] = Field(None, description="Uploaded key filename")
    has_key: bool = Field(False, description="Whether a key is uploaded")
    is_signed: bool = Field(False, description="Whether AppImage is signed")
    signed_file: Optional[str] = Field(None, description="Signed AppImage filename")


# Utility Models
class FileMetadata(BaseModel):
    """Metadata about an uploaded file."""

    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes", ge=0)
    mime_type: Optional[str] = Field(None, description="MIME type")
    md5: Optional[str] = Field(None, description="MD5 checksum")
    sha256: Optional[str] = Field(None, description="SHA256 checksum")
    uploaded_at: datetime = Field(
        default_factory=datetime.now,
        description="Upload timestamp"
    )

    @field_validator('size')
    @classmethod
    def validate_size(cls, v: int) -> int:
        """Validate file size is reasonable."""
        if v > 5 * 1024 * 1024 * 1024:  # 5GB
            raise ValueError("File size exceeds maximum allowed (5GB)")
        return v


class AppImageInfo(BaseModel):
    """Information extracted from an AppImage file."""

    filename: str = Field(..., description="AppImage filename")
    size: int = Field(..., description="File size in bytes", ge=0)
    elf_class: Optional[str] = Field(None, description="ELF class (32-bit or 64-bit)")
    architecture: Optional[str] = Field(None, description="CPU architecture")
    has_embedded_signature: bool = Field(
        False,
        description="Whether AppImage has embedded signature"
    )
    signature_offset: Optional[int] = Field(
        None,
        description="Offset of embedded signature",
        ge=0
    )
    signature_length: Optional[int] = Field(
        None,
        description="Length of embedded signature",
        ge=0
    )
