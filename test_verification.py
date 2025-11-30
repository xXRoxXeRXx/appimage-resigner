#!/usr/bin/env python3
"""
Test script to debug signature verification
"""

import sys
from pathlib import Path
from src.verify import AppImageVerifier
from src.key_manager import GPGKeyManager

def test_verification(appimage_path):
    """Test signature verification with detailed output."""
    print("=" * 60)
    print("Testing Signature Verification")
    print("=" * 60)
    
    appimage_path = Path(appimage_path)
    
    if not appimage_path.exists():
        print(f"❌ File not found: {appimage_path}")
        return
    
    print(f"📄 AppImage: {appimage_path}")
    print(f"📊 File size: {appimage_path.stat().st_size:,} bytes")
    
    # Check for .asc file
    asc_path = Path(str(appimage_path) + ".asc")
    if asc_path.exists():
        print(f"📝 External signature: {asc_path}")
    else:
        print("⚠ No external .asc file found")
    
    # Check for embedded signature
    print("\n" + "=" * 60)
    print("Checking for embedded signature...")
    print("=" * 60)
    
    with open(appimage_path, 'rb') as f:
        content = f.read()
        if b'-----BEGIN PGP SIGNATURE-----' in content:
            sig_pos = content.rfind(b'-----BEGIN PGP SIGNATURE-----')
            print(f"✓ Found embedded signature at position: {sig_pos:,}")
            print(f"  Data size before signature: {sig_pos:,} bytes")
            sig_end = content.find(b'-----END PGP SIGNATURE-----', sig_pos)
            if sig_end > 0:
                sig_end += len(b'-----END PGP SIGNATURE-----')
                print(f"  Signature size: {sig_end - sig_pos} bytes")
                # Show first few lines of signature
                sig_text = content[sig_pos:sig_end].decode('utf-8', errors='ignore')
                lines = sig_text.split('\n')[:5]
                print("  Signature preview:")
                for line in lines:
                    print(f"    {line}")
        else:
            print("⚠ No embedded signature found")
    
    # List available keys
    print("\n" + "=" * 60)
    print("Available GPG Keys in Keyring")
    print("=" * 60)
    
    manager = GPGKeyManager()
    keys = manager.gpg.list_keys()
    if keys:
        for key in keys:
            print(f"Key ID: {key.get('keyid', 'N/A')}")
            print(f"  User: {key.get('uids', ['N/A'])[0]}")
            print(f"  Fingerprint: {key.get('fingerprint', 'N/A')}")
            print()
    else:
        print("⚠ No keys found in keyring")
    
    # Try verification
    print("=" * 60)
    print("Attempting Verification")
    print("=" * 60)
    
    verifier = AppImageVerifier()
    result = verifier.verify_signature(str(appimage_path))
    
    print("\n📋 Verification Result:")
    print("-" * 60)
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    if result.get('valid'):
        print("✅ VERIFICATION SUCCESSFUL")
    else:
        print("❌ VERIFICATION FAILED")
        if 'error' in result:
            print(f"Error: {result['error']}")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_verification.py <path_to_appimage>")
        print("\nExample:")
        print("  python test_verification.py signed/abc123_Nextcloud.AppImage")
        sys.exit(1)
    
    test_verification(sys.argv[1])
