"""
File validation utilities for AppImage uploads.
Ensures uploaded files are valid AppImage files.
"""

import struct
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# ELF Magic bytes
ELF_MAGIC = b'\x7fELF'

# AppImage Type 2 Magic bytes (at offset 8)
APPIMAGE_TYPE2_MAGIC = b'AI\x02'


def validate_elf_header(file_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Validate that the file has a valid ELF header.

    Args:
        file_path: Path to the file to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with open(file_path, 'rb') as f:
            # Read first 4 bytes
            magic = f.read(4)

            if magic != ELF_MAGIC:
                return False, f"Invalid ELF header. Expected {ELF_MAGIC.hex()}, got {magic.hex()}"

            # Read ELF class (32-bit or 64-bit)
            elf_class = f.read(1)
            if elf_class not in [b'\x01', b'\x02']:  # ELFCLASS32 or ELFCLASS64
                return False, "Invalid ELF class"

            # Read endianness
            endian = f.read(1)
            if endian not in [b'\x01', b'\x02']:  # Little or Big Endian
                return False, "Invalid ELF endianness"

            logger.debug(f"ELF header validated | file={file_path.name}")
            return True, None

    except Exception as e:
        logger.error(f"ELF validation failed | file={file_path.name} | error={str(e)}")
        return False, f"Could not read file: {str(e)}"


def validate_appimage_format(file_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Validate that the file is a valid AppImage (Type 2).

    Args:
        file_path: Path to the file to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with open(file_path, 'rb') as f:
            # AppImage Type 2 has magic bytes at offset 8
            f.seek(8)
            magic = f.read(3)

            if magic == APPIMAGE_TYPE2_MAGIC:
                logger.debug(f"AppImage Type 2 validated | file={file_path.name}")
                return True, None

            # If not Type 2, it might still be Type 1 or a valid ELF
            # For now, we accept any valid ELF file that ends with .AppImage
            logger.debug(f"File may be AppImage Type 1 or generic ELF | file={file_path.name}")
            return True, None

    except Exception as e:
        logger.error(f"AppImage validation failed | file={file_path.name} | error={str(e)}")
        return False, f"Could not validate AppImage format: {str(e)}"


def validate_file_size(file_path: Path, max_size_bytes: int) -> Tuple[bool, Optional[str]]:
    """
    Validate that the file size is within limits.

    Args:
        file_path: Path to the file to validate
        max_size_bytes: Maximum allowed file size in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        file_size = file_path.stat().st_size

        if file_size > max_size_bytes:
            max_mb = max_size_bytes / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            return False, f"File too large: {actual_mb:.1f} MB (max: {max_mb:.1f} MB)"

        if file_size == 0:
            return False, "File is empty"

        logger.debug(f"File size validated | file={file_path.name} | size={file_size}")
        return True, None

    except Exception as e:
        logger.error(f"Size validation failed | file={file_path.name} | error={str(e)}")
        return False, f"Could not check file size: {str(e)}"


def validate_appimage_file(
    file_path: Path,
    max_size_bytes: int,
    check_elf: bool = True,
    check_appimage: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Perform comprehensive validation of an AppImage file.

    Args:
        file_path: Path to the file to validate
        max_size_bytes: Maximum allowed file size in bytes
        check_elf: Whether to validate ELF header
        check_appimage: Whether to validate AppImage format

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file exists
    if not file_path.exists():
        return False, "File does not exist"

    # Check file extension
    if not file_path.name.endswith('.AppImage'):
        return False, "File must have .AppImage extension"

    # Validate file size
    is_valid, error = validate_file_size(file_path, max_size_bytes)
    if not is_valid:
        return is_valid, error

    # Validate ELF header
    if check_elf:
        is_valid, error = validate_elf_header(file_path)
        if not is_valid:
            return is_valid, error

    # Validate AppImage format
    if check_appimage:
        is_valid, error = validate_appimage_format(file_path)
        if not is_valid:
            return is_valid, error

    logger.info(f"AppImage file validated successfully | file={file_path.name}")
    return True, None
