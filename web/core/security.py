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


# ============================================================================
# Additional Security Functions
# ============================================================================

def sanitize_path_component(component: str) -> str:
    """Sanitize a single path component (filename or directory name).

    More aggressive than sanitize_filename - removes all special characters.

    Args:
        component: Path component to sanitize

    Returns:
        Sanitized path component
    """
    import re

    # Remove any non-alphanumeric, non-underscore, non-hyphen, non-dot characters
    component = re.sub(r'[^a-zA-Z0-9._-]', '_', component)

    # Remove leading/trailing dots and spaces
    component = component.strip('. ')

    # Prevent hidden files (on Unix systems)
    if component.startswith('.'):
        component = '_' + component[1:]

    return component


def is_allowed_extension(filename: str, allowed_extensions: set) -> bool:
    """Check if filename has an allowed extension.

    Args:
        filename: Filename to check
        allowed_extensions: Set of allowed extensions (e.g., {'.AppImage', '.asc'})

    Returns:
        True if extension is allowed, False otherwise
    """
    ext = Path(filename).suffix.lower()
    return ext in {e.lower() for e in allowed_extensions}


def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent XSS.

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text
    """
    import html
    return html.escape(text, quote=True)


def validate_content_type(content_type: str, allowed_types: set) -> bool:
    """Validate Content-Type header.

    Args:
        content_type: Content-Type header value
        allowed_types: Set of allowed content types

    Returns:
        True if content type is allowed, False otherwise
    """
    # Extract main type (ignore parameters like charset)
    main_type = content_type.split(';')[0].strip().lower()
    return main_type in {t.lower() for t in allowed_types}


def get_client_ip(request) -> str:
    """Get real client IP address from request.

    Handles X-Forwarded-For header when behind proxy.

    Args:
        request: FastAPI Request object

    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header (when behind reverse proxy)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2, ...)
        # The first one is the real client IP
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (alternative header used by some proxies)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection IP
    if request.client:
        return request.client.host

    return "unknown"


def sanitize_log_message(message: str) -> str:
    """Sanitize log message to prevent log injection attacks.

    Args:
        message: Log message to sanitize

    Returns:
        Sanitized log message
    """
    # Remove newlines and carriage returns to prevent log injection
    message = message.replace('\n', ' ').replace('\r', ' ')

    # Remove null bytes
    message = message.replace('\0', '')

    # Limit length to prevent log file bloat
    max_length = 1000
    if len(message) > max_length:
        message = message[:max_length] + "... (truncated)"

    return message


def is_valid_session_id(session_id: str) -> bool:
    """Validate session ID format.

    Args:
        session_id: Session ID to validate

    Returns:
        True if valid format, False otherwise
    """
    import re

    # Session IDs should be alphanumeric with dashes/underscores
    # Length between 20 and 50 characters
    pattern = r'^[a-zA-Z0-9_-]{20,50}$'
    return bool(re.match(pattern, session_id))


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal, False otherwise
    """
    return secrets.compare_digest(a, b)
