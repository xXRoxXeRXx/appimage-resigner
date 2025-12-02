#!/usr/bin/env python3
"""
GPG Utility Functions
Common utilities for GPG operations used across the application.
"""

import os
import shutil
from typing import Optional

import gnupg  # type: ignore[import-untyped]


def find_gpg_binary() -> Optional[str]:
    """Find GPG binary on the system.

    Searches for GPG in the system PATH first, then checks common
    installation locations on Windows.

    Returns:
        Optional[str]: Path to GPG binary if found, None otherwise
    """
    # Check if gpg is in PATH (works on all platforms)
    gpg_in_path = shutil.which('gpg')
    if gpg_in_path:
        return gpg_in_path

    # Common GPG locations on Windows
    gpg_paths = [
        r"C:\Program Files (x86)\GnuPG\bin\gpg.exe",
        r"C:\Program Files\GnuPG\bin\gpg.exe",
        r"C:\Program Files (x86)\Gpg4win\bin\gpg.exe",
        r"C:\Program Files\Gpg4win\bin\gpg.exe",
    ]

    # Check common locations
    for path in gpg_paths:
        if os.path.exists(path):
            return path

    return None


def create_gpg_instance(gpg_home: Optional[str] = None) -> gnupg.GPG:
    """Create a GPG instance with automatic binary detection.

    Args:
        gpg_home: Path to GPG home directory. Defaults to ~/.gnupg

    Returns:
        gnupg.GPG: Configured GPG instance

    Raises:
        RuntimeError: If GPG binary cannot be found
    """
    gpg_binary = find_gpg_binary()

    if gpg_binary:
        if gpg_home:
            return gnupg.GPG(gnupghome=gpg_home, gpgbinary=gpg_binary)
        return gnupg.GPG(gpgbinary=gpg_binary)
    else:
        if gpg_home:
            return gnupg.GPG(gnupghome=gpg_home)
        return gnupg.GPG()
