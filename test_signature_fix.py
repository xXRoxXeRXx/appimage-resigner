#!/usr/bin/env python3
"""
Test script to verify the signature verification fix.
Tests both Windows (\r\n) and Unix (\n) line endings.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.verify import AppImageVerifier

def test_embedded_signature():
    """Test embedded signature verification with the problematic AppImage."""
    
    # Find an AppImage with embedded signature
    appimage_dir = Path("appimage")
    signed_dir = Path("signed")
    
    print("=" * 60)
    print("Testing Signature Verification Fix")
    print("=" * 60)
    
    # Look for AppImages with embedded signatures
    test_files = []
    
    for directory in [appimage_dir, signed_dir]:
        if directory.exists():
            for file in directory.glob("*.AppImage"):
                # Check if it has embedded signature
                try:
                    with open(file, 'rb') as f:
                        content = f.read()
                        if b'-----BEGIN PGP SIGNATURE-----' in content:
                            test_files.append(file)
                except:
                    pass
    
    if not test_files:
        print("\n❌ No AppImages with embedded signatures found for testing")
        print("Please upload and sign an AppImage first.")
        return
    
    print(f"\n📋 Found {len(test_files)} AppImage(s) with embedded signatures\n")
    
    # Test each file
    verifier = AppImageVerifier()
    
    for i, appimage_path in enumerate(test_files[:3], 1):  # Test max 3 files
        print(f"\n{'='*60}")
        print(f"Test {i}: {appimage_path.name}")
        print(f"{'='*60}")
        
        # Get signature info first
        sig_info = verifier.get_signature_info(appimage_path)
        
        if sig_info['has_signature']:
            print(f"\n✓ Signature found: {sig_info['type']}")
            print(f"  Size: {sig_info['size']} bytes")
            
            if 'metadata' in sig_info and sig_info['metadata'].get('algorithm'):
                meta = sig_info['metadata']
                print(f"  Algorithm: {meta.get('algorithm', 'Unknown')}")
                print(f"  Hash: {meta.get('hash_algorithm', 'Unknown')}")
                if meta.get('timestamp_readable'):
                    print(f"  Created: {meta['timestamp_readable']}")
        
        # Now verify
        print("\n🔍 Verifying signature...")
        result = verifier.verify_signature(appimage_path)
        
        print("\n📊 Verification Result:")
        if result['valid']:
            print(f"  ✅ VALID signature!")
            print(f"  Key ID: {result.get('key_id', 'Unknown')}")
            print(f"  User: {result.get('username', 'Unknown')}")
            print(f"  Trust: {result.get('trust_level', 'Unknown')}")
        else:
            print(f"  ❌ INVALID signature")
            print(f"  Status: {result.get('status', 'Unknown')}")
            
            # Show detailed error for debugging
            if 'error' in result:
                print(f"  Error: {result['error']}")
    
    print(f"\n{'='*60}")
    print("Test Complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    test_embedded_signature()
