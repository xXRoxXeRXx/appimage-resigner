"""
Security utilities for AppImage Re-Signer.
Provides security-related functions and helpers.
"""

import secrets
import hashlib
from pathlib import Path
from typing import Optional


def generate_session_id() -> str:
    """Generate a secure random session ID.
    
    Returns:
        36-character UUID-like session ID
    """
    return secrets.token_urlsafe(32)[:36]


def generate_api_key(length: int = 32) -> str:
    """Generate a secure API key.
    
    Args:
        length: Length of the API key in bytes (default: 32)
        
    Returns:
        Hex-encoded API key
    """
    return secrets.token_hex(length)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks.
    
    Removes directory separators and other dangerous characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem operations
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove parent directory references
    filename = filename.replace('..', '_')
    
    # Remove null bytes
    filename = filename.replace('\0', '')
    
    # Limit length
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
        max_name_len = 255 - len(ext)
        filename = name[:max_name_len] + ext
    
    return filename


def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Compute hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
        
    Returns:
        Hex-encoded hash digest
        
    Raises:
        ValueError: If algorithm is not supported
    """
    if algorithm not in hashlib.algorithms_available:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    hasher = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Check if target path is within base directory.
    
    Prevents path traversal attacks.
    
    Args:
        base_dir: Base directory
        target_path: Target path to check
        
    Returns:
        True if target_path is within base_dir, False otherwise
    """
    try:
        # Resolve to absolute paths
        base = base_dir.resolve()
        target = target_path.resolve()
        
        # Check if target is relative to base
        return str(target).startswith(str(base))
    except (ValueError, OSError):
        return False


def secure_delete_file(file_path: Path, passes: int = 3) -> bool:
    """Securely delete a file by overwriting before deletion.
    
    Overwrites file content with random data before deletion.
    
    Args:
        file_path: Path to the file to delete
        passes: Number of overwrite passes (default: 3)
        
    Returns:
        True if file was deleted, False otherwise
    """
    if not file_path.exists() or not file_path.is_file():
        return False
    
    try:
        file_size = file_path.stat().st_size
        
        # Overwrite with random data
        for _ in range(passes):
            with open(file_path, 'wb') as f:
                f.write(secrets.token_bytes(file_size))
                f.flush()
        
        # Delete the file
        file_path.unlink()
        return True
    except Exception:
        return False


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data for logging.
    
    Args:
        data: Sensitive string to mask
        visible_chars: Number of characters to show at start and end
        
    Returns:
        Masked string (e.g., "ABCD***WXYZ")
    """
    if len(data) <= visible_chars * 2:
        return "*" * len(data)
    
    return f"{data[:visible_chars]}***{data[-visible_chars:]}"


def obfuscate_passphrase(passphrase: str) -> None:
    """Overwrite passphrase string in memory.
    
    Note: Python strings are immutable, so this has limited effect.
    This is more of a best-practice gesture.
    
    Args:
        passphrase: Passphrase string to obfuscate
    """
    # Python strings are immutable, but we can try to help garbage collection
    try:
        import ctypes
        location = id(passphrase) + 20  # Offset to string data
        size = len(passphrase)
        ctypes.memset(location, 0, size)
    except:
        # If it fails, at least we tried
        pass


def validate_gpg_key_id(key_id: str) -> bool:
    """Validate GPG key ID format.
    
    Args:
        key_id: GPG key ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    # GPG key IDs are typically 8, 16, or 40 hex characters
    if not key_id:
        return False
    
    # Remove spaces and convert to uppercase
    key_id = key_id.replace(' ', '').upper()
    
    # Check if it's a valid hex string
    try:
        int(key_id, 16)
    except ValueError:
        return False
    
    # Check length
    return len(key_id) in [8, 16, 40]


def get_file_mime_type(file_path: Path) -> Optional[str]:
    """Get MIME type of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string or None if unable to determine
    """
    import mimetypes
    
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type
